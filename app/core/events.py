"""
Event-Driven Architecture for RISKCAST.

Production-grade event system with:
- In-memory event bus (development)
- Redis pub/sub (production)
- Dead letter queue
- Event replay
- Event sourcing support
- Saga pattern for distributed transactions
"""

import asyncio
import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable, TypeVar, Generic, Awaitable
from enum import Enum
import traceback

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

T = TypeVar("T", bound="Event")


# ============================================================================
# EVENT DEFINITIONS
# ============================================================================


class EventType(str, Enum):
    """Event types in the system."""
    
    # Signal events
    SIGNAL_DETECTED = "signal.detected"
    SIGNAL_VALIDATED = "signal.validated"
    SIGNAL_CONFIRMED = "signal.confirmed"
    SIGNAL_EXPIRED = "signal.expired"
    
    # Decision events
    DECISION_GENERATED = "decision.generated"
    DECISION_DELIVERED = "decision.delivered"
    DECISION_ACKNOWLEDGED = "decision.acknowledged"
    DECISION_EXPIRED = "decision.expired"
    
    # Customer events
    CUSTOMER_CREATED = "customer.created"
    CUSTOMER_UPDATED = "customer.updated"
    SHIPMENT_CREATED = "shipment.created"
    SHIPMENT_UPDATED = "shipment.updated"
    
    # Alert events
    ALERT_SENT = "alert.sent"
    ALERT_DELIVERED = "alert.delivered"
    ALERT_FAILED = "alert.failed"
    ALERT_RETRY = "alert.retry"
    
    # System events
    SYSTEM_HEALTH_CHECK = "system.health_check"
    SYSTEM_ERROR = "system.error"


class Event(BaseModel):
    """Base event class."""
    
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    payload: Dict[str, Any] = Field(default_factory=dict)
    version: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump(mode="json")
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Create from dictionary."""
        return cls(**data)


class SignalDetectedEvent(Event):
    """Event when a new signal is detected."""
    
    event_type: EventType = EventType.SIGNAL_DETECTED
    
    # Signal details in payload
    # payload = {signal_id, source, probability, chokepoint}


class DecisionGeneratedEvent(Event):
    """Event when a decision is generated."""
    
    event_type: EventType = EventType.DECISION_GENERATED
    
    # Decision details in payload
    # payload = {decision_id, customer_id, signal_id, severity, action_type}


class AlertSentEvent(Event):
    """Event when an alert is sent."""
    
    event_type: EventType = EventType.ALERT_SENT
    
    # Alert details in payload
    # payload = {alert_id, customer_id, channel, decision_id}


# ============================================================================
# EVENT HANDLER
# ============================================================================


EventHandler = Callable[[Event], Awaitable[None]]


@dataclass
class HandlerRegistration:
    """Handler registration details."""
    
    handler: EventHandler
    event_types: List[EventType]
    handler_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    retry_count: int = 3
    timeout_seconds: int = 30
    created_at: datetime = field(default_factory=datetime.utcnow)


# ============================================================================
# DEAD LETTER QUEUE
# ============================================================================


@dataclass
class DeadLetterEntry:
    """Entry in the dead letter queue."""
    
    event: Event
    error: str
    error_traceback: str
    handler_id: str
    attempt_count: int
    first_failure: datetime = field(default_factory=datetime.utcnow)
    last_failure: datetime = field(default_factory=datetime.utcnow)


class DeadLetterQueue:
    """
    Dead Letter Queue for failed events.
    
    Stores events that failed processing for later retry or manual intervention.
    """
    
    def __init__(self, max_size: int = 10000):
        self._queue: Dict[str, DeadLetterEntry] = {}
        self._max_size = max_size
    
    async def add(
        self,
        event: Event,
        error: Exception,
        handler_id: str,
        attempt_count: int,
    ) -> str:
        """Add event to DLQ."""
        key = f"{event.event_id}:{handler_id}"
        
        if key in self._queue:
            # Update existing entry
            entry = self._queue[key]
            entry.last_failure = datetime.utcnow()
            entry.attempt_count = attempt_count
            entry.error = str(error)
        else:
            # Check size limit
            if len(self._queue) >= self._max_size:
                # Remove oldest
                oldest_key = min(self._queue.keys(), key=lambda k: self._queue[k].first_failure)
                del self._queue[oldest_key]
            
            entry = DeadLetterEntry(
                event=event,
                error=str(error),
                error_traceback=traceback.format_exc(),
                handler_id=handler_id,
                attempt_count=attempt_count,
            )
            self._queue[key] = entry
        
        logger.warning(
            "event_dead_lettered",
            event_id=event.event_id,
            event_type=event.event_type,
            handler_id=handler_id,
            attempt_count=attempt_count,
            error=str(error),
        )
        
        return key
    
    async def get(self, key: str) -> Optional[DeadLetterEntry]:
        """Get entry by key."""
        return self._queue.get(key)
    
    async def remove(self, key: str) -> bool:
        """Remove entry from DLQ."""
        if key in self._queue:
            del self._queue[key]
            return True
        return False
    
    async def list_entries(
        self,
        event_type: Optional[EventType] = None,
        limit: int = 100,
    ) -> List[DeadLetterEntry]:
        """List DLQ entries."""
        entries = list(self._queue.values())
        
        if event_type:
            entries = [e for e in entries if e.event.event_type == event_type]
        
        # Sort by last failure
        entries.sort(key=lambda e: e.last_failure, reverse=True)
        
        return entries[:limit]
    
    async def retry(self, key: str, bus: "EventBus") -> bool:
        """Retry processing a dead-lettered event."""
        entry = self._queue.get(key)
        if not entry:
            return False
        
        # Publish back to bus
        await bus.publish(entry.event)
        
        # Remove from DLQ
        await self.remove(key)
        
        logger.info(
            "dlq_retry",
            event_id=entry.event.event_id,
            handler_id=entry.handler_id,
        )
        
        return True
    
    async def count(self) -> int:
        """Get DLQ size."""
        return len(self._queue)


# ============================================================================
# EVENT BUS
# ============================================================================


class EventBus(ABC):
    """Abstract event bus interface."""
    
    @abstractmethod
    async def publish(self, event: Event) -> None:
        """Publish an event."""
        pass
    
    @abstractmethod
    def subscribe(
        self,
        handler: EventHandler,
        event_types: List[EventType],
        **options,
    ) -> str:
        """Subscribe to events. Returns handler ID."""
        pass
    
    @abstractmethod
    def unsubscribe(self, handler_id: str) -> bool:
        """Unsubscribe a handler."""
        pass
    
    @abstractmethod
    async def start(self) -> None:
        """Start the event bus."""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the event bus."""
        pass


class InMemoryEventBus(EventBus):
    """
    In-memory event bus for development and testing.
    
    Supports:
    - Async event handling
    - Handler retry
    - Dead letter queue
    - Event replay (last N events)
    """
    
    def __init__(
        self,
        max_retry: int = 3,
        retry_delay_seconds: float = 1.0,
        event_history_size: int = 1000,
    ):
        self._handlers: Dict[str, HandlerRegistration] = {}
        self._dlq = DeadLetterQueue()
        self._event_history: List[Event] = []
        self._history_size = event_history_size
        self._max_retry = max_retry
        self._retry_delay = retry_delay_seconds
        self._running = False
        self._lock = asyncio.Lock()
    
    async def start(self) -> None:
        """Start the event bus."""
        self._running = True
        logger.info("event_bus_started", type="in_memory")
    
    async def stop(self) -> None:
        """Stop the event bus."""
        self._running = False
        logger.info("event_bus_stopped")
    
    async def publish(self, event: Event) -> None:
        """Publish an event to all subscribers."""
        if not self._running:
            logger.warning("event_published_to_stopped_bus", event_id=event.event_id)
        
        # Store in history
        async with self._lock:
            self._event_history.append(event)
            if len(self._event_history) > self._history_size:
                self._event_history = self._event_history[-self._history_size:]
        
        logger.info(
            "event_published",
            event_id=event.event_id,
            event_type=event.event_type,
        )
        
        # Find matching handlers
        matching_handlers = [
            h for h in self._handlers.values()
            if event.event_type in h.event_types
        ]
        
        # Execute handlers concurrently
        tasks = [
            self._execute_handler(handler, event)
            for handler in matching_handlers
        ]
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _execute_handler(
        self,
        registration: HandlerRegistration,
        event: Event,
    ) -> None:
        """Execute a handler with retry logic."""
        for attempt in range(registration.retry_count):
            try:
                # Execute with timeout
                await asyncio.wait_for(
                    registration.handler(event),
                    timeout=registration.timeout_seconds,
                )
                
                logger.debug(
                    "handler_executed",
                    handler_id=registration.handler_id,
                    event_id=event.event_id,
                )
                return
                
            except asyncio.TimeoutError as e:
                logger.warning(
                    "handler_timeout",
                    handler_id=registration.handler_id,
                    event_id=event.event_id,
                    attempt=attempt + 1,
                )
                if attempt == registration.retry_count - 1:
                    await self._dlq.add(event, e, registration.handler_id, attempt + 1)
                    
            except Exception as e:
                logger.error(
                    "handler_error",
                    handler_id=registration.handler_id,
                    event_id=event.event_id,
                    attempt=attempt + 1,
                    error=str(e),
                )
                
                if attempt < registration.retry_count - 1:
                    # Exponential backoff
                    delay = self._retry_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                else:
                    await self._dlq.add(event, e, registration.handler_id, attempt + 1)
    
    def subscribe(
        self,
        handler: EventHandler,
        event_types: List[EventType],
        **options,
    ) -> str:
        """Subscribe to events."""
        registration = HandlerRegistration(
            handler=handler,
            event_types=event_types,
            retry_count=options.get("retry_count", self._max_retry),
            timeout_seconds=options.get("timeout_seconds", 30),
        )
        
        self._handlers[registration.handler_id] = registration
        
        logger.info(
            "handler_subscribed",
            handler_id=registration.handler_id,
            event_types=[et.value for et in event_types],
        )
        
        return registration.handler_id
    
    def unsubscribe(self, handler_id: str) -> bool:
        """Unsubscribe a handler."""
        if handler_id in self._handlers:
            del self._handlers[handler_id]
            logger.info("handler_unsubscribed", handler_id=handler_id)
            return True
        return False
    
    async def replay_events(
        self,
        event_types: Optional[List[EventType]] = None,
        since: Optional[datetime] = None,
    ) -> int:
        """Replay historical events."""
        events = self._event_history
        
        if event_types:
            events = [e for e in events if e.event_type in event_types]
        
        if since:
            events = [e for e in events if e.timestamp >= since]
        
        for event in events:
            await self.publish(event)
        
        logger.info("events_replayed", count=len(events))
        return len(events)
    
    @property
    def dead_letter_queue(self) -> DeadLetterQueue:
        """Access the dead letter queue."""
        return self._dlq


# ============================================================================
# REDIS EVENT BUS
# ============================================================================


class RedisEventBus(EventBus):
    """
    Redis-based event bus for production.
    
    Uses Redis Pub/Sub for event distribution.
    """
    
    def __init__(
        self,
        redis_url: str,
        channel_prefix: str = "riskcast:events",
        max_retry: int = 3,
    ):
        self._redis_url = redis_url
        self._channel_prefix = channel_prefix
        self._max_retry = max_retry
        self._handlers: Dict[str, HandlerRegistration] = {}
        self._dlq = DeadLetterQueue()
        self._running = False
        self._redis = None
        self._pubsub = None
        self._listen_task = None
    
    async def start(self) -> None:
        """Start the Redis event bus."""
        import redis.asyncio as redis
        
        self._redis = redis.from_url(self._redis_url)
        self._pubsub = self._redis.pubsub()
        
        # Subscribe to all event channels
        await self._pubsub.psubscribe(f"{self._channel_prefix}:*")
        
        # Start listening task
        self._running = True
        self._listen_task = asyncio.create_task(self._listen())
        
        logger.info("redis_event_bus_started", channel_prefix=self._channel_prefix)
    
    async def stop(self) -> None:
        """Stop the Redis event bus."""
        self._running = False
        
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()
        
        if self._redis:
            await self._redis.close()
        
        logger.info("redis_event_bus_stopped")
    
    async def _listen(self) -> None:
        """Listen for events."""
        while self._running:
            try:
                message = await self._pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )
                
                if message and message["type"] == "pmessage":
                    data = json.loads(message["data"])
                    event = Event.from_dict(data)
                    await self._process_event(event)
                    
            except Exception as e:
                logger.error("redis_listen_error", error=str(e))
                await asyncio.sleep(1)
    
    async def _process_event(self, event: Event) -> None:
        """Process received event."""
        matching_handlers = [
            h for h in self._handlers.values()
            if event.event_type in h.event_types
        ]
        
        for handler in matching_handlers:
            try:
                await handler.handler(event)
            except Exception as e:
                logger.error(
                    "handler_error",
                    handler_id=handler.handler_id,
                    event_id=event.event_id,
                    error=str(e),
                )
                await self._dlq.add(event, e, handler.handler_id, 1)
    
    async def publish(self, event: Event) -> None:
        """Publish event to Redis."""
        channel = f"{self._channel_prefix}:{event.event_type.value}"
        data = json.dumps(event.to_dict())
        
        await self._redis.publish(channel, data)
        
        logger.info(
            "event_published",
            event_id=event.event_id,
            event_type=event.event_type,
            channel=channel,
        )
    
    def subscribe(
        self,
        handler: EventHandler,
        event_types: List[EventType],
        **options,
    ) -> str:
        """Subscribe to events."""
        registration = HandlerRegistration(
            handler=handler,
            event_types=event_types,
            retry_count=options.get("retry_count", self._max_retry),
            timeout_seconds=options.get("timeout_seconds", 30),
        )
        
        self._handlers[registration.handler_id] = registration
        
        logger.info(
            "handler_subscribed",
            handler_id=registration.handler_id,
            event_types=[et.value for et in event_types],
        )
        
        return registration.handler_id
    
    def unsubscribe(self, handler_id: str) -> bool:
        """Unsubscribe a handler."""
        if handler_id in self._handlers:
            del self._handlers[handler_id]
            return True
        return False
    
    @property
    def dead_letter_queue(self) -> DeadLetterQueue:
        """Access the dead letter queue."""
        return self._dlq


# ============================================================================
# SAGA PATTERN
# ============================================================================


class SagaStep(ABC):
    """Abstract saga step."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the step."""
        pass
    
    @abstractmethod
    async def compensate(self, context: Dict[str, Any]) -> None:
        """Compensate (rollback) the step."""
        pass


class Saga:
    """
    Saga pattern implementation.
    
    Manages distributed transactions with compensating actions.
    """
    
    def __init__(self, name: str, steps: List[SagaStep]):
        self._name = name
        self._steps = steps
        self._completed_steps: List[SagaStep] = []
    
    async def execute(self, initial_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute the saga."""
        context = initial_context or {}
        self._completed_steps = []
        
        try:
            for step in self._steps:
                logger.info(
                    "saga_step_executing",
                    saga=self._name,
                    step=step.name,
                )
                
                result = await step.execute(context)
                context.update(result)
                self._completed_steps.append(step)
                
                logger.info(
                    "saga_step_completed",
                    saga=self._name,
                    step=step.name,
                )
            
            logger.info("saga_completed", saga=self._name)
            return context
            
        except Exception as e:
            logger.error(
                "saga_failed",
                saga=self._name,
                error=str(e),
            )
            await self._compensate(context)
            raise
    
    async def _compensate(self, context: Dict[str, Any]) -> None:
        """Run compensating actions for completed steps."""
        for step in reversed(self._completed_steps):
            try:
                logger.info(
                    "saga_compensating",
                    saga=self._name,
                    step=step.name,
                )
                await step.compensate(context)
            except Exception as e:
                logger.error(
                    "saga_compensation_failed",
                    saga=self._name,
                    step=step.name,
                    error=str(e),
                )


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================


_event_bus: Optional[EventBus] = None


async def init_event_bus(use_redis: bool = False, redis_url: str = None) -> EventBus:
    """Initialize global event bus."""
    global _event_bus
    
    if use_redis and redis_url:
        _event_bus = RedisEventBus(redis_url)
    else:
        _event_bus = InMemoryEventBus()
    
    await _event_bus.start()
    return _event_bus


async def close_event_bus() -> None:
    """Close event bus."""
    global _event_bus
    if _event_bus:
        await _event_bus.stop()
        _event_bus = None


def get_event_bus() -> EventBus:
    """Get global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = InMemoryEventBus()
    return _event_bus

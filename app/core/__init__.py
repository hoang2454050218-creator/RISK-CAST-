"""
RISKCAST Core Infrastructure Module.

This module provides all foundational infrastructure components:
- Caching (Redis)
- Circuit breakers
- Encryption & security
- Event bus
- Tracing & observability
- Database connections

Usage:
    from app.core import (
        init_core_services,
        close_core_services,
        get_cache,
        get_event_bus,
        get_tracer,
    )
"""

import asyncio
from typing import Optional

import structlog

from app.core.cache import (
    RedisCache,
    RedisRateLimiter,
    RedisIdempotencyStore,
    init_cache,
    close_cache,
    get_cache,
    get_rate_limiter,
    get_idempotency_store,
    cached,
)

from app.core.circuit_breaker import (
    CircuitBreaker,
    CircuitConfig,
    CircuitState,
    CircuitOpenError,
    CircuitBreakerRegistry,
    get_registry,
    get_circuit_breaker,
    circuit_breaker,
    get_polymarket_breaker,
    get_database_breaker,
    get_redis_breaker,
    get_whatsapp_breaker,
)

from app.core.encryption import (
    FieldEncryptor,
    EncryptedValue,
    SecureHasher,
    PIIProtector,
    EncryptionError,
    DecryptionError,
    init_encryption,
    get_encryptor,
    get_hasher,
    get_pii_protector,
)

from app.core.events import (
    Event,
    EventType,
    EventBus,
    InMemoryEventBus,
    RedisEventBus,
    DeadLetterQueue,
    Saga,
    SagaStep,
    SignalDetectedEvent,
    DecisionGeneratedEvent,
    AlertSentEvent,
    init_event_bus,
    close_event_bus,
    get_event_bus,
)

from app.core.tracing import (
    Tracer,
    Span,
    SpanContext,
    SpanKind,
    SpanStatus,
    MetricsCollector,
    init_tracing,
    close_tracing,
    get_tracer,
    get_metrics,
    get_current_span,
    get_current_trace_id,
    trace,
    tracing_middleware,
)

logger = structlog.get_logger(__name__)


# ============================================================================
# GLOBAL INITIALIZATION
# ============================================================================


_initialized = False


async def init_core_services(
    redis_url: str = None,
    encryption_key: str = None,
    use_redis_events: bool = False,
    service_name: str = "riskcast",
) -> None:
    """
    Initialize all core services.
    
    This should be called during application startup.
    
    Args:
        redis_url: Redis connection URL
        encryption_key: Master encryption key (base64)
        use_redis_events: Whether to use Redis for events
        service_name: Service name for tracing
    """
    global _initialized
    
    if _initialized:
        logger.warning("core_services_already_initialized")
        return
    
    logger.info("initializing_core_services")
    
    try:
        # Initialize components in order
        
        # 1. Tracing (first, to trace other initialization)
        await init_tracing(service_name=service_name)
        logger.info("tracing_initialized")
        
        # 2. Cache (Redis)
        cache = await init_cache()
        logger.info("cache_initialized", connected=cache._connected)
        
        # 3. Encryption
        init_encryption(encryption_key)
        logger.info("encryption_initialized")
        
        # 4. Event bus
        await init_event_bus(
            use_redis=use_redis_events,
            redis_url=redis_url,
        )
        logger.info("event_bus_initialized", type="redis" if use_redis_events else "memory")
        
        # 5. Circuit breakers (auto-initialize on first use)
        _ = get_registry()
        logger.info("circuit_breakers_initialized")
        
        _initialized = True
        logger.info("core_services_ready")
        
    except Exception as e:
        logger.error("core_services_initialization_failed", error=str(e))
        raise


async def close_core_services() -> None:
    """
    Close all core services.
    
    This should be called during application shutdown.
    """
    global _initialized
    
    if not _initialized:
        return
    
    logger.info("closing_core_services")
    
    try:
        # Close in reverse order
        await close_event_bus()
        await close_cache()
        await close_tracing()
        
        _initialized = False
        logger.info("core_services_closed")
        
    except Exception as e:
        logger.error("core_services_close_failed", error=str(e))


def is_initialized() -> bool:
    """Check if core services are initialized."""
    return _initialized


# ============================================================================
# HEALTH CHECK
# ============================================================================


async def get_core_health() -> dict:
    """
    Get health status of all core services.
    
    Returns:
        Dictionary with health status of each component
    """
    health = {
        "status": "healthy",
        "components": {},
    }
    
    # Check cache
    try:
        cache = get_cache()
        cache_health = await cache.health_check()
        health["components"]["cache"] = cache_health
        if not cache_health.get("connected"):
            health["status"] = "degraded"
    except Exception as e:
        health["components"]["cache"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "degraded"
    
    # Check circuit breakers
    try:
        registry = get_registry()
        breaker_health = registry.get_health()
        
        open_breakers = [
            name for name, info in breaker_health.items()
            if info["state"] == "open"
        ]
        
        health["components"]["circuit_breakers"] = {
            "status": "healthy" if not open_breakers else "degraded",
            "open_circuits": open_breakers,
            "total_circuits": len(breaker_health),
        }
        
        if open_breakers:
            health["status"] = "degraded"
    except Exception as e:
        health["components"]["circuit_breakers"] = {"status": "unhealthy", "error": str(e)}
    
    # Check encryption
    try:
        encryptor = get_encryptor()
        # Simple test
        test_encrypted = encryptor.encrypt_string("test", "health_check")
        test_decrypted = encryptor.decrypt_string(test_encrypted, "health_check")
        health["components"]["encryption"] = {
            "status": "healthy" if test_decrypted == "test" else "unhealthy",
        }
    except Exception as e:
        health["components"]["encryption"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "degraded"
    
    # Check event bus
    try:
        event_bus = get_event_bus()
        health["components"]["event_bus"] = {
            "status": "healthy",
            "type": type(event_bus).__name__,
        }
    except Exception as e:
        health["components"]["event_bus"] = {"status": "unhealthy", "error": str(e)}
    
    return health


# ============================================================================
# EXPORTS
# ============================================================================


__all__ = [
    # Initialization
    "init_core_services",
    "close_core_services",
    "is_initialized",
    "get_core_health",
    
    # Cache
    "RedisCache",
    "RedisRateLimiter",
    "RedisIdempotencyStore",
    "init_cache",
    "close_cache",
    "get_cache",
    "get_rate_limiter",
    "get_idempotency_store",
    "cached",
    
    # Circuit Breakers
    "CircuitBreaker",
    "CircuitConfig",
    "CircuitState",
    "CircuitOpenError",
    "CircuitBreakerRegistry",
    "get_registry",
    "get_circuit_breaker",
    "circuit_breaker",
    "get_polymarket_breaker",
    "get_database_breaker",
    "get_redis_breaker",
    "get_whatsapp_breaker",
    
    # Encryption
    "FieldEncryptor",
    "EncryptedValue",
    "SecureHasher",
    "PIIProtector",
    "EncryptionError",
    "DecryptionError",
    "init_encryption",
    "get_encryptor",
    "get_hasher",
    "get_pii_protector",
    
    # Events
    "Event",
    "EventType",
    "EventBus",
    "InMemoryEventBus",
    "RedisEventBus",
    "DeadLetterQueue",
    "Saga",
    "SagaStep",
    "SignalDetectedEvent",
    "DecisionGeneratedEvent",
    "AlertSentEvent",
    "init_event_bus",
    "close_event_bus",
    "get_event_bus",
    
    # Tracing
    "Tracer",
    "Span",
    "SpanContext",
    "SpanKind",
    "SpanStatus",
    "MetricsCollector",
    "init_tracing",
    "close_tracing",
    "get_tracer",
    "get_metrics",
    "get_current_span",
    "get_current_trace_id",
    "trace",
    "tracing_middleware",
]

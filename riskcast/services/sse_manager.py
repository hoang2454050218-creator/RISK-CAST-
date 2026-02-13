"""
SSE Manager — Server-Sent Events pub/sub for real-time notifications.

All server→client push uses SSE (not WebSocket).
SSE is simpler: Nginx config, debugging, auto-reconnect all easier.

Usage:
- Subscribe: GET /api/v1/events/stream?token=xxx
- Publish: await sse_manager.broadcast(company_id, event_dict)
"""

import asyncio
import json
from collections import defaultdict
from typing import AsyncGenerator

import structlog

logger = structlog.get_logger(__name__)


class SSEManager:
    """
    SSE pub/sub manager.

    Each company has a set of subscriber queues.
    Broadcast puts event into all company queues.
    Subscribe yields SSE-formatted strings.
    """

    def __init__(self):
        self._subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)

    @property
    def subscriber_count(self) -> int:
        return sum(len(queues) for queues in self._subscribers.values())

    async def subscribe(self, company_id: str) -> AsyncGenerator[str, None]:
        """
        Subscribe to events for a company. Yields SSE-formatted strings.

        Sends keepalive comment every 30s to prevent connection timeout.
        """
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers[company_id].add(queue)
        logger.info(
            "sse_subscriber_added",
            company_id=company_id,
            total=len(self._subscribers[company_id]),
        )

        try:
            while True:
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    # SSE comment = keepalive (not data, won't trigger onmessage)
                    yield ": keepalive\n\n"
        finally:
            self._subscribers[company_id].discard(queue)
            logger.info(
                "sse_subscriber_removed",
                company_id=company_id,
                remaining=len(self._subscribers[company_id]),
            )

    async def broadcast(self, company_id: str, event: dict):
        """Send an event to all subscribers of a company."""
        queues = self._subscribers.get(company_id, set())
        if not queues:
            return

        for queue in queues:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("sse_queue_full", company_id=company_id)

        logger.debug(
            "sse_broadcast",
            company_id=company_id,
            event_type=event.get("type"),
            recipients=len(queues),
        )


# Global singleton — shared across the API process
sse_manager = SSEManager()

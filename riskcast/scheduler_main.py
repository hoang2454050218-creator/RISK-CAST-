"""
Scheduler Entry Point — runs in a separate container.

Usage:
    python -m riskcast.scheduler_main

This does NOT run a web server. It runs the APScheduler
background loop for signal scanning and expiry.
"""

import asyncio
import signal
import sys

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from riskcast.config import settings
from riskcast.services.omen_client import OmenClient
from riskcast.services.scheduler import SignalScheduler

logger = structlog.get_logger(__name__)


async def main():
    """Initialize and run the scheduler."""
    logger.info("scheduler_starting", version=settings.app_version)

    # Database
    engine = create_async_engine(
        settings.async_database_url,
        pool_size=5,
        max_overflow=5,
        echo=settings.debug,
    )
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # OMEN client
    omen_client = OmenClient(base_url=settings.omen_url)

    # Scheduler
    scheduler = SignalScheduler(
        session_factory=session_factory,
        omen_client=omen_client,
    )

    # Run initial scan on startup
    logger.info("running_initial_scan")
    await scheduler.run_full_scan()

    # Start periodic scheduler
    scheduler.start()

    # Graceful shutdown handling
    stop_event = asyncio.Event()

    def _handle_signal(signum, frame):
        logger.info("shutdown_signal_received", signal=signum)
        stop_event.set()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    logger.info("scheduler_running", msg="Waiting for jobs... Ctrl+C to stop.")

    # Block until shutdown signal
    await stop_event.wait()

    # Cleanup
    scheduler.stop()
    await engine.dispose()
    logger.info("scheduler_shutdown_complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

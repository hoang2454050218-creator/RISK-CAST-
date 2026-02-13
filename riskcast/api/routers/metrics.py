"""
Prometheus Metrics Endpoint.

GET /metrics — Exposes operational metrics in Prometheus text format.

Includes:
- Signal ingest counters (total, duplicates, errors)
- Database status
- Uptime
"""

import time
from datetime import datetime

import structlog
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from riskcast.services.ingest_service import get_ingest_metrics

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["observability"])

_start_time = time.time()


def _format_prometheus(metrics: dict[str, float | int | str]) -> str:
    """Format metrics dict as Prometheus text exposition format."""
    lines: list[str] = []
    for key, value in metrics.items():
        # Prometheus format: metric_name value
        safe_key = key.replace(".", "_").replace("-", "_")
        if isinstance(value, (int, float)):
            lines.append(f"riskcast_{safe_key} {value}")
    return "\n".join(lines) + "\n"


@router.get(
    "/metrics",
    response_class=PlainTextResponse,
    summary="Prometheus metrics",
    description="Operational metrics in Prometheus text exposition format.",
)
async def prometheus_metrics():
    """Return Prometheus-compatible metrics."""
    ingest = get_ingest_metrics()

    metrics = {
        # Uptime
        "uptime_seconds": round(time.time() - _start_time, 1),
        # Ingest pipeline
        "ingest_total_received": ingest["total_received"],
        "ingest_total_ingested": ingest["total_ingested"],
        "ingest_total_duplicates": ingest["total_duplicates"],
        "ingest_total_errors": ingest["total_errors"],
        # Ingest rate (approximate)
        "ingest_success_rate": (
            round(ingest["total_ingested"] / max(ingest["total_received"], 1), 4)
        ),
    }

    # Add DB health check
    try:
        from sqlalchemy import text as sa_text
        from riskcast.db.engine import get_engine
        async with get_engine().connect() as conn:
            await conn.execute(sa_text("SELECT 1"))
        metrics["database_up"] = 1
    except Exception:
        metrics["database_up"] = 0

    return _format_prometheus(metrics)

"""Metrics Endpoint.

Exposes Prometheus metrics for scraping.
"""

from fastapi import APIRouter
from fastapi.responses import Response

from app.common.metrics import get_metrics, get_metrics_content_type

router = APIRouter()


@router.get(
    "/metrics",
    summary="Prometheus metrics",
    description="Returns application metrics in Prometheus format",
    response_class=Response,
)
async def metrics():
    """
    Prometheus metrics endpoint.

    Returns all application metrics in Prometheus text format.
    """
    return Response(
        content=get_metrics(),
        media_type=get_metrics_content_type(),
    )

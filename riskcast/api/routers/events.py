"""
SSE Events Stream.

GET /api/v1/events/stream?token=xxx

Client usage:
    const es = new EventSource('/api/v1/events/stream?token=xxx');
    es.onmessage = (e) => { const data = JSON.parse(e.data); ... };

Auth via query param token (v1). Will move to cookie auth in v2.
EventSource API does not support custom headers.
"""

import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from riskcast.api.deps import get_company_id
from riskcast.services.sse_manager import sse_manager

router = APIRouter(prefix="/api/v1/events", tags=["events"])


@router.get("/stream")
async def event_stream(
    request: Request,
    company_id: uuid.UUID = Depends(get_company_id),
):
    """
    SSE notification stream for the current tenant.

    Events include:
    - morning_brief: new brief generated
    - signal_alert: high-severity signal detected
    - scan_completed: signal scan finished
    """
    return StreamingResponse(
        sse_manager.subscribe(str(company_id)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )

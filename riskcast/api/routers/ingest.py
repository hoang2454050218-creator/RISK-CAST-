"""
OMEN Signal Ingest Endpoint.

POST /api/v1/signals/ingest

This is THE endpoint OMEN calls to push signals into RiskCast.
- Requires X-API-Key authentication (set by TenantMiddleware)
- Accepts SignalEvent JSON body
- Supports X-Idempotency-Key header for dedup
- Returns ack_id on success (200) or duplicate (409)
- Writes to immutable ledger BEFORE inserting into DB
- NEVER leaks internal errors to client
"""

import uuid

import structlog
from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.db.engine import get_db_session
from riskcast.schemas.omen_signal import IngestAck, SignalEvent
from riskcast.services.ingest_service import IngestService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/signals", tags=["omen-ingest"])

_ingest_service = IngestService()


@router.post(
    "/ingest",
    response_model=IngestAck,
    summary="Ingest signal from OMEN",
    description=(
        "Receives a SignalEvent from the OMEN pipeline. "
        "Requires X-API-Key authentication. "
        "Idempotent: duplicate signal_id returns 409 with the same ack_id."
    ),
    responses={
        200: {
            "description": "Signal ingested successfully",
            "content": {
                "application/json": {
                    "example": {"ack_id": "riskcast-ack-a1b2c3d4"}
                }
            },
        },
        409: {
            "description": "Duplicate signal (idempotent — not an error)",
            "content": {
                "application/json": {
                    "example": {"ack_id": "riskcast-ack-a1b2c3d4", "duplicate": True}
                }
            },
        },
    },
)
async def ingest_signal(
    event: SignalEvent,
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
):
    """
    Ingest a signal event from OMEN.

    The X-Idempotency-Key header is optional but recommended.
    If provided, it must match the signal_id in the body.
    """
    # Validate idempotency key matches signal_id if provided
    if x_idempotency_key and x_idempotency_key != event.signal_id:
        return JSONResponse(
            status_code=400,
            content={
                "error": "idempotency_key_mismatch",
                "detail": "X-Idempotency-Key does not match signal_id in body",
            },
        )

    async with get_db_session() as session:
        try:
            ack, status_code = await _ingest_service.ingest(session, event)
            return JSONResponse(
                status_code=status_code,
                content=ack.model_dump(),
            )
        except Exception:
            error_id = str(uuid.uuid4())
            logger.error(
                "ingest_endpoint_error",
                error_id=error_id,
                signal_id=event.signal_id,
                exc_info=True,
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Signal ingestion failed",
                    "error_id": error_id,
                },
            )

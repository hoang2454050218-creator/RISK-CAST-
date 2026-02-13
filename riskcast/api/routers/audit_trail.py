"""
Audit Trail API Endpoints.

GET /api/v1/audit-trail           — paginated, filterable event log
GET /api/v1/audit-trail/integrity — hash chain integrity check
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, desc, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.api.deps import get_company_id, get_db
from riskcast.db.models import SecurityAuditLog
from riskcast.schemas.audit import AuditEventResponse, AuditIntegrityResponse, AuditTrailResponse
from riskcast.services.security_audit import get_audit_service

router = APIRouter(prefix="/api/v1/audit-trail", tags=["audit"])


@router.get("", response_model=AuditTrailResponse)
async def list_audit_trail(
    action: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """Paginated audit trail for the current tenant."""
    stmt = select(SecurityAuditLog).where(
        SecurityAuditLog.company_id == company_id
    )

    if action:
        stmt = stmt.where(SecurityAuditLog.action == action)
    if resource_type:
        stmt = stmt.where(SecurityAuditLog.resource_type == resource_type)

    # Count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    # Fetch
    stmt = stmt.order_by(desc(SecurityAuditLog.timestamp)).offset(offset).limit(limit)
    result = await db.execute(stmt)
    events = result.scalars().all()

    return AuditTrailResponse(
        events=[
            AuditEventResponse(
                id=str(e.id),
                timestamp=e.timestamp.isoformat() if e.timestamp else "",
                action=e.action,
                status=e.status,
                resource_type=e.resource_type,
                resource_id=e.resource_id,
                user_id=str(e.user_id) if e.user_id else None,
                api_key_prefix=e.api_key_prefix,
                ip_address=e.ip_address,
                request_method=e.request_method,
                request_path=e.request_path,
                details=e.details,
            )
            for e in events
        ],
        total=total,
        has_more=(offset + limit) < total,
    )


@router.get("/integrity", response_model=AuditIntegrityResponse)
async def check_integrity(
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """Verify the audit trail hash chain is unbroken."""
    svc = get_audit_service()
    report = await svc.verify_chain_integrity(db)
    return AuditIntegrityResponse(
        status=report["status"],
        total_entries=report["total_entries"],
        chain_intact=report["chain_intact"],
        breaks_found=report.get("breaks_found", 0),
    )

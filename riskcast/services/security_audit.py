"""
Security Audit Trail Service.

Immutable, append-only logging of ALL security-relevant events.
Each entry carries a SHA-256 hash chain for tamper detection.
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.db.engine import get_db_session
from riskcast.db.models import SecurityAuditLog

logger = structlog.get_logger(__name__)


def _compute_entry_hash(
    entry_id: str,
    timestamp: str,
    action: str,
    company_id: str,
    user_id: str,
    status: str,
    previous_hash: str,
) -> str:
    """Compute SHA-256 hash of an audit entry for chain integrity."""
    payload = f"{entry_id}|{timestamp}|{action}|{company_id}|{user_id}|{status}|{previous_hash}"
    return hashlib.sha256(payload.encode()).hexdigest()


class SecurityAuditService:
    """Append-only audit trail with hash chain integrity."""

    async def log_event(
        self,
        session: AsyncSession,
        *,
        action: str,
        status: str = "success",
        company_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        api_key_prefix: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_method: Optional[str] = None,
        request_path: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> SecurityAuditLog:
        """
        Record a security event with hash chain integrity.

        Actions include: login, login_failed, permission_denied, data_export,
        settings_change, role_change, api_key_created, api_key_revoked,
        decision_approved, signal_ingested, reconcile_triggered, etc.
        """
        # Get the hash of the most recent entry for chain linking
        previous_hash = await self._get_last_hash(session)

        entry_id = uuid.uuid4()
        now = datetime.utcnow()

        entry_hash = _compute_entry_hash(
            entry_id=str(entry_id),
            timestamp=now.isoformat(),
            action=action,
            company_id=str(company_id) if company_id else "",
            user_id=str(user_id) if user_id else "",
            status=status,
            previous_hash=previous_hash or "",
        )

        entry = SecurityAuditLog(
            id=entry_id,
            timestamp=now,
            company_id=company_id,
            user_id=user_id,
            api_key_prefix=api_key_prefix,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_method=request_method,
            request_path=request_path,
            status=status,
            details=details,
            previous_hash=previous_hash,
            entry_hash=entry_hash,
        )

        session.add(entry)
        await session.flush()

        logger.info(
            "security_audit_logged",
            action=action,
            status=status,
            company_id=str(company_id) if company_id else None,
            user_id=str(user_id) if user_id else None,
        )

        return entry

    async def _get_last_hash(self, session: AsyncSession) -> Optional[str]:
        """Get the entry_hash of the most recent audit log entry."""
        result = await session.execute(
            select(SecurityAuditLog.entry_hash)
            .order_by(desc(SecurityAuditLog.timestamp))
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return row

    async def verify_chain_integrity(self, session: AsyncSession) -> dict:
        """
        Verify the hash chain is unbroken.

        Returns a report with integrity status and any breaks found.
        """
        result = await session.execute(
            select(SecurityAuditLog)
            .order_by(SecurityAuditLog.timestamp)
        )
        entries = result.scalars().all()

        if not entries:
            return {
                "status": "empty",
                "total_entries": 0,
                "chain_intact": True,
                "breaks": [],
            }

        breaks: list[dict] = []
        previous_hash: Optional[str] = None

        for entry in entries:
            # Verify this entry's previous_hash matches the last entry's hash
            if entry.previous_hash != previous_hash:
                breaks.append({
                    "entry_id": str(entry.id),
                    "timestamp": entry.timestamp.isoformat(),
                    "expected_previous_hash": previous_hash,
                    "actual_previous_hash": entry.previous_hash,
                })

            # Verify this entry's own hash is correct
            expected_hash = _compute_entry_hash(
                entry_id=str(entry.id),
                timestamp=entry.timestamp.isoformat(),
                action=entry.action,
                company_id=str(entry.company_id) if entry.company_id else "",
                user_id=str(entry.user_id) if entry.user_id else "",
                status=entry.status,
                previous_hash=entry.previous_hash or "",
            )
            if entry.entry_hash != expected_hash:
                breaks.append({
                    "entry_id": str(entry.id),
                    "timestamp": entry.timestamp.isoformat(),
                    "issue": "entry_hash_mismatch",
                    "expected": expected_hash,
                    "actual": entry.entry_hash,
                })

            previous_hash = entry.entry_hash

        return {
            "status": "intact" if not breaks else "broken",
            "total_entries": len(entries),
            "chain_intact": len(breaks) == 0,
            "breaks_found": len(breaks),
            "breaks": breaks[:10],  # Cap output
        }


# Module-level singleton
_audit_service = SecurityAuditService()


async def log_security_event(**kwargs) -> None:
    """Convenience function: log a security event using a fresh session."""
    async with get_db_session() as session:
        await _audit_service.log_event(session, **kwargs)


def get_audit_service() -> SecurityAuditService:
    """Get the singleton audit service."""
    return _audit_service

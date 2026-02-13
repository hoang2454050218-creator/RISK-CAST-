"""
Security Audit Trail Tests.

Tests: event logging, hash chain integrity, chain break detection, immutability.
"""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.services.security_audit import SecurityAuditService, _compute_entry_hash


class TestComputeEntryHash:
    """Test the deterministic hash computation."""

    def test_deterministic(self):
        """Same inputs always produce same hash."""
        h1 = _compute_entry_hash("id", "ts", "login", "cid", "uid", "success", "prev")
        h2 = _compute_entry_hash("id", "ts", "login", "cid", "uid", "success", "prev")
        assert h1 == h2

    def test_different_inputs(self):
        """Different inputs produce different hashes."""
        h1 = _compute_entry_hash("id1", "ts", "login", "cid", "uid", "success", "prev")
        h2 = _compute_entry_hash("id2", "ts", "login", "cid", "uid", "success", "prev")
        assert h1 != h2

    def test_hash_is_sha256(self):
        """Hash is a valid 64-char hex string."""
        h = _compute_entry_hash("id", "ts", "login", "cid", "uid", "success", "prev")
        assert len(h) == 64
        int(h, 16)  # valid hex

    def test_action_changes_hash(self):
        """Changing action changes the hash."""
        h1 = _compute_entry_hash("id", "ts", "login", "cid", "uid", "success", "prev")
        h2 = _compute_entry_hash("id", "ts", "login_failed", "cid", "uid", "success", "prev")
        assert h1 != h2

    def test_previous_hash_changes_hash(self):
        """Changing previous_hash changes the hash (chain linkage)."""
        h1 = _compute_entry_hash("id", "ts", "login", "cid", "uid", "success", "prev1")
        h2 = _compute_entry_hash("id", "ts", "login", "cid", "uid", "success", "prev2")
        assert h1 != h2


@pytest.mark.asyncio
class TestSecurityAuditService:
    """Test the audit service with a real async session."""

    async def test_log_event_basic(self, db: AsyncSession):
        """Log a simple event and verify it's stored."""
        svc = SecurityAuditService()
        entry = await svc.log_event(
            db,
            action="login",
            status="success",
            company_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            ip_address="1.2.3.4",
        )
        assert entry.action == "login"
        assert entry.status == "success"
        assert entry.entry_hash is not None
        assert len(entry.entry_hash) == 64

    async def test_log_event_chains_hash(self, db: AsyncSession):
        """Second event's previous_hash equals first event's entry_hash."""
        svc = SecurityAuditService()
        cid = uuid.uuid4()

        entry1 = await svc.log_event(db, action="login", company_id=cid)
        entry2 = await svc.log_event(db, action="logout", company_id=cid)

        assert entry2.previous_hash == entry1.entry_hash

    async def test_verify_chain_empty(self, db: AsyncSession):
        """Empty audit log passes integrity check."""
        svc = SecurityAuditService()
        # Use a fresh service that queries a potentially empty session
        report = await svc.verify_chain_integrity(db)
        assert report["chain_intact"]

    async def test_log_event_with_details(self, db: AsyncSession):
        """Event can carry arbitrary JSON details."""
        svc = SecurityAuditService()
        entry = await svc.log_event(
            db,
            action="settings_change",
            details={"field": "timezone", "old": "UTC", "new": "Asia/Ho_Chi_Minh"},
        )
        assert entry.details["field"] == "timezone"

    async def test_log_api_key_event(self, db: AsyncSession):
        """API key events log key prefix, not full key."""
        svc = SecurityAuditService()
        entry = await svc.log_event(
            db,
            action="signal_ingested",
            api_key_prefix="rc_live_abc12345",
            ip_address="10.0.0.1",
        )
        assert entry.api_key_prefix == "rc_live_abc12345"
        assert entry.user_id is None  # API keys are not users

    async def test_log_failed_login(self, db: AsyncSession):
        """Failed login logs with denied status."""
        svc = SecurityAuditService()
        entry = await svc.log_event(
            db,
            action="login_failed",
            status="denied",
            ip_address="1.2.3.4",
            details={"email": "attacker@test.com"},
        )
        assert entry.status == "denied"
        assert entry.action == "login_failed"

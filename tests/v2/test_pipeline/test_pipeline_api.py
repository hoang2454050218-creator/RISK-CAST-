"""
Tests for Pipeline API Endpoints.

Covers:
- POST /api/v1/pipeline/validate
- GET /api/v1/pipeline/health
- GET /api/v1/pipeline/integrity
- GET /api/v1/pipeline/integrity/replay
- GET /api/v1/pipeline/trace/{signal_id}
- GET /api/v1/pipeline/coverage
"""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from riskcast.api.deps import get_db
from riskcast.main import app


@pytest_asyncio.fixture
async def client(session_factory, admin_user, admin_token):
    """Authenticated async test client with DB dependency override."""

    async def _override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {admin_token}"},
    ) as c:
        yield c
    app.dependency_overrides.clear()


# ── Validate Endpoint ──────────────────────────────────────────────────


class TestValidateEndpoint:
    @pytest.mark.asyncio
    async def test_valid_signal(self, client):
        """Valid signal → 200 with is_valid=True."""
        payload = {
            "schema_version": "1.0.0",
            "signal_id": "OMEN-TEST-12345",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "emitted_at": datetime.now(timezone.utc).isoformat(),
            "signal": {
                "signal_id": "OMEN-TEST-12345",
                "title": "Major port congestion at Shanghai",
                "description": "Expected delays for 2 weeks",
                "probability": 0.75,
                "confidence_score": 0.85,
                "confidence_level": "HIGH",
                "category": "SUPPLY_CHAIN",
                "tags": ["port"],
                "evidence": [
                    {"source": "reuters", "source_type": "news_article"},
                ],
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        }
        resp = await client.post("/api/v1/pipeline/validate", json=payload)
        assert resp.status_code == 200, f"Response: {resp.text}"
        data = resp.json()
        assert data["is_valid"] is True
        assert data["quality_score"] > 0

    @pytest.mark.asyncio
    async def test_invalid_signal_mismatch(self, client):
        """Mismatched signal IDs → is_valid=False."""
        payload = {
            "schema_version": "1.0.0",
            "signal_id": "OMEN-OUTER-123",
            "signal": {
                "signal_id": "OMEN-INNER-456",
                "title": "Test signal title here",
                "probability": 0.5,
                "confidence_score": 0.5,
                "category": "ECONOMIC",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        }
        resp = await client.post("/api/v1/pipeline/validate", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_valid"] is False
        assert data["errors"] > 0


# ── Health Endpoint ────────────────────────────────────────────────────


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_structure(self, client):
        resp = await client.get("/api/v1/pipeline/health")
        assert resp.status_code == 200, f"Response: {resp.text}"
        data = resp.json()
        assert "freshness_status" in data
        assert "ingest_lag" in data
        assert "volume" in data
        assert "overall_status" in data
        assert "recommendations" in data


# ── Integrity Endpoint ─────────────────────────────────────────────────


class TestIntegrityEndpoint:
    @pytest.mark.asyncio
    async def test_integrity_returns_structure(self, client):
        resp = await client.get("/api/v1/pipeline/integrity")
        assert resp.status_code == 200, f"Response: {resp.text}"
        data = resp.json()
        assert "is_consistent" in data
        assert "counts" in data
        assert "issues" in data

    @pytest.mark.asyncio
    async def test_integrity_custom_hours(self, client):
        resp = await client.get("/api/v1/pipeline/integrity?hours_back=48")
        assert resp.status_code == 200
        assert resp.json()["period_hours"] == 48


# ── Replay Endpoint ───────────────────────────────────────────────────


class TestReplayEndpoint:
    @pytest.mark.asyncio
    async def test_replay_returns_list(self, client):
        resp = await client.get("/api/v1/pipeline/integrity/replay")
        assert resp.status_code == 200, f"Response: {resp.text}"
        data = resp.json()
        assert "signals_needing_replay" in data
        assert "count" in data


# ── Trace Endpoint ────────────────────────────────────────────────────


class TestTraceEndpoint:
    @pytest.mark.asyncio
    async def test_trace_unknown_signal(self, client):
        resp = await client.get("/api/v1/pipeline/trace/OMEN-NOPE-999")
        assert resp.status_code == 200, f"Response: {resp.text}"
        data = resp.json()
        assert data["is_complete"] is False
        assert len(data["steps"]) == 0


# ── Coverage Endpoint ─────────────────────────────────────────────────


class TestCoverageEndpoint:
    @pytest.mark.asyncio
    async def test_coverage_returns_structure(self, client):
        resp = await client.get("/api/v1/pipeline/coverage")
        assert resp.status_code == 200, f"Response: {resp.text}"
        data = resp.json()
        assert "total_in_ledger" in data
        assert "total_ingested" in data
        assert "ingest_coverage" in data
        assert "needs_reconciliation" in data

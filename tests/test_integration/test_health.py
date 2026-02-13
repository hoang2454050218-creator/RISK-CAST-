"""Integration tests for Health Check endpoints.

Tests:
- Liveness probe
- Readiness probe
- Full health check
- Circuit breaker status
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.health import router
from app.core.circuit_breaker import (
    get_circuit_breaker_registry,
    CircuitState,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def app():
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def circuit_registry():
    """Reset and get circuit breaker registry."""
    registry = get_circuit_breaker_registry()
    registry.reset_all()
    return registry


# ============================================================================
# LIVENESS TESTS
# ============================================================================


class TestLiveness:
    """Tests for liveness probe."""

    def test_liveness_returns_alive(self, app):
        """Liveness should always return alive=true."""
        client = TestClient(app)

        response = client.get("/live")

        assert response.status_code == 200
        data = response.json()
        assert data["alive"] is True
        assert "timestamp" in data


# ============================================================================
# READINESS TESTS
# ============================================================================


class TestReadiness:
    """Tests for readiness probe."""

    @patch("app.api.routes.health.check_database")
    @patch("app.api.routes.health.check_redis")
    @patch("app.api.routes.health.get_db_session")
    def test_ready_when_dependencies_healthy(
        self,
        mock_db_session,
        mock_redis,
        mock_db,
        app,
    ):
        """Should return ready=true when dependencies healthy."""
        mock_db_session.return_value = AsyncMock()
        mock_db.return_value = MagicMock(status="healthy")
        mock_redis.return_value = MagicMock(status="healthy")

        client = TestClient(app)

        response = client.get("/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is True

    @patch("app.api.routes.health.check_database")
    @patch("app.api.routes.health.get_db_session")
    def test_not_ready_when_database_unhealthy(
        self,
        mock_db_session,
        mock_db,
        app,
    ):
        """Should return 503 when database unhealthy."""
        mock_db_session.return_value = AsyncMock()
        mock_db.return_value = MagicMock(status="unhealthy")

        client = TestClient(app)

        response = client.get("/ready")

        assert response.status_code == 503


# ============================================================================
# HEALTH TESTS
# ============================================================================


class TestHealth:
    """Tests for full health check."""

    @patch("app.api.routes.health.check_database")
    @patch("app.api.routes.health.check_redis")
    @patch("app.api.routes.health.check_circuit_breakers")
    @patch("app.api.routes.health.get_db_session")
    def test_health_aggregates_components(
        self,
        mock_db_session,
        mock_cb,
        mock_redis,
        mock_db,
        app,
    ):
        """Health should return status for all components."""
        mock_db_session.return_value = AsyncMock()
        mock_db.return_value = MagicMock(
            name="database",
            status="healthy",
            latency_ms=10,
        )
        mock_redis.return_value = MagicMock(
            name="redis",
            status="healthy",
            latency_ms=5,
        )
        mock_cb.return_value = MagicMock(
            name="circuit_breakers",
            status="healthy",
        )

        client = TestClient(app)

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "components" in data
        assert len(data["components"]) == 3

    @patch("app.api.routes.health.check_database")
    @patch("app.api.routes.health.check_redis")
    @patch("app.api.routes.health.check_circuit_breakers")
    @patch("app.api.routes.health.get_db_session")
    def test_health_degraded_when_redis_unhealthy(
        self,
        mock_db_session,
        mock_cb,
        mock_redis,
        mock_db,
        app,
    ):
        """Health should be degraded when non-critical component unhealthy."""
        mock_db_session.return_value = AsyncMock()
        mock_db.return_value = MagicMock(status="healthy")
        mock_redis.return_value = MagicMock(status="unhealthy")
        mock_cb.return_value = MagicMock(status="healthy")

        client = TestClient(app)

        response = client.get("/health")

        data = response.json()
        # Overall status should reflect the worst component
        assert data["status"] in ["degraded", "unhealthy"]


# ============================================================================
# CIRCUIT BREAKER TESTS
# ============================================================================


class TestCircuitBreakers:
    """Tests for circuit breaker status endpoint."""

    def test_circuit_status(self, app, circuit_registry):
        """Should return circuit breaker status."""
        # Ensure some circuits exist
        circuit_registry.get_or_create("test_service")

        client = TestClient(app)

        response = client.get("/circuits")

        assert response.status_code == 200
        data = response.json()
        assert "circuit_breakers" in data
        assert "timestamp" in data

    def test_reset_circuit(self, app, circuit_registry):
        """Should reset a circuit breaker."""
        # Create a circuit
        cb = circuit_registry.get_or_create("test_reset")
        # Manually set to open
        cb._state = CircuitState.OPEN

        client = TestClient(app)

        response = client.post("/circuits/test_reset/reset")

        assert response.status_code == 200
        assert cb.state == CircuitState.CLOSED

    def test_reset_nonexistent_circuit(self, app, circuit_registry):
        """Should return 404 for nonexistent circuit."""
        client = TestClient(app)

        response = client.post("/circuits/nonexistent/reset")

        assert response.status_code == 404

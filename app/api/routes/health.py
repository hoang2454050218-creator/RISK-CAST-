"""Health Check Endpoints.

Provides health and readiness checks for:
- Kubernetes probes (liveness, readiness)
- Load balancer health checks
- Monitoring dashboards
- Operational debugging
"""

from datetime import datetime
from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import cache
from app.core.circuit_breaker import get_registry as get_circuit_breaker_registry

logger = structlog.get_logger(__name__)

router = APIRouter()

# Startup time tracking
_startup_time: Optional[datetime] = None


def set_startup_time() -> None:
    """Set the application startup time."""
    global _startup_time
    _startup_time = datetime.utcnow()


def get_startup_time() -> Optional[datetime]:
    """Get the application startup time."""
    return _startup_time


# ============================================================================
# SCHEMAS
# ============================================================================


class ComponentHealth(BaseModel):
    """Health status of a component."""

    name: str
    status: str  # healthy, degraded, unhealthy
    latency_ms: Optional[float] = None
    message: Optional[str] = None
    details: Optional[dict] = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(description="Overall health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(default="1.0.0")
    components: list[ComponentHealth] = Field(default_factory=list)


class ReadinessResponse(BaseModel):
    """Readiness check response."""

    ready: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    checks: dict[str, bool] = Field(default_factory=dict)


class LivenessResponse(BaseModel):
    """Liveness check response."""

    alive: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# HEALTH CHECK FUNCTIONS
# ============================================================================


async def check_database(session: AsyncSession) -> ComponentHealth:
    """Check database connectivity."""
    import time

    start = time.perf_counter()
    try:
        # Simple query to test connection
        result = await session.execute(text("SELECT 1"))
        result.scalar()
        latency = (time.perf_counter() - start) * 1000

        return ComponentHealth(
            name="database",
            status="healthy" if latency < 100 else "degraded",
            latency_ms=round(latency, 2),
            message="PostgreSQL connection OK",
        )
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        logger.error("database_health_check_failed", error=str(e))
        return ComponentHealth(
            name="database",
            status="unhealthy",
            latency_ms=round(latency, 2),
            message=f"Database error: {str(e)[:100]}",
        )


async def check_redis() -> ComponentHealth:
    """Check Redis connectivity."""
    import time

    start = time.perf_counter()
    try:
        # Ping Redis
        if cache._client:
            await cache._client.ping()
            latency = (time.perf_counter() - start) * 1000

            return ComponentHealth(
                name="redis",
                status="healthy" if latency < 50 else "degraded",
                latency_ms=round(latency, 2),
                message="Redis connection OK",
            )
        else:
            return ComponentHealth(
                name="redis",
                status="degraded",
                message="Redis not configured",
            )
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        logger.error("redis_health_check_failed", error=str(e))
        return ComponentHealth(
            name="redis",
            status="unhealthy",
            latency_ms=round(latency, 2),
            message=f"Redis error: {str(e)[:100]}",
        )


def check_circuit_breakers() -> ComponentHealth:
    """Check circuit breaker states."""
    registry = get_circuit_breaker_registry()
    health = registry.get_all_health()

    open_circuits = [
        name for name, info in health.items() if info["state"] == "open"
    ]

    if not open_circuits:
        return ComponentHealth(
            name="circuit_breakers",
            status="healthy",
            message="All circuits closed",
            details={"circuits": len(health)},
        )
    elif len(open_circuits) == len(health):
        return ComponentHealth(
            name="circuit_breakers",
            status="unhealthy",
            message=f"All circuits open: {', '.join(open_circuits)}",
            details=health,
        )
    else:
        return ComponentHealth(
            name="circuit_breakers",
            status="degraded",
            message=f"Open circuits: {', '.join(open_circuits)}",
            details=health,
        )


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Comprehensive health check including all dependencies",
)
async def health_check() -> HealthResponse:
    """
    Comprehensive health check.

    Checks:
    - Application status (always healthy if responding)
    - Database connectivity (optional, graceful degradation)
    - Redis connectivity (optional)
    - Circuit breaker states

    Returns overall health status and component details.
    This endpoint does NOT require authentication or database session
    to ensure it works even when services are degraded.
    """
    components: list[ComponentHealth] = []

    # Application is alive
    components.append(
        ComponentHealth(
            name="application",
            status="healthy",
            message="RISKCAST is running",
        )
    )

    # Check database (optional - don't fail health if DB is down)
    try:
        from app.core.database import get_session_factory
        factory = get_session_factory()
        async with factory() as session:
            db_health = await check_database(session)
            components.append(db_health)
    except Exception as e:
        components.append(
            ComponentHealth(
                name="database",
                status="degraded",
                message=f"Database check skipped: {str(e)[:80]}",
            )
        )

    # Check Redis (optional)
    try:
        redis_health = await check_redis()
        components.append(redis_health)
    except Exception as e:
        components.append(
            ComponentHealth(
                name="redis",
                status="degraded",
                message=f"Redis check skipped: {str(e)[:80]}",
            )
        )

    # Check circuit breakers
    try:
        cb_health = check_circuit_breakers()
        components.append(cb_health)
    except Exception:
        pass

    # Determine overall status
    statuses = [c.status for c in components]
    if all(s == "healthy" for s in statuses):
        overall = "healthy"
    elif any(s == "unhealthy" for s in statuses):
        overall = "unhealthy"
    else:
        overall = "degraded"

    return HealthResponse(
        status=overall,
        components=components,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness check",
    description="Check if the service is ready to receive traffic",
)
async def readiness_check() -> ReadinessResponse:
    """
    Readiness check for Kubernetes.

    Returns ready=true only if all critical dependencies are available.
    Used by load balancers to determine if traffic should be routed.
    """
    checks = {}

    # Database is critical
    try:
        from app.core.database import get_session_factory
        factory = get_session_factory()
        async with factory() as session:
            db_health = await check_database(session)
            checks["database"] = db_health.status != "unhealthy"
    except Exception:
        checks["database"] = False

    # Redis is not critical (graceful degradation)
    try:
        redis_health = await check_redis()
        checks["redis"] = redis_health.status != "unhealthy"
    except Exception:
        checks["redis"] = False

    # All critical checks must pass
    ready = checks.get("database", False)

    if not ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"ready": False, "checks": checks},
        )

    return ReadinessResponse(
        ready=ready,
        checks=checks,
    )


@router.get(
    "/live",
    response_model=LivenessResponse,
    summary="Liveness check",
    description="Check if the service is alive",
)
async def liveness_check() -> LivenessResponse:
    """
    Liveness check for Kubernetes.

    Returns alive=true if the process is running.
    Does NOT check dependencies (that's readiness).

    If this fails, Kubernetes should restart the pod.
    """
    return LivenessResponse(alive=True)


@router.get(
    "/circuits",
    summary="Circuit breaker status",
    description="Get status of all circuit breakers",
)
async def circuit_status() -> dict:
    """
    Get detailed circuit breaker status.

    Returns state and statistics for all circuit breakers.
    Useful for debugging and monitoring.
    """
    registry = get_circuit_breaker_registry()
    return {
        "circuit_breakers": registry.get_all_health(),
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post(
    "/circuits/{name}/reset",
    summary="Reset circuit breaker",
    description="Reset a circuit breaker to closed state",
)
async def reset_circuit(name: str) -> dict:
    """
    Reset a circuit breaker.

    Use with caution - this allows traffic to a potentially unhealthy service.
    """
    registry = get_circuit_breaker_registry()
    cb = registry.get(name)

    if not cb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Circuit breaker '{name}' not found",
        )

    cb.reset()

    return {
        "message": f"Circuit breaker '{name}' reset",
        "new_state": cb.get_health(),
    }

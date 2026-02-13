"""
Health Check Module.

Production-grade health checks with:
- Liveness probe (is the app running?)
- Readiness probe (can the app serve requests?)
- Component health checks
- Kubernetes-compatible endpoints
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from enum import Enum

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel, Field
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


# ============================================================================
# ENUMS
# ============================================================================


class HealthStatus(str, Enum):
    """Health status values."""
    
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


# ============================================================================
# MODELS
# ============================================================================


class ComponentHealth(BaseModel):
    """Health status of a component."""
    
    name: str
    status: HealthStatus
    message: Optional[str] = None
    latency_ms: Optional[float] = None
    details: Optional[Dict[str, Any]] = None
    checked_at: datetime = Field(default_factory=datetime.utcnow)


class HealthResponse(BaseModel):
    """Overall health response."""
    
    status: HealthStatus
    version: str
    environment: str
    uptime_seconds: float
    components: List[ComponentHealth]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class LivenessResponse(BaseModel):
    """Liveness probe response."""
    
    alive: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ReadinessResponse(BaseModel):
    """Readiness probe response."""
    
    ready: bool
    reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# HEALTH CHECKERS
# ============================================================================


class HealthChecker:
    """
    Comprehensive health checker for all system components.
    """
    
    def __init__(self):
        self._start_time = datetime.utcnow()
        self._last_health: Optional[HealthResponse] = None
        self._cache_ttl_seconds = 5
    
    @property
    def uptime_seconds(self) -> float:
        """Get application uptime in seconds."""
        return (datetime.utcnow() - self._start_time).total_seconds()
    
    async def check_database(
        self,
        session_factory,
    ) -> ComponentHealth:
        """Check PostgreSQL database health."""
        start = datetime.utcnow()
        
        try:
            async with session_factory() as session:
                # Simple connectivity check
                result = await session.execute(text("SELECT 1"))
                result.scalar()
                
                # Check connection pool
                pool_status = {}
                
            latency = (datetime.utcnow() - start).total_seconds() * 1000
            
            return ComponentHealth(
                name="postgresql",
                status=HealthStatus.HEALTHY,
                message="Database connection successful",
                latency_ms=latency,
                details=pool_status,
            )
        
        except Exception as e:
            logger.error("health_check_database_failed", error=str(e))
            return ComponentHealth(
                name="postgresql",
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {str(e)}",
            )
    
    async def check_redis(self) -> ComponentHealth:
        """Check Redis health."""
        start = datetime.utcnow()
        
        try:
            client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            
            # Ping check
            await client.ping()
            
            # Get info
            info = await client.info("server")
            
            latency = (datetime.utcnow() - start).total_seconds() * 1000
            await client.close()
            
            return ComponentHealth(
                name="redis",
                status=HealthStatus.HEALTHY,
                message="Redis connection successful",
                latency_ms=latency,
                details={
                    "redis_version": info.get("redis_version"),
                    "uptime_seconds": info.get("uptime_in_seconds"),
                },
            )
        
        except Exception as e:
            logger.error("health_check_redis_failed", error=str(e))
            return ComponentHealth(
                name="redis",
                status=HealthStatus.DEGRADED,  # Redis failure is degraded, not unhealthy
                message=f"Redis connection failed: {str(e)}",
            )
    
    async def check_external_api(
        self,
        name: str,
        url: str,
        timeout_seconds: float = 5.0,
    ) -> ComponentHealth:
        """Check external API health."""
        import httpx
        
        start = datetime.utcnow()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=timeout_seconds)
                response.raise_for_status()
            
            latency = (datetime.utcnow() - start).total_seconds() * 1000
            
            return ComponentHealth(
                name=name,
                status=HealthStatus.HEALTHY,
                message=f"{name} API reachable",
                latency_ms=latency,
            )
        
        except Exception as e:
            logger.warning(f"health_check_{name}_failed", error=str(e))
            return ComponentHealth(
                name=name,
                status=HealthStatus.DEGRADED,
                message=f"{name} API unreachable: {str(e)}",
            )
    
    async def check_disk_space(self) -> ComponentHealth:
        """Check available disk space."""
        import shutil
        
        try:
            total, used, free = shutil.disk_usage("/")
            free_pct = (free / total) * 100
            
            if free_pct < 5:
                status = HealthStatus.UNHEALTHY
                message = f"Critical: Only {free_pct:.1f}% disk space free"
            elif free_pct < 15:
                status = HealthStatus.DEGRADED
                message = f"Warning: Only {free_pct:.1f}% disk space free"
            else:
                status = HealthStatus.HEALTHY
                message = f"{free_pct:.1f}% disk space free"
            
            return ComponentHealth(
                name="disk",
                status=status,
                message=message,
                details={
                    "total_gb": round(total / (1024**3), 2),
                    "used_gb": round(used / (1024**3), 2),
                    "free_gb": round(free / (1024**3), 2),
                    "free_pct": round(free_pct, 2),
                },
            )
        
        except Exception as e:
            return ComponentHealth(
                name="disk",
                status=HealthStatus.DEGRADED,
                message=f"Could not check disk space: {str(e)}",
            )
    
    async def check_memory(self) -> ComponentHealth:
        """Check memory usage."""
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            used_pct = memory.percent
            
            if used_pct > 95:
                status = HealthStatus.UNHEALTHY
                message = f"Critical: {used_pct}% memory used"
            elif used_pct > 85:
                status = HealthStatus.DEGRADED
                message = f"Warning: {used_pct}% memory used"
            else:
                status = HealthStatus.HEALTHY
                message = f"{used_pct}% memory used"
            
            return ComponentHealth(
                name="memory",
                status=status,
                message=message,
                details={
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "used_pct": used_pct,
                },
            )
        
        except ImportError:
            return ComponentHealth(
                name="memory",
                status=HealthStatus.DEGRADED,
                message="psutil not available for memory check",
            )
        except Exception as e:
            return ComponentHealth(
                name="memory",
                status=HealthStatus.DEGRADED,
                message=f"Could not check memory: {str(e)}",
            )
    
    def _determine_overall_status(
        self,
        components: List[ComponentHealth],
    ) -> HealthStatus:
        """Determine overall health from components."""
        statuses = [c.status for c in components]
        
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY
    
    async def full_health_check(
        self,
        session_factory=None,
    ) -> HealthResponse:
        """
        Run full health check on all components.
        
        Results are cached for a short TTL to prevent overload.
        """
        # Check cache
        if self._last_health:
            age = (datetime.utcnow() - self._last_health.timestamp).total_seconds()
            if age < self._cache_ttl_seconds:
                return self._last_health
        
        # Run all checks in parallel
        tasks = [
            self.check_redis(),
            self.check_disk_space(),
            self.check_memory(),
        ]
        
        if session_factory:
            tasks.insert(0, self.check_database(session_factory))
        
        components = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        clean_components = []
        for comp in components:
            if isinstance(comp, Exception):
                clean_components.append(ComponentHealth(
                    name="unknown",
                    status=HealthStatus.UNHEALTHY,
                    message=str(comp),
                ))
            else:
                clean_components.append(comp)
        
        response = HealthResponse(
            status=self._determine_overall_status(clean_components),
            version=settings.app_version,
            environment=settings.environment,
            uptime_seconds=self.uptime_seconds,
            components=clean_components,
        )
        
        self._last_health = response
        return response
    
    async def liveness_check(self) -> LivenessResponse:
        """
        Simple liveness check.
        
        Returns true if the application is running.
        Used by Kubernetes liveness probe.
        """
        return LivenessResponse(alive=True)
    
    async def readiness_check(
        self,
        session_factory=None,
    ) -> ReadinessResponse:
        """
        Readiness check for serving traffic.
        
        Returns true if the application can handle requests.
        Used by Kubernetes readiness probe.
        """
        # Check critical dependencies
        if session_factory:
            db_health = await self.check_database(session_factory)
            if db_health.status == HealthStatus.UNHEALTHY:
                return ReadinessResponse(
                    ready=False,
                    reason="Database connection failed",
                )
        
        return ReadinessResponse(ready=True)


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get the global health checker instance."""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker

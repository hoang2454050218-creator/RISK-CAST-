"""API Routes.

Aggregates all API routers.
"""

from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.customers import router as customers_router
from app.api.routes.shipments import router as shipments_router
from app.api.routes.decisions import router as decisions_router
from app.api.routes.signals import router as signals_router
from app.api.routes.metrics import router as metrics_router
from app.api.routes.human import router as human_router
from app.api.routes.audit import router as audit_router
from app.api.routes.calibration import router as calibration_router
from app.api.routes.governance import router as governance_router
from app.api.routes.benchmark import router as benchmark_router
from app.api.routes.intelligence import router as intelligence_router

router = APIRouter()

# Include all routers
router.include_router(health_router, tags=["Health"])
router.include_router(metrics_router, tags=["Metrics"])
router.include_router(customers_router, prefix="/customers", tags=["Customers"])
router.include_router(shipments_router, prefix="/shipments", tags=["Shipments"])
router.include_router(decisions_router, prefix="/decisions", tags=["Decisions"])
router.include_router(signals_router, prefix="/signals", tags=["Signals"])
router.include_router(human_router, prefix="/human", tags=["Human-AI Collaboration"])
router.include_router(audit_router, prefix="/audit", tags=["Audit Trail"])
router.include_router(calibration_router, tags=["Calibration"])
router.include_router(governance_router, tags=["Governance"])
router.include_router(benchmark_router, tags=["Benchmark"])
router.include_router(intelligence_router, prefix="/intelligence", tags=["Intelligence"])

__all__ = ["router"]

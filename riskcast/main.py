"""
RiskCast V2 — FastAPI Application.

Entry point for the V2 API server.
Run: uvicorn riskcast.api.app:app --host 0.0.0.0 --port 8001 --reload

OMEN Integration:
  - POST /api/v1/signals/ingest  ← OMEN pushes signals here
  - POST /reconcile/run          ← replay missed signals
  - GET  /reconcile/status/{date}
  - GET  /reconcile/history/{date}
  - GET  /health                 ← health check
  - GET  /metrics                ← Prometheus metrics
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from riskcast.config import settings
from riskcast.db.engine import close_db, init_db
from riskcast.middleware.error_handler import ErrorHandlerMiddleware
from riskcast.middleware.rate_limit import RateLimitMiddleware
from riskcast.middleware.request_context import RequestContextMiddleware
from riskcast.middleware.security_headers import SecurityHeadersMiddleware
from riskcast.middleware.tenant import TenantMiddleware
from riskcast.services.cache import close_redis

# Import all routers
from riskcast.auth.router import router as auth_router
from riskcast.api.routers.companies import router as companies_router
from riskcast.api.routers.customers import router as customers_router
from riskcast.api.routers.orders import router as orders_router
from riskcast.api.routers.payments import router as payments_router
from riskcast.api.routers.routes_api import router as routes_router
from riskcast.api.routers.incidents import router as incidents_router
from riskcast.api.routers.import_csv import router as import_router
from riskcast.api.routers.signals import router as signals_router
from riskcast.api.routers.chat import router as chat_router
from riskcast.api.routers.events import router as events_router
from riskcast.api.routers.briefs import router as briefs_router
from riskcast.api.routers.feedback import router as feedback_router
from riskcast.api.routers.onboarding import router as onboarding_router
from riskcast.api.routers.dashboard import router as dashboard_router
from riskcast.api.routers.analytics import router as analytics_router
from riskcast.api.routers.audit_trail import router as audit_trail_router
from riskcast.api.routers.risk import router as risk_router
from riskcast.api.routers.decisions import router as decisions_router
from riskcast.api.routers.human import router as human_router
from riskcast.api.routers.outcomes import router as outcomes_router
from riskcast.api.routers.alerts import router as alerts_router
from riskcast.api.routers.pipeline import router as pipeline_router
from riskcast.api.routers.pipeline_process import router as pipeline_process_router
from riskcast.api.routers.ingest import router as ingest_router
from riskcast.api.routers.reconcile import router as reconcile_router
from riskcast.api.routers.metrics import router as metrics_router
from riskcast.api.routers.plan import router as plan_router

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown."""
    logger.info("riskcast_v2_starting", version=settings.app_version)
    if not settings.anthropic_api_key:
        logger.warning("anthropic_api_key_not_set", msg="Chat/AI features will return fallback responses")
    await init_db()
    yield
    await close_redis()
    await close_db()
    logger.info("riskcast_v2_shutdown")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        redirect_slashes=True,
        title="RiskCast V2",
        description=(
            "# RiskCast V2 — Decision Intelligence Platform\n\n"
            "Multi-tenant SaaS API for supply chain risk assessment, "
            "decision support, and outcome tracking.\n\n"
            "## Architecture\n"
            "- **Signal Pipeline**: OMEN → Ingest → Validate → Fuse → Assess\n"
            "- **Decision Engine**: Risk Assessment → Action Generation → Tradeoff Analysis → Escalation\n"
            "- **Learning Loop**: Outcome Recording → Accuracy Metrics → Flywheel Priors\n"
            "- **Alerting**: Rule Engine → Deduplication → Multi-channel Dispatch\n\n"
            "## Authentication\n"
            "All endpoints (except /health, /ready, /auth/*) require either:\n"
            "- `Authorization: Bearer <JWT>` header\n"
            "- `X-API-Key: <key>` header\n"
        ),
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_tags=[
            {"name": "health", "description": "Liveness and readiness probes"},
            {"name": "auth", "description": "Authentication (register, login, token)"},
            {"name": "dashboard", "description": "Aggregated dashboard metrics"},
            {"name": "analytics", "description": "Risk analytics and trends"},
            {"name": "signals", "description": "Signal monitoring and listing"},
            {"name": "risk-engine", "description": "Risk assessment engine (Bayesian + fusion + ensemble)"},
            {"name": "decisions", "description": "Decision generation with tradeoff analysis"},
            {"name": "human-review", "description": "Human review / escalation queue"},
            {"name": "outcomes", "description": "Outcome recording, accuracy, ROI"},
            {"name": "alerts", "description": "Alert rules, dispatch, early warning"},
            {"name": "pipeline", "description": "Pipeline health, integrity, traceability"},
            {"name": "audit", "description": "Audit trail with hash chain integrity"},
            {"name": "omen-ingest", "description": "OMEN signal ingest endpoint"},
            {"name": "reconcile", "description": "Ledger ↔ DB reconciliation"},
            {"name": "companies", "description": "Company settings"},
            {"name": "customers", "description": "Customer CRUD"},
            {"name": "orders", "description": "Order CRUD"},
            {"name": "payments", "description": "Payment CRUD"},
            {"name": "routes", "description": "Route CRUD"},
            {"name": "incidents", "description": "Incident management"},
            {"name": "chat", "description": "AI chat assistant (Claude)"},
            {"name": "briefs", "description": "Morning risk briefs"},
            {"name": "feedback", "description": "Suggestion feedback loop"},
            {"name": "events", "description": "Server-Sent Events stream"},
            {"name": "observability", "description": "Prometheus metrics"},
        ],
    )

    # ── Middleware (order matters — last added = outermost = first to process) ──
    # Error handler — catches everything, returns structured JSON
    app.add_middleware(ErrorHandlerMiddleware)

    # Request context — request_id, timing, structured logging
    app.add_middleware(RequestContextMiddleware)

    # Security headers (OWASP A05)
    app.add_middleware(SecurityHeadersMiddleware)

    # Rate limiter — per tenant / per API key, token bucket
    app.add_middleware(RateLimitMiddleware)

    # Tenant isolation (extracts JWT or API key, sets request.state)
    app.add_middleware(TenantMiddleware)

    # CORS — MUST be outermost so OPTIONS preflight is handled before auth
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routes ────────────────────────────────────────────────────────
    app.include_router(auth_router)
    app.include_router(companies_router)
    app.include_router(customers_router)
    app.include_router(orders_router)
    app.include_router(payments_router)
    app.include_router(routes_router)
    app.include_router(incidents_router)
    app.include_router(import_router)
    app.include_router(signals_router)
    app.include_router(chat_router)
    app.include_router(events_router)
    app.include_router(briefs_router)
    app.include_router(feedback_router)
    app.include_router(onboarding_router)

    # ── Data API Routes (Phase 2 — real data, zero mock) ─────────────
    app.include_router(dashboard_router)    # GET /api/v1/dashboard/summary
    app.include_router(analytics_router)    # GET /api/v1/analytics/*
    app.include_router(audit_trail_router)  # GET /api/v1/audit-trail

    # ── Risk Engine (Phase 3 — algorithm engine) ─────────────────────
    app.include_router(risk_router)         # GET /api/v1/risk/assess/*

    # ── Decision Support (Phase 4 — decision quality) ────────────────
    app.include_router(decisions_router)    # /api/v1/decisions/*
    app.include_router(human_router)        # /api/v1/human/escalations

    # ── Outcome Tracking (Phase 5 — irreplaceability) ────────────────
    app.include_router(outcomes_router)     # /api/v1/outcomes/*

    # ── Alerting & Early Warning (Phase 6 — risk reduction) ──────────
    app.include_router(alerts_router)       # /api/v1/alerts/*

    # ── Pipeline Integrity (Phase 7 — OMEN bridge) ───────────────────
    app.include_router(pipeline_router)         # /api/v1/pipeline/*
    app.include_router(pipeline_process_router)  # POST /api/v1/pipeline/process

    # ── Plan & Subscription ──────────────────────────────────────────
    app.include_router(plan_router)            # /api/v1/plan/*

    # ── OMEN Integration Routes ──────────────────────────────────────
    app.include_router(ingest_router)       # POST /api/v1/signals/ingest
    app.include_router(reconcile_router)    # POST /reconcile/run, GET /reconcile/...
    app.include_router(metrics_router)      # GET /metrics

    # ── Health Check (Liveness Probe) ─────────────────────────────────
    @app.get("/health", tags=["health"])
    async def health():
        """
        Liveness probe — is the process alive?

        Returns 200 if the API can respond. Does NOT check dependencies.
        Use /ready for full dependency checks.
        """
        return {
            "status": "ok",
            "version": settings.app_version,
            "service": "riskcast-v2",
        }

    # ── Readiness Check (full dependency probe) ────────────────────
    @app.get("/ready", tags=["health"])
    async def readiness():
        """
        Readiness probe — can the service handle requests?

        Checks: database, Redis, OMEN, ingest pipeline.
        Returns 200 if DB is ok (hard dependency), 503 otherwise.
        """
        import asyncio
        from datetime import datetime, timezone

        checks: dict = {"api": "ok"}
        degraded_services: list[str] = []

        # Database check (hard dependency)
        try:
            from sqlalchemy import text as sa_text
            from riskcast.db.engine import get_engine
            async with get_engine().connect() as conn:
                await asyncio.wait_for(
                    conn.execute(sa_text("SELECT 1")),
                    timeout=settings.health_check_timeout_seconds,
                )
            checks["database"] = "ok"
        except Exception:
            checks["database"] = "unavailable"

        # Redis check (soft dependency)
        try:
            from riskcast.services.cache import get_redis
            r = await get_redis()
            if r:
                await asyncio.wait_for(r.ping(), timeout=2)
                checks["redis"] = "ok"
            else:
                checks["redis"] = "not_configured"
        except Exception:
            checks["redis"] = "unavailable"
            degraded_services.append("redis")

        # OMEN check (soft dependency)
        try:
            from riskcast.services.omen_client import OmenClient
            omen = OmenClient(base_url=settings.omen_url)
            healthy = await asyncio.wait_for(omen.health_check(), timeout=10)
            checks["omen"] = "ok" if healthy else "unavailable"
        except Exception:
            checks["omen"] = "unavailable"
            degraded_services.append("omen")

        # Ingest pipeline metrics
        try:
            from riskcast.services.ingest_service import get_ingest_metrics
            m = get_ingest_metrics()
            checks["ingest_pipeline"] = {
                "total_received": m["total_received"],
                "total_ingested": m["total_ingested"],
                "total_duplicates": m["total_duplicates"],
                "total_errors": m["total_errors"],
            }
        except Exception:
            checks["ingest_pipeline"] = "unavailable"

        # Overall status: DB is hard dependency, rest are soft
        db_ok = checks["database"] == "ok"
        status = "ok" if db_ok and not degraded_services else "degraded" if db_ok else "unavailable"
        status_code = 200 if db_ok else 503

        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=status_code,
            content={
                "status": status,
                "version": settings.app_version,
                "service": "riskcast-v2",
                "environment": settings.environment,
                "checks": checks,
                "degraded_services": degraded_services,
                "timestamp": datetime.utcnow().isoformat(),
                "config": {
                    "severity_bands": {
                        "critical": f">= {settings.severity_critical_threshold}",
                        "high": f">= {settings.severity_high_threshold}",
                        "moderate": f">= {settings.severity_moderate_threshold}",
                    },
                    "escalation_thresholds": {
                        "exposure_usd": settings.escalation_exposure_threshold,
                        "confidence_floor": settings.escalation_confidence_floor,
                        "risk_ceiling": settings.escalation_risk_ceiling,
                    },
                    "alert_cooldown_minutes": settings.alert_cooldown_minutes,
                    "rate_limit": f"{settings.rate_limit_default}/min",
                },
            },
        )

    # ── System Info (debug only) ───────────────────────────────────
    if settings.debug:
        @app.get("/system/info", tags=["health"])
        async def system_info():
            """Debug-only: system configuration summary."""
            return {
                "environment": settings.environment,
                "debug": settings.debug,
                "database_url": settings.database_url[:30] + "***",
                "omen_url": settings.omen_url,
                "engine_config": {
                    "ensemble_weights": {
                        "fusion": settings.ensemble_weight_fusion,
                        "bayesian": settings.ensemble_weight_bayesian,
                    },
                    "risk_weights": {
                        "customer": settings.weight_customer,
                        "route": settings.weight_route,
                        "value": settings.weight_value,
                        "new_customer": settings.weight_new_customer,
                    },
                    "halflife_default_hours": settings.halflife_default,
                    "temporal_min_weight": settings.temporal_min_weight,
                    "composite_emit_threshold": settings.composite_emit_threshold,
                },
            }

    return app


# Application instance
app = create_app()

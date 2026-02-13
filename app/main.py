"""NEXUS RISKCAST - Main Application Entry Point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.core.config import settings
from app.core.database import init_db, close_connections
from app.core.middleware import setup_middleware
from app.api.routes import router as api_router
from app.api.routes.health import set_startup_time

# Import new core services
from app.core import (
    init_core_services,
    close_core_services,
    get_core_health,
    tracing_middleware,
)


# Configure structlog with request ID injection
def add_request_context(logger, method_name, event_dict):
    """Add request context to logs."""
    from app.core.middleware import request_id_var, correlation_id_var, customer_id_var
    
    request_id = request_id_var.get()
    if request_id:
        event_dict["request_id"] = request_id
    
    correlation_id = correlation_id_var.get()
    if correlation_id:
        event_dict["correlation_id"] = correlation_id
    
    customer_id = customer_id_var.get()
    if customer_id:
        event_dict["customer_id"] = customer_id
    
    return event_dict


structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        add_request_context,  # Add request context to all logs
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if settings.log_format == "json"
        else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


# ============================================================================
# LIFESPAN
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info(
        "nexus_riskcast_starting",
        version=settings.app_version,
        environment=settings.environment,
    )

    # Set startup time for health checks
    set_startup_time()

    # Initialize core services (cache, tracing, encryption, events, circuit breakers)
    try:
        await init_core_services(
            redis_url=getattr(settings, 'redis_url', None),
            encryption_key=getattr(settings, 'encryption_key', None),
            use_redis_events=getattr(settings, 'use_redis_events', False),
            service_name="riskcast",
        )
        logger.info("core_services_initialized")
    except Exception as e:
        logger.warning("core_services_init_failed", error=str(e))
        # Continue - services will use fallback modes

    # Initialize database
    try:
        await init_db()
        logger.info("database_initialized")
    except Exception as e:
        logger.warning("database_init_failed", error=str(e))
        # Continue anyway - might be using in-memory mode

    # Initialize ML pipeline
    try:
        from app.ml import get_ml_pipeline
        ml_pipeline = get_ml_pipeline()
        logger.info("ml_pipeline_initialized")
    except Exception as e:
        logger.warning("ml_pipeline_init_failed", error=str(e))

    # Start services
    try:
        from app.omen.service import get_omen_service
        from app.oracle.service import get_oracle_service

        omen = get_omen_service()
        await omen.start()

        oracle = get_oracle_service()
        await oracle.start()

        logger.info("services_started")
    except Exception as e:
        logger.warning("services_start_failed", error=str(e))

    # Verify core health
    try:
        health = await get_core_health()
        logger.info(
            "startup_health_check",
            status=health["status"],
            components=list(health["components"].keys()),
        )
    except Exception as e:
        logger.warning("startup_health_check_failed", error=str(e))

    logger.info(
        "nexus_riskcast_ready",
        host=settings.host,
        port=settings.port,
        docs_url="/docs",
    )

    yield

    # Shutdown
    logger.info("nexus_riskcast_shutting_down")

    # Stop services
    try:
        omen = get_omen_service()
        await omen.stop()

        oracle = get_oracle_service()
        await oracle.stop()
    except Exception as e:
        logger.warning("services_stop_failed", error=str(e))

    # Close database connections
    await close_connections()

    # Close core services (cache, tracing, events)
    try:
        await close_core_services()
        logger.info("core_services_closed")
    except Exception as e:
        logger.warning("core_services_close_failed", error=str(e))

    logger.info("nexus_riskcast_stopped")


# ============================================================================
# APP FACTORY
# ============================================================================


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        description="""
# NEXUS RISKCAST - Supply Chain Decision Intelligence

**Transform supply chain disruptions into actionable decisions.**

RISKCAST is the Decision Engine of the NEXUS platform:
- OMEN provides signals (what might happen)
- ORACLE provides reality (what IS happening)
- RISKCAST provides decisions (what to DO about it)

## Key Features

- **7 Questions Framework**: Every decision answers 7 critical questions
- **Personalized Decisions**: Based on your specific shipments and exposure
- **Dollar-Denominated**: All costs in USD, all delays in days
- **Deadline-Driven**: Clear action deadlines and inaction costs

## API Sections

- **Health**: Service health and readiness checks
- **Customers**: Customer profile management
- **Shipments**: Shipment tracking and management
- **Decisions**: Decision generation and retrieval
- **Signals**: OMEN signal queries and ORACLE intelligence
        """,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=[
            {"name": "Health", "description": "Health and readiness checks"},
            {"name": "Metrics", "description": "Prometheus metrics and observability"},
            {"name": "Customers", "description": "Customer profile CRUD operations"},
            {"name": "Shipments", "description": "Shipment management"},
            {"name": "Decisions", "description": "Decision generation and retrieval"},
            {"name": "Signals", "description": "OMEN signals and ORACLE intelligence"},
            {"name": "Human-AI Collaboration", "description": "Human override, escalation, and feedback"},
            {"name": "Audit Trail", "description": "Decision audit and compliance logging"},
            {"name": "Calibration", "description": "Confidence calibration and validation"},
            {"name": "Governance", "description": "AI governance and model registry"},
            {"name": "Benchmark", "description": "Benchmark evidence and flywheel metrics"},
        ],
        lifespan=lifespan,
    )

    # Setup all middleware (security, logging, rate limiting, etc.)
    setup_middleware(app)
    
    # CORS middleware (added after custom middleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes
    app.include_router(api_router, prefix="/api/v1")

    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint - service info."""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "status": "operational",
            "environment": settings.environment,
            "philosophy": "OMEN sees the future. RISKCAST tells you what to DO.",
            "docs": "/docs",
            "api": "/api/v1",
        }

    return app


# Create app instance
app = create_app()


# ============================================================================
# DEVELOPMENT SERVER
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )

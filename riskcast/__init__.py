"""
RiskCast V2 — Decision Intelligence Platform.

Architecture:
    riskcast/
    ├── api/             # FastAPI routers (HTTP layer)
    ├── auth/            # JWT + API key authentication, RBAC
    ├── db/              # SQLAlchemy models, engine, repositories
    ├── middleware/       # Tenant isolation, rate limiting, error handling
    ├── schemas/         # Pydantic request/response models
    ├── services/        # Business logic (ingest, LLM, cache, etc.)
    ├── analyzers/       # Internal signal generators (order, payment, route)
    ├── engine/          # Risk engine (Bayesian, fusion, ensemble, temporal)
    ├── decisions/       # Decision support (actions, tradeoffs, escalation)
    ├── outcomes/        # Outcome tracking (recorder, accuracy, ROI, flywheel)
    ├── alerting/        # Alert engine (rules, channels, dedup, early warning)
    └── pipeline/        # Pipeline integrity (validator, health, traceability)

Module Boundaries:
    - OMEN is SIGNAL ENGINE ONLY — it sends SignalEvent, never decisions
    - RiskCast is DECISION ENGINE — it receives signals, produces decisions
    - Every number on screen traces to a real DB query
    - Every decision has an audit trail
    - Every confidence score has uncertainty bounds

Data Flow:
    OMEN → Ingest → Validate → Ledger → DB → Risk Engine → Decision Engine
    → Outcome Tracker → Flywheel → Updated Priors

Version: 2.0.0
"""

__version__ = "2.0.0"

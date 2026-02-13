"""
Plan & Subscription API Router.

Returns the current company's plan details, limits, usage, and available plans.
Handles plan upgrades/downgrades.
"""

from typing import Optional

import structlog
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from sqlalchemy import text, select

from riskcast.db.engine import get_db_session
from riskcast.db.models import Company

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/plan", tags=["plan"])


# ──────────────────────────────────────────────────────────
# Plan Definitions (single source of truth)
# ──────────────────────────────────────────────────────────

PLAN_DEFINITIONS = {
    "free": {
        "name": "Monitor",
        "display_name": "Monitor",
        "price_monthly": 0,
        "price_annual_monthly": 0,
        "limits": {
            "max_shipments": 5,
            "max_customers": 2,
            "max_routes": 1,
            "max_team_members": 1,
            "max_alerts_per_day": 3,
            "max_chokepoints": 1,
            "api_rate_limit_per_minute": 10,
            "historical_data_days": 7,
        },
        "features": {
            "dashboard": True,
            "dashboard_readonly": True,
            "signals_monitoring": True,
            "red_sea_monitoring": True,
            "weekly_digest": True,
            "decision_engine": False,
            "multi_channel_alerts": False,
            "email_alerts": False,
            "whatsapp_alerts": False,
            "discord_alerts": False,
            "analytics": False,
            "api_access": False,
            "scenario_analysis": False,
            "exposure_mapping": False,
            "custom_integrations": False,
            "dedicated_support": False,
            "sla_guarantee": False,
            "on_premise": False,
            "seven_question_format": False,
            "human_review": False,
            "audit_trail": False,
            "morning_briefs": False,
            "ai_chat": False,
        },
    },
    "starter": {
        "name": "Growth",
        "display_name": "Growth",
        "price_monthly": 199,
        "price_annual_monthly": 159,
        "limits": {
            "max_shipments": 100,
            "max_customers": 15,
            "max_routes": 5,
            "max_team_members": 3,
            "max_alerts_per_day": 25,
            "max_chokepoints": 3,
            "api_rate_limit_per_minute": 60,
            "historical_data_days": 30,
        },
        "features": {
            "dashboard": True,
            "dashboard_readonly": False,
            "signals_monitoring": True,
            "red_sea_monitoring": True,
            "weekly_digest": True,
            "decision_engine": True,
            "multi_channel_alerts": False,
            "email_alerts": True,
            "whatsapp_alerts": False,
            "discord_alerts": False,
            "analytics": True,
            "api_access": False,
            "scenario_analysis": False,
            "exposure_mapping": False,
            "custom_integrations": False,
            "dedicated_support": False,
            "sla_guarantee": False,
            "on_premise": False,
            "seven_question_format": True,
            "human_review": False,
            "audit_trail": False,
            "morning_briefs": True,
            "ai_chat": False,
        },
    },
    "professional": {
        "name": "Professional",
        "display_name": "Professional",
        "price_monthly": 599,
        "price_annual_monthly": 479,
        "limits": {
            "max_shipments": 500,
            "max_customers": 50,
            "max_routes": 20,
            "max_team_members": 10,
            "max_alerts_per_day": 100,
            "max_chokepoints": 10,
            "api_rate_limit_per_minute": 300,
            "historical_data_days": 90,
        },
        "features": {
            "dashboard": True,
            "dashboard_readonly": False,
            "signals_monitoring": True,
            "red_sea_monitoring": True,
            "weekly_digest": True,
            "decision_engine": True,
            "multi_channel_alerts": True,
            "email_alerts": True,
            "whatsapp_alerts": True,
            "discord_alerts": True,
            "analytics": True,
            "api_access": True,
            "scenario_analysis": True,
            "exposure_mapping": True,
            "custom_integrations": False,
            "dedicated_support": False,
            "sla_guarantee": False,
            "on_premise": False,
            "seven_question_format": True,
            "human_review": True,
            "audit_trail": True,
            "morning_briefs": True,
            "ai_chat": True,
        },
    },
    "enterprise": {
        "name": "Enterprise",
        "display_name": "Enterprise",
        "price_monthly": 1499,
        "price_annual_monthly": 1199,
        "limits": {
            "max_shipments": 99999,
            "max_customers": 99999,
            "max_routes": 99999,
            "max_team_members": 100,
            "max_alerts_per_day": 99999,
            "max_chokepoints": 99999,
            "api_rate_limit_per_minute": 1000,
            "historical_data_days": 365,
        },
        "features": {
            "dashboard": True,
            "dashboard_readonly": False,
            "signals_monitoring": True,
            "red_sea_monitoring": True,
            "weekly_digest": True,
            "decision_engine": True,
            "multi_channel_alerts": True,
            "email_alerts": True,
            "whatsapp_alerts": True,
            "discord_alerts": True,
            "analytics": True,
            "api_access": True,
            "scenario_analysis": True,
            "exposure_mapping": True,
            "custom_integrations": True,
            "dedicated_support": True,
            "sla_guarantee": True,
            "on_premise": True,
            "seven_question_format": True,
            "human_review": True,
            "audit_trail": True,
            "morning_briefs": True,
            "ai_chat": True,
        },
    },
}


# ──────────────────────────────────────────────────────────
# Response Schemas
# ──────────────────────────────────────────────────────────


class PlanLimits(BaseModel):
    max_shipments: int
    max_customers: int
    max_routes: int
    max_team_members: int
    max_alerts_per_day: int
    max_chokepoints: int
    api_rate_limit_per_minute: int
    historical_data_days: int


class PlanFeatures(BaseModel):
    dashboard: bool = True
    dashboard_readonly: bool = False
    signals_monitoring: bool = True
    red_sea_monitoring: bool = True
    weekly_digest: bool = True
    decision_engine: bool = False
    multi_channel_alerts: bool = False
    email_alerts: bool = False
    whatsapp_alerts: bool = False
    discord_alerts: bool = False
    analytics: bool = False
    api_access: bool = False
    scenario_analysis: bool = False
    exposure_mapping: bool = False
    custom_integrations: bool = False
    dedicated_support: bool = False
    sla_guarantee: bool = False
    on_premise: bool = False
    seven_question_format: bool = False
    human_review: bool = False
    audit_trail: bool = False
    morning_briefs: bool = False
    ai_chat: bool = False


class PlanUsage(BaseModel):
    shipments: int = 0
    customers: int = 0
    routes: int = 0
    team_members: int = 0
    signals_active: int = 0


class CurrentPlanResponse(BaseModel):
    plan_id: str
    plan_name: str
    display_name: str
    price_monthly: int
    price_annual_monthly: int
    limits: PlanLimits
    features: PlanFeatures
    usage: PlanUsage
    company_name: str
    company_industry: Optional[str] = None
    trial_active: bool = False
    trial_ends_at: Optional[str] = None


class AvailablePlan(BaseModel):
    plan_id: str
    name: str
    display_name: str
    price_monthly: int
    price_annual_monthly: int
    limits: PlanLimits
    features: PlanFeatures
    is_current: bool = False
    is_popular: bool = False


class AvailablePlansResponse(BaseModel):
    plans: list[AvailablePlan]
    current_plan: str


class PlanUpgradeRequest(BaseModel):
    plan_id: str = Field(..., pattern=r"^(free|starter|professional|enterprise)$")


class PlanUpgradeResponse(BaseModel):
    success: bool
    plan_id: str
    plan_name: str
    message: str


# ──────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────


@router.get("/current", response_model=CurrentPlanResponse)
async def get_current_plan(request: Request):
    """Get the current company's plan, limits, features, and usage."""
    company_id = getattr(request.state, "company_id", None)
    if not company_id:
        # Fallback for unauthenticated requests
        return _build_plan_response("free", "Unknown", None, PlanUsage())

    async with get_db_session() as session:
        # Get company info
        result = await session.execute(
            select(Company).where(Company.id == company_id)
        )
        company = result.scalar_one_or_none()
        if not company:
            return _build_plan_response("free", "Unknown", None, PlanUsage())

        plan_id = company.plan or "starter"
        company_name = company.name
        company_industry = company.industry

        # Calculate usage
        usage = await _get_usage(session, company_id)

    return _build_plan_response(plan_id, company_name, company_industry, usage)


@router.get("/available", response_model=AvailablePlansResponse)
async def get_available_plans(request: Request):
    """Get all available plans with comparison."""
    company_id = getattr(request.state, "company_id", None)
    current_plan = "free"

    if company_id:
        async with get_db_session() as session:
            result = await session.execute(
                select(Company.plan).where(Company.id == company_id)
            )
            row = result.scalar_one_or_none()
            if row:
                current_plan = row

    plans = []
    for plan_id, defn in PLAN_DEFINITIONS.items():
        plans.append(AvailablePlan(
            plan_id=plan_id,
            name=defn["name"],
            display_name=defn["display_name"],
            price_monthly=defn["price_monthly"],
            price_annual_monthly=defn["price_annual_monthly"],
            limits=PlanLimits(**defn["limits"]),
            features=PlanFeatures(**defn["features"]),
            is_current=(plan_id == current_plan),
            is_popular=(plan_id == "professional"),
        ))

    return AvailablePlansResponse(plans=plans, current_plan=current_plan)


@router.post("/upgrade", response_model=PlanUpgradeResponse)
async def upgrade_plan(request: Request, body: PlanUpgradeRequest):
    """Upgrade or change the company's plan."""
    company_id = getattr(request.state, "company_id", None)
    if not company_id:
        return PlanUpgradeResponse(
            success=False, plan_id=body.plan_id,
            plan_name="", message="Not authenticated"
        )

    if body.plan_id not in PLAN_DEFINITIONS:
        return PlanUpgradeResponse(
            success=False, plan_id=body.plan_id,
            plan_name="", message="Invalid plan ID"
        )

    async with get_db_session() as session:
        await session.execute(
            text("UPDATE v2_companies SET plan = :plan, updated_at = NOW() WHERE id = :cid"),
            {"plan": body.plan_id, "cid": str(company_id)},
        )

    plan_name = PLAN_DEFINITIONS[body.plan_id]["display_name"]
    logger.info("plan_upgraded", company_id=str(company_id), new_plan=body.plan_id)

    return PlanUpgradeResponse(
        success=True,
        plan_id=body.plan_id,
        plan_name=plan_name,
        message=f"Successfully upgraded to {plan_name} plan!",
    )


# ──────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────


async def _get_usage(session, company_id) -> PlanUsage:
    """Get current usage counts for a company."""
    cid = str(company_id)

    orders_q = await session.execute(
        text("SELECT COUNT(*) FROM v2_orders WHERE company_id = :cid AND status != 'completed'"),
        {"cid": cid},
    )
    customers_q = await session.execute(
        text("SELECT COUNT(*) FROM v2_customers WHERE company_id = :cid"),
        {"cid": cid},
    )
    routes_q = await session.execute(
        text("SELECT COUNT(*) FROM v2_routes WHERE company_id = :cid AND is_active = true"),
        {"cid": cid},
    )
    users_q = await session.execute(
        text("SELECT COUNT(*) FROM v2_users WHERE company_id = :cid"),
        {"cid": cid},
    )
    signals_q = await session.execute(
        text("SELECT COUNT(*) FROM v2_signals WHERE company_id = :cid AND is_active = true"),
        {"cid": cid},
    )

    return PlanUsage(
        shipments=orders_q.scalar() or 0,
        customers=customers_q.scalar() or 0,
        routes=routes_q.scalar() or 0,
        team_members=users_q.scalar() or 0,
        signals_active=signals_q.scalar() or 0,
    )


def _build_plan_response(
    plan_id: str,
    company_name: str,
    company_industry: Optional[str],
    usage: PlanUsage,
) -> CurrentPlanResponse:
    """Build the plan response from definition + usage."""
    defn = PLAN_DEFINITIONS.get(plan_id, PLAN_DEFINITIONS["free"])

    return CurrentPlanResponse(
        plan_id=plan_id,
        plan_name=defn["name"],
        display_name=defn["display_name"],
        price_monthly=defn["price_monthly"],
        price_annual_monthly=defn["price_annual_monthly"],
        limits=PlanLimits(**defn["limits"]),
        features=PlanFeatures(**defn["features"]),
        usage=usage,
        company_name=company_name,
        company_industry=company_industry,
    )

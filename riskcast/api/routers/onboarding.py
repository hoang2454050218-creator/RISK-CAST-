"""
Onboarding API — Guided setup wizard for new companies.

GET  /onboarding/status     — Check onboarding progress
POST /onboarding/profile    — Update company profile
GET  /onboarding/templates  — Get CSV templates for data import
"""

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.api.deps import get_company_id, get_db
from riskcast.db.models import Customer, Incident, Order, Payment, Route
from riskcast.db.repositories.company import company_repo

router = APIRouter(prefix="/api/v1/onboarding", tags=["onboarding"])


class OnboardingStatus(BaseModel):
    """Tracks what the user has completed."""
    company_profile: bool = False
    customers_imported: bool = False
    routes_imported: bool = False
    orders_imported: bool = False
    payments_imported: bool = False
    incidents_imported: bool = False
    first_scan_done: bool = False
    completion_pct: int = 0


class ProfileUpdate(BaseModel):
    industry: str | None = Field(default=None, max_length=100)
    timezone: str | None = Field(default=None, max_length=50)


@router.get("/status", response_model=OnboardingStatus)
async def get_onboarding_status(
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """Check what onboarding steps have been completed."""
    company = await company_repo.get_by_id(db, company_id)

    # Count records in each table
    counts = {}
    for model, key in [
        (Customer, "customers_imported"),
        (Route, "routes_imported"),
        (Order, "orders_imported"),
        (Payment, "payments_imported"),
        (Incident, "incidents_imported"),
    ]:
        result = await db.execute(select(func.count()).select_from(model))
        counts[key] = result.scalar_one() > 0

    # Check signals
    from riskcast.db.models import Signal
    sig_count = await db.execute(select(func.count()).select_from(Signal))
    first_scan = sig_count.scalar_one() > 0

    # Profile completeness
    profile_done = bool(company and company.industry)

    steps = {
        "company_profile": profile_done,
        **counts,
        "first_scan_done": first_scan,
    }

    completed = sum(1 for v in steps.values() if v)
    total = len(steps)

    return OnboardingStatus(
        **steps,
        completion_pct=round(completed / total * 100),
    )


@router.post("/profile")
async def update_profile(
    body: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """Update company profile during onboarding."""
    updates = body.model_dump(exclude_unset=True)
    company = await company_repo.update(db, company_id, **updates)
    return {"status": "updated", "company": company.name if company else None}


@router.get("/templates")
async def get_csv_templates():
    """Return CSV template definitions for data import."""
    return {
        "templates": [
            {
                "entity": "customers",
                "columns": ["name", "code", "tier", "contact_email", "contact_phone", "payment_terms"],
                "required": ["name"],
                "example_row": "Công ty ABC,ABC,standard,abc@example.vn,+84901234567,30",
            },
            {
                "entity": "routes",
                "columns": ["name", "origin", "destination", "transport_mode", "avg_duration_days"],
                "required": ["name", "origin", "destination"],
                "example_row": "HCM-HP,TP HCM,Hải Phòng,road,3",
            },
            {
                "entity": "orders",
                "columns": ["order_number", "status", "total_value", "currency", "origin", "destination", "expected_date"],
                "required": ["order_number", "status"],
                "example_row": "ORD-001,pending,50000000,VND,HCM,HP,2026-03-01",
            },
            {
                "entity": "payments",
                "columns": ["amount", "currency", "status", "due_date", "paid_date"],
                "required": ["amount", "status", "due_date"],
                "example_row": "25000000,VND,paid,2026-02-15,2026-02-14",
            },
            {
                "entity": "incidents",
                "columns": ["type", "severity", "description"],
                "required": ["type", "severity"],
                "example_row": "delivery_delay,medium,Hàng trễ 3 ngày do mưa lớn",
            },
        ]
    }

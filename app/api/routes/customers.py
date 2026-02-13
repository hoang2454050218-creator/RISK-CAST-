"""Customer API Endpoints.

CRUD operations for customer profiles.
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.riskcast.constants import RiskTolerance
from app.riskcast.schemas.customer import CustomerProfile, CustomerContext
from app.riskcast.repos.customer import (
    PostgresCustomerRepository,
    CustomerNotFoundError,
    DuplicateCustomerError,
)

router = APIRouter()


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================


class AlertPreferencesRequest(BaseModel):
    """Alert fine-tuning preferences."""

    min_probability: float = Field(default=0.5, ge=0.0, le=1.0, description="Minimum probability to trigger alert")
    min_exposure_usd: float = Field(default=0.0, ge=0.0, description="Minimum exposure to trigger alert")
    quiet_hours_start: Optional[str] = Field(default=None, description="Quiet hours start (HH:MM)")
    quiet_hours_end: Optional[str] = Field(default=None, description="Quiet hours end (HH:MM)")
    max_alerts_per_day: int = Field(default=10, ge=1, le=100, description="Maximum alerts per day")
    include_inaction_cost: bool = Field(default=True, description="Include cost of not acting")
    include_confidence: bool = Field(default=True, description="Include confidence scores")


class CustomerCreateRequest(BaseModel):
    """Request to create a new customer."""

    customer_id: str = Field(min_length=1, max_length=50, description="Unique customer ID")
    company_name: str = Field(min_length=1, max_length=200)
    industry: Optional[str] = Field(default=None, max_length=100)
    primary_phone: str = Field(min_length=8, max_length=30, description="WhatsApp number with country code")
    secondary_phone: Optional[str] = None
    email: Optional[str] = None
    risk_tolerance: RiskTolerance = RiskTolerance.BALANCED
    primary_routes: list[str] = Field(default_factory=list, description="List of route codes")
    tier: str = Field(default="standard")
    # Extended fields for full system capability
    cargo_types: list[str] = Field(default_factory=list, description="Types of cargo shipped")
    company_description: Optional[str] = Field(default=None, max_length=2000, description="Business description for AI context")
    language: str = Field(default="en", max_length=10, description="Preferred alert language")
    timezone: str = Field(default="UTC", max_length=50, description="Customer timezone")
    max_reroute_premium_pct: float = Field(default=0.5, ge=0.0, le=2.0, description="Max acceptable reroute cost premium (0.0-2.0)")
    notification_enabled: bool = Field(default=True, description="Master notification toggle")
    whatsapp_enabled: bool = Field(default=True, description="WhatsApp channel enabled")
    email_enabled: bool = Field(default=True, description="Email channel enabled")
    sms_enabled: bool = Field(default=False, description="SMS channel enabled")
    alert_preferences: Optional[AlertPreferencesRequest] = Field(default=None, description="Alert fine-tuning")

    @field_validator("primary_phone", "secondary_phone", mode="before")
    @classmethod
    def normalize_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        # Remove spaces and ensure starts with +
        v = v.replace(" ", "").replace("-", "")
        if not v.startswith("+"):
            v = "+" + v
        return v


class CustomerUpdateRequest(BaseModel):
    """Request to update customer profile."""

    company_name: Optional[str] = None
    industry: Optional[str] = None
    primary_phone: Optional[str] = None
    secondary_phone: Optional[str] = None
    email: Optional[str] = None
    risk_tolerance: Optional[RiskTolerance] = None
    notification_enabled: Optional[bool] = None
    whatsapp_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    primary_routes: Optional[list[str]] = None
    tier: Optional[str] = None


class CustomerResponse(BaseModel):
    """Customer profile response."""

    customer_id: str
    company_name: str
    industry: Optional[str]
    primary_phone: str
    secondary_phone: Optional[str]
    email: Optional[str]
    risk_tolerance: str
    notification_enabled: bool
    whatsapp_enabled: bool
    email_enabled: bool
    primary_routes: list[str]
    relevant_chokepoints: list[str]
    is_active: bool
    tier: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_profile(cls, profile: CustomerProfile) -> "CustomerResponse":
        return cls(
            customer_id=profile.customer_id,
            company_name=profile.company_name,
            industry=profile.industry,
            primary_phone=profile.primary_phone,
            secondary_phone=profile.secondary_phone,
            email=profile.email,
            risk_tolerance=profile.risk_tolerance.value,
            notification_enabled=profile.notification_enabled,
            whatsapp_enabled=profile.whatsapp_enabled,
            email_enabled=profile.email_enabled,
            primary_routes=profile.primary_routes,
            relevant_chokepoints=profile.relevant_chokepoints,
            is_active=profile.is_active,
            tier=profile.tier,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )


class CustomerListResponse(BaseModel):
    """Paginated list of customers."""

    items: list[CustomerResponse]
    total: int
    page: int
    page_size: int


# ============================================================================
# DEPENDENCIES
# ============================================================================


def get_repository(session: AsyncSession = Depends(get_db_session)) -> PostgresCustomerRepository:
    """Get customer repository with database session."""
    return PostgresCustomerRepository(session)


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create customer",
    description="Create a new customer profile",
)
async def create_customer(
    request: CustomerCreateRequest,
    repo: PostgresCustomerRepository = Depends(get_repository),
) -> CustomerResponse:
    """
    Create a new customer profile.

    - **customer_id**: Unique identifier (e.g., "CUST-001")
    - **company_name**: Company name
    - **primary_phone**: WhatsApp number with country code
    - **primary_routes**: List of trading routes (e.g., ["CNSHA-NLRTM"])
    """
    try:
        profile = CustomerProfile(
            customer_id=request.customer_id,
            company_name=request.company_name,
            industry=request.industry,
            primary_phone=request.primary_phone,
            secondary_phone=request.secondary_phone,
            email=request.email,
            risk_tolerance=request.risk_tolerance,
            primary_routes=request.primary_routes,
            tier=request.tier,
        )

        created = await repo.create_profile(profile)
        return CustomerResponse.from_profile(created)

    except DuplicateCustomerError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Customer {request.customer_id} already exists",
        )


@router.get(
    "/{customer_id}",
    response_model=CustomerResponse,
    summary="Get customer",
    description="Get customer profile by ID",
)
async def get_customer(
    customer_id: str,
    repo: PostgresCustomerRepository = Depends(get_repository),
) -> CustomerResponse:
    """Get customer profile by ID."""
    profile = await repo.get_profile(customer_id)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {customer_id} not found",
        )

    return CustomerResponse.from_profile(profile)


@router.patch(
    "/{customer_id}",
    response_model=CustomerResponse,
    summary="Update customer",
    description="Update customer profile fields",
)
async def update_customer(
    customer_id: str,
    request: CustomerUpdateRequest,
    repo: PostgresCustomerRepository = Depends(get_repository),
) -> CustomerResponse:
    """Update customer profile fields."""
    # Filter out None values
    updates = {k: v for k, v in request.model_dump().items() if v is not None}

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    updated = await repo.update_profile(customer_id, **updates)

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {customer_id} not found",
        )

    return CustomerResponse.from_profile(updated)


@router.delete(
    "/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete customer",
    description="Delete customer profile and all associated data",
)
async def delete_customer(
    customer_id: str,
    repo: PostgresCustomerRepository = Depends(get_repository),
):
    """Delete customer profile."""
    deleted = await repo.delete_profile(customer_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {customer_id} not found",
        )

    return None


@router.get(
    "",
    response_model=CustomerListResponse,
    summary="List customers",
    description="List all customers with pagination",
)
async def list_customers(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    repo: PostgresCustomerRepository = Depends(get_repository),
) -> CustomerListResponse:
    """List customers with pagination."""
    customers = await repo.get_all_customers()
    total = len(customers)

    # Manual pagination (ideally done in SQL)
    start = (page - 1) * page_size
    end = start + page_size
    page_customers = customers[start:end]

    return CustomerListResponse(
        items=[CustomerResponse.from_profile(c) for c in page_customers],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/by-phone/{phone}",
    response_model=CustomerResponse,
    summary="Get customer by phone",
    description="Find customer by phone number",
)
async def get_customer_by_phone(
    phone: str,
    repo: PostgresCustomerRepository = Depends(get_repository),
) -> CustomerResponse:
    """Get customer by phone number."""
    # Normalize phone
    phone = phone.replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = "+" + phone

    profile = await repo.get_by_phone(phone)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with phone {phone} not found",
        )

    return CustomerResponse.from_profile(profile)


@router.get(
    "/chokepoint/{chokepoint}",
    response_model=list[CustomerResponse],
    summary="Get customers by chokepoint",
    description="Get customers with exposure to a specific chokepoint",
)
async def get_customers_by_chokepoint(
    chokepoint: str,
    repo: PostgresCustomerRepository = Depends(get_repository),
) -> list[CustomerResponse]:
    """Get customers with exposure to a chokepoint."""
    contexts = await repo.get_customers_by_chokepoint(chokepoint)
    return [CustomerResponse.from_profile(c.profile) for c in contexts]

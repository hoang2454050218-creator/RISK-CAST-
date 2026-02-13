"""Shipment API Endpoints.

CRUD operations for shipments.
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.riskcast.constants import ShipmentStatus, derive_chokepoints
from app.riskcast.schemas.customer import Shipment
from app.riskcast.repos.customer import (
    PostgresCustomerRepository,
    ShipmentNotFoundError,
    DuplicateShipmentError,
    CustomerNotFoundError,
)

router = APIRouter()


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================


class ShipmentCreateRequest(BaseModel):
    """Request to create a new shipment."""

    shipment_id: str = Field(min_length=1, max_length=100)
    customer_id: str = Field(min_length=1, max_length=50)
    origin_port: str = Field(min_length=2, max_length=10, description="UN/LOCODE")
    destination_port: str = Field(min_length=2, max_length=10, description="UN/LOCODE")
    cargo_value_usd: float = Field(gt=0, description="Total cargo value in USD")
    cargo_description: Optional[str] = None
    container_count: int = Field(default=1, ge=1)
    container_type: str = Field(default="40HC")
    hs_code: Optional[str] = None
    carrier_code: Optional[str] = None
    carrier_name: Optional[str] = None
    booking_reference: Optional[str] = None
    bill_of_lading: Optional[str] = None
    etd: Optional[datetime] = None
    eta: Optional[datetime] = None
    is_insured: bool = False
    insurance_value_usd: Optional[float] = None


class ShipmentUpdateRequest(BaseModel):
    """Request to update shipment."""

    status: Optional[ShipmentStatus] = None
    carrier_code: Optional[str] = None
    carrier_name: Optional[str] = None
    booking_reference: Optional[str] = None
    bill_of_lading: Optional[str] = None
    etd: Optional[datetime] = None
    eta: Optional[datetime] = None
    actual_departure: Optional[datetime] = None
    actual_arrival: Optional[datetime] = None
    is_insured: Optional[bool] = None
    insurance_value_usd: Optional[float] = None


class ShipmentResponse(BaseModel):
    """Shipment response."""

    shipment_id: str
    customer_id: str
    origin_port: str
    destination_port: str
    route_code: Optional[str]
    route_chokepoints: list[str]
    cargo_value_usd: float
    cargo_description: Optional[str]
    container_count: int
    container_type: str
    hs_code: Optional[str]
    carrier_code: Optional[str]
    carrier_name: Optional[str]
    booking_reference: Optional[str]
    bill_of_lading: Optional[str]
    etd: Optional[datetime]
    eta: Optional[datetime]
    actual_departure: Optional[datetime]
    actual_arrival: Optional[datetime]
    status: str
    is_insured: bool
    insurance_value_usd: Optional[float]
    teu_count: float
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_shipment(cls, shipment: Shipment) -> "ShipmentResponse":
        return cls(
            shipment_id=shipment.shipment_id,
            customer_id=shipment.customer_id,
            origin_port=shipment.origin_port,
            destination_port=shipment.destination_port,
            route_code=shipment.route_code,
            route_chokepoints=shipment.route_chokepoints,
            cargo_value_usd=shipment.cargo_value_usd,
            cargo_description=shipment.cargo_description,
            container_count=shipment.container_count,
            container_type=shipment.container_type,
            hs_code=shipment.hs_code,
            carrier_code=shipment.carrier_code,
            carrier_name=shipment.carrier_name,
            booking_reference=shipment.booking_reference,
            bill_of_lading=shipment.bill_of_lading,
            etd=shipment.etd,
            eta=shipment.eta,
            actual_departure=shipment.actual_departure,
            actual_arrival=shipment.actual_arrival,
            status=shipment.status.value,
            is_insured=shipment.is_insured,
            insurance_value_usd=shipment.insurance_value_usd,
            teu_count=shipment.teu_count,
            is_active=shipment.is_active,
            created_at=shipment.created_at,
            updated_at=shipment.updated_at,
        )


class ShipmentListResponse(BaseModel):
    """Paginated list of shipments."""

    items: list[ShipmentResponse]
    total: int


# ============================================================================
# DEPENDENCIES
# ============================================================================


def get_repository(session: AsyncSession = Depends(get_db_session)) -> PostgresCustomerRepository:
    """Get repository with database session."""
    return PostgresCustomerRepository(session)


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.post(
    "",
    response_model=ShipmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create shipment",
    description="Create a new shipment for a customer",
)
async def create_shipment(
    request: ShipmentCreateRequest,
    repo: PostgresCustomerRepository = Depends(get_repository),
) -> ShipmentResponse:
    """
    Create a new shipment.

    Route chokepoints are automatically derived from origin/destination.
    """
    try:
        # Derive chokepoints
        route_chokepoints = derive_chokepoints(request.origin_port, request.destination_port)
        route_code = f"{request.origin_port}-{request.destination_port}"

        shipment = Shipment(
            shipment_id=request.shipment_id,
            customer_id=request.customer_id,
            origin_port=request.origin_port,
            destination_port=request.destination_port,
            route_code=route_code,
            route_chokepoints=route_chokepoints,
            cargo_value_usd=request.cargo_value_usd,
            cargo_description=request.cargo_description,
            container_count=request.container_count,
            container_type=request.container_type,
            hs_code=request.hs_code,
            carrier_code=request.carrier_code,
            carrier_name=request.carrier_name,
            booking_reference=request.booking_reference,
            bill_of_lading=request.bill_of_lading,
            etd=request.etd,
            eta=request.eta,
            is_insured=request.is_insured,
            insurance_value_usd=request.insurance_value_usd,
        )

        created = await repo.add_shipment(shipment)
        return ShipmentResponse.from_shipment(created)

    except DuplicateShipmentError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Shipment {request.shipment_id} already exists",
        )
    except CustomerNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {request.customer_id} not found",
        )


@router.get(
    "/{shipment_id}",
    response_model=ShipmentResponse,
    summary="Get shipment",
    description="Get shipment by ID",
)
async def get_shipment(
    shipment_id: str,
    repo: PostgresCustomerRepository = Depends(get_repository),
) -> ShipmentResponse:
    """Get shipment by ID."""
    shipment = await repo.get_shipment(shipment_id)

    if not shipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shipment {shipment_id} not found",
        )

    return ShipmentResponse.from_shipment(shipment)


@router.patch(
    "/{shipment_id}",
    response_model=ShipmentResponse,
    summary="Update shipment",
    description="Update shipment fields",
)
async def update_shipment(
    shipment_id: str,
    request: ShipmentUpdateRequest,
    repo: PostgresCustomerRepository = Depends(get_repository),
) -> ShipmentResponse:
    """Update shipment fields."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    updated = await repo.update_shipment(shipment_id, **updates)

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shipment {shipment_id} not found",
        )

    return ShipmentResponse.from_shipment(updated)


@router.delete(
    "/{shipment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete shipment",
    description="Delete a shipment",
)
async def delete_shipment(
    shipment_id: str,
    repo: PostgresCustomerRepository = Depends(get_repository),
):
    """Delete a shipment."""
    deleted = await repo.delete_shipment(shipment_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shipment {shipment_id} not found",
        )

    return None


@router.get(
    "/customer/{customer_id}",
    response_model=ShipmentListResponse,
    summary="List customer shipments",
    description="List all shipments for a customer",
)
async def list_customer_shipments(
    customer_id: str,
    status_filter: Optional[ShipmentStatus] = Query(default=None, alias="status"),
    repo: PostgresCustomerRepository = Depends(get_repository),
) -> ShipmentListResponse:
    """List shipments for a customer."""
    shipments = await repo.get_shipments(customer_id, status=status_filter)

    return ShipmentListResponse(
        items=[ShipmentResponse.from_shipment(s) for s in shipments],
        total=len(shipments),
    )


@router.post(
    "/{shipment_id}/status",
    response_model=ShipmentResponse,
    summary="Update shipment status",
    description="Update only the status of a shipment",
)
async def update_shipment_status(
    shipment_id: str,
    new_status: ShipmentStatus,
    repo: PostgresCustomerRepository = Depends(get_repository),
) -> ShipmentResponse:
    """Quick status update for a shipment."""
    updated = await repo.update_shipment(shipment_id, status=new_status)

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shipment {shipment_id} not found",
        )

    return ShipmentResponse.from_shipment(updated)

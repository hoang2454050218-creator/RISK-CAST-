"""Pydantic schemas for Order resource."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class OrderCreate(BaseModel):
    customer_id: Optional[uuid.UUID] = None
    route_id: Optional[uuid.UUID] = None
    order_number: str = Field(min_length=1, max_length=100)
    status: str = Field(min_length=1, max_length=50)
    total_value: Optional[Decimal] = Field(default=None, ge=0)
    currency: str = Field(default="VND", max_length=3)
    origin: Optional[str] = Field(default=None, max_length=255)
    destination: Optional[str] = Field(default=None, max_length=255)
    expected_date: Optional[date] = None
    actual_date: Optional[date] = None
    metadata: Optional[dict] = Field(default_factory=dict, alias="metadata_extra")


class OrderUpdate(BaseModel):
    customer_id: Optional[uuid.UUID] = None
    route_id: Optional[uuid.UUID] = None
    status: Optional[str] = Field(default=None, max_length=50)
    total_value: Optional[Decimal] = Field(default=None, ge=0)
    currency: Optional[str] = Field(default=None, max_length=3)
    origin: Optional[str] = Field(default=None, max_length=255)
    destination: Optional[str] = Field(default=None, max_length=255)
    expected_date: Optional[date] = None
    actual_date: Optional[date] = None
    metadata: Optional[dict] = Field(default=None, alias="metadata_extra")


class OrderResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    customer_id: Optional[uuid.UUID]
    route_id: Optional[uuid.UUID]
    order_number: str
    status: str
    total_value: Optional[Decimal]
    currency: str
    origin: Optional[str]
    destination: Optional[str]
    expected_date: Optional[date]
    actual_date: Optional[date]
    metadata: dict = Field(alias="metadata_")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}

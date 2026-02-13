"""Pydantic schemas for Route resource."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class RouteCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    origin: str = Field(min_length=1, max_length=255)
    destination: str = Field(min_length=1, max_length=255)
    transport_mode: Optional[str] = Field(default=None, max_length=50)
    avg_duration_days: Optional[Decimal] = Field(default=None, ge=0)
    is_active: bool = True
    metadata: Optional[dict] = Field(default_factory=dict, alias="metadata_extra")


class RouteUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    origin: Optional[str] = Field(default=None, max_length=255)
    destination: Optional[str] = Field(default=None, max_length=255)
    transport_mode: Optional[str] = Field(default=None, max_length=50)
    avg_duration_days: Optional[Decimal] = Field(default=None, ge=0)
    is_active: Optional[bool] = None
    metadata: Optional[dict] = Field(default=None, alias="metadata_extra")


class RouteResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    origin: str
    destination: str
    transport_mode: Optional[str]
    avg_duration_days: Optional[Decimal]
    is_active: bool
    metadata: dict = Field(alias="metadata_")
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}

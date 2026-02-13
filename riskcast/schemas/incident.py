"""Pydantic schemas for Incident resource."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class IncidentCreate(BaseModel):
    order_id: Optional[uuid.UUID] = None
    route_id: Optional[uuid.UUID] = None
    customer_id: Optional[uuid.UUID] = None
    type: str = Field(min_length=1, max_length=100)
    severity: str = Field(min_length=1, max_length=20)
    description: Optional[str] = None
    resolution: Optional[str] = None
    metadata: Optional[dict] = Field(default_factory=dict, alias="metadata_extra")


class IncidentUpdate(BaseModel):
    severity: Optional[str] = Field(default=None, max_length=20)
    description: Optional[str] = None
    resolution: Optional[str] = None
    resolved_at: Optional[datetime] = None
    metadata: Optional[dict] = Field(default=None, alias="metadata_extra")


class IncidentResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    order_id: Optional[uuid.UUID]
    route_id: Optional[uuid.UUID]
    customer_id: Optional[uuid.UUID]
    type: str
    severity: str
    description: Optional[str]
    resolution: Optional[str]
    resolved_at: Optional[datetime]
    metadata: dict = Field(alias="metadata_")
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}

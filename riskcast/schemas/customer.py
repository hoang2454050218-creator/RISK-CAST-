"""Pydantic schemas for Customer resource."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: Optional[str] = Field(default=None, max_length=50)
    tier: str = Field(default="standard", max_length=50)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(default=None, max_length=50)
    payment_terms: int = Field(default=30, ge=0)
    metadata: Optional[dict] = Field(default_factory=dict, alias="metadata_extra")


class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    code: Optional[str] = Field(default=None, max_length=50)
    tier: Optional[str] = Field(default=None, max_length=50)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(default=None, max_length=50)
    payment_terms: Optional[int] = Field(default=None, ge=0)
    metadata: Optional[dict] = Field(default=None, alias="metadata_extra")


class CustomerResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    code: Optional[str]
    tier: str
    contact_email: Optional[str]
    contact_phone: Optional[str]
    payment_terms: int
    metadata: dict = Field(alias="metadata_")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}

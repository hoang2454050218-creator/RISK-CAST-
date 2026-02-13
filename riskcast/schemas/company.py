"""Pydantic schemas for Company resource."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9\-]+$")
    industry: Optional[str] = Field(default=None, max_length=100)
    timezone: str = Field(default="Asia/Ho_Chi_Minh", max_length=50)
    plan: str = Field(default="starter", max_length=50)


class CompanyUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    industry: Optional[str] = Field(default=None, max_length=100)
    timezone: Optional[str] = Field(default=None, max_length=50)
    plan: Optional[str] = Field(default=None, max_length=50)
    settings: Optional[dict] = None


class CompanyResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    industry: Optional[str]
    timezone: str
    plan: str
    settings: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

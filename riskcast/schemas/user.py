"""Pydantic schemas for User resource."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=255)
    role: str = Field(default="member", max_length=50)


class UserResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    email: str
    name: str
    role: str
    preferences: dict
    last_login_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}

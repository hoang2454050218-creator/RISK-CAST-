"""Pydantic schemas for authentication endpoints."""

from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Register a new company + admin user."""

    company_name: str = Field(min_length=1, max_length=255)
    company_slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9\-]+$")
    industry: Optional[str] = Field(default=None, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    company_id: str
    email: str
    role: str
    name: str

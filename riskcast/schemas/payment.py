"""Pydantic schemas for Payment resource."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class PaymentCreate(BaseModel):
    order_id: Optional[uuid.UUID] = None
    customer_id: Optional[uuid.UUID] = None
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="VND", max_length=3)
    status: str = Field(min_length=1, max_length=50)
    due_date: date
    paid_date: Optional[date] = None
    metadata: Optional[dict] = Field(default_factory=dict, alias="metadata_extra")


class PaymentUpdate(BaseModel):
    status: Optional[str] = Field(default=None, max_length=50)
    paid_date: Optional[date] = None
    metadata: Optional[dict] = Field(default=None, alias="metadata_extra")


class PaymentResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    order_id: Optional[uuid.UUID]
    customer_id: Optional[uuid.UUID]
    amount: Decimal
    currency: str
    status: str
    due_date: date
    paid_date: Optional[date]
    metadata: dict = Field(alias="metadata_")
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}

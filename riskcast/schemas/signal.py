"""Pydantic schemas for Signal resource."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class SignalResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    source: str
    signal_type: str
    entity_type: Optional[str]
    entity_id: Optional[uuid.UUID]
    confidence: Decimal
    severity_score: Optional[Decimal]
    evidence: dict
    context: dict
    is_active: bool
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SignalListResponse(BaseModel):
    signals: list[SignalResponse]
    total: int


class TriggerScanResponse(BaseModel):
    status: str
    company_id: str
    signals_upserted: int

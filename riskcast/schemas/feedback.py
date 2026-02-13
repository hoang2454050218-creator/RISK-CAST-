"""Pydantic schemas for Feedback endpoints."""

from typing import Optional

from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    decision: str = Field(
        description="accepted, rejected, deferred",
        pattern=r"^(accepted|rejected|deferred)$",
    )
    reason_code: Optional[str] = Field(
        default=None,
        description="vip_client, high_margin, low_priority, incorrect, other",
    )
    reason_text: Optional[str] = Field(default=None, max_length=1000)


class OutcomeRequest(BaseModel):
    outcome: str = Field(
        description="correct, incorrect, partially_correct, unknown",
    )

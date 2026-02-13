"""
Feedback Loop — ORM-based for cross-database compatibility.
"""

import json
import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.db.models import RiskAppetiteProfile, SuggestionFeedback

logger = structlog.get_logger(__name__)


class FeedbackProcessor:
    MIN_FEEDBACK = 10

    async def record_feedback(
        self,
        session: AsyncSession,
        suggestion_id: str,
        user_id: str,
        company_id: str,
        decision: str,
        reason_code: str | None = None,
        reason_text: str | None = None,
    ):
        fb = SuggestionFeedback(
            suggestion_id=uuid.UUID(suggestion_id),
            user_id=uuid.UUID(user_id),
            company_id=uuid.UUID(company_id),
            decision=decision,
            reason_code=reason_code,
            reason_text=reason_text,
        )
        session.add(fb)
        await session.flush()

        logger.info("feedback_recorded", suggestion_id=suggestion_id, decision=decision)
        await self._maybe_update_appetite(session, company_id)

    async def record_outcome(self, session: AsyncSession, suggestion_id: str, outcome: str):
        result = await session.execute(
            select(SuggestionFeedback).where(
                SuggestionFeedback.suggestion_id == uuid.UUID(suggestion_id)
            )
        )
        for fb in result.scalars().all():
            fb.outcome = outcome
        await session.flush()

    async def _maybe_update_appetite(self, session: AsyncSession, company_id: str):
        cid = uuid.UUID(company_id)
        result = await session.execute(
            select(SuggestionFeedback)
            .where(SuggestionFeedback.company_id == cid)
            .order_by(SuggestionFeedback.created_at.desc())
            .limit(50)
        )
        feedback = result.scalars().all()

        if len(feedback) < self.MIN_FEEDBACK:
            return

        profile_result = await session.execute(
            select(RiskAppetiteProfile).where(RiskAppetiteProfile.company_id == cid)
        )
        profile_row = profile_result.scalar_one_or_none()
        if not profile_row:
            return

        profile = dict(profile_row.profile) if profile_row.profile else {}
        rules = list(profile.get("learned_rules", []))

        vip_rejects = [f for f in feedback if f.reason_code == "vip_client" and f.decision == "rejected"]
        if len(vip_rejects) >= 3:
            self._upsert_rule(rules, {"type": "vip_tolerance", "confidence": min(0.9, len(vip_rejects) / 10)})

        margin_rejects = [f for f in feedback if f.reason_code == "high_margin" and f.decision == "rejected"]
        if len(margin_rejects) >= 3:
            self._upsert_rule(rules, {"type": "margin_tradeoff", "confidence": min(0.9, len(margin_rejects) / 10)})

        reject_ratio = len([f for f in feedback if f.decision == "rejected"]) / len(feedback)
        if reject_ratio > 0.6:
            profile["payment_risk_tolerance"] = "high"
        elif reject_ratio < 0.3:
            profile["payment_risk_tolerance"] = "low"
        else:
            profile["payment_risk_tolerance"] = "medium"

        profile["learned_rules"] = rules
        profile_row.profile = profile
        await session.flush()

    def _upsert_rule(self, rules: list, new_rule: dict):
        for i, rule in enumerate(rules):
            if rule.get("type") == new_rule["type"]:
                rules[i] = new_rule
                return
        rules.append(new_rule)

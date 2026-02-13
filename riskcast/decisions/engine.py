"""
Decision Engine — Orchestrates risk assessment → decision generation.

Pipeline:
1. Get risk assessment from RiskEngine
2. Estimate financial exposure
3. Generate actions
4. Analyze tradeoffs
5. Evaluate escalation rules
6. Generate counterfactual scenarios
7. Package into an auditable Decision object
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.db.models import Order, Signal
from riskcast.decisions.actions import ActionGenerator
from riskcast.decisions.counterfactual import CounterfactualEngine
from riskcast.decisions.escalation import EscalationEngine
from riskcast.decisions.schemas import (
    Action,
    ActionType,
    Decision,
    DecisionListResponse,
    DecisionStatus,
    SeverityLevel,
)
from riskcast.decisions.tradeoffs import TradeoffAnalyzer
from riskcast.engine.risk_engine import RiskAssessment, RiskEngine

logger = structlog.get_logger(__name__)


class DecisionEngine:
    """
    Unified decision generation engine.

    Takes a risk assessment and produces a fully-auditable decision
    with actions, tradeoffs, escalation rules, and counterfactuals.
    """

    def __init__(self):
        self.risk_engine = RiskEngine()
        self.action_generator = ActionGenerator()
        self.tradeoff_analyzer = TradeoffAnalyzer()
        self.escalation_engine = EscalationEngine()
        self.counterfactual_engine = CounterfactualEngine()

    async def generate_decision(
        self,
        session: AsyncSession,
        company_id: str,
        entity_type: str,
        entity_id: str,
        exposure_usd: Optional[float] = None,
    ) -> Decision:
        """
        Generate a complete decision for an entity.

        Steps:
        1. Assess risk via RiskEngine
        2. Estimate exposure if not provided
        3. Generate actions
        4. Analyze tradeoffs
        5. Evaluate escalation rules
        6. Generate counterfactuals
        7. Package decision
        """
        now = datetime.utcnow()
        decision_id = f"dec_{uuid.uuid4().hex[:16]}"

        # ── 1. Risk Assessment ──────────────────────────────────────
        assessment = await self.risk_engine.assess_entity(
            session, company_id, entity_type, entity_id
        )

        # ── 2. Estimate Exposure ────────────────────────────────────
        if exposure_usd is None:
            exposure_usd = await self._estimate_exposure(
                session, company_id, entity_type, entity_id
            )

        # ── 3. Generate Actions ─────────────────────────────────────
        actions = self.action_generator.generate_actions(
            assessment, exposure_usd=exposure_usd
        )

        # ── 4. Analyze Tradeoffs ────────────────────────────────────
        inaction_cost = exposure_usd * (assessment.risk_score / 100)
        tradeoff = self.tradeoff_analyzer.analyze(actions, inaction_cost)

        # ── 5. Escalation Rules ─────────────────────────────────────
        needs_escalation, esc_rules, esc_reason = self.escalation_engine.evaluate(
            assessment, exposure_usd
        )

        # ── 6. Counterfactuals ──────────────────────────────────────
        counterfactuals = self.counterfactual_engine.generate_scenarios(
            assessment, exposure_usd
        )

        # ── 7. Package Decision ─────────────────────────────────────
        severity = SeverityLevel(assessment.severity_label)
        recommended = next(
            (a for a in actions if a.action_type == tradeoff.recommended_action),
            actions[0] if actions else Action(
                action_type=ActionType.MONITOR,
                description="No actions available.",
            ),
        )
        alternatives = [a for a in actions if a.action_type != recommended.action_type]

        valid_until = (now + timedelta(hours=24)).isoformat()

        decision = Decision(
            decision_id=decision_id,
            entity_type=entity_type,
            entity_id=entity_id,
            company_id=company_id,
            status=DecisionStatus.ESCALATED if needs_escalation else DecisionStatus.RECOMMENDED,
            severity=severity,
            situation_summary=assessment.summary,
            risk_score=assessment.risk_score,
            confidence=assessment.confidence,
            ci_lower=assessment.ci_lower,
            ci_upper=assessment.ci_upper,
            recommended_action=recommended,
            alternative_actions=alternatives,
            tradeoff=tradeoff,
            inaction_cost=round(inaction_cost, 2),
            inaction_risk=(
                f"If no action is taken, estimated loss is "
                f"${inaction_cost:,.0f} with {assessment.risk_score:.0f}% probability."
            ),
            counterfactuals=counterfactuals,
            needs_human_review=needs_escalation,
            escalation_rules=esc_rules,
            escalation_reason=esc_reason if needs_escalation else None,
            algorithm_trace=assessment.algorithm_trace,
            data_sources=[
                f"signals:{assessment.n_signals}",
                f"active:{assessment.n_active_signals}",
                f"freshness:{assessment.data_freshness}",
            ],
            generated_at=now.isoformat(),
            valid_until=valid_until,
            n_signals_used=assessment.n_signals,
            is_reliable=assessment.is_reliable,
            data_freshness=assessment.data_freshness,
        )

        logger.info(
            "decision_generated",
            decision_id=decision_id,
            entity=f"{entity_type}/{entity_id}",
            risk_score=assessment.risk_score,
            recommended=recommended.action_type.value,
            escalated=needs_escalation,
        )

        # ── Auto-trigger alerts (Discord, WhatsApp, etc.) ──────────
        try:
            from riskcast.alerting.auto_trigger import on_decision_generated
            fired = await on_decision_generated(decision, company_id)
            if fired:
                logger.info(
                    "auto_alerts_fired",
                    decision_id=decision_id,
                    count=len(fired),
                    rules=[a.rule_name for a in fired],
                )
        except Exception as alert_err:
            logger.error(
                "auto_alert_failed",
                decision_id=decision_id,
                error=str(alert_err),
                exc_info=True,
            )

        return decision

    async def generate_decisions_for_company(
        self,
        session: AsyncSession,
        company_id: str,
        entity_type: str = "order",
        min_severity: float = 30.0,
        limit: int = 20,
    ) -> DecisionListResponse:
        """Generate decisions for all at-risk entities in a company."""
        # Find entities with active high-severity signals
        result = await session.execute(
            select(Signal.entity_id)
            .where(
                Signal.company_id == company_id,
                Signal.is_active.is_(True),
                Signal.entity_type == entity_type,
                Signal.severity_score >= min_severity,
            )
            .group_by(Signal.entity_id)
            .order_by(func.max(Signal.severity_score).desc())
            .limit(limit)
        )
        entity_ids = [str(row[0]) for row in result.all() if row[0]]

        decisions: list[Decision] = []
        for eid in entity_ids:
            try:
                decision = await self.generate_decision(
                    session, company_id, entity_type, eid
                )
                decisions.append(decision)
            except Exception as e:
                logger.error(
                    "decision_generation_failed",
                    entity_id=eid,
                    error=str(e),
                )

        return DecisionListResponse(decisions=decisions, total=len(decisions))

    async def _estimate_exposure(
        self,
        session: AsyncSession,
        company_id: str,
        entity_type: str,
        entity_id: str,
    ) -> float:
        """Estimate financial exposure for an entity."""
        if entity_type == "order":
            result = await session.execute(
                select(Order.total_value).where(
                    Order.company_id == company_id,
                    Order.id == entity_id,
                )
            )
            value = result.scalar_one_or_none()
            return float(value) if value else 0.0

        # Default: estimate from signal severity
        result = await session.execute(
            select(func.avg(Signal.severity_score))
            .where(
                Signal.company_id == company_id,
                Signal.entity_type == entity_type,
                Signal.entity_id == entity_id,
            )
        )
        avg_sev = result.scalar_one_or_none()
        return float(avg_sev or 0) * 1000  # Basic estimate

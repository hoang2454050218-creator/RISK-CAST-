"""
Alert & Early Warning API Endpoints.

POST /api/v1/alerts/rules                  — create an alert rule
GET  /api/v1/alerts/rules                  — list alert rules
PUT  /api/v1/alerts/rules/{rule_id}        — update a rule
DELETE /api/v1/alerts/rules/{rule_id}      — delete a rule

POST /api/v1/alerts/evaluate               — evaluate rules against metrics
GET  /api/v1/alerts                        — list fired alerts
POST /api/v1/alerts/{alert_id}/acknowledge — acknowledge an alert

GET  /api/v1/alerts/early-warnings         — get early warning signals
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.alerting.channels import ChannelRouter
from riskcast.alerting.dedup import DedupManager
from riskcast.alerting.early_warning import EarlyWarningDetector
from riskcast.alerting.engine import AlertEngine
from riskcast.alerting.schemas import (
    AlertChannel,
    AlertListResponse,
    AlertRecord,
    AlertRule,
    AlertRuleCreateRequest,
    AlertSeverity,
    AlertStatus,
    EarlyWarningListResponse,
    RuleOperator,
)
from riskcast.api.deps import get_company_id, get_db, get_user_id
from riskcast.db.models import Alert, AlertRuleModel

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])

_engine = AlertEngine()
_dedup = DedupManager()
_channels = ChannelRouter()
_early_warning = EarlyWarningDetector()


# ── Rule Management ────────────────────────────────────────────────────


@router.post("/rules", response_model=AlertRule)
async def create_alert_rule(
    body: AlertRuleCreateRequest,
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """Create a new alert rule."""
    now = datetime.utcnow()
    rule_id = f"rule_{uuid.uuid4().hex[:12]}"

    model = AlertRuleModel(
        id=uuid.uuid4(),
        rule_id=rule_id,
        company_id=company_id,
        rule_name=body.rule_name,
        description=body.description,
        is_active=True,
        metric=body.metric,
        operator=body.operator.value,
        threshold=Decimal(str(body.threshold)),
        entity_type=body.entity_type,
        severity=body.severity.value,
        channels=[c.value for c in body.channels],
        cooldown_minutes=body.cooldown_minutes,
        max_per_day=body.max_per_day,
        created_at=now,
        updated_at=now,
    )
    db.add(model)
    await db.flush()

    return AlertRule(
        rule_id=rule_id,
        rule_name=body.rule_name,
        description=body.description,
        company_id=str(company_id),
        is_active=True,
        metric=body.metric,
        operator=body.operator,
        threshold=body.threshold,
        entity_type=body.entity_type,
        severity=body.severity,
        channels=body.channels,
        cooldown_minutes=body.cooldown_minutes,
        max_per_day=body.max_per_day,
        created_at=now.isoformat(),
        updated_at=now.isoformat(),
    )


@router.get("/rules", response_model=list[AlertRule])
async def list_alert_rules(
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """List all alert rules for the company."""
    result = await db.execute(
        select(AlertRuleModel).where(
            AlertRuleModel.company_id == company_id,
        ).order_by(AlertRuleModel.created_at.desc())
    )
    rows = result.scalars().all()
    return [
        AlertRule(
            rule_id=r.rule_id,
            rule_name=r.rule_name,
            description=r.description or "",
            company_id=str(r.company_id),
            is_active=r.is_active,
            metric=r.metric,
            operator=RuleOperator(r.operator),
            threshold=float(r.threshold),
            entity_type=r.entity_type,
            severity=AlertSeverity(r.severity),
            channels=[AlertChannel(c) for c in (r.channels or [])],
            cooldown_minutes=r.cooldown_minutes,
            max_per_day=r.max_per_day,
            created_at=r.created_at.isoformat() if r.created_at else "",
            updated_at=r.updated_at.isoformat() if r.updated_at else "",
        )
        for r in rows
    ]


@router.delete("/rules/{rule_id}")
async def delete_alert_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """Delete an alert rule."""
    result = await db.execute(
        delete(AlertRuleModel).where(
            AlertRuleModel.rule_id == rule_id,
            AlertRuleModel.company_id == company_id,
        )
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return {"deleted": True, "rule_id": rule_id}


# ── Evaluate Rules ─────────────────────────────────────────────────────


class EvaluateRequest(BaseModel):
    """Metrics to evaluate against alert rules."""
    metrics: dict[str, float]
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None


@router.post("/evaluate", response_model=list[AlertRecord])
async def evaluate_alerts(
    body: EvaluateRequest,
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """
    Evaluate all active rules against provided metrics.

    Triggers alerts, applies dedup/cooldown, dispatches to channels.
    """
    # Load rules
    result = await db.execute(
        select(AlertRuleModel).where(
            AlertRuleModel.company_id == company_id,
            AlertRuleModel.is_active.is_(True),
        )
    )
    rule_models = result.scalars().all()
    rules = [
        AlertRule(
            rule_id=r.rule_id,
            rule_name=r.rule_name,
            description=r.description or "",
            company_id=str(r.company_id),
            is_active=r.is_active,
            metric=r.metric,
            operator=RuleOperator(r.operator),
            threshold=float(r.threshold),
            entity_type=r.entity_type,
            severity=AlertSeverity(r.severity),
            channels=[AlertChannel(c) for c in (r.channels or [])],
            cooldown_minutes=r.cooldown_minutes,
            max_per_day=r.max_per_day,
        )
        for r in rule_models
    ]

    # Evaluate
    fired = _engine.evaluate_rules(
        rules, body.metrics, body.entity_type, body.entity_id
    )

    sent: list[AlertRecord] = []
    for alert in fired:
        # Find matching rule for cooldown config
        rule = next((r for r in rules if r.rule_id == alert.rule_id), None)
        cooldown = rule.cooldown_minutes if rule else 30
        max_day = rule.max_per_day if rule else 10

        # Dedup check
        suppressed, reason = _dedup.should_suppress(alert, cooldown, max_day)
        if suppressed:
            alert.status = AlertStatus.SUPPRESSED
            alert.delivery_results = {"suppressed": True, "reason": reason}
        else:
            # Dispatch to channels
            channel_configs = _build_channel_configs()
            delivery = await _channels.dispatch_alert(alert, channel_configs)
            alert.delivery_results = delivery
            alert.status = AlertStatus.SENT
            alert.sent_at = datetime.utcnow().isoformat()
            _dedup.record_fired(alert)

        # Persist
        alert_model = Alert(
            id=uuid.uuid4(),
            alert_id=alert.alert_id,
            rule_id=alert.rule_id,
            rule_name=alert.rule_name,
            company_id=company_id,
            severity=alert.severity.value,
            status=alert.status.value,
            metric=alert.metric,
            metric_value=Decimal(str(alert.metric_value)),
            threshold=Decimal(str(alert.threshold)),
            entity_type=alert.entity_type,
            entity_id=alert.entity_id,
            title=alert.title,
            message=alert.message,
            channels=[c.value for c in alert.channels],
            delivery_results=alert.delivery_results,
            triggered_at=datetime.fromisoformat(alert.triggered_at),
            sent_at=datetime.fromisoformat(alert.sent_at) if alert.sent_at else None,
        )
        db.add(alert_model)
        sent.append(alert)

    await db.flush()
    return sent


# ── Alert History ──────────────────────────────────────────────────────


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    status: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """List fired alerts for the company."""
    query = select(Alert).where(Alert.company_id == company_id)
    if status:
        query = query.where(Alert.status == status)
    if severity:
        query = query.where(Alert.severity == severity)
    query = query.order_by(Alert.triggered_at.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    rows = result.scalars().all()

    alerts = [
        AlertRecord(
            alert_id=a.alert_id,
            rule_id=a.rule_id,
            rule_name=a.rule_name,
            company_id=str(a.company_id),
            severity=AlertSeverity(a.severity),
            status=AlertStatus(a.status),
            metric=a.metric,
            metric_value=float(a.metric_value),
            threshold=float(a.threshold),
            entity_type=a.entity_type,
            entity_id=a.entity_id,
            title=a.title,
            message=a.message,
            channels=[AlertChannel(c) for c in (a.channels or [])],
            delivery_results=a.delivery_results or {},
            triggered_at=a.triggered_at.isoformat() if a.triggered_at else "",
            sent_at=a.sent_at.isoformat() if a.sent_at else None,
            acknowledged_at=a.acknowledged_at.isoformat() if a.acknowledged_at else None,
            acknowledged_by=a.acknowledged_by,
        )
        for a in rows
    ]
    return AlertListResponse(alerts=alerts, total=len(alerts))


# ── Acknowledge Alert ──────────────────────────────────────────────────


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
    user_id: uuid.UUID = Depends(get_user_id),
):
    """Acknowledge an alert (mark as seen/handled)."""
    now = datetime.utcnow()
    result = await db.execute(
        update(Alert)
        .where(Alert.alert_id == alert_id, Alert.company_id == company_id)
        .values(
            status="delivered",
            acknowledged_at=now,
            acknowledged_by=str(user_id),
        )
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"acknowledged": True, "alert_id": alert_id}


# ── Early Warnings ────────────────────────────────────────────────────


@router.get("/early-warnings", response_model=EarlyWarningListResponse)
async def early_warnings(
    days_back: int = Query(default=14, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """
    Get early warning signals.

    Detects rising risk trends and predicts when thresholds will be crossed.
    """
    risk_warnings = await _early_warning.detect_risk_trends(
        db, str(company_id), days_back=days_back
    )
    signal_warnings = await _early_warning.detect_signal_trends(
        db, str(company_id), days_back=days_back
    )

    all_warnings = risk_warnings + signal_warnings
    # Sort by urgency (critical first)
    urgency_order = {"critical": 0, "high": 1, "warning": 2, "info": 3}
    all_warnings.sort(key=lambda w: urgency_order.get(w.urgency.value, 4))

    return EarlyWarningListResponse(warnings=all_warnings, total=len(all_warnings))


# ── Helpers ────────────────────────────────────────────────────────────


def _build_channel_configs() -> dict[str, dict]:
    """Build channel configurations from app settings."""
    from riskcast.config import settings
    configs: dict[str, dict] = {}

    if settings.alert_webhook_url:
        configs["webhook"] = {"url": settings.alert_webhook_url}

    if settings.alert_smtp_host:
        configs["email"] = {
            "smtp_host": settings.alert_smtp_host,
            "smtp_port": settings.alert_smtp_port,
            "from_email": settings.alert_from_email,
        }

    configs["in_app"] = {}  # Always available
    return configs

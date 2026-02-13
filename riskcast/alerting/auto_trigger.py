"""
Auto-Trigger — Automatically evaluates alert rules when decisions/signals change.

This is the "glue" that connects:
  Decision Engine → Alert Engine → Channel Dispatch (Discord, WhatsApp, etc.)
  Signal Ingestion → Alert Engine → Channel Dispatch

Default rules are created per-company on first use.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog

from riskcast.alerting.channels import ChannelRouter
from riskcast.alerting.engine import AlertEngine
from riskcast.alerting.schemas import (
    AlertChannel,
    AlertRecord,
    AlertRule,
    AlertSeverity,
    RuleOperator,
)
from riskcast.config import settings

logger = structlog.get_logger(__name__)

# ── Singleton instances ──────────────────────────────────────────────────

_engine = AlertEngine()
_router = ChannelRouter()

# ── Default Rules (applied to all companies) ─────────────────────────────

_DEFAULT_RULES: list[AlertRule] = [
    AlertRule(
        rule_id="default_critical_risk",
        rule_name="Critical Risk Score",
        description="Risk score exceeds critical threshold (75+)",
        company_id="*",
        metric="risk_score",
        operator=RuleOperator.GTE,
        threshold=75.0,
        severity=AlertSeverity.CRITICAL,
        channels=[AlertChannel.WEBHOOK, AlertChannel.IN_APP],
        cooldown_minutes=15,
        max_per_day=20,
    ),
    AlertRule(
        rule_id="default_high_risk",
        rule_name="High Risk Score",
        description="Risk score exceeds high threshold (50+)",
        company_id="*",
        metric="risk_score",
        operator=RuleOperator.GTE,
        threshold=50.0,
        severity=AlertSeverity.HIGH,
        channels=[AlertChannel.WEBHOOK, AlertChannel.IN_APP],
        cooldown_minutes=30,
        max_per_day=10,
    ),
    AlertRule(
        rule_id="default_high_exposure",
        rule_name="High Exposure",
        description="Financial exposure exceeds $200,000",
        company_id="*",
        metric="exposure_usd",
        operator=RuleOperator.GTE,
        threshold=200_000.0,
        severity=AlertSeverity.HIGH,
        channels=[AlertChannel.WEBHOOK, AlertChannel.IN_APP],
        cooldown_minutes=60,
        max_per_day=5,
    ),
    AlertRule(
        rule_id="default_escalation",
        rule_name="Decision Escalated",
        description="Decision requires human review",
        company_id="*",
        metric="needs_escalation",
        operator=RuleOperator.GTE,
        threshold=1.0,
        severity=AlertSeverity.HIGH,
        channels=[AlertChannel.WEBHOOK, AlertChannel.IN_APP],
        cooldown_minutes=15,
        max_per_day=20,
    ),
    AlertRule(
        rule_id="default_critical_signal",
        rule_name="Critical Signal Ingested",
        description="A signal with severity >= 80 was ingested from OMEN",
        company_id="*",
        metric="severity_score",
        operator=RuleOperator.GTE,
        threshold=80.0,
        severity=AlertSeverity.CRITICAL,
        channels=[AlertChannel.WEBHOOK, AlertChannel.IN_APP],
        cooldown_minutes=10,
        max_per_day=30,
    ),
]

# ── In-memory cooldown tracker (simple, per-rule) ────────────────────────

_last_fired: dict[str, datetime] = {}


def _check_cooldown(rule: AlertRule) -> bool:
    """Return True if the rule is allowed to fire (not in cooldown)."""
    last = _last_fired.get(rule.rule_id)
    if last is None:
        return True
    elapsed = (datetime.utcnow() - last).total_seconds() / 60
    return elapsed >= rule.cooldown_minutes


def _mark_fired(rule_id: str):
    """Mark a rule as having fired now."""
    _last_fired[rule_id] = datetime.utcnow()


# ── Channel config builder ───────────────────────────────────────────────

async def _build_channel_configs(company_id: str = "") -> dict[str, dict]:
    """
    Build channel configs — per-company first, fallback to global.

    Priority:
    1. Company's own webhook URL (from company.settings.notifications)
    2. Global ALERT_WEBHOOK_URL from environment (fallback)
    """
    configs: dict[str, dict] = {}

    webhook_url = ""
    company_notif = {}

    # 1. Try per-company webhook from DB
    if company_id:
        try:
            from riskcast.db.engine import get_db_session
            from riskcast.db.models import Company
            from sqlalchemy import select as sa_select

            async with get_db_session() as session:
                result = await session.execute(
                    sa_select(Company.settings).where(
                        Company.id == company_id
                    )
                )
                row = result.scalar_one_or_none()
                if row and isinstance(row, dict):
                    company_notif = row.get("notifications", {})
                    if company_notif.get("discord_enabled") and company_notif.get("discord_webhook_url"):
                        webhook_url = company_notif["discord_webhook_url"]
        except Exception as e:
            logger.warning("company_webhook_lookup_failed", company_id=company_id, error=str(e))

    # 2. Fallback to global env var
    if not webhook_url and settings.alert_webhook_url:
        webhook_url = settings.alert_webhook_url

    if webhook_url:
        configs["webhook"] = {"url": webhook_url}

    # In-app always enabled unless explicitly disabled
    if company_notif.get("in_app_enabled", True):
        configs["in_app"] = {}

    return configs


# ── Public API: trigger from Decision Engine ─────────────────────────────

async def on_decision_generated(
    decision,
    company_id: str,
) -> list[AlertRecord]:
    """
    Called after DecisionEngine.generate_decision().
    Evaluates default rules and dispatches alerts.

    Args:
        decision: The Decision object just generated
        company_id: Company ID

    Returns:
        List of AlertRecords that were fired and dispatched
    """
    metrics = {
        "risk_score": decision.risk_score,
        "confidence": decision.confidence,
        "exposure_usd": float(decision.inaction_cost / max(decision.risk_score / 100, 0.01))
            if decision.risk_score > 0 else 0.0,
        "needs_escalation": 1.0 if decision.needs_human_review else 0.0,
    }

    entity_type = decision.entity_type
    entity_id = decision.entity_id

    fired = []
    channel_configs = await _build_channel_configs(company_id)

    for rule in _DEFAULT_RULES:
        if rule.metric not in metrics:
            continue

        # Check cooldown
        if not _check_cooldown(rule):
            continue

        # Override company_id for default rules
        rule_copy = rule.model_copy(update={"company_id": company_id})

        alert = _engine.evaluate_rule(
            rule_copy, metrics[rule.metric], entity_type, entity_id
        )

        if alert:
            # ── Làm giàu message bằng ngôn ngữ kinh doanh tiếng Việt ──
            action = decision.recommended_action
            action_cost = action.estimated_cost_usd
            savings = action.estimated_benefit_usd - action_cost if action.estimated_benefit_usd else 0
            inaction = decision.inaction_cost
            deadline_str = action.deadline or "Càng sớm càng tốt"

            # Action type → nhãn tiếng Việt
            action_labels = {
                "insure": "Mua bảo hiểm hàng hóa",
                "reroute": "Đổi tuyến vận chuyển",
                "delay_shipment": "Hoãn xuất hàng",
                "hedge_exposure": "Phòng ngừa rủi ro tài chính",
                "split_shipment": "Chia nhỏ lô hàng",
                "monitor_only": "Tiếp tục theo dõi",
            }
            action_label = action_labels.get(
                action.action_type.value, action.action_type.value.replace("_", " ").title()
            )

            # Severity → mô tả tiếng Việt
            sev = decision.severity.value if hasattr(decision, 'severity') else "high"
            sev_desc = {
                "critical": "🔴 CỰC KỲ NGHIÊM TRỌNG",
                "high": "🟠 MỨC ĐỘ CAO",
                "moderate": "🟡 CẦN CHÚ Ý",
                "low": "🟢 MỨC ĐỘ THẤP",
            }.get(sev, "⚠️ CẦN XEM XÉT")

            # ── Xây dựng message tiếng Việt (gọn, không lặp) ──
            lines = []

            # TÌNH HUỐNG
            lines.append(f"{decision.situation_summary[:250]}")
            lines.append(f"Rủi ro: **{decision.risk_score:.0f}%** — {sev_desc}")

            # TÀI CHÍNH — gộp chung, không lặp
            lines.append("")
            lines.append("💰 **TÀI CHÍNH**")
            if inaction > 0:
                lines.append(f"Thiệt hại nếu không hành động: **${inaction:,.0f}**")
            if action_cost > 0:
                lines.append(f"Chi phí xử lý: **${action_cost:,.0f}**")
            if savings > 0:
                lines.append(f"Tiết kiệm: **${savings:,.0f}**")
            if inaction > 0 and action_cost > 0:
                roi = inaction / action_cost
                lines.append(f"ROI: **{roi:.0f}x** (bỏ $1 → bảo vệ ${roi:.0f})")

            # HÀNH ĐỘNG
            lines.append("")
            lines.append(f"✅ **KHUYẾN NGHỊ: {action_label}**")
            lines.append(f"⏰ Hạn: **{deadline_str}**")
            if decision.inaction_risk:
                lines.append(f"⚠️ Nếu chờ: {decision.inaction_risk[:150]}")

            # BƯỚC TIẾP THEO — ngắn gọn
            lines.append("")
            if decision.needs_human_review:
                lines.append("📌 Mở dashboard → duyệt và phê duyệt hành động")
            else:
                lines.append(f"📌 Mở dashboard → xác nhận **{action_label}**")

            alert.message = "\n".join(lines)

            # Title tiếng Việt — ngắn gọn, đủ ý
            if decision.risk_score >= 75:
                alert.title = f"🚨 Rủi ro {decision.risk_score:.0f}%"
            elif decision.risk_score >= 50:
                alert.title = f"⚠️ Rủi ro {decision.risk_score:.0f}%"
            else:
                alert.title = f"📋 Rủi ro {decision.risk_score:.0f}%"

            if inaction > 0:
                alert.title += f" — ${inaction:,.0f} đang gặp nguy"

            # Dispatch to channels
            results = await _router.dispatch_alert(alert, channel_configs)
            alert.delivery_results = results

            _mark_fired(rule.rule_id)
            fired.append(alert)

            logger.info(
                "auto_alert_dispatched",
                alert_id=alert.alert_id,
                rule=rule.rule_name,
                severity=alert.severity.value,
                entity=f"{entity_type}/{entity_id}",
                channels={k: v.get("success") for k, v in results.items()},
            )

    if fired:
        logger.info(
            "decision_alerts_summary",
            decision_id=decision.decision_id,
            alerts_fired=len(fired),
            risk_score=decision.risk_score,
        )

    return fired


# ── Public API: trigger from Signal Ingestion ────────────────────────────

async def on_signal_ingested(
    signal_id: str,
    severity_score: float,
    confidence_score: float,
    category: str,
    title: str,
    company_id: str = "system",
) -> list[AlertRecord]:
    """
    Called after IngestService.ingest() for new signals.
    Only fires for high-severity signals.

    Args:
        signal_id: OMEN signal ID
        severity_score: Signal severity (0-100)
        confidence_score: Signal confidence (0-1)
        category: Signal category
        title: Signal title
        company_id: Company or "system" for global signals

    Returns:
        List of AlertRecords that were fired
    """
    metrics = {
        "severity_score": severity_score,
        "confidence": confidence_score,
    }

    fired = []
    channel_configs = await _build_channel_configs(company_id)

    for rule in _DEFAULT_RULES:
        if rule.metric not in metrics:
            continue
        if not _check_cooldown(rule):
            continue

        rule_copy = rule.model_copy(update={"company_id": company_id})
        alert = _engine.evaluate_rule(
            rule_copy, metrics[rule.metric], "signal", signal_id
        )

        if alert:
            # Tín hiệu tiếng Việt — gọn
            category_labels = {
                "geopolitical": "Địa chính trị",
                "weather": "Thời tiết",
                "port_congestion": "Tắc nghẽn cảng",
                "trade_policy": "Chính sách thương mại",
                "supply_chain": "Chuỗi cung ứng",
                "economic": "Kinh tế",
                "labor": "Lao động",
                "piracy": "An ninh hàng hải",
                "regulatory": "Quy định pháp lý",
            }
            cat_vi = category_labels.get(category, category.replace("_", " ").title())

            lines = [
                f"{title[:250]}",
                "",
                f"📡 **{cat_vi}** — Mức nghiêm trọng: **{severity_score:.0f}/100**",
                "",
                f"📌 Mở dashboard → kiểm tra lô hàng bị ảnh hưởng",
            ]
            alert.message = "\n".join(lines)

            alert.title = f"📡 {cat_vi} — Mức {severity_score:.0f}/100"

            results = await _router.dispatch_alert(alert, channel_configs)
            alert.delivery_results = results
            _mark_fired(rule.rule_id)
            fired.append(alert)

            logger.info(
                "signal_alert_dispatched",
                alert_id=alert.alert_id,
                signal_id=signal_id,
                severity=alert.severity.value,
                category=category,
            )

    return fired


# ── Public API: trigger from Scheduler scan ──────────────────────────────

async def on_scan_completed(
    company_id: str,
    signals_upserted: int,
    critical_count: int = 0,
    high_count: int = 0,
) -> Optional[AlertRecord]:
    """
    Called after a scheduled scan completes.
    Sends a summary alert if critical signals were found.
    """
    if critical_count == 0 and high_count == 0:
        return None

    channel_configs = await _build_channel_configs(company_id)

    severity = AlertSeverity.CRITICAL if critical_count > 0 else AlertSeverity.HIGH
    alert = AlertRecord(
        alert_id=f"alert_{uuid.uuid4().hex[:16]}",
        rule_id="scan_summary",
        rule_name="Scan Summary",
        company_id=company_id,
        severity=severity,
        status="pending",
        metric="scan_results",
        metric_value=float(critical_count + high_count),
        threshold=0,
        title=f"📊 Quét xong — {critical_count} nghiêm trọng, {high_count} mức cao",
        message=(
            f"Tổng tín hiệu: **{signals_upserted}**\n"
            f"🔴 Nghiêm trọng: **{critical_count}** — cần xử lý ngay\n"
            f"🟠 Mức cao: **{high_count}** — nên xem trong hôm nay\n\n"
            f"📌 Mở dashboard → xem lô hàng bị ảnh hưởng và khuyến nghị"
        ),
        channels=[AlertChannel.WEBHOOK, AlertChannel.IN_APP],
        triggered_at=datetime.utcnow().isoformat(),
    )

    results = await _router.dispatch_alert(alert, channel_configs)
    alert.delivery_results = results

    logger.info(
        "scan_alert_dispatched",
        signals=signals_upserted,
        critical=critical_count,
        high=high_count,
    )

    return alert

"""
Alert Engine — Rule-based alert triggering with configurable thresholds.

Evaluates alert rules against incoming metrics / risk assessments
and fires alerts when conditions are met.

Pipeline:
1. Extract metric value from the context (risk score, confidence, exposure, etc.)
2. Evaluate rule condition (operator + threshold)
3. Check dedup / cooldown (prevent alert storms)
4. Generate alert message
5. Dispatch to channels
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog

from riskcast.alerting.schemas import (
    AlertChannel,
    AlertRecord,
    AlertRule,
    AlertSeverity,
    AlertStatus,
    RuleOperator,
)

logger = structlog.get_logger(__name__)


class AlertEngine:
    """
    Core alert engine — evaluates rules and triggers alerts.

    Stateless: all state is in the DB (rules, alert history).
    Dedup and cooldown are handled by the DedupManager (separate component).
    """

    def evaluate_rule(
        self,
        rule: AlertRule,
        metric_value: float,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
    ) -> Optional[AlertRecord]:
        """
        Evaluate a single rule against a metric value.

        Args:
            rule: The alert rule to evaluate
            metric_value: Current value of the metric
            entity_type: Entity type (for entity-specific rules)
            entity_id: Entity identifier

        Returns:
            AlertRecord if rule fires, None otherwise
        """
        if not rule.is_active:
            return None

        # Entity type filter
        if rule.entity_type and entity_type and rule.entity_type != entity_type:
            return None

        # Evaluate condition
        if not self._check_condition(rule.operator, metric_value, rule.threshold):
            return None

        # Rule fires — create alert
        now = datetime.utcnow()
        alert_id = f"alert_{uuid.uuid4().hex[:16]}"

        title = self._generate_title(rule, metric_value)
        message = self._generate_message(rule, metric_value, entity_type, entity_id)

        alert = AlertRecord(
            alert_id=alert_id,
            rule_id=rule.rule_id,
            rule_name=rule.rule_name,
            company_id=rule.company_id,
            severity=rule.severity,
            status=AlertStatus.PENDING,
            metric=rule.metric,
            metric_value=metric_value,
            threshold=rule.threshold,
            entity_type=entity_type,
            entity_id=entity_id,
            title=title,
            message=message,
            channels=rule.channels,
            triggered_at=now.isoformat(),
        )

        logger.info(
            "alert_triggered",
            alert_id=alert_id,
            rule_id=rule.rule_id,
            rule_name=rule.rule_name,
            metric=rule.metric,
            metric_value=metric_value,
            threshold=rule.threshold,
            severity=rule.severity.value,
        )

        return alert

    def evaluate_rules(
        self,
        rules: list[AlertRule],
        metrics: dict[str, float],
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
    ) -> list[AlertRecord]:
        """
        Evaluate multiple rules against a metrics dict.

        Args:
            rules: List of alert rules to evaluate
            metrics: Dict of metric_name → metric_value
            entity_type: Entity type for filtering
            entity_id: Entity identifier

        Returns:
            List of fired AlertRecords
        """
        fired: list[AlertRecord] = []
        for rule in rules:
            value = metrics.get(rule.metric)
            if value is None:
                continue
            alert = self.evaluate_rule(rule, value, entity_type, entity_id)
            if alert:
                fired.append(alert)
        return fired

    def _check_condition(
        self, operator: RuleOperator, value: float, threshold: float
    ) -> bool:
        """Evaluate a rule condition."""
        if operator == RuleOperator.GT:
            return value > threshold
        elif operator == RuleOperator.GTE:
            return value >= threshold
        elif operator == RuleOperator.LT:
            return value < threshold
        elif operator == RuleOperator.LTE:
            return value <= threshold
        elif operator == RuleOperator.EQ:
            return abs(value - threshold) < 1e-9
        elif operator == RuleOperator.NEQ:
            return abs(value - threshold) >= 1e-9
        return False

    def _generate_title(self, rule: AlertRule, value: float) -> str:
        """
        Tạo tiêu đề thông báo tiếng Việt — rõ ràng, dễ hiểu.
        """
        severity_label = {
            AlertSeverity.INFO: "Thông tin",
            AlertSeverity.WARNING: "Cần chú ý",
            AlertSeverity.HIGH: "Cần hành động",
            AlertSeverity.CRITICAL: "Khẩn cấp",
        }
        label = severity_label.get(rule.severity, "Thông báo")

        metric_labels = {
            "risk_score": f"Rủi ro {value:.0f}%",
            "exposure_usd": f"${value:,.0f} đang gặp rủi ro",
            "needs_escalation": "Cần người duyệt",
            "severity_score": f"Tín hiệu mức {value:.0f}/100",
        }
        metric_desc = metric_labels.get(rule.metric, f"{rule.metric}: {value:.2f}")

        return f"{label} — {metric_desc}"

    def _generate_message(
        self,
        rule: AlertRule,
        value: float,
        entity_type: Optional[str],
        entity_id: Optional[str],
    ) -> str:
        """
        Tạo message mặc định tiếng Việt.
        Sẽ được auto_trigger ghi đè bằng nội dung chi tiết hơn.
        """
        if rule.metric == "risk_score":
            summary = (
                f"Đánh giá rủi ro lô hàng: **{value:.0f}%** "
                f"(ngưỡng cảnh báo: {rule.threshold:.0f}%).\n"
                f"Mở dashboard để xem khuyến nghị hành động và phân tích chi phí."
            )
        elif rule.metric == "exposure_usd":
            summary = (
                f"Phát hiện giá trị **${value:,.0f}** đang gặp rủi ro "
                f"(ngưỡng: ${rule.threshold:,.0f}).\n"
                f"Cần xem xét ngay để hạn chế thiệt hại."
            )
        elif rule.metric == "needs_escalation":
            summary = (
                f"Quyết định này cần được **người có thẩm quyền duyệt**.\n"
                f"AI đã đưa ra khuyến nghị nhưng cần phê duyệt trước khi thực hiện."
            )
        else:
            summary = f"{rule.description or rule.rule_name}"

        if entity_type and entity_id:
            short_id = entity_id[:12] + "..." if entity_id and len(entity_id) > 16 else entity_id
            summary += f"\n📦 Đơn hàng: `{entity_type}/{short_id}`"

        return summary

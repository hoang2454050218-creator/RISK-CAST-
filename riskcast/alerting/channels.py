"""
Alert Channels — Dispatch alerts via webhook, email, or in-app notification.

Each channel is independent and fault-tolerant:
- Webhook: POST JSON to configured URL (with SSRF protection)
- Email: Send via SMTP (async)
- In-App: Store in DB for frontend polling

All dispatches are logged and tracked.
"""

import json
from datetime import datetime, timezone
from typing import Optional, Protocol

import structlog

from riskcast.alerting.schemas import AlertChannel, AlertRecord, AlertStatus

logger = structlog.get_logger(__name__)


class ChannelDispatcher(Protocol):
    """Protocol for alert channel dispatchers."""

    async def dispatch(self, alert: AlertRecord, config: dict) -> dict:
        """
        Send an alert via this channel.

        Returns:
            dict with delivery result: {"success": bool, "detail": str}
        """
        ...


class WebhookDispatcher:
    """
    Dispatch alerts via HTTP webhook.

    Posts a JSON payload to the configured webhook URL.
    Includes SSRF protection via URL validation.
    """

    async def dispatch(self, alert: AlertRecord, config: dict) -> dict:
        """
        Send alert to webhook URL.

        Config keys:
        - url: Webhook URL (required)
        - headers: Optional extra headers
        - timeout: Request timeout in seconds (default: 10)
        """
        url = config.get("url")
        if not url:
            return {"success": False, "detail": "No webhook URL configured"}

        # SSRF protection
        from riskcast.services.input_sanitizer import validate_webhook_url
        is_valid, reason = validate_webhook_url(url)
        if not is_valid:
            logger.warning("webhook_ssrf_blocked", url=url, reason=reason)
            return {"success": False, "detail": f"SSRF blocked: {reason}"}

        payload = self._build_payload(url, alert)

        timeout = config.get("timeout", 10)
        headers = config.get("headers", {})
        headers.setdefault("Content-Type", "application/json")

        try:
            import httpx
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                if response.status_code < 400:
                    logger.info(
                        "webhook_alert_sent",
                        alert_id=alert.alert_id,
                        url=url,
                        status=response.status_code,
                    )
                    return {"success": True, "detail": f"HTTP {response.status_code}"}
                else:
                    logger.warning(
                        "webhook_alert_failed",
                        alert_id=alert.alert_id,
                        url=url,
                        status=response.status_code,
                    )
                    return {"success": False, "detail": f"HTTP {response.status_code}"}
        except Exception as e:
            logger.error("webhook_dispatch_error", alert_id=alert.alert_id, error=str(e))
            return {"success": False, "detail": str(e)}


    # ── Payload builders ───────────────────────────────────────────

    @staticmethod
    def _build_payload(url: str, alert: AlertRecord) -> dict:
        """Build payload — auto-detects Discord vs generic webhook."""
        if "discord.com/api/webhooks" in url:
            return WebhookDispatcher._build_discord_payload(alert)
        # Generic webhook (Slack-compatible)
        return {
            "alert_id": alert.alert_id,
            "rule_name": alert.rule_name,
            "severity": alert.severity.value,
            "title": alert.title,
            "message": alert.message,
            "metric": alert.metric,
            "metric_value": alert.metric_value,
            "threshold": alert.threshold,
            "entity_type": alert.entity_type,
            "entity_id": alert.entity_id,
            "triggered_at": alert.triggered_at,
        }

    @staticmethod
    def _format_usd(value: float) -> str:
        """Format USD amount for display."""
        if value >= 1_000_000:
            return f"${value / 1_000_000:,.1f}M"
        elif value >= 1_000:
            return f"${value:,.0f}"
        elif value > 0:
            return f"${value:,.2f}"
        return "—"

    @staticmethod
    def _build_discord_payload(alert: AlertRecord) -> dict:
        """
        Build Discord embed — tiếng Việt, ngôn ngữ kinh doanh.

        Nguyên tắc: đọc xong phải biết
        1. Chuyện gì đang xảy ra?
        2. Mất bao nhiêu tiền?
        3. Phải làm gì tiếp?
        """
        severity_colors = {
            "critical": 0xFF0000,   # Đỏ — cần hành động ngay
            "high": 0xFF6600,       # Cam — cần hành động trong ngày
            "warning": 0xFFCC00,    # Vàng — theo dõi sát
            "info": 0x0099FF,       # Xanh — thông tin
        }
        color = severity_colors.get(alert.severity.value, 0x808080)

        severity_labels = {
            "critical": "🔴 KHẨN CẤP",
            "high": "🟠 CẦN XỬ LÝ",
            "warning": "🟡 THEO DÕI",
            "info": "🔵 THÔNG TIN",
        }
        sev_label = severity_labels.get(alert.severity.value, "⚠️ CẢNH BÁO")

        # ── Build fields tiếng Việt ──
        fields = [
            {
                "name": "Mức độ",
                "value": sev_label,
                "inline": True,
            },
        ]

        # Mức rủi ro
        if alert.metric == "risk_score" and alert.metric_value is not None:
            risk_bar = WebhookDispatcher._risk_bar(alert.metric_value)
            risk_level = "Rất cao" if alert.metric_value >= 75 else "Cao" if alert.metric_value >= 50 else "Trung bình"
            fields.append({
                "name": "Rủi ro",
                "value": f"{risk_bar}\n**{alert.metric_value:.0f}%** — {risk_level}",
                "inline": True,
            })
        elif alert.metric == "exposure_usd" and alert.metric_value is not None:
            fields.append({
                "name": "Giá trị gặp rủi ro",
                "value": f"**{WebhookDispatcher._format_usd(alert.metric_value)}**",
                "inline": True,
            })
        elif alert.metric == "needs_escalation":
            fields.append({
                "name": "Trạng thái",
                "value": "🔍 **Cần người duyệt**",
                "inline": True,
            })
        elif alert.metric_value is not None:
            fields.append({
                "name": "Điểm",
                "value": f"**{alert.metric_value:.0f}**/100",
                "inline": True,
            })

        # Đơn hàng
        if alert.entity_type and alert.entity_id:
            entity_labels = {
                "order": "📦 Đơn hàng",
                "shipment": "🚢 Lô hàng",
                "route": "🗺️ Tuyến",
                "signal": "📡 Tín hiệu",
            }
            label = entity_labels.get(alert.entity_type, "📋 Đối tượng")
            short_id = alert.entity_id
            if len(short_id) > 16:
                short_id = short_id[:8] + "..." + short_id[-4:]
            fields.append({
                "name": label,
                "value": f"`{short_id}`",
                "inline": True,
            })

        # Thời gian phát hiện
        if alert.triggered_at:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(alert.triggered_at)
                friendly_time = dt.strftime("%d/%m/%Y %H:%M")
            except (ValueError, TypeError):
                friendly_time = alert.triggered_at
            fields.append({
                "name": "🕐 Phát hiện lúc",
                "value": friendly_time,
                "inline": True,
            })

        return {
            "username": "RiskCast",
            "avatar_url": "https://i.imgur.com/4M34hi2.png",
            "embeds": [{
                "title": alert.title or "RiskCast — Thông báo",
                "description": alert.message or "",
                "color": color,
                "fields": fields,
                "footer": {
                    "text": f"RiskCast Decision Engine",
                },
                "timestamp": alert.triggered_at or "",
            }],
        }

    @staticmethod
    def _risk_bar(score: float) -> str:
        """Thanh rủi ro trực quan cho Discord."""
        if score >= 80:
            return "🔴🔴🔴🔴🔴"
        elif score >= 60:
            return "🟠🟠🟠🟠⚪"
        elif score >= 40:
            return "🟡🟡🟡⚪⚪"
        elif score >= 20:
            return "🟢🟢⚪⚪⚪"
        return "🟢⚪⚪⚪⚪"


class EmailDispatcher:
    """
    Dispatch alerts via email (SMTP).

    Constructs a plain-text email with alert details.
    """

    async def dispatch(self, alert: AlertRecord, config: dict) -> dict:
        """
        Send alert via email.

        Config keys:
        - smtp_host: SMTP server hostname (required)
        - smtp_port: SMTP port (default: 587)
        - smtp_user: SMTP username
        - smtp_password: SMTP password
        - from_email: Sender email
        - to_emails: List of recipient emails (required)
        """
        to_emails = config.get("to_emails", [])
        if not to_emails:
            return {"success": False, "detail": "No recipient emails configured"}

        smtp_host = config.get("smtp_host", "")
        if not smtp_host:
            return {"success": False, "detail": "No SMTP host configured"}

        smtp_port = config.get("smtp_port", 587)
        smtp_user = config.get("smtp_user", "")
        smtp_password = config.get("smtp_password", "")
        from_email = config.get("from_email", "alerts@riskcast.io")

        subject = alert.title
        # Xóa markdown cho email (plain text)
        clean_message = alert.message.replace("**", "").replace("`", "").replace("_", "")
        sev_vi = {
            "critical": "KHẨN CẤP", "high": "CẦN XỬ LÝ",
            "warning": "THEO DÕI", "info": "THÔNG TIN",
        }.get(alert.severity.value, alert.severity.value.upper())
        body = (
            f"RiskCast — {sev_vi}\n"
            f"{'=' * 50}\n\n"
            f"{clean_message}\n\n"
            f"{'─' * 50}\n"
            f"Mức độ: {sev_vi}\n"
        )
        if alert.entity_type and alert.entity_id:
            body += f"Đối tượng: {alert.entity_type}/{alert.entity_id}\n"
        if alert.triggered_at:
            body += f"Thời gian: {alert.triggered_at}\n"
        body += (
            f"\n{'─' * 50}\n"
            f"Xem chi tiết tại dashboard RiskCast.\n"
        )

        try:
            import aiosmtplib
            from email.mime.text import MIMEText

            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = from_email
            msg["To"] = ", ".join(to_emails)

            await aiosmtplib.send(
                msg,
                hostname=smtp_host,
                port=smtp_port,
                username=smtp_user or None,
                password=smtp_password or None,
                start_tls=True,
            )
            logger.info(
                "email_alert_sent",
                alert_id=alert.alert_id,
                to=to_emails,
            )
            return {"success": True, "detail": f"Sent to {len(to_emails)} recipients"}
        except ImportError:
            logger.warning("aiosmtplib_not_installed", alert_id=alert.alert_id)
            return {"success": False, "detail": "aiosmtplib not installed"}
        except Exception as e:
            logger.error("email_dispatch_error", alert_id=alert.alert_id, error=str(e))
            return {"success": False, "detail": str(e)}


class InAppDispatcher:
    """
    In-app notification — stores alert in DB for frontend polling.

    This is always available (no external dependencies).
    """

    async def dispatch(self, alert: AlertRecord, config: dict) -> dict:
        """
        Store alert as an in-app notification.

        The actual DB write is handled by the AlertService (which calls this),
        so here we just confirm readiness.
        """
        logger.info(
            "in_app_alert_created",
            alert_id=alert.alert_id,
            rule_name=alert.rule_name,
        )
        return {"success": True, "detail": "Stored as in-app notification"}


class ChannelRouter:
    """
    Routes alerts to the appropriate channel dispatcher(s).

    Dispatches to all configured channels in parallel.
    """

    def __init__(self):
        self._dispatchers: dict[AlertChannel, ChannelDispatcher] = {
            AlertChannel.WEBHOOK: WebhookDispatcher(),
            AlertChannel.EMAIL: EmailDispatcher(),
            AlertChannel.IN_APP: InAppDispatcher(),
        }

    async def dispatch_alert(
        self,
        alert: AlertRecord,
        channel_configs: dict[str, dict],
    ) -> dict[str, dict]:
        """
        Dispatch an alert to all its configured channels.

        Args:
            alert: The alert to dispatch
            channel_configs: Dict of channel_name → config dict

        Returns:
            Dict of channel_name → delivery result
        """
        results: dict[str, dict] = {}

        for channel in alert.channels:
            dispatcher = self._dispatchers.get(channel)
            if not dispatcher:
                results[channel.value] = {
                    "success": False,
                    "detail": f"Unknown channel: {channel}",
                }
                continue

            config = channel_configs.get(channel.value, {})
            try:
                result = await dispatcher.dispatch(alert, config)
                results[channel.value] = result
            except Exception as e:
                logger.error(
                    "channel_dispatch_error",
                    channel=channel.value,
                    alert_id=alert.alert_id,
                    error=str(e),
                )
                results[channel.value] = {"success": False, "detail": str(e)}

        return results

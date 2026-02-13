"""
Alerter Service.

Main service for delivering decisions to customers via WhatsApp.

Responsibilities:
- Format decisions into messages
- Send via appropriate channel (WhatsApp, email)
- Track delivery status
- Handle retries and failures
- Prevent duplicate alerts
"""

from typing import Optional
from datetime import datetime, timedelta
import asyncio

import structlog

from app.riskcast.schemas.decision import DecisionObject
from app.riskcast.schemas.customer import CustomerProfile, CustomerContext
from app.alerter.templates import (
    build_decision_message,
    TemplateType,
    MessageContent,
    render_template,
)
from app.alerter.twilio_client import (
    TwilioWhatsAppClient,
    SendResult,
    DeliveryStatus,
    get_twilio_client,
)

logger = structlog.get_logger(__name__)


# ============================================================================
# MODELS
# ============================================================================


class AlertRecord:
    """Record of a sent alert."""

    def __init__(
        self,
        alert_id: str,
        customer_id: str,
        decision_id: str,
        channel: str,
        recipient: str,
        template_type: TemplateType,
        message_sid: Optional[str] = None,
    ):
        self.alert_id = alert_id
        self.customer_id = customer_id
        self.decision_id = decision_id
        self.channel = channel
        self.recipient = recipient
        self.template_type = template_type
        self.message_sid = message_sid
        self.status = DeliveryStatus.QUEUED
        self.created_at = datetime.utcnow()
        self.sent_at: Optional[datetime] = None
        self.delivered_at: Optional[datetime] = None
        self.error_message: Optional[str] = None
        self.retry_count = 0


class AlertResult:
    """Result of alert delivery."""

    def __init__(
        self,
        success: bool,
        alert_id: Optional[str] = None,
        message_sid: Optional[str] = None,
        channel: Optional[str] = None,
        error: Optional[str] = None,
    ):
        self.success = success
        self.alert_id = alert_id
        self.message_sid = message_sid
        self.channel = channel
        self.error = error


# ============================================================================
# SERVICE
# ============================================================================


class AlerterService:
    """
    Main alerter service.

    Delivers decisions to customers and tracks delivery status.

    Usage:
        service = AlerterService()
        await service.start()

        # Send decision to customer
        result = await service.send_decision(decision, customer)

        # Send to all affected customers
        results = await service.broadcast_decision(decision, customers)

        await service.stop()
    """

    def __init__(
        self,
        twilio_client: Optional[TwilioWhatsAppClient] = None,
    ):
        """Initialize service."""
        self._twilio = twilio_client
        self._running = False

        # Alert tracking (in production, use database)
        self._alerts: dict[str, AlertRecord] = {}
        self._sent_hashes: set[str] = set()  # For deduplication

        # Configuration
        self._retry_limit = 3
        self._retry_delay_seconds = 60
        self._dedup_window_hours = 24

    async def start(self):
        """Start the alerter service."""
        if self._running:
            return

        if self._twilio is None:
            self._twilio = get_twilio_client()

        await self._twilio.connect()
        self._running = True

        logger.info("alerter_service_started")

    async def stop(self):
        """Stop the alerter service."""
        self._running = False

        if self._twilio:
            await self._twilio.disconnect()

        logger.info("alerter_service_stopped")

    # ========================================================================
    # SENDING
    # ========================================================================

    async def send_decision(
        self,
        decision: DecisionObject,
        customer: CustomerProfile,
        force: bool = False,
    ) -> AlertResult:
        """
        Send decision alert to a customer.

        Args:
            decision: The decision to send
            customer: Customer profile
            force: If True, send even if duplicate

        Returns:
            AlertResult with delivery status
        """
        if not customer.notification_enabled:
            return AlertResult(
                success=False,
                error="Notifications disabled for customer",
            )

        # Check for duplicates
        message_hash = self._twilio.generate_message_hash(
            customer.customer_id,
            decision.decision_id,
            TemplateType.DECISION_URGENT,
        )

        if not force and message_hash in self._sent_hashes:
            logger.info(
                "duplicate_alert_skipped",
                customer_id=customer.customer_id,
                decision_id=decision.decision_id,
            )
            return AlertResult(
                success=False,
                error="Duplicate alert",
            )

        # Build message
        message = build_decision_message(decision)

        # Send via WhatsApp if enabled
        if customer.whatsapp_enabled:
            result = await self._send_whatsapp(decision, customer, message, message_hash)
            if result.success:
                return result

        # Fallback to email if enabled (not implemented yet)
        if customer.email_enabled and customer.email:
            # TODO: Implement email sending
            pass

        return AlertResult(
            success=False,
            error="No delivery channel available",
        )

    async def broadcast_decision(
        self,
        decision: DecisionObject,
        customers: list[CustomerContext],
    ) -> list[AlertResult]:
        """
        Send decision to multiple customers.

        Args:
            decision: The decision to broadcast
            customers: List of customer contexts

        Returns:
            List of AlertResults
        """
        results = []

        for context in customers:
            result = await self.send_decision(decision, context.profile)
            results.append(result)

            # Small delay between messages
            await asyncio.sleep(0.1)

        success_count = sum(1 for r in results if r.success)
        logger.info(
            "decision_broadcast_complete",
            decision_id=decision.decision_id,
            total=len(customers),
            success=success_count,
        )

        return results

    async def send_reminder(
        self,
        decision: DecisionObject,
        customer: CustomerProfile,
        hours_until_deadline: int,
    ) -> AlertResult:
        """
        Send deadline reminder.

        Args:
            decision: The decision
            customer: Customer profile
            hours_until_deadline: Hours until action deadline

        Returns:
            AlertResult
        """
        if not customer.whatsapp_enabled:
            return AlertResult(success=False, error="WhatsApp not enabled")

        # Build reminder message
        from app.alerter.templates import TEMPLATES, render_template

        params = [
            decision.q1_what.headline,  # {{1}} - Event
            f"{hours_until_deadline} hours",  # {{2}} - Time remaining
            f"{decision.q7_inaction.inaction_cost_usd:,.0f}",  # {{3}} - New cost
            f"{decision.q7_inaction.additional_delay_days:.0f}",  # {{4}} - Additional delay
        ]

        message = MessageContent(
            template_type=TemplateType.DEADLINE_REMINDER,
            template_name=TEMPLATES[TemplateType.DEADLINE_REMINDER]["name"],
            language="en",
            parameters=params,
            preview_text=f"Deadline approaching for {decision.q1_what.headline}",
        )

        return await self._send_whatsapp(
            decision,
            customer,
            message,
            message_hash=None,
        )

    # ========================================================================
    # INTERNAL
    # ========================================================================

    async def _send_whatsapp(
        self,
        decision: DecisionObject,
        customer: CustomerProfile,
        message: MessageContent,
        message_hash: Optional[str],
    ) -> AlertResult:
        """Send via WhatsApp."""
        # Create alert record
        alert_id = f"ALERT-{decision.decision_id}-{datetime.utcnow().strftime('%H%M%S')}"
        record = AlertRecord(
            alert_id=alert_id,
            customer_id=customer.customer_id,
            decision_id=decision.decision_id,
            channel="whatsapp",
            recipient=customer.primary_phone,
            template_type=message.template_type,
        )

        # Send message
        result = await self._twilio.send_template(
            to=customer.primary_phone,
            message=message,
        )

        # Update record
        record.message_sid = result.message_sid
        record.status = result.status
        record.sent_at = datetime.utcnow() if result.success else None
        record.error_message = result.error_message

        # Store record
        self._alerts[alert_id] = record

        # Mark as sent for dedup
        if result.success and message_hash:
            self._sent_hashes.add(message_hash)

        logger.info(
            "whatsapp_alert_sent" if result.success else "whatsapp_alert_failed",
            alert_id=alert_id,
            customer_id=customer.customer_id,
            decision_id=decision.decision_id,
            message_sid=result.message_sid,
            error=result.error_message,
        )

        return AlertResult(
            success=result.success,
            alert_id=alert_id,
            message_sid=result.message_sid,
            channel="whatsapp",
            error=result.error_message,
        )

    # ========================================================================
    # STATUS
    # ========================================================================

    async def check_delivery_status(self, alert_id: str) -> Optional[DeliveryStatus]:
        """
        Check delivery status of an alert.

        Args:
            alert_id: Alert ID

        Returns:
            DeliveryStatus or None
        """
        record = self._alerts.get(alert_id)
        if not record or not record.message_sid:
            return None

        status = await self._twilio.get_message_status(record.message_sid)

        if status:
            record.status = status
            if status == DeliveryStatus.DELIVERED:
                record.delivered_at = datetime.utcnow()

        return status

    async def get_alert(self, alert_id: str) -> Optional[AlertRecord]:
        """Get alert record."""
        return self._alerts.get(alert_id)

    async def get_customer_alerts(
        self,
        customer_id: str,
        limit: int = 10,
    ) -> list[AlertRecord]:
        """Get recent alerts for a customer."""
        alerts = [
            a for a in self._alerts.values()
            if a.customer_id == customer_id
        ]
        # Sort by created_at desc
        alerts.sort(key=lambda a: a.created_at, reverse=True)
        return alerts[:limit]

    # ========================================================================
    # RETRY
    # ========================================================================

    async def retry_failed_alerts(self):
        """Retry failed alerts."""
        for alert in self._alerts.values():
            if (
                alert.status == DeliveryStatus.FAILED and
                alert.retry_count < self._retry_limit
            ):
                # Get customer (in production, from database)
                # For now, skip retry logic
                alert.retry_count += 1

    # ========================================================================
    # CLEANUP
    # ========================================================================

    def cleanup_old_hashes(self):
        """Clean up old deduplication hashes."""
        # In production, this would be time-based
        # For now, just limit size
        if len(self._sent_hashes) > 10000:
            # Keep most recent half
            self._sent_hashes = set(list(self._sent_hashes)[-5000:])


# ============================================================================
# FACTORY
# ============================================================================


_service_instance: Optional[AlerterService] = None


def get_alerter_service() -> AlerterService:
    """Get alerter service singleton."""
    global _service_instance
    if _service_instance is None:
        _service_instance = AlerterService()
    return _service_instance


async def create_alerter_service() -> AlerterService:
    """Create and start alerter service."""
    service = AlerterService()
    await service.start()
    return service

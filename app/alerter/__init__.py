"""Alerter Module.

Delivers decisions to customers via WhatsApp and other channels.
"""

from app.alerter.templates import (
    TemplateType,
    MessageContent,
    build_decision_message,
    render_template,
)
from app.alerter.twilio_client import (
    TwilioWhatsAppClient,
    TwilioConfig,
    SendResult,
    DeliveryStatus,
    get_twilio_client,
    create_twilio_client,
)
from app.alerter.service import (
    AlerterService,
    AlertRecord,
    AlertResult,
    get_alerter_service,
    create_alerter_service,
)

__all__ = [
    # Templates
    "TemplateType",
    "MessageContent",
    "build_decision_message",
    "render_template",
    # Twilio
    "TwilioWhatsAppClient",
    "TwilioConfig",
    "SendResult",
    "DeliveryStatus",
    "get_twilio_client",
    "create_twilio_client",
    # Service
    "AlerterService",
    "AlertRecord",
    "AlertResult",
    "get_alerter_service",
    "create_alerter_service",
]

"""
Twilio WhatsApp Client.

Sends WhatsApp messages via Twilio API.
Handles template messages, rate limiting, and delivery status.
"""

from typing import Optional
from datetime import datetime
from enum import Enum
import asyncio
import hashlib

import httpx
import structlog
from pydantic import BaseModel, Field

from app.core.config import settings
from app.common.resilience import retry_with_backoff, CircuitBreaker
from app.alerter.templates import MessageContent, TemplateType

logger = structlog.get_logger(__name__)


# ============================================================================
# MODELS
# ============================================================================


class DeliveryStatus(str, Enum):
    """Message delivery status."""

    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    UNDELIVERED = "undelivered"


class SendResult(BaseModel):
    """Result of sending a message."""

    success: bool
    message_sid: Optional[str] = None
    status: DeliveryStatus = DeliveryStatus.QUEUED
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TwilioConfig(BaseModel):
    """Twilio configuration — supports Account SID+Token or API Key auth."""

    account_sid: str = ""  # AC... (auto-discovered if using API Key)
    auth_token: str = ""
    api_key_sid: str = ""  # SK... (API Key authentication)
    api_key_secret: str = ""
    whatsapp_number: str = ""  # e.g., "whatsapp:+14155238886"
    status_callback_url: Optional[str] = None
    timeout_seconds: float = 30.0

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key_sid and self.api_key_secret)

    @property
    def has_account_auth(self) -> bool:
        return bool(self.account_sid and self.auth_token)

    @property
    def auth_credentials(self) -> tuple[str, str]:
        """Return (username, password) for HTTP Basic Auth.
        Prefers Account SID + Auth Token (most reliable).
        Falls back to API Key SID + Secret.
        """
        if self.has_account_auth:
            return (self.account_sid, self.auth_token)
        if self.has_api_key:
            return (self.api_key_sid, self.api_key_secret)
        return ("", "")


# ============================================================================
# CLIENT
# ============================================================================


class TwilioWhatsAppClient:
    """
    WhatsApp client using Twilio API.

    Supports:
    - Template messages (for outbound)
    - Free-form messages (for customer service)
    - Delivery status tracking
    - Rate limiting

    Usage:
        client = TwilioWhatsAppClient(config)
        await client.connect()

        result = await client.send_template(
            to="+1234567890",
            message=message_content,
        )

        await client.disconnect()
    """

    TWILIO_API_BASE = "https://api.twilio.com/2010-04-01"

    def __init__(self, config: Optional[TwilioConfig] = None):
        """Initialize client with config."""
        if config:
            self._config = config
        else:
            # Load from settings — support both Account SID+Token and API Key
            self._config = TwilioConfig(
                account_sid=settings.twilio_account_sid or "",
                auth_token=settings.twilio_auth_token or "",
                api_key_sid=getattr(settings, "twilio_api_key_sid", None) or "",
                api_key_secret=getattr(settings, "twilio_api_key_secret", None) or "",
                whatsapp_number=settings.twilio_whatsapp_number or "",
            )

        self._http_client: Optional[httpx.AsyncClient] = None
        self._circuit_breaker = CircuitBreaker(
            name="twilio_api",
            failure_threshold=5,
            recovery_timeout=60.0,
        )

        # Rate limiting
        self._send_times: list[datetime] = []
        self._max_messages_per_second = 10

    @property
    def is_configured(self) -> bool:
        """Check if Twilio is properly configured."""
        has_auth = self._config.has_api_key or self._config.has_account_auth
        return has_auth and bool(self._config.whatsapp_number)

    async def connect(self):
        """Initialize HTTP client, auto-discovering Account SID if needed."""
        if self._http_client is None:
            # If using API Key and Account SID not set, discover it
            if self._config.has_api_key and not self._config.account_sid:
                discovered = await self._discover_account_sid()
                if discovered:
                    self._config.account_sid = discovered
                    logger.info("twilio_account_sid_discovered", sid=discovered[:8] + "...")
                else:
                    logger.error("twilio_account_sid_discovery_failed")
                    return

            self._http_client = httpx.AsyncClient(
                base_url=self.TWILIO_API_BASE,
                timeout=httpx.Timeout(self._config.timeout_seconds),
                auth=self._config.auth_credentials,
                follow_redirects=True,
            )
            logger.info("twilio_client_connected", auth_mode="api_key" if self._config.has_api_key else "account")

    async def _discover_account_sid(self) -> Optional[str]:
        """Auto-discover Account SID using API Key credentials."""
        try:
            async with httpx.AsyncClient(
                base_url=self.TWILIO_API_BASE,
                timeout=httpx.Timeout(10.0),
                auth=self._config.auth_credentials,
            ) as client:
                resp = await client.get("/2010-04-01/Accounts.json")
                if resp.status_code == 200:
                    data = resp.json()
                    accounts = data.get("accounts", [])
                    if accounts:
                        return accounts[0]["sid"]
                logger.warning("twilio_discovery_failed", status=resp.status_code)
        except Exception as e:
            logger.error("twilio_discovery_error", error=str(e))
        return None

    async def disconnect(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
            logger.info("twilio_client_disconnected")

    # ========================================================================
    # SENDING
    # ========================================================================

    async def send_template(
        self,
        to: str,
        message: MessageContent,
    ) -> SendResult:
        """
        Send a template message.

        Args:
            to: Recipient phone number (with country code)
            message: Formatted message content

        Returns:
            SendResult with delivery status
        """
        if not self.is_configured:
            logger.warning("twilio_not_configured")
            return SendResult(
                success=False,
                error_code="NOT_CONFIGURED",
                error_message="Twilio credentials not configured",
            )

        # Rate limiting
        await self._enforce_rate_limit()

        # Format phone number
        to_whatsapp = self._format_whatsapp_number(to)

        # Build template message body
        body = self._build_template_body(message)

        return await self._send_message(to_whatsapp, body)

    async def send_text(
        self,
        to: str,
        text: str,
    ) -> SendResult:
        """
        Send a plain text message.

        Note: Can only be sent within 24-hour session window.

        Args:
            to: Recipient phone number
            text: Message text

        Returns:
            SendResult
        """
        if not self.is_configured:
            return SendResult(
                success=False,
                error_code="NOT_CONFIGURED",
                error_message="Twilio credentials not configured",
            )

        await self._enforce_rate_limit()
        to_whatsapp = self._format_whatsapp_number(to)

        return await self._send_message(to_whatsapp, text)

    @retry_with_backoff(max_retries=3)
    async def _send_message(
        self,
        to: str,
        body: str,
    ) -> SendResult:
        """Send message via Twilio API."""
        async with self._circuit_breaker:
            try:
                response = await self._http_client.post(
                    f"/Accounts/{self._config.account_sid}/Messages.json",
                    data={
                        "From": self._config.whatsapp_number,
                        "To": to,
                        "Body": body,
                        "StatusCallback": self._config.status_callback_url,
                    },
                )

                data = response.json()

                if response.is_success:
                    logger.info(
                        "message_sent",
                        message_sid=data.get("sid"),
                        to=to,
                        status=data.get("status"),
                    )

                    return SendResult(
                        success=True,
                        message_sid=data.get("sid"),
                        status=DeliveryStatus(data.get("status", "queued")),
                    )
                else:
                    logger.error(
                        "message_send_failed",
                        error_code=data.get("code"),
                        error_message=data.get("message"),
                    )

                    return SendResult(
                        success=False,
                        error_code=str(data.get("code")),
                        error_message=data.get("message"),
                        status=DeliveryStatus.FAILED,
                    )

            except httpx.HTTPError as e:
                logger.error("twilio_http_error", error=str(e))
                return SendResult(
                    success=False,
                    error_code="HTTP_ERROR",
                    error_message=str(e),
                    status=DeliveryStatus.FAILED,
                )

    # ========================================================================
    # STATUS
    # ========================================================================

    async def get_message_status(self, message_sid: str) -> Optional[DeliveryStatus]:
        """
        Get delivery status of a message.

        Args:
            message_sid: Twilio message SID

        Returns:
            DeliveryStatus or None
        """
        if not self.is_configured:
            return None

        try:
            response = await self._http_client.get(
                f"/Accounts/{self._config.account_sid}/Messages/{message_sid}.json"
            )

            if response.is_success:
                data = response.json()
                return DeliveryStatus(data.get("status", "failed"))
            return None

        except Exception as e:
            logger.warning("status_check_failed", error=str(e))
            return None

    # ========================================================================
    # HELPERS
    # ========================================================================

    def _format_whatsapp_number(self, phone: str) -> str:
        """Format phone number for WhatsApp."""
        # Remove spaces and dashes
        phone = phone.replace(" ", "").replace("-", "")

        # Ensure starts with +
        if not phone.startswith("+"):
            phone = "+" + phone

        # Add whatsapp: prefix
        if not phone.startswith("whatsapp:"):
            phone = f"whatsapp:{phone}"

        return phone

    def _build_template_body(self, message: MessageContent) -> str:
        """
        Build message body for template.

        For Twilio Content Templates, we use Content SID.
        For regular templates, we build the body with parameters.
        """
        # For now, use preview text as body
        # In production, use Content Templates API
        body_parts = []

        if message.header:
            body_parts.append(message.header)

        body_parts.append(message.preview_text)

        return "\n\n".join(body_parts)

    async def _enforce_rate_limit(self):
        """Enforce rate limiting."""
        now = datetime.utcnow()

        # Remove old timestamps
        cutoff = now.timestamp() - 1.0  # 1 second window
        self._send_times = [t for t in self._send_times if t.timestamp() > cutoff]

        # Check if at limit
        if len(self._send_times) >= self._max_messages_per_second:
            # Wait until oldest message is outside window
            wait_time = 1.0 - (now.timestamp() - self._send_times[0].timestamp())
            if wait_time > 0:
                await asyncio.sleep(wait_time)

        # Record this send
        self._send_times.append(now)

    def generate_message_hash(
        self,
        customer_id: str,
        decision_id: str,
        template_type: TemplateType,
    ) -> str:
        """Generate hash for deduplication."""
        content = f"{customer_id}:{decision_id}:{template_type.value}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]


# ============================================================================
# FACTORY
# ============================================================================


_client_instance: Optional[TwilioWhatsAppClient] = None


def get_twilio_client() -> TwilioWhatsAppClient:
    """Get Twilio client singleton."""
    global _client_instance
    if _client_instance is None:
        _client_instance = TwilioWhatsAppClient()
    return _client_instance


async def create_twilio_client() -> TwilioWhatsAppClient:
    """Create and connect Twilio client."""
    client = TwilioWhatsAppClient()
    await client.connect()
    return client

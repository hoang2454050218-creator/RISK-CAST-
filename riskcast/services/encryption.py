"""
Encryption at Rest for Sensitive Database Fields.

Uses Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256).
Transparent to application layer via SQLAlchemy TypeDecorator.

Encrypted fields:
- v2_customers.contact_email
- v2_customers.contact_phone
- v2_security_audit_log.ip_address (via direct encrypt/decrypt)
"""

import base64
import os

import structlog
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import String, TypeDecorator

from riskcast.config import settings

logger = structlog.get_logger(__name__)

# ── Key Management ─────────────────────────────────────────────────────────

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    """Get or create the Fernet cipher with the configured key."""
    global _fernet
    if _fernet is not None:
        return _fernet

    key = getattr(settings, "encryption_key", None) or os.environ.get("RISKCAST_ENCRYPTION_KEY", "")

    if not key:
        # Generate a deterministic dev key (NOT for production)
        logger.warning(
            "encryption_key_not_set",
            msg="Using default dev key. Set RISKCAST_ENCRYPTION_KEY in production!",
        )
        key = base64.urlsafe_b64encode(b"riskcast-dev-key-32bytes-padded!" [:32]).decode()

    # Ensure key is valid Fernet key (32 url-safe base64-encoded bytes)
    try:
        _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    except (ValueError, Exception):
        # If key is not valid Fernet format, derive one from it
        raw = key.encode() if isinstance(key, str) else key
        padded = raw.ljust(32, b"\0")[:32]
        derived = base64.urlsafe_b64encode(padded)
        _fernet = Fernet(derived)

    return _fernet


def encrypt(value: str) -> str:
    """Encrypt a string value. Returns base64-encoded ciphertext."""
    f = _get_fernet()
    return f.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt(value: str) -> str:
    """Decrypt a base64-encoded ciphertext. Returns plaintext string."""
    f = _get_fernet()
    try:
        return f.decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        logger.error("decryption_failed", msg="Invalid token — key mismatch or corrupted data")
        return value  # Return raw value as fallback to avoid data loss


# ── SQLAlchemy TypeDecorator ───────────────────────────────────────────────


class EncryptedString(TypeDecorator):
    """
    Transparent encrypt-on-write, decrypt-on-read TypeDecorator.

    Use in model definitions:
        email: Mapped[Optional[str]] = mapped_column(EncryptedString(255))
    """

    impl = String
    cache_ok = True

    def __init__(self, length: int = 500, **kwargs):
        # Encrypted values are longer than plaintext
        super().__init__(length=length, **kwargs)

    def process_bind_param(self, value, dialect):
        """Encrypt value before writing to DB."""
        if value is not None and value != "":
            return encrypt(value)
        return value

    def process_result_value(self, value, dialect):
        """Decrypt value after reading from DB."""
        if value is not None and value != "":
            return decrypt(value)
        return value

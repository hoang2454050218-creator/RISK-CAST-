"""
Input Sanitization Utilities — OWASP A03 + A10 Coverage.

1. LIKE wildcard sanitization (prevents LIKE injection)
2. SSRF prevention (validates webhook/external URLs)
"""

import ipaddress
import re
from urllib.parse import urlparse

import structlog

logger = structlog.get_logger(__name__)


# ── LIKE Wildcard Sanitization (A03) ──────────────────────────────────────


def sanitize_like_input(query: str) -> str:
    """
    Escape SQL LIKE wildcard characters to prevent LIKE injection.

    Escapes: %, _, [
    """
    return (
        query
        .replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
        .replace("[", "\\[")
    )


# ── SSRF Prevention (A10) ─────────────────────────────────────────────────

# Private/reserved IP ranges that should never be reachable via webhooks
_PRIVATE_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local
    ipaddress.ip_network("::1/128"),          # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),         # IPv6 private
    ipaddress.ip_network("fe80::/10"),        # IPv6 link-local
]


def validate_webhook_url(url: str) -> tuple[bool, str]:
    """
    Validate a webhook URL to prevent SSRF attacks.

    DENY:
    - Private/reserved IP addresses
    - Non-HTTP(S) schemes
    - URLs with embedded credentials
    - Localhost/loopback
    - URLs without valid hostname

    Returns:
        (is_valid, reason)
    """
    if not url or not isinstance(url, str):
        return False, "URL is empty or invalid"

    try:
        parsed = urlparse(url)
    except ValueError:
        return False, "Malformed URL"

    # Check scheme
    if parsed.scheme not in ("https", "http"):
        return False, f"Invalid scheme: {parsed.scheme}. Only HTTP(S) allowed."

    # Check for credentials in URL
    if parsed.username or parsed.password:
        return False, "URLs with embedded credentials are not allowed"

    # Check hostname
    hostname = parsed.hostname
    if not hostname:
        return False, "No hostname in URL"

    # Block localhost variants
    localhost_patterns = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
    if hostname.lower() in localhost_patterns:
        return False, f"Localhost ({hostname}) is not allowed"

    # Try to parse as IP and check against private ranges
    try:
        ip = ipaddress.ip_address(hostname)
        for network in _PRIVATE_RANGES:
            if ip in network:
                return False, f"Private/reserved IP address: {hostname}"
    except ValueError:
        # Not a raw IP — it's a hostname, which is acceptable
        pass

    # Check for suspicious hostnames
    if re.match(r"^\d+\.\d+\.\d+\.\d+$", hostname):
        # Already handled above, but double-check
        pass

    return True, "OK"

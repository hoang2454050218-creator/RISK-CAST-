"""
SSRF Prevention Tests — OWASP A10 Coverage.

Tests: private IPs blocked, localhost blocked, credentials blocked,
invalid schemes blocked, valid URLs allowed.
"""

import pytest

from riskcast.services.input_sanitizer import validate_webhook_url


class TestSSRFPrevention:
    """Test webhook URL validation against SSRF attacks."""

    # ── Valid URLs ─────────────────────────────────────────────────

    def test_valid_https_url(self):
        valid, _ = validate_webhook_url("https://hooks.slack.com/services/abc")
        assert valid

    def test_valid_http_url(self):
        valid, _ = validate_webhook_url("http://example.com/webhook")
        assert valid

    def test_valid_url_with_port(self):
        valid, _ = validate_webhook_url("https://example.com:8443/hook")
        assert valid

    def test_valid_url_with_path(self):
        valid, _ = validate_webhook_url("https://api.company.com/v1/notify")
        assert valid

    # ── Blocked: Private IPs ──────────────────────────────────────

    def test_blocked_10_network(self):
        valid, reason = validate_webhook_url("http://10.0.0.1/hook")
        assert not valid
        assert "Private" in reason

    def test_blocked_172_16_network(self):
        valid, reason = validate_webhook_url("http://172.16.0.1/hook")
        assert not valid

    def test_blocked_192_168_network(self):
        valid, reason = validate_webhook_url("http://192.168.1.1/hook")
        assert not valid

    def test_blocked_127_network(self):
        valid, reason = validate_webhook_url("http://127.0.0.1/hook")
        assert not valid

    # ── Blocked: Localhost ────────────────────────────────────────

    def test_blocked_localhost(self):
        valid, _ = validate_webhook_url("http://localhost/hook")
        assert not valid

    def test_blocked_localhost_with_port(self):
        valid, _ = validate_webhook_url("http://localhost:8080/hook")
        assert not valid

    def test_blocked_ipv6_loopback(self):
        valid, _ = validate_webhook_url("http://[::1]/hook")
        assert not valid

    def test_blocked_zero_ip(self):
        valid, _ = validate_webhook_url("http://0.0.0.0/hook")
        assert not valid

    # ── Blocked: Invalid Schemes ──────────────────────────────────

    def test_blocked_ftp_scheme(self):
        valid, reason = validate_webhook_url("ftp://example.com/file")
        assert not valid
        assert "scheme" in reason.lower()

    def test_blocked_file_scheme(self):
        valid, _ = validate_webhook_url("file:///etc/passwd")
        assert not valid

    def test_blocked_javascript_scheme(self):
        valid, _ = validate_webhook_url("javascript:alert(1)")
        assert not valid

    # ── Blocked: Credentials in URL ──────────────────────────────

    def test_blocked_credentials_in_url(self):
        valid, reason = validate_webhook_url("https://user:pass@example.com/hook")
        assert not valid
        assert "credentials" in reason.lower()

    # ── Edge Cases ────────────────────────────────────────────────

    def test_empty_url(self):
        valid, _ = validate_webhook_url("")
        assert not valid

    def test_none_url(self):
        valid, _ = validate_webhook_url(None)
        assert not valid

    def test_no_hostname(self):
        valid, _ = validate_webhook_url("https:///path")
        assert not valid

"""
Security Headers Tests — OWASP A05 Coverage.

Tests that all security headers are present and correct on every response.
"""

import pytest

from riskcast.middleware.security_headers import SECURITY_HEADERS


class TestSecurityHeaderDefinitions:
    """Test that all required headers are defined."""

    def test_x_content_type_options(self):
        assert SECURITY_HEADERS["X-Content-Type-Options"] == "nosniff"

    def test_x_frame_options(self):
        assert SECURITY_HEADERS["X-Frame-Options"] == "DENY"

    def test_x_xss_protection(self):
        assert SECURITY_HEADERS["X-XSS-Protection"] == "1; mode=block"

    def test_strict_transport_security(self):
        hsts = SECURITY_HEADERS["Strict-Transport-Security"]
        assert "max-age=" in hsts
        assert "includeSubDomains" in hsts

    def test_content_security_policy(self):
        csp = SECURITY_HEADERS["Content-Security-Policy"]
        assert "default-src" in csp
        assert "script-src" in csp

    def test_referrer_policy(self):
        assert SECURITY_HEADERS["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_permissions_policy(self):
        pp = SECURITY_HEADERS["Permissions-Policy"]
        assert "camera=()" in pp
        assert "microphone=()" in pp
        assert "geolocation=()" in pp

    def test_cache_control(self):
        cc = SECURITY_HEADERS["Cache-Control"]
        assert "no-store" in cc

    def test_all_required_headers_present(self):
        """Every OWASP-recommended header is defined."""
        required = {
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Content-Security-Policy",
            "Referrer-Policy",
            "Permissions-Policy",
        }
        assert required.issubset(set(SECURITY_HEADERS.keys()))

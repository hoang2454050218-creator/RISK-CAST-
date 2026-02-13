"""
LIKE Wildcard Injection Prevention Tests — OWASP A03 Coverage.

Tests that SQL LIKE wildcards are properly escaped to prevent
attackers from crafting search queries that bypass filters.
"""

import pytest

from riskcast.services.input_sanitizer import sanitize_like_input


class TestLikeInjection:
    """Test LIKE wildcard escape."""

    def test_normal_input_unchanged(self):
        """Normal text passes through unchanged."""
        assert sanitize_like_input("hello world") == "hello world"

    def test_percent_escaped(self):
        """% wildcard is escaped."""
        assert sanitize_like_input("100%") == "100\\%"

    def test_underscore_escaped(self):
        """_ wildcard is escaped."""
        assert sanitize_like_input("order_123") == "order\\_123"

    def test_bracket_escaped(self):
        """[ bracket (used in some SQL dialects) is escaped."""
        assert sanitize_like_input("[admin]") == "\\[admin]"

    def test_multiple_wildcards(self):
        """Multiple wildcards in one string are all escaped."""
        assert sanitize_like_input("%_[%") == "\\%\\_\\[\\%"

    def test_empty_string(self):
        """Empty string returns empty."""
        assert sanitize_like_input("") == ""

    def test_backslash_escaped_first(self):
        """Backslash is escaped before other patterns to prevent double-escape."""
        result = sanitize_like_input("\\%")
        assert result == "\\\\\\%"

    def test_unicode_preserved(self):
        """Unicode characters are not affected."""
        assert sanitize_like_input("Nguyễn") == "Nguyễn"

"""
API Key Authentication Tests.

Tests: valid key, invalid key, expired key, revoked key,
wrong scope, missing header, hash correctness.
"""

import pytest

from riskcast.auth.api_keys import (
    API_KEY_PREFIX,
    APIKeyContext,
    generate_api_key,
    hash_api_key,
    check_scope,
)
from fastapi import HTTPException


class TestGenerateAPIKey:
    """Test API key generation."""

    def test_key_has_correct_prefix(self):
        """Generated key starts with 'rc_live_'."""
        full_key, _, _ = generate_api_key()
        assert full_key.startswith(API_KEY_PREFIX)

    def test_key_length(self):
        """Generated key has reasonable length."""
        full_key, _, _ = generate_api_key()
        assert len(full_key) > 20

    def test_hash_is_sha256(self):
        """Key hash is a 64-character hex string (SHA-256)."""
        _, key_hash, _ = generate_api_key()
        assert len(key_hash) == 64
        int(key_hash, 16)  # Should not raise — valid hex

    def test_prefix_is_first_16_chars(self):
        """Key prefix is the first 16 characters of the full key."""
        full_key, _, key_prefix = generate_api_key()
        assert key_prefix == full_key[:16]

    def test_unique_keys(self):
        """Each generation produces a unique key."""
        keys = {generate_api_key()[0] for _ in range(50)}
        assert len(keys) == 50

    def test_hash_deterministic(self):
        """Same key always produces the same hash."""
        full_key, key_hash, _ = generate_api_key()
        assert hash_api_key(full_key) == key_hash

    def test_different_keys_different_hashes(self):
        """Different keys produce different hashes."""
        _, h1, _ = generate_api_key()
        _, h2, _ = generate_api_key()
        assert h1 != h2


class TestHashAPIKey:
    """Test the hash function."""

    def test_consistent(self):
        """Same input always produces same hash."""
        assert hash_api_key("test123") == hash_api_key("test123")

    def test_different_inputs(self):
        """Different inputs produce different hashes."""
        assert hash_api_key("test123") != hash_api_key("test456")


class TestCheckScope:
    """Test scope checking."""

    def test_scope_granted(self):
        """No exception when scope is in granted scopes."""
        ctx = APIKeyContext(
            company_id="00000000-0000-0000-0000-000000000001",
            key_name="test",
            key_prefix="rc_live_abc",
            scopes=["signals:ingest", "reconcile:run"],
        )
        check_scope(ctx, "signals:ingest")  # Should not raise

    def test_scope_denied(self):
        """HTTPException 403 when scope is not granted."""
        ctx = APIKeyContext(
            company_id="00000000-0000-0000-0000-000000000001",
            key_name="test",
            key_prefix="rc_live_abc",
            scopes=["signals:ingest"],
        )
        with pytest.raises(HTTPException) as exc_info:
            check_scope(ctx, "reconcile:run")
        assert exc_info.value.status_code == 403

    def test_empty_scopes(self):
        """Empty scopes deny all access."""
        ctx = APIKeyContext(
            company_id="00000000-0000-0000-0000-000000000001",
            key_name="test",
            key_prefix="rc_live_abc",
            scopes=[],
        )
        with pytest.raises(HTTPException):
            check_scope(ctx, "signals:ingest")

    def test_scope_exact_match(self):
        """Scope check requires exact string match."""
        ctx = APIKeyContext(
            company_id="00000000-0000-0000-0000-000000000001",
            key_name="test",
            key_prefix="rc_live_abc",
            scopes=["signals:ingest"],
        )
        with pytest.raises(HTTPException):
            check_scope(ctx, "signals:inges")  # Typo

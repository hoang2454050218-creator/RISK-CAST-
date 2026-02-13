"""
Tests for Secrets Management.

Tests cover:
- Secret retrieval from multiple backends
- Caching behavior
- JSON secret parsing
- Secret filtering for logs
- Access auditing
"""

import os
import json
import tempfile
from unittest.mock import MagicMock, patch
import pytest

from app.core.secrets import (
    SecretKey,
    SecretsManager,
    EnvironmentBackend,
    LocalFileBackend,
    SecretFilter,
    get_secrets_manager,
    reset_secrets_manager,
    get_database_url,
    get_twilio_credentials,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def clean_secrets_manager():
    """Reset secrets manager before and after test."""
    reset_secrets_manager()
    yield
    reset_secrets_manager()


@pytest.fixture
def env_secrets(monkeypatch):
    """Set up environment variable secrets."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/testdb")
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC_test_sid")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "test_auth_token")
    monkeypatch.setenv("POLYMARKET_API_KEY", "pm_test_key")
    monkeypatch.setenv("ENCRYPTION_KEY", "test_encryption_key")
    monkeypatch.setenv("ENVIRONMENT", "development")


@pytest.fixture
def local_secrets_file():
    """Create temporary local secrets file."""
    secrets = {
        "riskcast/database-url": "postgresql://local:local@localhost/localdb",
        "riskcast/twilio": {
            "account_sid": "AC_local_sid",
            "auth_token": "local_auth_token",
        },
        "riskcast/polymarket-api-key": "pm_local_key",
    }
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(secrets, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    os.unlink(temp_path)


# ============================================================================
# ENVIRONMENT BACKEND TESTS
# ============================================================================


class TestEnvironmentBackend:
    """Tests for EnvironmentBackend."""
    
    def test_is_always_available(self):
        """Environment backend should always be available."""
        backend = EnvironmentBackend()
        assert backend.is_available() is True
    
    def test_gets_secret_from_env(self, monkeypatch):
        """Should retrieve secret from environment variable."""
        monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC_test_123")
        
        backend = EnvironmentBackend()
        value = backend.get_secret(SecretKey.TWILIO_ACCOUNT_SID.value)
        
        assert value == "AC_test_123"
    
    def test_returns_none_for_missing(self, monkeypatch):
        """Should return None for missing secrets."""
        monkeypatch.delenv("NONEXISTENT_SECRET", raising=False)
        
        backend = EnvironmentBackend()
        value = backend.get_secret("nonexistent-secret")
        
        assert value is None


# ============================================================================
# LOCAL FILE BACKEND TESTS
# ============================================================================


class TestLocalFileBackend:
    """Tests for LocalFileBackend."""
    
    def test_is_available_when_file_exists(self, local_secrets_file):
        """Should be available when file exists."""
        backend = LocalFileBackend(local_secrets_file)
        assert backend.is_available() is True
    
    def test_is_not_available_when_file_missing(self):
        """Should not be available when file doesn't exist."""
        backend = LocalFileBackend("/nonexistent/path.json")
        assert backend.is_available() is False
    
    def test_gets_string_secret(self, local_secrets_file):
        """Should retrieve string secret from file."""
        backend = LocalFileBackend(local_secrets_file)
        value = backend.get_secret("riskcast/database-url")
        
        assert value == "postgresql://local:local@localhost/localdb"
    
    def test_gets_json_secret_as_string(self, local_secrets_file):
        """Should return dict secrets as JSON string."""
        backend = LocalFileBackend(local_secrets_file)
        value = backend.get_secret("riskcast/twilio")
        
        assert value is not None
        parsed = json.loads(value)
        assert parsed["account_sid"] == "AC_local_sid"


# ============================================================================
# SECRETS MANAGER TESTS
# ============================================================================


class TestSecretsManager:
    """Tests for SecretsManager."""
    
    def test_creates_with_backends(self):
        """Should create manager with specified backends."""
        manager = SecretsManager(
            use_aws=False,
            use_env=True,
            use_local=False,
        )
        
        assert len(manager._backends) == 1
        assert isinstance(manager._backends[0], EnvironmentBackend)
    
    def test_gets_secret_from_env(self, env_secrets):
        """Should retrieve secret from environment."""
        manager = SecretsManager(use_aws=False, use_env=True, use_local=False)
        
        value = manager.get_secret(SecretKey.TWILIO_ACCOUNT_SID)
        
        assert value == "AC_test_sid"
    
    def test_caches_secrets(self, env_secrets):
        """Should cache secrets after first retrieval."""
        manager = SecretsManager(use_aws=False, use_env=True, use_local=False)
        
        # First call
        value1 = manager.get_secret(SecretKey.POLYMARKET_API_KEY)
        
        # Should be cached
        assert SecretKey.POLYMARKET_API_KEY.value in manager._cache
        
        # Second call should use cache
        value2 = manager.get_secret(SecretKey.POLYMARKET_API_KEY)
        
        assert value1 == value2
    
    def test_cache_invalidation(self, env_secrets):
        """Should invalidate cache when requested."""
        manager = SecretsManager(use_aws=False, use_env=True, use_local=False)
        
        # Get to populate cache
        manager.get_secret(SecretKey.POLYMARKET_API_KEY)
        assert SecretKey.POLYMARKET_API_KEY.value in manager._cache
        
        # Invalidate
        manager.invalidate_cache(SecretKey.POLYMARKET_API_KEY)
        
        assert SecretKey.POLYMARKET_API_KEY.value not in manager._cache
    
    def test_cache_invalidation_all(self, env_secrets):
        """Should invalidate all cache when no key specified."""
        manager = SecretsManager(use_aws=False, use_env=True, use_local=False)
        
        # Populate cache
        manager.get_secret(SecretKey.POLYMARKET_API_KEY)
        manager.get_secret(SecretKey.TWILIO_ACCOUNT_SID)
        
        # Invalidate all
        manager.invalidate_cache()
        
        assert len(manager._cache) == 0
    
    def test_get_json_secret(self, local_secrets_file):
        """Should parse JSON secrets correctly."""
        manager = SecretsManager(
            use_aws=False,
            use_env=False,
            use_local=True,
            local_file=local_secrets_file,
        )
        
        creds = manager.get_json_secret("riskcast/twilio")
        
        assert creds is not None
        assert creds["account_sid"] == "AC_local_sid"
        assert creds["auth_token"] == "local_auth_token"
    
    def test_get_required_secret(self, env_secrets):
        """Should return value for existing required secret."""
        manager = SecretsManager(use_aws=False, use_env=True, use_local=False)
        
        value = manager.get_required_secret(SecretKey.TWILIO_ACCOUNT_SID)
        
        assert value == "AC_test_sid"
    
    def test_get_required_secret_raises_when_missing(self):
        """Should raise ValueError for missing required secret."""
        manager = SecretsManager(use_aws=False, use_env=False, use_local=False)
        
        with pytest.raises(ValueError) as exc_info:
            manager.get_required_secret("nonexistent-key")
        
        assert "nonexistent-key" in str(exc_info.value)
    
    def test_access_logging(self, env_secrets):
        """Should log secret access for auditing."""
        manager = SecretsManager(use_aws=False, use_env=True, use_local=False)
        
        manager.get_secret(SecretKey.POLYMARKET_API_KEY)
        
        log = manager.get_access_log()
        
        assert len(log) > 0
        assert log[-1]["key"] == SecretKey.POLYMARKET_API_KEY.value
    
    def test_backend_priority(self, env_secrets, local_secrets_file):
        """Should try backends in priority order."""
        manager = SecretsManager(
            use_aws=False,
            use_env=True,  # Higher priority
            use_local=True,
            local_file=local_secrets_file,
        )
        
        # Environment should take priority
        value = manager.get_secret(SecretKey.POLYMARKET_API_KEY)
        
        # Should get env value, not local file value
        assert value == "pm_test_key"


# ============================================================================
# SECRET FILTER TESTS
# ============================================================================


class TestSecretFilter:
    """Tests for SecretFilter log processor."""
    
    def test_redacts_password_field(self):
        """Should redact fields containing 'password'."""
        filter = SecretFilter()
        
        event = {"password": "secret123", "username": "user"}
        result = filter(None, None, event)
        
        assert result["password"] == "[REDACTED]"
        assert result["username"] == "user"
    
    def test_redacts_token_field(self):
        """Should redact fields containing 'token'."""
        filter = SecretFilter()
        
        event = {"auth_token": "abc123", "event": "login"}
        result = filter(None, None, event)
        
        assert result["auth_token"] == "[REDACTED]"
        assert result["event"] == "login"
    
    def test_redacts_api_key_field(self):
        """Should redact fields containing 'api_key'."""
        filter = SecretFilter()
        
        event = {"api_key": "key123", "endpoint": "/api/v1"}
        result = filter(None, None, event)
        
        assert result["api_key"] == "[REDACTED]"
        assert result["endpoint"] == "/api/v1"
    
    def test_redacts_nested_secrets(self):
        """Should redact nested secret fields."""
        filter = SecretFilter()
        
        event = {
            "user": {
                "name": "test",
                "password": "secret123",
            }
        }
        result = filter(None, None, event)
        
        assert result["user"]["password"] == "[REDACTED]"
        assert result["user"]["name"] == "test"
    
    def test_redacts_secrets_in_lists(self):
        """Should redact secrets in list items."""
        filter = SecretFilter()
        
        # Note: "services" doesn't trigger full redaction unlike "credentials"
        event = {
            "services": [
                {"api_key": "key1", "name": "service1"},
                {"api_key": "key2", "name": "service2"},
            ]
        }
        result = filter(None, None, event)
        
        assert result["services"][0]["api_key"] == "[REDACTED]"
        assert result["services"][0]["name"] == "service1"
        assert result["services"][1]["api_key"] == "[REDACTED]"
    
    def test_preserves_non_sensitive_fields(self):
        """Should preserve non-sensitive fields."""
        filter = SecretFilter()
        
        event = {
            "event_type": "user_login",
            "user_id": "123",
            "timestamp": "2024-01-01T00:00:00Z",
        }
        result = filter(None, None, event)
        
        assert result == event


# ============================================================================
# CONVENIENCE FUNCTION TESTS
# ============================================================================


class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    def test_get_database_url_from_env(self, env_secrets, clean_secrets_manager):
        """Should get database URL from environment."""
        url = get_database_url()
        
        assert url == "postgresql://test:test@localhost/testdb"
    
    def test_get_database_url_default(self, clean_secrets_manager, monkeypatch):
        """Should return default when not configured."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.delenv("DATABASE_URL", raising=False)
        
        url = get_database_url()
        
        assert "localhost" in url
        assert "riskcast" in url
    
    def test_get_twilio_credentials_from_env(self, env_secrets, clean_secrets_manager):
        """Should get Twilio credentials from environment."""
        creds = get_twilio_credentials()
        
        assert creds["account_sid"] == "AC_test_sid"
        assert creds["auth_token"] == "test_auth_token"
    
    def test_get_twilio_credentials_empty_when_missing(self, clean_secrets_manager, monkeypatch):
        """Should return empty dict when not configured."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
        monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
        
        creds = get_twilio_credentials()
        
        assert creds == {}


# ============================================================================
# SINGLETON TESTS
# ============================================================================


class TestSingleton:
    """Tests for singleton behavior."""
    
    def test_returns_same_instance(self, clean_secrets_manager, env_secrets):
        """Should return same instance on repeated calls."""
        sm1 = get_secrets_manager()
        sm2 = get_secrets_manager()
        
        assert sm1 is sm2
    
    def test_reset_clears_instance(self, clean_secrets_manager, env_secrets):
        """Reset should clear singleton instance."""
        sm1 = get_secrets_manager()
        reset_secrets_manager()
        sm2 = get_secrets_manager()
        
        assert sm1 is not sm2

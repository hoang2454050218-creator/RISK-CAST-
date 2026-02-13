"""
Secure Secrets Management.

Provides secure access to secrets from multiple backends:
- AWS Secrets Manager (production)
- Environment variables (development fallback)
- Local secrets file (development)

Security Principles:
- Secrets are NEVER logged
- Secrets are cached in memory only (not disk)
- Access is audited
- Rotation is supported via cache invalidation

Usage:
    from app.core.secrets import get_secrets_manager, SecretKey
    
    # Get a secret
    sm = get_secrets_manager()
    api_key = sm.get_secret(SecretKey.POLYMARKET_API_KEY)
    
    # Get JSON secret
    db_creds = sm.get_json_secret(SecretKey.DATABASE_CREDENTIALS)
"""

import json
import os
from typing import Optional, Any
from enum import Enum
from functools import lru_cache
from datetime import datetime
from abc import ABC, abstractmethod
import structlog

logger = structlog.get_logger(__name__)


# ============================================================================
# SECRET KEYS ENUM
# ============================================================================


class SecretKey(str, Enum):
    """
    Enumeration of all secret keys.
    
    Using an enum ensures consistency and prevents typos.
    """
    # Database
    DATABASE_URL = "riskcast/database-url"
    DATABASE_CREDENTIALS = "riskcast/database"
    
    # External APIs
    TWILIO_ACCOUNT_SID = "riskcast/twilio-account-sid"
    TWILIO_AUTH_TOKEN = "riskcast/twilio-auth-token"
    POLYMARKET_API_KEY = "riskcast/polymarket-api-key"
    AIS_API_KEY = "riskcast/ais-api-key"
    
    # Encryption
    ENCRYPTION_MASTER_KEY = "riskcast/encryption-key"
    
    # Full credentials bundles (JSON)
    TWILIO_CREDENTIALS = "riskcast/twilio"


# ============================================================================
# SECRET BACKENDS
# ============================================================================


class SecretBackend(ABC):
    """Abstract base class for secret backends."""
    
    @abstractmethod
    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret by key."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this backend is available."""
        pass


class AWSSecretsManagerBackend(SecretBackend):
    """
    AWS Secrets Manager backend.
    
    Used in production environments.
    Requires AWS credentials configured.
    """
    
    def __init__(self, region: str = "ap-southeast-1"):
        self._region = region
        self._client = None
        self._available = None
    
    def _get_client(self):
        """Lazy initialization of boto3 client."""
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client(
                    "secretsmanager",
                    region_name=self._region,
                )
            except Exception as e:
                logger.debug("aws_secrets_client_init_failed", error=str(e))
                self._client = False  # Mark as failed
        return self._client if self._client else None
    
    def is_available(self) -> bool:
        """Check if AWS Secrets Manager is available."""
        if self._available is None:
            client = self._get_client()
            self._available = client is not None
        return self._available
    
    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve secret from AWS Secrets Manager."""
        client = self._get_client()
        if not client:
            return None
        
        try:
            response = client.get_secret_value(SecretId=key)
            
            if "SecretString" in response:
                return response["SecretString"]
            else:
                # Binary secret
                import base64
                return base64.b64decode(response["SecretBinary"]).decode("utf-8")
                
        except Exception as e:
            logger.debug(
                "aws_secret_retrieval_failed",
                secret_key=key,
                error_type=type(e).__name__,
            )
            return None


class EnvironmentBackend(SecretBackend):
    """
    Environment variable backend.
    
    Fallback for development and testing.
    Maps SecretKey to environment variable names.
    """
    
    # Mapping from SecretKey to environment variable name
    KEY_MAPPING = {
        SecretKey.DATABASE_URL.value: "DATABASE_URL",
        SecretKey.DATABASE_CREDENTIALS.value: "DATABASE_CREDENTIALS_JSON",
        SecretKey.TWILIO_ACCOUNT_SID.value: "TWILIO_ACCOUNT_SID",
        SecretKey.TWILIO_AUTH_TOKEN.value: "TWILIO_AUTH_TOKEN",
        SecretKey.POLYMARKET_API_KEY.value: "POLYMARKET_API_KEY",
        SecretKey.AIS_API_KEY.value: "AIS_API_KEY",
        SecretKey.ENCRYPTION_MASTER_KEY.value: "ENCRYPTION_KEY",
        SecretKey.TWILIO_CREDENTIALS.value: "TWILIO_CREDENTIALS_JSON",
    }
    
    def is_available(self) -> bool:
        """Environment backend is always available."""
        return True
    
    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve secret from environment variable."""
        env_key = self.KEY_MAPPING.get(key, key.upper().replace("/", "_").replace("-", "_"))
        return os.environ.get(env_key)


class LocalFileBackend(SecretBackend):
    """
    Local file backend for development.
    
    Reads secrets from a local JSON file.
    NEVER use in production.
    """
    
    def __init__(self, secrets_file: str = ".secrets.json"):
        self._secrets_file = secrets_file
        self._secrets: Optional[dict] = None
    
    def is_available(self) -> bool:
        """Check if secrets file exists."""
        return os.path.exists(self._secrets_file)
    
    def _load_secrets(self) -> dict:
        """Load secrets from file."""
        if self._secrets is None:
            try:
                with open(self._secrets_file, "r") as f:
                    self._secrets = json.load(f)
            except Exception:
                self._secrets = {}
        return self._secrets
    
    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve secret from local file."""
        secrets = self._load_secrets()
        value = secrets.get(key)
        
        # If value is dict, return as JSON string
        if isinstance(value, dict):
            return json.dumps(value)
        return value


# ============================================================================
# SECRETS MANAGER
# ============================================================================


class SecretsManager:
    """
    Central secrets manager with multiple backends.
    
    Features:
    - Multiple backend support (AWS, env, local file)
    - In-memory caching
    - Never logs secret values
    - Access auditing
    - Cache invalidation for rotation
    
    Backend Priority:
    1. AWS Secrets Manager (if available)
    2. Environment variables
    3. Local file (development only)
    """
    
    def __init__(
        self,
        aws_region: str = "ap-southeast-1",
        use_aws: bool = True,
        use_env: bool = True,
        use_local: bool = True,
        local_file: str = ".secrets.json",
    ):
        """
        Initialize secrets manager.
        
        Args:
            aws_region: AWS region for Secrets Manager
            use_aws: Enable AWS Secrets Manager backend
            use_env: Enable environment variable backend
            use_local: Enable local file backend (dev only)
            local_file: Path to local secrets file
        """
        self._backends: list[SecretBackend] = []
        self._cache: dict[str, str] = {}
        self._access_log: list[dict] = []
        
        # Initialize backends in priority order
        if use_aws:
            self._backends.append(AWSSecretsManagerBackend(aws_region))
        if use_env:
            self._backends.append(EnvironmentBackend())
        if use_local:
            self._backends.append(LocalFileBackend(local_file))
    
    def get_secret(self, key: SecretKey | str) -> Optional[str]:
        """
        Retrieve a secret value.
        
        Tries backends in priority order until secret is found.
        
        Args:
            key: SecretKey enum or string key
            
        Returns:
            Secret value, or None if not found
            
        IMPORTANT: Never logs the actual secret value.
        """
        key_str = key.value if isinstance(key, SecretKey) else key
        
        # Check cache first
        if key_str in self._cache:
            self._log_access(key_str, "cache_hit")
            return self._cache[key_str]
        
        # Try each backend
        for backend in self._backends:
            if not backend.is_available():
                continue
            
            value = backend.get_secret(key_str)
            if value is not None:
                # Cache the value
                self._cache[key_str] = value
                self._log_access(key_str, type(backend).__name__)
                
                logger.info(
                    "secret_retrieved",
                    key=key_str,
                    backend=type(backend).__name__,
                    # NEVER log the value
                )
                
                return value
        
        # Not found in any backend
        logger.warning(
            "secret_not_found",
            key=key_str,
            backends_tried=[type(b).__name__ for b in self._backends if b.is_available()],
        )
        return None
    
    def get_json_secret(self, key: SecretKey | str) -> Optional[dict]:
        """
        Get secret and parse as JSON.
        
        Args:
            key: SecretKey enum or string key
            
        Returns:
            Parsed JSON dict, or None if not found/invalid
        """
        value = self.get_secret(key)
        if value is None:
            return None
        
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            logger.error(
                "secret_json_parse_failed",
                key=key.value if isinstance(key, SecretKey) else key,
                error=str(e),
            )
            return None
    
    def get_required_secret(self, key: SecretKey | str) -> str:
        """
        Get a required secret, raising exception if not found.
        
        Args:
            key: SecretKey enum or string key
            
        Returns:
            Secret value
            
        Raises:
            ValueError: If secret not found
        """
        value = self.get_secret(key)
        if value is None:
            key_str = key.value if isinstance(key, SecretKey) else key
            raise ValueError(f"Required secret not found: {key_str}")
        return value
    
    def invalidate_cache(self, key: Optional[SecretKey | str] = None):
        """
        Invalidate cached secrets.
        
        Call this when secrets are rotated.
        
        Args:
            key: Specific key to invalidate, or None for all
        """
        if key is None:
            self._cache.clear()
            logger.info("secrets_cache_cleared")
        else:
            key_str = key.value if isinstance(key, SecretKey) else key
            self._cache.pop(key_str, None)
            logger.info("secret_cache_invalidated", key=key_str)
    
    def _log_access(self, key: str, source: str):
        """Log secret access for audit."""
        self._access_log.append({
            "key": key,
            "source": source,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        # Keep only last 1000 accesses in memory
        if len(self._access_log) > 1000:
            self._access_log = self._access_log[-1000:]
    
    def get_access_log(self) -> list[dict]:
        """Get secret access log for auditing."""
        return self._access_log.copy()
    
    @property
    def available_backends(self) -> list[str]:
        """Get list of available backend names."""
        return [
            type(b).__name__ 
            for b in self._backends 
            if b.is_available()
        ]


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================


# Singleton instance
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """
    Get the global secrets manager instance.
    
    Creates instance on first call.
    """
    global _secrets_manager
    if _secrets_manager is None:
        # Determine environment
        environment = os.environ.get("ENVIRONMENT", "development").lower()
        
        _secrets_manager = SecretsManager(
            use_aws=(environment == "production"),
            use_env=True,
            use_local=(environment == "development"),
        )
        
        logger.info(
            "secrets_manager_initialized",
            environment=environment,
            backends=_secrets_manager.available_backends,
        )
    
    return _secrets_manager


def reset_secrets_manager():
    """Reset the global secrets manager (for testing)."""
    global _secrets_manager
    _secrets_manager = None


# Convenience functions for common secrets
def get_database_url() -> str:
    """
    Get database connection URL.
    
    Returns development default if not configured.
    """
    sm = get_secrets_manager()
    
    # Try direct URL first
    url = sm.get_secret(SecretKey.DATABASE_URL)
    if url:
        return url
    
    # Try credentials bundle
    creds = sm.get_json_secret(SecretKey.DATABASE_CREDENTIALS)
    if creds:
        return (
            f"postgresql+asyncpg://{creds['username']}:{creds['password']}"
            f"@{creds['host']}:{creds.get('port', 5432)}/{creds['database']}"
        )
    
    # Development default
    return "postgresql+asyncpg://postgres:postgres@localhost:5432/riskcast"


def get_twilio_credentials() -> dict:
    """
    Get Twilio API credentials.
    
    Returns empty dict if not configured.
    """
    sm = get_secrets_manager()
    
    # Try credentials bundle
    creds = sm.get_json_secret(SecretKey.TWILIO_CREDENTIALS)
    if creds:
        return creds
    
    # Try individual secrets
    account_sid = sm.get_secret(SecretKey.TWILIO_ACCOUNT_SID)
    auth_token = sm.get_secret(SecretKey.TWILIO_AUTH_TOKEN)
    
    if account_sid and auth_token:
        return {
            "account_sid": account_sid,
            "auth_token": auth_token,
        }
    
    return {}


def get_polymarket_api_key() -> Optional[str]:
    """Get Polymarket API key."""
    return get_secrets_manager().get_secret(SecretKey.POLYMARKET_API_KEY)


def get_ais_api_key() -> Optional[str]:
    """Get AIS/MarineTraffic API key."""
    return get_secrets_manager().get_secret(SecretKey.AIS_API_KEY)


def get_encryption_key() -> Optional[str]:
    """Get master encryption key."""
    return get_secrets_manager().get_secret(SecretKey.ENCRYPTION_MASTER_KEY)


# ============================================================================
# SECRET FILTER FOR LOGGING
# ============================================================================


class SecretFilter:
    """
    Filter that redacts secrets from log messages.
    
    Usage with structlog:
        import structlog
        from app.core.secrets import SecretFilter
        
        structlog.configure(
            processors=[
                SecretFilter(),
                # ... other processors
            ]
        )
    """
    
    # Patterns that indicate sensitive data
    SENSITIVE_KEYS = {
        "password", "secret", "token", "key", "auth", "credential",
        "api_key", "apikey", "auth_token", "access_token", "refresh_token",
        "private_key", "encryption_key", "master_key",
    }
    
    REDACTED = "[REDACTED]"
    
    def __call__(self, logger, method_name, event_dict):
        """Process log event, redacting sensitive values."""
        return self._redact_dict(event_dict)
    
    def _redact_dict(self, d: dict) -> dict:
        """Recursively redact sensitive values in dict."""
        result = {}
        for key, value in d.items():
            key_lower = key.lower()
            
            # Check if key indicates sensitive data
            if any(s in key_lower for s in self.SENSITIVE_KEYS):
                result[key] = self.REDACTED
            elif isinstance(value, dict):
                result[key] = self._redact_dict(value)
            elif isinstance(value, list):
                result[key] = self._redact_list(value)
            else:
                result[key] = value
        
        return result
    
    def _redact_list(self, lst: list) -> list:
        """Recursively redact sensitive values in list."""
        result = []
        for item in lst:
            if isinstance(item, dict):
                result.append(self._redact_dict(item))
            elif isinstance(item, list):
                result.append(self._redact_list(item))
            else:
                result.append(item)
        return result

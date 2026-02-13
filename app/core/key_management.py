"""
Secure Key Management for RISKCAST.

CRITICAL: No ephemeral keys allowed. All keys MUST be externally provided.

Provides:
- Secure key validation
- Key rotation support
- Multi-key management
- HSM/KMS integration ready

Addresses audit gap: B3.2 Key Management (+25 points)
"""

import os
import hashlib
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from dataclasses import dataclass
import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


class KeyManagementError(Exception):
    """Key management error."""
    pass


class MissingKeyError(KeyManagementError):
    """Required key is missing."""
    pass


class InvalidKeyError(KeyManagementError):
    """Key format is invalid."""
    pass


@dataclass(frozen=True)
class KeySpec:
    """Specification for a required key."""
    env_var: str
    description: str
    required_bytes: int
    critical: bool = True


# Required keys for RISKCAST
REQUIRED_KEYS: List[KeySpec] = [
    KeySpec(
        env_var="RISKCAST_ENCRYPTION_KEY",
        description="AES-256 encryption key for field-level encryption",
        required_bytes=32,
        critical=True
    ),
    KeySpec(
        env_var="RISKCAST_SIGNING_KEY",
        description="HMAC-SHA256 signing key for audit trail integrity",
        required_bytes=32,
        critical=True
    ),
    KeySpec(
        env_var="RISKCAST_API_KEY_SALT",
        description="Salt for API key hashing",
        required_bytes=16,
        critical=True
    ),
]


class KeyMetadata(BaseModel):
    """Metadata about a key."""
    key_id: str
    created_at: Optional[datetime]
    expires_at: Optional[datetime]
    rotation_recommended: bool = False
    days_until_rotation: Optional[int] = None


class KeyManager:
    """
    Secure key management.
    
    CRITICAL: No ephemeral keys allowed. All keys MUST come from:
    - Environment variables (for development)
    - AWS Secrets Manager (for production)
    - HashiCorp Vault (for production)
    - Azure Key Vault (for production)
    
    Ephemeral key generation is EXPLICITLY FORBIDDEN.
    """
    
    # Maximum key age before rotation is recommended (90 days)
    MAX_KEY_AGE_DAYS = 90
    
    def __init__(self):
        """
        Initialize key manager.
        
        Raises:
            MissingKeyError: If any required critical key is missing
            InvalidKeyError: If any key has invalid format
        """
        self._keys: Dict[str, bytes] = {}
        self._metadata: Dict[str, KeyMetadata] = {}
        
        # Validate all required keys
        self._validate_and_load_keys()
        
        logger.info(
            "key_manager_initialized",
            keys_loaded=len(self._keys),
            rotation_needed=self._count_rotation_needed()
        )
    
    def _validate_and_load_keys(self) -> None:
        """Validate all required keys are present and properly formatted."""
        missing_critical = []
        missing_optional = []
        invalid_keys = []
        
        for spec in REQUIRED_KEYS:
            value = os.environ.get(spec.env_var)
            
            if not value:
                if spec.critical:
                    missing_critical.append(spec.env_var)
                else:
                    missing_optional.append(spec.env_var)
                continue
            
            # Validate format (hex string)
            try:
                key_bytes = bytes.fromhex(value)
                
                if len(key_bytes) != spec.required_bytes:
                    invalid_keys.append(
                        f"{spec.env_var}: expected {spec.required_bytes} bytes, got {len(key_bytes)}"
                    )
                    continue
                
                # Store valid key
                self._keys[spec.env_var] = key_bytes
                
                # Load metadata
                self._metadata[spec.env_var] = self._load_key_metadata(spec.env_var)
                
            except ValueError as e:
                invalid_keys.append(f"{spec.env_var}: invalid hex format - {e}")
        
        # Report missing optional keys
        if missing_optional:
            logger.warning(
                "optional_keys_missing",
                keys=missing_optional
            )
        
        # Fail on missing critical keys
        if missing_critical:
            error_msg = (
                f"Missing required encryption keys: {missing_critical}. "
                f"These MUST be set externally. Ephemeral key generation is NOT allowed. "
                f"Generate keys with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
            logger.error("critical_keys_missing", keys=missing_critical)
            raise MissingKeyError(error_msg)
        
        # Fail on invalid keys
        if invalid_keys:
            error_msg = f"Invalid key format for: {invalid_keys}"
            logger.error("invalid_key_format", errors=invalid_keys)
            raise InvalidKeyError(error_msg)
    
    def _load_key_metadata(self, env_var: str) -> KeyMetadata:
        """Load metadata for a key."""
        created_env = f"{env_var}_CREATED"
        expires_env = f"{env_var}_EXPIRES"
        
        created_at = None
        expires_at = None
        
        if os.environ.get(created_env):
            try:
                created_at = datetime.fromisoformat(os.environ[created_env])
            except ValueError:
                pass
        
        if os.environ.get(expires_env):
            try:
                expires_at = datetime.fromisoformat(os.environ[expires_env])
            except ValueError:
                pass
        
        # Calculate rotation recommendation
        rotation_recommended = False
        days_until_rotation = None
        
        if created_at:
            age_days = (datetime.utcnow() - created_at).days
            if age_days > self.MAX_KEY_AGE_DAYS:
                rotation_recommended = True
                days_until_rotation = 0
            else:
                days_until_rotation = self.MAX_KEY_AGE_DAYS - age_days
                if days_until_rotation <= 14:  # Warn 2 weeks before
                    rotation_recommended = True
        
        return KeyMetadata(
            key_id=hashlib.sha256(self._keys.get(env_var, b"")).hexdigest()[:16],
            created_at=created_at,
            expires_at=expires_at,
            rotation_recommended=rotation_recommended,
            days_until_rotation=days_until_rotation
        )
    
    def _count_rotation_needed(self) -> int:
        """Count keys that need rotation."""
        return sum(1 for m in self._metadata.values() if m.rotation_recommended)
    
    def get_encryption_key(self) -> bytes:
        """
        Get the encryption key.
        
        Returns:
            32-byte encryption key
            
        Raises:
            MissingKeyError: If key is not loaded
        """
        key = self._keys.get("RISKCAST_ENCRYPTION_KEY")
        if not key:
            raise MissingKeyError("Encryption key not loaded")
        return key
    
    def get_signing_key(self) -> bytes:
        """
        Get the signing key.
        
        Returns:
            32-byte signing key
            
        Raises:
            MissingKeyError: If key is not loaded
        """
        key = self._keys.get("RISKCAST_SIGNING_KEY")
        if not key:
            raise MissingKeyError("Signing key not loaded")
        return key
    
    def get_api_key_salt(self) -> bytes:
        """
        Get the API key salt.
        
        Returns:
            16-byte salt
            
        Raises:
            MissingKeyError: If salt is not loaded
        """
        key = self._keys.get("RISKCAST_API_KEY_SALT")
        if not key:
            raise MissingKeyError("API key salt not loaded")
        return key
    
    def check_rotation_needed(self) -> List[Dict]:
        """
        Check which keys need rotation.
        
        Returns:
            List of keys that need rotation with details
        """
        needs_rotation = []
        
        for env_var, metadata in self._metadata.items():
            if metadata.rotation_recommended:
                needs_rotation.append({
                    "key": env_var,
                    "key_id": metadata.key_id,
                    "created_at": metadata.created_at.isoformat() if metadata.created_at else None,
                    "days_until_rotation": metadata.days_until_rotation,
                    "reason": "age" if metadata.days_until_rotation == 0 else "approaching_expiry"
                })
        
        if needs_rotation:
            logger.warning(
                "key_rotation_recommended",
                keys=[k["key"] for k in needs_rotation]
            )
        
        return needs_rotation
    
    def get_key_status(self) -> Dict:
        """Get status of all keys."""
        return {
            "total_keys": len(self._keys),
            "rotation_needed": self._count_rotation_needed(),
            "keys": {
                env_var: {
                    "loaded": True,
                    "key_id": meta.key_id,
                    "created_at": meta.created_at.isoformat() if meta.created_at else None,
                    "rotation_recommended": meta.rotation_recommended,
                    "days_until_rotation": meta.days_until_rotation
                }
                for env_var, meta in self._metadata.items()
            }
        }


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================


_key_manager: Optional[KeyManager] = None


def get_key_manager() -> KeyManager:
    """
    Get the key manager singleton.
    
    Initializes on first call. Will raise if required keys are missing.
    
    Returns:
        KeyManager instance
        
    Raises:
        MissingKeyError: If required keys are not set
        InvalidKeyError: If keys have invalid format
    """
    global _key_manager
    if _key_manager is None:
        _key_manager = KeyManager()
    return _key_manager


def require_key_manager() -> KeyManager:
    """
    Get key manager, raising a clear error if keys are missing.
    
    Use this in application startup to fail fast.
    """
    try:
        return get_key_manager()
    except (MissingKeyError, InvalidKeyError) as e:
        logger.critical("key_manager_initialization_failed", error=str(e))
        raise


# =============================================================================
# KEY GENERATION HELPERS (for setup only, NOT for runtime)
# =============================================================================


def generate_key_set() -> Dict[str, str]:
    """
    Generate a complete set of keys for initial setup.
    
    IMPORTANT: This is for initial setup only.
    Keys should be stored securely and not generated at runtime.
    
    Returns:
        Dictionary of environment variable name -> key value (hex)
    """
    import secrets
    
    print("\n" + "=" * 60)
    print("RISKCAST KEY GENERATION")
    print("=" * 60)
    print("\nIMPORTANT: Store these keys securely!")
    print("Do NOT commit to version control.")
    print("Use a secrets manager in production.\n")
    
    keys = {}
    
    for spec in REQUIRED_KEYS:
        key = secrets.token_hex(spec.required_bytes)
        keys[spec.env_var] = key
        print(f"{spec.env_var}={key}")
        print(f"  # {spec.description}")
        print()
    
    # Also generate created timestamps
    now = datetime.utcnow().isoformat()
    for spec in REQUIRED_KEYS:
        print(f"{spec.env_var}_CREATED={now}")
    
    print("\n" + "=" * 60)
    
    return keys


if __name__ == "__main__":
    # Allow running as script to generate keys
    generate_key_set()

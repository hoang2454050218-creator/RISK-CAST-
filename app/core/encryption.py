"""
Encryption Module for RISKCAST.

Production-grade encryption for:
- PII data protection
- API key hashing
- Sensitive field encryption
- GDPR compliance
"""

import base64
import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass
from typing import Optional, Dict, Any, Union
from datetime import datetime
import json

import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


# ============================================================================
# ENCRYPTION PRIMITIVES
# ============================================================================


class EncryptionError(Exception):
    """Base encryption error."""
    pass


class DecryptionError(Exception):
    """Decryption failed."""
    pass


@dataclass
class EncryptedValue:
    """Container for encrypted data."""
    
    ciphertext: bytes
    nonce: bytes
    tag: bytes
    version: int = 1
    
    def to_string(self) -> str:
        """Encode to base64 string for storage."""
        data = {
            "v": self.version,
            "ct": base64.b64encode(self.ciphertext).decode(),
            "n": base64.b64encode(self.nonce).decode(),
            "t": base64.b64encode(self.tag).decode(),
        }
        return base64.b64encode(json.dumps(data).encode()).decode()
    
    @classmethod
    def from_string(cls, encoded: str) -> "EncryptedValue":
        """Decode from base64 string."""
        try:
            data = json.loads(base64.b64decode(encoded))
            return cls(
                ciphertext=base64.b64decode(data["ct"]),
                nonce=base64.b64decode(data["n"]),
                tag=base64.b64decode(data["t"]),
                version=data.get("v", 1),
            )
        except Exception as e:
            raise DecryptionError(f"Invalid encrypted value format: {e}")


class FieldEncryptor:
    """
    Field-level encryption using AES-256-GCM.
    
    Provides:
    - AES-256-GCM authenticated encryption
    - Key derivation from master key
    - Automatic nonce generation
    - Version tagging for key rotation
    """
    
    def __init__(self, master_key: bytes):
        """
        Initialize with master key.
        
        Args:
            master_key: 32-byte master encryption key
        """
        if len(master_key) != 32:
            raise ValueError("Master key must be 32 bytes")
        
        self._master_key = master_key
        self._key_version = 1
    
    @classmethod
    def from_key_string(cls, key_string: str) -> "FieldEncryptor":
        """Create from base64-encoded key string."""
        key_bytes = base64.b64decode(key_string)
        return cls(key_bytes)
    
    @classmethod
    def generate_key(cls) -> str:
        """Generate a new master key."""
        key = secrets.token_bytes(32)
        return base64.b64encode(key).decode()
    
    def _derive_key(self, context: str) -> bytes:
        """Derive a context-specific key from master key."""
        return hashlib.pbkdf2_hmac(
            "sha256",
            self._master_key,
            context.encode(),
            iterations=100000,
            dklen=32,
        )
    
    def encrypt(
        self,
        plaintext: Union[str, bytes],
        context: str = "default",
    ) -> EncryptedValue:
        """
        Encrypt data using AES-256-GCM.
        
        SECURITY: No fallback encryption. If cryptography is not available,
        this will fail fast rather than use insecure alternatives.
        
        Args:
            plaintext: Data to encrypt
            context: Context for key derivation
            
        Returns:
            EncryptedValue containing ciphertext and metadata
            
        Raises:
            EncryptionError: If cryptography library is not available
        """
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError as e:
            # CRITICAL: Fail fast instead of using insecure fallback
            raise EncryptionError(
                "cryptography library is required for encryption. "
                "Install with: pip install cryptography"
            ) from e
        
        if isinstance(plaintext, str):
            plaintext = plaintext.encode("utf-8")
        
        key = self._derive_key(context)
        nonce = secrets.token_bytes(12)
        
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        
        # AES-GCM appends tag to ciphertext
        tag = ciphertext[-16:]
        ciphertext = ciphertext[:-16]
        
        return EncryptedValue(
            ciphertext=ciphertext,
            nonce=nonce,
            tag=tag,
            version=self._key_version,
        )
    
    def decrypt(
        self,
        encrypted: EncryptedValue,
        context: str = "default",
    ) -> bytes:
        """
        Decrypt data using AES-256-GCM.
        
        SECURITY: No fallback decryption. Fails fast if cryptography unavailable.
        
        Args:
            encrypted: EncryptedValue to decrypt
            context: Context for key derivation
            
        Returns:
            Decrypted plaintext bytes
            
        Raises:
            DecryptionError: If decryption fails
            EncryptionError: If cryptography library is not available
        """
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError as e:
            # CRITICAL: Fail fast instead of using insecure fallback
            raise EncryptionError(
                "cryptography library is required for decryption. "
                "Install with: pip install cryptography"
            ) from e
        
        key = self._derive_key(context)
        aesgcm = AESGCM(key)
        
        # Reconstruct ciphertext with tag
        ciphertext_with_tag = encrypted.ciphertext + encrypted.tag
        
        try:
            plaintext = aesgcm.decrypt(encrypted.nonce, ciphertext_with_tag, None)
            return plaintext
        except Exception as e:
            raise DecryptionError(f"Decryption failed: {e}")
    
    def encrypt_string(self, plaintext: str, context: str = "default") -> str:
        """Encrypt string and return base64-encoded result."""
        encrypted = self.encrypt(plaintext, context)
        return encrypted.to_string()
    
    def decrypt_string(self, encrypted_string: str, context: str = "default") -> str:
        """Decrypt base64-encoded string."""
        encrypted = EncryptedValue.from_string(encrypted_string)
        plaintext = self.decrypt(encrypted, context)
        return plaintext.decode("utf-8")
    
    # SECURITY: Insecure fallback methods have been REMOVED.
    # The system will fail fast if cryptography library is not available.
    # This is intentional - weak encryption is worse than no encryption.


# ============================================================================
# HASHING
# ============================================================================


class SecureHasher:
    """
    Secure hashing for passwords and API keys.
    
    Uses:
    - bcrypt for passwords
    - SHA-256 with salt for API keys
    """
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        try:
            import bcrypt
            salt = bcrypt.gensalt(rounds=12)
            hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
            return hashed.decode("utf-8")
        except ImportError:
            # Fallback to PBKDF2
            salt = secrets.token_hex(16)
            hashed = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("utf-8"),
                iterations=100000,
            )
            return f"pbkdf2${salt}${base64.b64encode(hashed).decode()}"
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify a password against hash."""
        try:
            import bcrypt
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except ImportError:
            # Handle PBKDF2 fallback
            if hashed.startswith("pbkdf2$"):
                parts = hashed.split("$")
                salt = parts[1]
                expected = base64.b64decode(parts[2])
                actual = hashlib.pbkdf2_hmac(
                    "sha256",
                    password.encode("utf-8"),
                    salt.encode("utf-8"),
                    iterations=100000,
                )
                return hmac.compare_digest(expected, actual)
            return False
    
    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Hash an API key using SHA-256."""
        return hashlib.sha256(api_key.encode("utf-8")).hexdigest()
    
    @staticmethod
    def generate_api_key(prefix: str = "rc") -> tuple[str, str]:
        """
        Generate a new API key.
        
        Returns:
            Tuple of (full_key, key_hash)
        """
        key_body = secrets.token_urlsafe(32)
        full_key = f"{prefix}_{key_body}"
        key_hash = SecureHasher.hash_api_key(full_key)
        return full_key, key_hash
    
    @staticmethod
    def get_key_prefix(api_key: str) -> str:
        """Get the prefix/identifier of an API key."""
        return api_key[:8] if len(api_key) >= 8 else api_key


# ============================================================================
# PII PROTECTION
# ============================================================================


class PIIProtector:
    """
    PII (Personally Identifiable Information) protection.
    
    Provides:
    - Email masking
    - Phone masking
    - Name anonymization
    - Reversible encryption for authorized access
    """
    
    def __init__(self, encryptor: FieldEncryptor):
        self._encryptor = encryptor
    
    def mask_email(self, email: str) -> str:
        """Mask an email address for display."""
        if "@" not in email:
            return "***"
        
        local, domain = email.rsplit("@", 1)
        
        if len(local) <= 2:
            masked_local = "*" * len(local)
        else:
            masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
        
        domain_parts = domain.split(".")
        if len(domain_parts) >= 2:
            masked_domain = domain_parts[0][0] + "***." + domain_parts[-1]
        else:
            masked_domain = "***"
        
        return f"{masked_local}@{masked_domain}"
    
    def mask_phone(self, phone: str) -> str:
        """Mask a phone number for display."""
        # Remove non-digits
        digits = "".join(c for c in phone if c.isdigit())
        
        if len(digits) <= 4:
            return "*" * len(digits)
        
        return "*" * (len(digits) - 4) + digits[-4:]
    
    def mask_name(self, name: str) -> str:
        """Mask a name for display."""
        parts = name.split()
        masked_parts = []
        
        for part in parts:
            if len(part) <= 1:
                masked_parts.append("*")
            else:
                masked_parts.append(part[0] + "*" * (len(part) - 1))
        
        return " ".join(masked_parts)
    
    def encrypt_pii(self, data: Dict[str, str]) -> Dict[str, str]:
        """Encrypt PII fields in a dictionary."""
        pii_fields = ["email", "phone", "name", "address", "ssn", "dob"]
        result = data.copy()
        
        for field in pii_fields:
            if field in result and result[field]:
                result[field] = self._encryptor.encrypt_string(
                    result[field],
                    context=f"pii_{field}",
                )
        
        return result
    
    def decrypt_pii(self, data: Dict[str, str]) -> Dict[str, str]:
        """Decrypt PII fields in a dictionary."""
        pii_fields = ["email", "phone", "name", "address", "ssn", "dob"]
        result = data.copy()
        
        for field in pii_fields:
            if field in result and result[field]:
                try:
                    result[field] = self._encryptor.decrypt_string(
                        result[field],
                        context=f"pii_{field}",
                    )
                except DecryptionError:
                    # Field may not be encrypted
                    pass
        
        return result
    
    def anonymize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fully anonymize PII data for analytics/exports.
        
        This is one-way - data cannot be recovered.
        """
        result = data.copy()
        
        if "email" in result:
            result["email"] = hashlib.sha256(
                result["email"].encode()
            ).hexdigest()[:16] + "@anon.riskcast"
        
        if "phone" in result:
            result["phone"] = hashlib.sha256(
                result["phone"].encode()
            ).hexdigest()[:10]
        
        if "name" in result:
            result["name"] = f"User_{hashlib.sha256(result['name'].encode()).hexdigest()[:8]}"
        
        if "address" in result:
            result["address"] = "REDACTED"
        
        return result


# ============================================================================
# GLOBAL INSTANCES
# ============================================================================


_encryptor: Optional[FieldEncryptor] = None
_hasher: Optional[SecureHasher] = None
_pii_protector: Optional[PIIProtector] = None


def init_encryption(master_key: str = None) -> FieldEncryptor:
    """
    Initialize encryption with master key.
    
    SECURITY: Ephemeral key generation is NO LONGER ALLOWED.
    Keys MUST be provided via environment variable or parameter.
    
    Args:
        master_key: Base64-encoded 32-byte key (optional if env var is set)
        
    Returns:
        FieldEncryptor instance
        
    Raises:
        EncryptionError: If no key is provided
    """
    global _encryptor, _pii_protector, _hasher
    
    if master_key is None:
        # Try to get from environment
        master_key = os.environ.get("RISKCAST_ENCRYPTION_KEY")
    
    if master_key is None:
        # SECURITY: Do NOT generate ephemeral keys
        raise EncryptionError(
            "RISKCAST_ENCRYPTION_KEY must be set. "
            "Ephemeral key generation is NOT allowed in production. "
            "Generate a key with: python -c \"import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())\""
        )
    
    _encryptor = FieldEncryptor.from_key_string(master_key)
    _hasher = SecureHasher()
    _pii_protector = PIIProtector(_encryptor)
    
    logger.info("encryption_initialized")
    return _encryptor


def get_encryptor() -> FieldEncryptor:
    """Get global encryptor instance."""
    global _encryptor
    if _encryptor is None:
        init_encryption()
    return _encryptor


def get_hasher() -> SecureHasher:
    """Get global hasher instance."""
    global _hasher
    if _hasher is None:
        _hasher = SecureHasher()
    return _hasher


def get_pii_protector() -> PIIProtector:
    """Get global PII protector instance."""
    global _pii_protector
    if _pii_protector is None:
        init_encryption()
    return _pii_protector


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================


def hash_value(value: str) -> str:
    """
    Hash a value using SHA-256 with salt.
    
    Used for API keys and other sensitive identifiers.
    Returns format: salt:hash
    """
    salt = secrets.token_hex(16)
    hash_input = f"{salt}{value}".encode("utf-8")
    hash_value = hashlib.sha256(hash_input).hexdigest()
    return f"{salt}:{hash_value}"


def verify_hash(value: str, stored_hash: str) -> bool:
    """
    Verify a value against a stored hash.
    
    Args:
        value: The plain text value to verify
        stored_hash: The stored hash in format salt:hash
        
    Returns:
        True if the value matches the hash
    """
    try:
        if ":" not in stored_hash:
            # Fallback for simple hashes (legacy)
            return hashlib.sha256(value.encode("utf-8")).hexdigest() == stored_hash
        
        salt, expected_hash = stored_hash.split(":", 1)
        hash_input = f"{salt}{value}".encode("utf-8")
        actual_hash = hashlib.sha256(hash_input).hexdigest()
        return hmac.compare_digest(expected_hash, actual_hash)
    except Exception:
        return False


# ============================================================================
# KEY MANAGER
# ============================================================================


class KeyManager:
    """
    Manages encryption keys with rotation support.
    
    Features:
    - Key derivation from master key
    - Key rotation support
    - Key versioning
    - Secure key storage pattern
    """
    
    def __init__(self, master_key: str):
        """
        Initialize with master key.
        
        Args:
            master_key: Master key string for key derivation
        """
        self._master_key = master_key
        self._keys: Dict[str, bytes] = {}
        self._current_key_id: str = "v1"
        
        # Generate initial key
        self._keys[self._current_key_id] = self._derive_key(self._current_key_id)
    
    def _derive_key(self, key_id: str) -> bytes:
        """Derive a key from master key and key ID."""
        return hashlib.pbkdf2_hmac(
            "sha256",
            self._master_key.encode("utf-8"),
            key_id.encode("utf-8"),
            iterations=100000,
            dklen=32,
        )
    
    def get_current_key(self) -> bytes:
        """Get the current active key."""
        return self._keys[self._current_key_id]
    
    def get_key(self, key_id: str) -> Optional[bytes]:
        """Get a key by ID."""
        return self._keys.get(key_id)
    
    def rotate_key(self) -> str:
        """
        Rotate to a new key.
        
        Returns:
            New key ID
        """
        # Generate new key ID
        version = len(self._keys) + 1
        new_key_id = f"v{version}"
        
        # Derive and store new key
        self._keys[new_key_id] = self._derive_key(new_key_id)
        self._current_key_id = new_key_id
        
        logger.info("key_rotated", new_key_id=new_key_id)
        return new_key_id
    
    def get_current_key_id(self) -> str:
        """Get current key ID."""
        return self._current_key_id
    
    def list_keys(self) -> list:
        """List all key IDs."""
        return list(self._keys.keys())


# ============================================================================
# CONVENIENCE MASKING FUNCTIONS
# ============================================================================


def mask_email(email: str) -> str:
    """
    Mask an email address for display.
    
    Args:
        email: Email address to mask
        
    Returns:
        Masked email (e.g., "j***n@g***.com")
    """
    if "@" not in email:
        return "***"
    
    local, domain = email.rsplit("@", 1)
    
    if len(local) <= 2:
        masked_local = "*" * len(local)
    else:
        masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
    
    domain_parts = domain.split(".")
    if len(domain_parts) >= 2:
        masked_domain = domain_parts[0][0] + "***." + domain_parts[-1]
    else:
        masked_domain = "***"
    
    return f"{masked_local}@{masked_domain}"


def mask_phone(phone: str) -> str:
    """
    Mask a phone number for display.
    
    Args:
        phone: Phone number to mask
        
    Returns:
        Masked phone (e.g., "******4567")
    """
    # Remove non-digits
    digits = "".join(c for c in phone if c.isdigit())
    
    if len(digits) <= 4:
        return "*" * len(digits)
    
    return "*" * (len(digits) - 4) + digits[-4:]

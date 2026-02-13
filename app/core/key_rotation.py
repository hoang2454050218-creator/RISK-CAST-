"""
Key Rotation Support for RISKCAST.

Provides zero-downtime key rotation with:
- Multi-key support during rotation
- Automatic re-encryption
- Audit trail for rotations

Addresses audit gap: B3.3 Key Rotation (+10 points)
"""

import os
import asyncio
from datetime import datetime
from typing import Optional, Callable, AsyncIterator, List, Any
from dataclasses import dataclass
import structlog

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = structlog.get_logger(__name__)


class RotationError(Exception):
    """Key rotation error."""
    pass


@dataclass
class RotationStatus:
    """Status of a key rotation operation."""
    started_at: datetime
    completed_at: Optional[datetime]
    records_processed: int
    records_failed: int
    in_progress: bool
    error: Optional[str]


class KeyRotator:
    """
    Handles key rotation with zero downtime.
    
    Supports:
    - Dual-key operation during transition
    - Automatic decryption key detection
    - Gradual re-encryption
    
    Rotation Process:
    1. Add new key as "current", keep old as "previous"
    2. New encryptions use current key
    3. Decryptions try current, fallback to previous
    4. Background job re-encrypts old data
    5. After grace period, remove old key
    """
    
    # Key version prefix bytes
    VERSION_PREFIX_SIZE = 2
    NONCE_SIZE = 12
    
    def __init__(
        self,
        current_key: bytes,
        previous_key: Optional[bytes] = None,
        key_version: int = 1
    ):
        """
        Initialize key rotator.
        
        Args:
            current_key: Current encryption key (32 bytes for AES-256)
            previous_key: Previous key for decryption fallback (optional)
            key_version: Version number for current key
        """
        if len(current_key) != 32:
            raise ValueError("Current key must be 32 bytes for AES-256")
        if previous_key and len(previous_key) != 32:
            raise ValueError("Previous key must be 32 bytes for AES-256")
        
        self._current_key = current_key
        self._previous_key = previous_key
        self._key_version = key_version
        
        self._current_aesgcm = AESGCM(current_key)
        self._previous_aesgcm = AESGCM(previous_key) if previous_key else None
    
    def encrypt(self, plaintext: bytes) -> bytes:
        """
        Encrypt with current key.
        
        Format: version (2 bytes) + nonce (12 bytes) + ciphertext
        
        Args:
            plaintext: Data to encrypt
            
        Returns:
            Encrypted data with version prefix
        """
        nonce = os.urandom(self.NONCE_SIZE)
        ciphertext = self._current_aesgcm.encrypt(nonce, plaintext, None)
        
        # Encode version as 2 bytes (big endian)
        version_bytes = self._key_version.to_bytes(self.VERSION_PREFIX_SIZE, "big")
        
        return version_bytes + nonce + ciphertext
    
    def decrypt(self, data: bytes) -> bytes:
        """
        Decrypt with appropriate key based on version.
        
        Tries current key first, falls back to previous if available.
        
        Args:
            data: Encrypted data with version prefix
            
        Returns:
            Decrypted plaintext
            
        Raises:
            ValueError: If decryption fails with all available keys
        """
        if len(data) < self.VERSION_PREFIX_SIZE + self.NONCE_SIZE:
            raise ValueError("Invalid ciphertext: too short")
        
        version = int.from_bytes(data[:self.VERSION_PREFIX_SIZE], "big")
        nonce = data[self.VERSION_PREFIX_SIZE:self.VERSION_PREFIX_SIZE + self.NONCE_SIZE]
        ciphertext = data[self.VERSION_PREFIX_SIZE + self.NONCE_SIZE:]
        
        # Try current key first
        try:
            return self._current_aesgcm.decrypt(nonce, ciphertext, None)
        except Exception:
            pass
        
        # Try previous key if available
        if self._previous_aesgcm:
            try:
                return self._previous_aesgcm.decrypt(nonce, ciphertext, None)
            except Exception:
                pass
        
        raise ValueError(f"Decryption failed for key version: {version}")
    
    def re_encrypt_with_current(self, data: bytes) -> bytes:
        """
        Re-encrypt data with current key.
        
        Used during key rotation to update old encrypted data.
        
        Args:
            data: Data encrypted with any key
            
        Returns:
            Data encrypted with current key
        """
        plaintext = self.decrypt(data)
        return self.encrypt(plaintext)
    
    def get_data_version(self, data: bytes) -> int:
        """Get the key version used to encrypt data."""
        if len(data) < self.VERSION_PREFIX_SIZE:
            raise ValueError("Invalid data: too short")
        return int.from_bytes(data[:self.VERSION_PREFIX_SIZE], "big")
    
    def needs_re_encryption(self, data: bytes) -> bool:
        """Check if data needs re-encryption (encrypted with old key)."""
        try:
            version = self.get_data_version(data)
            return version < self._key_version
        except ValueError:
            return True  # Invalid data should be re-encrypted


class RotationCoordinator:
    """
    Coordinates key rotation across the system.
    
    Handles:
    - Batch re-encryption
    - Progress tracking
    - Error handling
    - Audit logging
    """
    
    def __init__(
        self,
        rotator: KeyRotator,
        batch_size: int = 100,
        max_errors: int = 10
    ):
        """
        Initialize rotation coordinator.
        
        Args:
            rotator: KeyRotator instance
            batch_size: Records to process per batch
            max_errors: Maximum errors before aborting
        """
        self._rotator = rotator
        self._batch_size = batch_size
        self._max_errors = max_errors
        self._status: Optional[RotationStatus] = None
        self._lock = asyncio.Lock()
    
    async def rotate(
        self,
        data_iterator: AsyncIterator[tuple[str, bytes]],
        persist_callback: Callable[[str, bytes], Any]
    ) -> RotationStatus:
        """
        Perform key rotation on all data.
        
        Args:
            data_iterator: Async iterator yielding (record_id, encrypted_data) tuples
            persist_callback: Async callback to persist re-encrypted data (record_id, new_data)
            
        Returns:
            RotationStatus with results
        """
        async with self._lock:
            if self._status and self._status.in_progress:
                raise RotationError("Rotation already in progress")
            
            self._status = RotationStatus(
                started_at=datetime.utcnow(),
                completed_at=None,
                records_processed=0,
                records_failed=0,
                in_progress=True,
                error=None
            )
        
        logger.info("key_rotation_started")
        
        try:
            batch: List[tuple[str, bytes]] = []
            
            async for record_id, encrypted_data in data_iterator:
                try:
                    # Check if re-encryption is needed
                    if not self._rotator.needs_re_encryption(encrypted_data):
                        self._status.records_processed += 1
                        continue
                    
                    # Re-encrypt
                    new_data = self._rotator.re_encrypt_with_current(encrypted_data)
                    batch.append((record_id, new_data))
                    
                    # Process batch
                    if len(batch) >= self._batch_size:
                        await self._process_batch(batch, persist_callback)
                        batch = []
                        
                        logger.info(
                            "key_rotation_progress",
                            processed=self._status.records_processed,
                            failed=self._status.records_failed
                        )
                
                except Exception as e:
                    self._status.records_failed += 1
                    logger.error(
                        "key_rotation_record_failed",
                        record_id=record_id,
                        error=str(e)
                    )
                    
                    if self._status.records_failed >= self._max_errors:
                        raise RotationError(f"Too many errors ({self._status.records_failed})")
            
            # Process final batch
            if batch:
                await self._process_batch(batch, persist_callback)
            
            self._status.completed_at = datetime.utcnow()
            self._status.in_progress = False
            
            duration = (self._status.completed_at - self._status.started_at).total_seconds()
            
            logger.info(
                "key_rotation_complete",
                processed=self._status.records_processed,
                failed=self._status.records_failed,
                duration_seconds=duration
            )
            
        except Exception as e:
            self._status.completed_at = datetime.utcnow()
            self._status.in_progress = False
            self._status.error = str(e)
            
            logger.error("key_rotation_failed", error=str(e))
            raise
        
        return self._status
    
    async def _process_batch(
        self,
        batch: List[tuple[str, bytes]],
        persist_callback: Callable[[str, bytes], Any]
    ) -> None:
        """Process a batch of re-encrypted records."""
        for record_id, new_data in batch:
            try:
                await persist_callback(record_id, new_data)
                self._status.records_processed += 1
            except Exception as e:
                self._status.records_failed += 1
                logger.error(
                    "key_rotation_persist_failed",
                    record_id=record_id,
                    error=str(e)
                )
    
    def get_status(self) -> Optional[RotationStatus]:
        """Get current rotation status."""
        return self._status


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================


def create_rotator_from_env() -> KeyRotator:
    """
    Create KeyRotator from environment variables.
    
    Uses:
    - RISKCAST_ENCRYPTION_KEY: Current key
    - RISKCAST_ENCRYPTION_KEY_PREVIOUS: Previous key (optional)
    - RISKCAST_ENCRYPTION_KEY_VERSION: Key version (default: 1)
    
    Returns:
        Configured KeyRotator
    """
    current_key_hex = os.environ.get("RISKCAST_ENCRYPTION_KEY")
    if not current_key_hex:
        raise ValueError("RISKCAST_ENCRYPTION_KEY not set")
    
    current_key = bytes.fromhex(current_key_hex)
    
    previous_key = None
    previous_key_hex = os.environ.get("RISKCAST_ENCRYPTION_KEY_PREVIOUS")
    if previous_key_hex:
        previous_key = bytes.fromhex(previous_key_hex)
    
    version = int(os.environ.get("RISKCAST_ENCRYPTION_KEY_VERSION", "1"))
    
    return KeyRotator(current_key, previous_key, version)

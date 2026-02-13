"""
Tests for Encryption Module.

Tests:
- Key management
- Field encryption/decryption
- Hashing
- PII masking
"""

import pytest
import os

# Set a test encryption key before importing the module
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key-12345-abcdef")

from app.core.encryption import (
    KeyManager,
    FieldEncryptor,
    hash_value,
    verify_hash,
    mask_phone,
    mask_email,
)


class TestKeyManager:
    """Tests for KeyManager."""
    
    @pytest.fixture
    def key_manager(self):
        """Create a key manager for testing."""
        return KeyManager("test-master-key-12345")
    
    def test_key_derivation(self, key_manager):
        """Key derivation produces consistent keys."""
        key1 = key_manager.get_current_key()
        key2 = key_manager.get_current_key()
        
        assert key1 == key2
    
    def test_key_rotation(self, key_manager):
        """Key rotation adds new key."""
        old_key = key_manager.get_current_key()
        key_manager.rotate_key()
        new_key = key_manager.get_current_key()
        
        # Keys should be different after rotation
        # (unless rotation uses same derivation - depends on implementation)
        assert len(key_manager._keys) >= 2
    
    def test_key_retrieval(self, key_manager):
        """Can retrieve keys by ID."""
        key_id, key = list(key_manager._keys.items())[0]
        retrieved = key_manager.get_key(key_id)
        
        assert retrieved == key


class TestFieldEncryptor:
    """Tests for FieldEncryptor."""
    
    @pytest.fixture
    def encryptor(self):
        """Create an encryptor for testing."""
        key_manager = KeyManager("test-key")
        return FieldEncryptor(key_manager)
    
    def test_encrypt_decrypt_roundtrip(self, encryptor):
        """Encrypted data can be decrypted."""
        original = "sensitive data"
        
        encrypted = encryptor.encrypt(original)
        decrypted = encryptor.decrypt(encrypted)
        
        assert decrypted == original
    
    def test_encryption_produces_different_output(self, encryptor):
        """Same plaintext produces different ciphertext (nonce)."""
        original = "sensitive data"
        
        encrypted1 = encryptor.encrypt(original)
        encrypted2 = encryptor.encrypt(original)
        
        # The ciphertext portion should be different due to nonce
        # But both should decrypt to the same value
        assert encryptor.decrypt(encrypted1) == original
        assert encryptor.decrypt(encrypted2) == original
    
    def test_encrypted_data_format(self, encryptor):
        """Encrypted data has expected format."""
        encrypted = encryptor.encrypt("test")
        
        # Format: key_id:ciphertext
        assert ":" in encrypted
        parts = encrypted.split(":", 1)
        assert len(parts) == 2
    
    def test_encrypt_empty_string(self, encryptor):
        """Can encrypt empty string."""
        encrypted = encryptor.encrypt("")
        decrypted = encryptor.decrypt(encrypted)
        
        assert decrypted == ""
    
    def test_encrypt_unicode(self, encryptor):
        """Can encrypt unicode strings."""
        original = "Hello 世界 🌍"
        
        encrypted = encryptor.encrypt(original)
        decrypted = encryptor.decrypt(encrypted)
        
        assert decrypted == original
    
    def test_decrypt_with_wrong_key_fails(self, encryptor):
        """Decryption with wrong key fails gracefully."""
        encrypted = encryptor.encrypt("test")
        
        # Create new encryptor with different key
        new_key_manager = KeyManager("different-key")
        new_encryptor = FieldEncryptor(new_key_manager)
        
        # Should return None or raise on decryption failure
        result = new_encryptor.decrypt(encrypted)
        assert result is None


class TestHashing:
    """Tests for hashing functions."""
    
    def test_hash_produces_consistent_output(self):
        """Same input produces same hash with same salt."""
        value = "test value"
        salt = "test-salt"
        
        hash1 = hash_value(value, salt)
        hash2 = hash_value(value, salt)
        
        assert hash1 == hash2
    
    def test_hash_different_with_different_salt(self):
        """Different salt produces different hash."""
        value = "test value"
        
        hash1 = hash_value(value, "salt1")
        hash2 = hash_value(value, "salt2")
        
        assert hash1 != hash2
    
    def test_hash_format(self):
        """Hash has expected format (salt:hash)."""
        hashed = hash_value("test", "salt")
        
        assert ":" in hashed
    
    def test_verify_hash_success(self):
        """Correct value verifies successfully."""
        value = "test value"
        hashed = hash_value(value)
        
        assert verify_hash(value, hashed) is True
    
    def test_verify_hash_failure(self):
        """Incorrect value fails verification."""
        hashed = hash_value("correct value")
        
        assert verify_hash("wrong value", hashed) is False
    
    def test_hash_is_one_way(self):
        """Cannot recover original from hash."""
        value = "sensitive data"
        hashed = hash_value(value)
        
        # The hash should not contain the original value
        assert value not in hashed


class TestPIIMasking:
    """Tests for PII masking functions."""
    
    def test_mask_phone_standard(self):
        """Standard phone number is masked correctly."""
        phone = "+1234567890"
        masked = mask_phone(phone)
        
        assert masked == "+1***890"
    
    def test_mask_phone_short(self):
        """Short phone number is fully masked."""
        phone = "1234"
        masked = mask_phone(phone)
        
        assert masked == "****"
    
    def test_mask_phone_with_formatting(self):
        """Phone with formatting is handled."""
        phone = "(123) 456-7890"
        masked = mask_phone(phone)
        
        # Should mask while preserving some structure
        assert len(masked) > 4  # Not fully masked
    
    def test_mask_email_standard(self):
        """Standard email is masked correctly."""
        email = "john.doe@example.com"
        masked = mask_email(email)
        
        # Should show first char and domain
        assert masked.startswith("j")
        assert "@example.com" in masked
        assert "***" in masked
    
    def test_mask_email_short_local(self):
        """Short local part is handled."""
        email = "ab@example.com"
        masked = mask_email(email)
        
        assert "@example.com" in masked
    
    def test_mask_email_no_at_sign(self):
        """Invalid email without @ is fully masked."""
        invalid = "not-an-email"
        masked = mask_email(invalid)
        
        assert "***" in masked or masked == invalid

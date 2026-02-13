"""
Tests for Encryption Module (B3.2: Data Protection).

Tests cover:
- Field-level encryption with AES-256-GCM
- Secure hashing
- PII protection
"""

import pytest
import secrets

from app.core.encryption import (
    FieldEncryptor,
    EncryptedValue,
    EncryptionError,
    DecryptionError,
    SecureHasher,
    PIIProtector,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def master_key():
    """Generate a valid 32-byte master key."""
    return secrets.token_bytes(32)


@pytest.fixture
def field_encryptor(master_key):
    """Create a FieldEncryptor instance."""
    return FieldEncryptor(master_key)


@pytest.fixture
def secure_hasher():
    """Create a SecureHasher instance."""
    return SecureHasher()


@pytest.fixture
def pii_protector(master_key):
    """Create a PIIProtector instance."""
    return PIIProtector(master_key)


# ============================================================================
# FIELD ENCRYPTOR TESTS
# ============================================================================


class TestFieldEncryptor:
    """Tests for FieldEncryptor (AES-256-GCM)."""
    
    def test_encrypt_decrypt_roundtrip(self, field_encryptor):
        """Encrypted data can be decrypted back."""
        plaintext = "Sensitive customer data"
        
        encrypted = field_encryptor.encrypt(plaintext)
        decrypted = field_encryptor.decrypt(encrypted)
        
        assert decrypted.decode("utf-8") == plaintext
    
    def test_encrypt_produces_different_ciphertext(self, field_encryptor):
        """Same plaintext produces different ciphertext (nonce)."""
        plaintext = "Same data"
        
        encrypted1 = field_encryptor.encrypt(plaintext)
        encrypted2 = field_encryptor.encrypt(plaintext)
        
        # Different nonces mean different ciphertexts
        assert encrypted1.ciphertext != encrypted2.ciphertext
        assert encrypted1.nonce != encrypted2.nonce
    
    def test_invalid_master_key_length_raises(self):
        """Master key must be exactly 32 bytes."""
        with pytest.raises(ValueError, match="32 bytes"):
            FieldEncryptor(b"too_short")
        
        with pytest.raises(ValueError, match="32 bytes"):
            FieldEncryptor(b"x" * 64)  # Too long
    
    def test_tampered_ciphertext_fails(self, field_encryptor):
        """Tampered ciphertext fails authentication."""
        plaintext = "Original data"
        encrypted = field_encryptor.encrypt(plaintext)
        
        # Tamper with ciphertext
        tampered = EncryptedValue(
            ciphertext=bytes([b ^ 0xFF for b in encrypted.ciphertext]),
            nonce=encrypted.nonce,
            tag=encrypted.tag,
            version=encrypted.version,
        )
        
        with pytest.raises(DecryptionError):
            field_encryptor.decrypt(tampered)
    
    def test_encrypted_value_serialization(self, field_encryptor):
        """EncryptedValue can be serialized to/from string."""
        plaintext = "Data for storage"
        encrypted = field_encryptor.encrypt(plaintext)
        
        # Serialize to string
        encoded = encrypted.to_string()
        assert isinstance(encoded, str)
        
        # Deserialize
        decoded = EncryptedValue.from_string(encoded)
        
        # Decrypt should work
        decrypted = field_encryptor.decrypt(decoded)
        assert decrypted.decode("utf-8") == plaintext
    
    def test_encrypt_unicode_data(self, field_encryptor):
        """Can encrypt Unicode strings."""
        unicode_text = "日本語テキスト émojis"
        
        encrypted = field_encryptor.encrypt(unicode_text)
        decrypted = field_encryptor.decrypt(encrypted)
        
        assert decrypted.decode("utf-8") == unicode_text
    
    def test_encrypt_string_helper(self, field_encryptor):
        """encrypt_string returns base64-encoded string."""
        plaintext = "Easy encryption"
        
        encrypted_str = field_encryptor.encrypt_string(plaintext)
        decrypted_str = field_encryptor.decrypt_string(encrypted_str)
        
        assert decrypted_str == plaintext
    
    def test_context_separation(self, field_encryptor):
        """Different contexts produce different ciphertexts."""
        plaintext = "Context test"
        
        encrypted1 = field_encryptor.encrypt(plaintext, context="context1")
        encrypted2 = field_encryptor.encrypt(plaintext, context="context2")
        
        # Same plaintext, different derived keys
        # Decrypt with wrong context should fail
        with pytest.raises(DecryptionError):
            field_encryptor.decrypt(encrypted1, context="context2")
    
    def test_generate_key(self):
        """Can generate new master keys."""
        key1 = FieldEncryptor.generate_key()
        key2 = FieldEncryptor.generate_key()
        
        assert key1 != key2
        assert len(key1) > 0
    
    def test_from_key_string(self):
        """Can create encryptor from base64 key string."""
        key_string = FieldEncryptor.generate_key()
        encryptor = FieldEncryptor.from_key_string(key_string)
        
        plaintext = "Test from key string"
        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)
        
        assert decrypted.decode("utf-8") == plaintext


# ============================================================================
# SECURE HASHER TESTS
# ============================================================================


class TestSecureHasher:
    """Tests for SecureHasher."""
    
    def test_hash_password(self, secure_hasher):
        """Can hash passwords."""
        password = "secure_password_123"
        
        hashed = secure_hasher.hash_password(password)
        
        assert hashed is not None
        assert hashed != password
        assert len(hashed) > 0
    
    def test_verify_password(self, secure_hasher):
        """Can verify passwords against hash."""
        password = "verify_me"
        
        hashed = secure_hasher.hash_password(password)
        
        assert secure_hasher.verify_password(password, hashed) is True
        assert secure_hasher.verify_password("wrong_password", hashed) is False
    
    def test_different_passwords_different_hashes(self, secure_hasher):
        """Different passwords produce different hashes."""
        hash1 = secure_hasher.hash_password("password1")
        hash2 = secure_hasher.hash_password("password2")
        
        assert hash1 != hash2
    
    def test_same_password_different_hashes(self, secure_hasher):
        """Same password produces different hashes (salting)."""
        password = "same_password"
        
        hash1 = secure_hasher.hash_password(password)
        hash2 = secure_hasher.hash_password(password)
        
        # Different salts
        assert hash1 != hash2
        
        # But both verify
        assert secure_hasher.verify_password(password, hash1) is True
        assert secure_hasher.verify_password(password, hash2) is True


# ============================================================================
# PII PROTECTOR TESTS
# ============================================================================


class TestPIIProtector:
    """Tests for PIIProtector."""
    
    def test_encrypt_phone(self, pii_protector):
        """Can encrypt phone numbers."""
        phone = "+1-555-123-4567"
        
        encrypted = pii_protector.encrypt_phone(phone)
        
        # Encrypted should not contain phone
        assert phone not in encrypted
        assert "555" not in encrypted
    
    def test_decrypt_phone(self, pii_protector):
        """Can decrypt phone numbers."""
        phone = "+1-555-123-4567"
        
        encrypted = pii_protector.encrypt_phone(phone)
        decrypted = pii_protector.decrypt_phone(encrypted)
        
        assert decrypted == phone
    
    def test_encrypt_email(self, pii_protector):
        """Can encrypt email addresses."""
        email = "customer@example.com"
        
        encrypted = pii_protector.encrypt_email(email)
        
        # Encrypted should not contain email
        assert email not in encrypted
        assert "example.com" not in encrypted
    
    def test_decrypt_email(self, pii_protector):
        """Can decrypt email addresses."""
        email = "customer@example.com"
        
        encrypted = pii_protector.encrypt_email(email)
        decrypted = pii_protector.decrypt_email(encrypted)
        
        assert decrypted == email


# ============================================================================
# ENCRYPTED VALUE TESTS
# ============================================================================


class TestEncryptedValue:
    """Tests for EncryptedValue container."""
    
    def test_to_string_from_string_roundtrip(self):
        """EncryptedValue roundtrips through string serialization."""
        ev = EncryptedValue(
            ciphertext=b"ciphertext_data",
            nonce=b"nonce_12byte",  # 12 bytes
            tag=b"tag_16_bytes!!!!",  # 16 bytes
            version=1,
        )
        
        encoded = ev.to_string()
        decoded = EncryptedValue.from_string(encoded)
        
        assert decoded.ciphertext == ev.ciphertext
        assert decoded.nonce == ev.nonce
        assert decoded.tag == ev.tag
        assert decoded.version == ev.version
    
    def test_invalid_encoded_format_raises(self):
        """Invalid encoded format raises error."""
        with pytest.raises(DecryptionError, match="Invalid"):
            EncryptedValue.from_string("not_valid_base64!@#$")


# ============================================================================
# KEY ROTATION TESTS
# ============================================================================


class TestKeyRotation:
    """Tests for encryption key rotation."""
    
    def test_different_keys_cannot_decrypt(self):
        """Data encrypted with one key cannot be decrypted with another."""
        key1 = secrets.token_bytes(32)
        key2 = secrets.token_bytes(32)
        
        encryptor1 = FieldEncryptor(key1)
        encryptor2 = FieldEncryptor(key2)
        
        encrypted = encryptor1.encrypt("secret")
        
        with pytest.raises(DecryptionError):
            encryptor2.decrypt(encrypted)
    
    def test_re_encrypt_with_new_key(self):
        """Can re-encrypt data with a new key."""
        old_key = secrets.token_bytes(32)
        new_key = secrets.token_bytes(32)
        
        old_encryptor = FieldEncryptor(old_key)
        new_encryptor = FieldEncryptor(new_key)
        
        plaintext = "rotate_me"
        
        # Encrypt with old key
        encrypted_old = old_encryptor.encrypt(plaintext)
        
        # Decrypt and re-encrypt with new key
        decrypted = old_encryptor.decrypt(encrypted_old)
        encrypted_new = new_encryptor.encrypt(decrypted)
        
        # New key can decrypt
        assert new_encryptor.decrypt(encrypted_new).decode("utf-8") == plaintext


# ============================================================================
# SECURITY TESTS
# ============================================================================


class TestSecurityProperties:
    """Tests for security properties."""
    
    def test_plaintext_not_in_ciphertext(self, field_encryptor):
        """Plaintext is not present in ciphertext."""
        plaintext = "FINDME_SENSITIVE_DATA"
        encrypted = field_encryptor.encrypt(plaintext)
        
        # Plaintext should not appear in ciphertext
        assert plaintext.encode() not in encrypted.ciphertext
        assert plaintext not in encrypted.to_string()
    
    def test_empty_string_encryption(self, field_encryptor):
        """Can encrypt empty string."""
        encrypted = field_encryptor.encrypt("")
        decrypted = field_encryptor.decrypt(encrypted)
        
        assert decrypted.decode("utf-8") == ""
    
    def test_large_data_encryption(self, field_encryptor):
        """Can encrypt large data."""
        large_data = "x" * 10000  # 10KB
        
        encrypted = field_encryptor.encrypt(large_data)
        decrypted = field_encryptor.decrypt(encrypted)
        
        assert decrypted.decode("utf-8") == large_data

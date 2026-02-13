"""
Encryption at Rest Tests.

Tests: encrypt/decrypt roundtrip, null handling, key consistency, TypeDecorator.
"""

import pytest

from riskcast.services.encryption import EncryptedString, decrypt, encrypt


class TestEncryptDecrypt:
    """Test the encrypt/decrypt functions."""

    def test_roundtrip(self):
        """Encrypting then decrypting returns the original value."""
        original = "user@example.com"
        encrypted = encrypt(original)
        decrypted = decrypt(encrypted)
        assert decrypted == original

    def test_encrypted_differs_from_plaintext(self):
        """Encrypted value is different from plaintext."""
        original = "sensitive-data"
        encrypted = encrypt(original)
        assert encrypted != original

    def test_empty_string(self):
        """Empty string encrypts and decrypts correctly."""
        encrypted = encrypt("")
        decrypted = decrypt(encrypted)
        assert decrypted == ""

    def test_unicode(self):
        """Unicode strings encrypt/decrypt correctly."""
        original = "Nguyễn Văn A — email: nguyenvana@vn.com"
        encrypted = encrypt(original)
        decrypted = decrypt(encrypted)
        assert decrypted == original

    def test_long_string(self):
        """Long strings encrypt/decrypt correctly."""
        original = "a" * 10000
        encrypted = encrypt(original)
        decrypted = decrypt(encrypted)
        assert decrypted == original

    def test_consistent_key(self):
        """Multiple encryptions use the same key (can be decrypted)."""
        originals = ["email1@test.com", "email2@test.com", "+84-123-456-789"]
        for original in originals:
            assert decrypt(encrypt(original)) == original

    def test_different_ciphertexts(self):
        """Same plaintext produces different ciphertext (Fernet uses random IV)."""
        original = "same-input"
        c1 = encrypt(original)
        c2 = encrypt(original)
        assert c1 != c2  # Fernet adds random IV
        assert decrypt(c1) == decrypt(c2) == original


class TestEncryptedStringTypeDecorator:
    """Test the SQLAlchemy TypeDecorator."""

    def test_process_bind_param_encrypts(self):
        """TypeDecorator encrypts on write."""
        td = EncryptedString()
        result = td.process_bind_param("test@email.com", None)
        assert result != "test@email.com"
        assert result is not None

    def test_process_result_value_decrypts(self):
        """TypeDecorator decrypts on read."""
        td = EncryptedString()
        encrypted = encrypt("test@email.com")
        result = td.process_result_value(encrypted, None)
        assert result == "test@email.com"

    def test_null_passthrough(self):
        """None values pass through without encryption."""
        td = EncryptedString()
        assert td.process_bind_param(None, None) is None
        assert td.process_result_value(None, None) is None

    def test_empty_passthrough(self):
        """Empty strings pass through without encryption."""
        td = EncryptedString()
        assert td.process_bind_param("", None) == ""
        assert td.process_result_value("", None) == ""

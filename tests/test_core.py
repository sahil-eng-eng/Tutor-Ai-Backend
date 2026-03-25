"""Tests for core security utilities."""

import pytest

from app.core.security import hash_password, verify_password
from app.core.jwt_handler import create_access_token, create_refresh_token, verify_access_token
from app.utils.otp import generate_otp


class TestPasswordHashing:
    def test_hash_and_verify(self):
        password = "SecurePassword123!"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed) is True

    def test_wrong_password(self):
        hashed = hash_password("CorrectPassword!")
        assert verify_password("WrongPassword!", hashed) is False

    def test_different_hashes(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        # bcrypt produces different hashes for same input (due to salt)
        assert h1 != h2
        assert verify_password("same", h1)
        assert verify_password("same", h2)


class TestJWT:
    def test_create_access_token(self):
        token = create_access_token(data={"sub": "user-123"})
        assert isinstance(token, str)
        assert len(token) > 20

    def test_verify_access_token(self):
        token = create_access_token(data={"sub": "user-456"})
        payload = verify_access_token(token)
        assert payload is not None
        assert payload["sub"] == "user-456"

    def test_verify_invalid_token(self):
        payload = verify_access_token("invalid.token.here")
        assert payload is None

    def test_create_refresh_token(self):
        token = create_refresh_token(data={"sub": "user-789"})
        assert isinstance(token, str)
        assert len(token) > 20


class TestOTP:
    def test_generate_otp_length(self):
        otp = generate_otp()
        assert len(otp) == 6
        assert otp.isdigit()

    def test_generate_otp_uniqueness(self):
        otps = {generate_otp() for _ in range(50)}
        # At least some should be different
        assert len(otps) > 1

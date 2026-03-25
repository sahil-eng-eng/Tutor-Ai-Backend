"""Tests for utility functions."""

import os
import pytest

from app.utils.otp import generate_otp
from app.utils.file_handler import validate_file_extension, validate_file_size


class TestFileHandler:
    def test_validate_allowed_extension(self):
        assert validate_file_extension("notes.pdf", "document") is True

    def test_validate_disallowed_extension(self):
        assert validate_file_extension("hack.exe", "document") is False

    def test_validate_file_size_ok(self):
        assert validate_file_size(1024 * 1024) is True

    def test_validate_file_size_too_large(self):
        assert validate_file_size(500 * 1024 * 1024) is False


class TestOTP:
    def test_otp_format(self):
        for _ in range(20):
            otp = generate_otp()
            assert len(otp) == 6
            assert otp.isdigit()

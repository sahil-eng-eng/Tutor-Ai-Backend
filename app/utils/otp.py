"""
OTP utility — generates and validates OTP codes.
"""

import secrets


def generate_otp(length: int = 6) -> str:
    """Generate a secure numeric OTP code."""
    return "".join(str(secrets.randbelow(10)) for _ in range(length))

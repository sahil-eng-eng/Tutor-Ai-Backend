"""
Two-Factor Authentication Service — TOTP-based 2FA using pyotp.
Users scan a QR code with Google Authenticator/Authy.
"""

from __future__ import annotations

import io
import base64
import logging
from typing import Optional

logger = logging.getLogger("ai_tutor")


def generate_totp_secret() -> str:
    """Generate a new TOTP secret for a user."""
    import pyotp
    return pyotp.random_base32()


def get_totp_provisioning_uri(
    secret: str, email: str, issuer: str = "AI Tutor Platform"
) -> str:
    """Get the OTP provisioning URI for QR code generation."""
    import pyotp
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=issuer)


def generate_qr_code_base64(provisioning_uri: str) -> str:
    """Generate a QR code image as a base64-encoded PNG string."""
    try:
        import qrcode

        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except ImportError:
        logger.warning("qrcode library not installed — QR generation unavailable")
        return ""


def verify_totp_code(secret: str, code: str) -> bool:
    """Verify a TOTP code against the user's secret."""
    import pyotp
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)  # Allow 1 step drift (±30s)

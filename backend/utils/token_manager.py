

import hashlib
import logging
import os
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

logger = logging.getLogger("fundforge.utils.token_manager")





_EMAIL_VERIFY_TTL_HOURS: int = int(os.getenv("EMAIL_VERIFY_TOKEN_TTL_HOURS", "24"))
_RESET_TOKEN_TTL_HOURS: int = int(os.getenv("RESET_TOKEN_TTL_HOURS", "1"))
_TOKEN_BYTE_LENGTH: int = int(os.getenv("TOKEN_BYTE_LENGTH", "32"))






def generate_token() -> str:
    
    token = secrets.token_urlsafe(_TOKEN_BYTE_LENGTH)
    logger.debug("Generated secure token (length=%d).", len(token))
    return token


def hash_token(raw_token: str) -> str:
    
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def verify_token_hash(raw_token: str, stored_hash: str) -> bool:
    
    if not raw_token or not stored_hash:
        return False
    expected_hash = hash_token(raw_token)
    return secrets.compare_digest(expected_hash, stored_hash)






def generate_email_verify_token() -> Tuple[str, str, datetime]:
    
    raw = generate_token()
    token_hash = hash_token(raw)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=_EMAIL_VERIFY_TTL_HOURS)
    logger.debug("Email verify token generated; expires_at=%s", expires_at.isoformat())
    return raw, token_hash, expires_at


def validate_email_verify_token(
    raw_token: str,
    stored_hash: Optional[str],
    sent_at: Optional[datetime],
) -> Tuple[bool, str]:
    
    if not stored_hash:
        return False, "No pending email verification found. Please request a new link."

    if not verify_token_hash(raw_token, stored_hash):
        return False, "Invalid or already-used verification token."

    if sent_at is not None:
        if sent_at.tzinfo is None:
            sent_at = sent_at.replace(tzinfo=timezone.utc)
        expiry = sent_at + timedelta(hours=_EMAIL_VERIFY_TTL_HOURS)
        if datetime.now(timezone.utc) > expiry:
            return False, (
                f"Verification link has expired (valid for {_EMAIL_VERIFY_TTL_HOURS}h). "
                "Please request a new one."
            )

    return True, ""






def generate_reset_token() -> Tuple[str, str, datetime]:
    
    raw = generate_token()
    token_hash = hash_token(raw)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=_RESET_TOKEN_TTL_HOURS)
    logger.debug("Password reset token generated; expires_at=%s", expires_at.isoformat())
    return raw, token_hash, expires_at


def validate_reset_token(
    raw_token: str,
    stored_hash: Optional[str],
    expires_at: Optional[datetime],
) -> Tuple[bool, str]:
    
    if not stored_hash or not expires_at:
        return False, "No active password reset request found. Please request a new link."

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) > expires_at:
        return False, (
            "Password reset link has expired. Please request a new one. "
            f"(Links are valid for {_RESET_TOKEN_TTL_HOURS} hour(s).)"
        )

    if not verify_token_hash(raw_token, stored_hash):
        return False, "Invalid or already-used reset token."

    return True, ""






def mask_token(raw_token: str) -> str:
    
    if len(raw_token) <= 8:
        return "****"
    return raw_token[:8] + "..."


def build_verification_url(base_url: str, token: str) -> str:
    
    base_url = base_url.rstrip("/")
    return f"{base_url}/verify-email?token={token}"


def build_reset_url(base_url: str, token: str) -> str:
    
    base_url = base_url.rstrip("/")
    return f"{base_url}/reset-password?token={token}"

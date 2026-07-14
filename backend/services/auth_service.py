

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from backend.app import db
from backend.models import User
from backend.models.user import UserRole, UserStatus
from backend.utils.password import (
    validate_and_hash,
    verify_password,
)
from backend.utils.jwt_manager import (
    create_tokens,
    revoke_token,
)
from backend.utils.token_manager import (
    generate_email_verify_token,
    generate_reset_token,
    validate_email_verify_token,
    validate_reset_token,
    build_verification_url,
    build_reset_url,
    mask_token,
)

logger = logging.getLogger("fundforge.services.auth")


_FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")






class AuthError(Exception):
    
    http_status: int = 400
    error_code: str = "AUTH_ERROR"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class UserNotFoundError(AuthError):
    
    http_status = 404
    error_code = "USER_NOT_FOUND"


class InvalidCredentialsError(AuthError):
    
    http_status = 401
    error_code = "INVALID_CREDENTIALS"


class AccountLockedError(AuthError):
    
    http_status = 423
    error_code = "ACCOUNT_LOCKED"


class AccountSuspendedError(AuthError):
    
    http_status = 403
    error_code = "ACCOUNT_SUSPENDED"


class EmailNotVerifiedError(AuthError):
    
    http_status = 403
    error_code = "EMAIL_NOT_VERIFIED"


class EmailAlreadyExistsError(AuthError):
    
    http_status = 409
    error_code = "EMAIL_EXISTS"


class InvalidTokenError(AuthError):
    
    http_status = 400
    error_code = "INVALID_TOKEN"


class WeakPasswordError(AuthError):
    
    http_status = 422
    error_code = "WEAK_PASSWORD"


class PasswordMismatchError(AuthError):
    
    http_status = 401
    error_code = "PASSWORD_MISMATCH"


class ValidationError(AuthError):
    
    http_status = 422
    error_code = "VALIDATION_ERROR"






def register_user(
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    role: str = "founder",
) -> Dict[str, Any]:
    
    
    email = (email or "").strip().lower()
    first_name = (first_name or "").strip()
    last_name = (last_name or "").strip()

    if not email or "@" not in email:
        raise ValidationError("A valid email address is required.")
    if not first_name:
        raise ValidationError("first_name is required.")
    if not last_name:
        raise ValidationError("last_name is required.")

    
    result, password_hash = validate_and_hash(password)
    if not result.is_valid:
        raise WeakPasswordError(
            f"Password does not meet requirements: {'; '.join(result.errors)}"
        )

    
    existing = db.session.query(User).filter_by(email=email).first()
    if existing:
        raise EmailAlreadyExistsError(
            f"An account with the email '{email}' already exists."
        )

    
    try:
        user_role = UserRole(role.lower())
    except ValueError:
        user_role = UserRole.FOUNDER

    
    user = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        password_hash=password_hash,
        role=user_role,
        status=UserStatus.PENDING,
        email_verified=False,
    )

    
    raw_token, token_hash, _ = generate_email_verify_token()
    user.email_verify_token_hash = token_hash
    user.email_verify_sent_at = datetime.now(timezone.utc)
    user.created_by = str(user.id)
    user.updated_by = str(user.id)

    try:
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise EmailAlreadyExistsError(
            f"An account with the email '{email}' already exists."
        )
    except SQLAlchemyError as exc:
        db.session.rollback()
        logger.error("DB error during registration: %s", exc, exc_info=True)
        raise AuthError("Registration failed due to a database error.") from exc

    verify_url = build_verification_url(_FRONTEND_URL, raw_token)
    logger.info("New user registered: id=%s email=%s", user.id, email)

    return {
        "user": user.to_safe_dict(),
        "verify_token": raw_token,
        "verify_url": verify_url,
        "message": "Registration successful. Please check your email to verify your account.",
    }






def login_user(
    email: str,
    password: str,
    ip_address: Optional[str] = None,
) -> Dict[str, Any]:
    
    email = (email or "").strip().lower()

    user: Optional[User] = (
        db.session.query(User)
        .filter_by(email=email, is_deleted=False)
        .first()
    )

    
    
    if user is None:
        logger.warning("Login attempt for non-existent email: %s", email)
        raise InvalidCredentialsError("Account not found.")

    if user.is_locked():
        logger.warning("Login blocked — account locked: user=%s", user.id)
        raise AccountLockedError(
            "Account is temporarily locked due to repeated failed login attempts. "
            "Please try again later or reset your password."
        )

    if not verify_password(password, user.password_hash):
        user.record_login_attempt(success=False, ip=ip_address)
        db.session.commit()
        logger.warning("Failed login (wrong password): user=%s ip=%s", user.id, ip_address)
        raise InvalidCredentialsError("Incorrect email or password.")

    if user.status == UserStatus.SUSPENDED:
        logger.warning("Suspended user login attempt: user=%s", user.id)
        raise AccountSuspendedError(
            "Your account has been suspended. Please contact support."
        )

    if user.status == UserStatus.DEACTIVATED:
        raise InvalidCredentialsError(
            "This account has been deactivated. Please contact support to reactivate."
        )

    if not user.email_verified:
        logger.info("Unverified email login attempt: user=%s", user.id)
        raise EmailNotVerifiedError(
            "Please verify your email address before logging in. "
            "Check your inbox for a verification link."
        )

    
    user.record_login_attempt(success=True, ip=ip_address)
    user.status = UserStatus.ACTIVE
    db.session.commit()

    tokens = create_tokens(user)
    logger.info("Successful login: user=%s ip=%s", user.id, ip_address)

    return {
        **tokens,
        "user": user.to_safe_dict(),
        "message": "Login successful.",
    }






def logout_user(jti: str) -> Dict[str, str]:
    
    revoke_token(jti)
    logger.info("User logged out: jti=%s", jti)
    return {"message": "Logged out successfully."}






def refresh_access_token(user_id: str, refresh_jti: str) -> Dict[str, str]:
    
    user: Optional[User] = db.session.get(User, user_id)
    if user is None or user.is_deleted:
        raise UserNotFoundError("User not found.")

    if user.status == UserStatus.SUSPENDED:
        raise AccountSuspendedError("Account has been suspended.")

    
    revoke_token(refresh_jti)
    tokens = create_tokens(user)
    logger.info("Token refreshed for user: %s", user_id)
    return {
        **tokens,
        "message": "Token refreshed successfully.",
    }






def send_verification_email(user_id: str) -> Dict[str, str]:
    
    user: Optional[User] = db.session.get(User, user_id)
    if user is None:
        raise UserNotFoundError("User not found.")

    if user.email_verified:
        raise AuthError("Email address is already verified.")

    raw_token, token_hash, _ = generate_email_verify_token()
    user.email_verify_token_hash = token_hash
    user.email_verify_sent_at = datetime.now(timezone.utc)
    user.updated_by = user_id
    db.session.commit()

    verify_url = build_verification_url(_FRONTEND_URL, raw_token)
    logger.info("Verification email resent: user=%s url=%s", user_id, verify_url)

    return {
        "message": "Verification email sent. Please check your inbox.",
        "verify_url": verify_url,  
    }


def verify_email(token: str) -> Dict[str, Any]:
    
    token = (token or "").strip()
    if not token:
        raise InvalidTokenError("Verification token is required.")

    
    from backend.utils.token_manager import hash_token
    token_hash = hash_token(token)

    user: Optional[User] = (
        db.session.query(User)
        .filter_by(email_verify_token_hash=token_hash, is_deleted=False)
        .first()
    )

    if user is None:
        raise InvalidTokenError("Invalid or already-used verification token.")

    is_valid, error_msg = validate_email_verify_token(
        raw_token=token,
        stored_hash=user.email_verify_token_hash,
        sent_at=user.email_verify_sent_at,
    )

    if not is_valid:
        raise InvalidTokenError(error_msg)

    
    user.email_verified = True
    user.status = UserStatus.ACTIVE
    user.email_verify_token_hash = None  
    user.updated_by = str(user.id)
    db.session.commit()

    logger.info("Email verified: user=%s", user.id)
    return {
        "user": user.to_safe_dict(),
        "message": "Email verified successfully. You can now log in.",
    }






def forgot_password(email: str) -> Dict[str, str]:
    
    email = (email or "").strip().lower()
    _GENERIC_MESSAGE = (
        "If that email address is registered, you will receive a password reset link shortly."
    )

    user: Optional[User] = (
        db.session.query(User)
        .filter_by(email=email, is_deleted=False)
        .first()
    )

    if user is None:
        logger.info("Password reset requested for unknown email: %s", email)
        return {"message": _GENERIC_MESSAGE}

    raw_token, token_hash, expires_at = generate_reset_token()
    user.reset_token_hash = token_hash
    user.reset_token_expires_at = expires_at
    user.updated_by = str(user.id)
    db.session.commit()

    reset_url = build_reset_url(_FRONTEND_URL, raw_token)
    logger.info(
        "Password reset token generated: user=%s token=%s expires=%s",
        user.id,
        mask_token(raw_token),
        expires_at.isoformat(),
    )

    return {
        "message": _GENERIC_MESSAGE,
        "reset_url": reset_url,  
    }


def reset_password(token: str, new_password: str) -> Dict[str, str]:
    
    token = (token or "").strip()
    if not token:
        raise InvalidTokenError("Reset token is required.")

    from backend.utils.token_manager import hash_token
    token_hash = hash_token(token)

    user: Optional[User] = (
        db.session.query(User)
        .filter_by(reset_token_hash=token_hash, is_deleted=False)
        .first()
    )

    if user is None:
        raise InvalidTokenError("Invalid or already-used reset token.")

    is_valid, error_msg = validate_reset_token(
        raw_token=token,
        stored_hash=user.reset_token_hash,
        expires_at=user.reset_token_expires_at,
    )

    if not is_valid:
        raise InvalidTokenError(error_msg)

    
    val_result, new_hash = validate_and_hash(new_password)
    if not val_result.is_valid:
        raise WeakPasswordError(
            f"Password does not meet requirements: {'; '.join(val_result.errors)}"
        )

    user.password_hash = new_hash
    user.reset_token_hash = None   
    user.reset_token_expires_at = None
    user.failed_login_attempts = "0"
    user.locked_until = None
    user.updated_by = str(user.id)
    db.session.commit()

    logger.info("Password reset completed: user=%s", user.id)
    return {"message": "Password has been reset successfully. You can now log in."}






def get_current_user(user_id: str) -> Dict[str, Any]:
    
    user: Optional[User] = db.session.get(User, user_id)
    if user is None or user.is_deleted:
        raise UserNotFoundError("User not found.")
    return {"user": user.to_safe_dict()}






def update_profile(
    user_id: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    display_name: Optional[str] = None,
    avatar_url: Optional[str] = None,
) -> Dict[str, Any]:
    
    user: Optional[User] = db.session.get(User, user_id)
    if user is None or user.is_deleted:
        raise UserNotFoundError("User not found.")

    if first_name is not None:
        first_name = first_name.strip()
        if not first_name:
            raise ValidationError("first_name must not be blank.")
        user.first_name = first_name

    if last_name is not None:
        last_name = last_name.strip()
        if not last_name:
            raise ValidationError("last_name must not be blank.")
        user.last_name = last_name

    if display_name is not None:
        user.display_name = display_name.strip() or None

    if avatar_url is not None:
        user.avatar_url = avatar_url.strip() or None

    user.updated_by = user_id
    db.session.commit()

    logger.info("Profile updated: user=%s", user_id)
    return {
        "user": user.to_safe_dict(),
        "message": "Profile updated successfully.",
    }






def change_password(
    user_id: str,
    current_password: str,
    new_password: str,
    current_jti: Optional[str] = None,
) -> Dict[str, Any]:
    
    user: Optional[User] = db.session.get(User, user_id)
    if user is None or user.is_deleted:
        raise UserNotFoundError("User not found.")

    if not verify_password(current_password, user.password_hash):
        logger.warning("Change password — wrong current password: user=%s", user_id)
        raise PasswordMismatchError("Current password is incorrect.")

    val_result, new_hash = validate_and_hash(new_password)
    if not val_result.is_valid:
        raise WeakPasswordError(
            f"New password does not meet requirements: {'; '.join(val_result.errors)}"
        )

    user.password_hash = new_hash
    user.failed_login_attempts = "0"
    user.locked_until = None
    user.updated_by = user_id
    db.session.commit()

    
    if current_jti:
        revoke_token(current_jti)

    
    new_tokens = create_tokens(user)

    logger.info("Password changed: user=%s", user_id)
    return {
        **new_tokens,
        "message": "Password changed successfully. Please use your new password to log in.",
    }






def delete_account(
    user_id: str,
    password: str,
    current_jti: Optional[str] = None,
) -> Dict[str, str]:
    
    user: Optional[User] = db.session.get(User, user_id)
    if user is None or user.is_deleted:
        raise UserNotFoundError("User not found.")

    if not verify_password(password, user.password_hash):
        raise PasswordMismatchError(
            "Password is incorrect. Account deletion was not completed."
        )

    user.soft_delete()
    user.status = UserStatus.DEACTIVATED
    user.updated_by = user_id
    db.session.commit()

    if current_jti:
        revoke_token(current_jti)

    logger.info("Account soft-deleted: user=%s", user_id)
    return {"message": "Account has been permanently deleted."}

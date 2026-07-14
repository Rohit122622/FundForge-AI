

import logging
from http import HTTPStatus
from typing import Any, Dict, Optional, Tuple

from flask import Response, g, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

import backend.services.auth_service as auth_svc
from backend.services.auth_service import (
    AuthError,
)

logger = logging.getLogger("fundforge.controllers.auth")






def _ok(data: Any = None, message: str = "", status: int = 200) -> Tuple[Response, int]:
    payload: Dict[str, Any] = {"success": True}
    if message:
        payload["message"] = message
    if data is not None:
        payload["data"] = data
    return jsonify(payload), status


def _created(data: Any = None, message: str = "") -> Tuple[Response, int]:
    return _ok(data=data, message=message, status=HTTPStatus.CREATED.value)


def _error(
    message: str,
    code: int = 400,
    error_code: Optional[str] = None,
    details: Optional[Any] = None,
) -> Tuple[Response, int]:
    payload: Dict[str, Any] = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
        },
    }
    if error_code:
        payload["error"]["error_code"] = error_code
    if details is not None:
        payload["error"]["details"] = details
    payload["request_id"] = getattr(g, "request_id", None)
    return jsonify(payload), code


def _rollback() -> None:
    try:
        from backend.app import db
        db.session.rollback()
    except Exception:
        pass


def _handle_auth_error(exc: AuthError) -> Tuple[Response, int]:
    
    logger.warning(
        "Auth error [%s]: %s [request_id=%s]",
        exc.error_code,
        exc.message,
        getattr(g, "request_id", "?"),
    )
    return _error(
        message=exc.message,
        code=exc.http_status,
        error_code=exc.error_code,
    )


def _require_json() -> Optional[Tuple[Response, int]]:
    
    if not request.is_json:
        return _error("Request body must be JSON (Content-Type: application/json).", code=400)
    return None


def _get_body() -> dict:
    
    return request.get_json(silent=True) or {}


def _get_remote_ip() -> Optional[str]:
    
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.remote_addr






def register() -> Tuple[Response, int]:
    
    if (err := _require_json()):
        return err

    body = _get_body()
    email      = body.get("email", "")
    password   = body.get("password", "")
    first_name = body.get("first_name", "")
    last_name  = body.get("last_name", "")

    if not all([email, password, first_name, last_name]):
        return _error(
            "email, password, first_name, and last_name are all required.",
            code=422,
            error_code="MISSING_FIELDS",
        )

    try:
        result = auth_svc.register_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        logger.info("Registration endpoint: user=%s", result["user"].get("id"))
        import os
        res_data = {"user": result["user"]}
        if os.getenv("FLASK_ENV") == "development":
            res_data["verify_token"] = result.get("verify_token")
            res_data["verify_url"] = result.get("verify_url")
        return _created(
            data=res_data,
            message=result["message"],
        )
    except AuthError as exc:
        return _handle_auth_error(exc)
    except Exception as exc:
        _rollback()
        logger.error("Unexpected error during register: %s", exc, exc_info=True)
        return _error("Registration failed due to an unexpected error.", code=500)


def login() -> Tuple[Response, int]:
    
    if (err := _require_json()):
        return err

    body = _get_body()
    email    = body.get("email", "")
    password = body.get("password", "")

    if not email or not password:
        return _error("email and password are required.", code=422, error_code="MISSING_FIELDS")

    try:
        result = auth_svc.login_user(
            email=email,
            password=password,
            ip_address=_get_remote_ip(),
        )
        return _ok(
            data={
                "access_token":  result["access_token"],
                "refresh_token": result["refresh_token"],
                "user":          result["user"],
            },
            message=result["message"],
        )
    except AuthError as exc:
        return _handle_auth_error(exc)
    except Exception as exc:
        _rollback()
        logger.error("Unexpected error during login: %s", exc, exc_info=True)
        return _error("Login failed due to an unexpected error.", code=500)


@jwt_required()
def logout() -> Tuple[Response, int]:
    
    try:
        jti: str = get_jwt()["jti"]
        result = auth_svc.logout_user(jti=jti)
        return _ok(message=result["message"])
    except Exception as exc:
        logger.error("Unexpected error during logout: %s", exc, exc_info=True)
        return _error("Logout failed.", code=500)


@jwt_required(refresh=True)
def refresh_token() -> Tuple[Response, int]:
    
    try:
        user_id: str = get_jwt_identity()
        refresh_jti: str = get_jwt()["jti"]
        result = auth_svc.refresh_access_token(
            user_id=user_id,
            refresh_jti=refresh_jti,
        )
        return _ok(
            data={
                "access_token":  result["access_token"],
                "refresh_token": result["refresh_token"],
            },
            message=result["message"],
        )
    except AuthError as exc:
        return _handle_auth_error(exc)
    except Exception as exc:
        _rollback()
        logger.error("Unexpected error during token refresh: %s", exc, exc_info=True)
        return _error("Token refresh failed.", code=500)


def forgot_password() -> Tuple[Response, int]:
    
    if (err := _require_json()):
        return err

    body = _get_body()
    email = body.get("email", "").strip()

    if not email:
        return _error("email is required.", code=422, error_code="MISSING_FIELDS")

    try:
        result = auth_svc.forgot_password(email=email)
        
        return _ok(message=result["message"])
    except Exception as exc:
        _rollback()
        logger.error("Unexpected error during forgot-password: %s", exc, exc_info=True)
        return _ok(message=(
            "If that email address is registered, "
            "you will receive a password reset link shortly."
        ))


def reset_password() -> Tuple[Response, int]:
    
    if (err := _require_json()):
        return err

    body = _get_body()
    token        = body.get("token", "").strip()
    new_password = body.get("new_password", "")

    if not token or not new_password:
        return _error(
            "token and new_password are required.",
            code=422,
            error_code="MISSING_FIELDS",
        )

    try:
        result = auth_svc.reset_password(token=token, new_password=new_password)
        return _ok(message=result["message"])
    except AuthError as exc:
        return _handle_auth_error(exc)
    except Exception as exc:
        _rollback()
        logger.error("Unexpected error during reset-password: %s", exc, exc_info=True)
        return _error("Password reset failed.", code=500)


def verify_email() -> Tuple[Response, int]:
    
    if (err := _require_json()):
        return err

    body = _get_body()
    token = body.get("token", "").strip()

    if not token:
        return _error("token is required.", code=422, error_code="MISSING_FIELDS")

    try:
        result = auth_svc.verify_email(token=token)
        return _ok(data={"user": result["user"]}, message=result["message"])
    except AuthError as exc:
        return _handle_auth_error(exc)
    except Exception as exc:
        _rollback()
        logger.error("Unexpected error during email verification: %s", exc, exc_info=True)
        return _error("Email verification failed.", code=500)


@jwt_required()
def resend_verification() -> Tuple[Response, int]:
    
    try:
        user_id: str = get_jwt_identity()
        result = auth_svc.send_verification_email(user_id=user_id)
        return _ok(message=result["message"])
    except AuthError as exc:
        return _handle_auth_error(exc)
    except Exception as exc:
        _rollback()
        logger.error("Unexpected error resending verification: %s", exc, exc_info=True)
        return _error("Failed to resend verification email.", code=500)


@jwt_required()
def get_current_user() -> Tuple[Response, int]:
    
    try:
        user_id: str = get_jwt_identity()
        result = auth_svc.get_current_user(user_id=user_id)
        return _ok(data=result)
    except AuthError as exc:
        return _handle_auth_error(exc)
    except Exception as exc:
        logger.error("Unexpected error in get_current_user: %s", exc, exc_info=True)
        return _error("Failed to retrieve user.", code=500)


@jwt_required()
def update_profile() -> Tuple[Response, int]:
    
    if (err := _require_json()):
        return err

    body = _get_body()
    try:
        user_id: str = get_jwt_identity()
        result = auth_svc.update_profile(
            user_id=user_id,
            first_name=body.get("first_name"),
            last_name=body.get("last_name"),
            display_name=body.get("display_name"),
            avatar_url=body.get("avatar_url"),
        )
        return _ok(data={"user": result["user"]}, message=result["message"])
    except AuthError as exc:
        return _handle_auth_error(exc)
    except Exception as exc:
        _rollback()
        logger.error("Unexpected error in update_profile: %s", exc, exc_info=True)
        return _error("Profile update failed.", code=500)


@jwt_required(fresh=True)
def change_password() -> Tuple[Response, int]:
    
    if (err := _require_json()):
        return err

    body = _get_body()
    current_pw = body.get("current_password", "")
    new_pw     = body.get("new_password", "")

    if not current_pw or not new_pw:
        return _error(
            "current_password and new_password are required.",
            code=422,
            error_code="MISSING_FIELDS",
        )

    try:
        user_id: str = get_jwt_identity()
        jti: str     = get_jwt()["jti"]
        result = auth_svc.change_password(
            user_id=user_id,
            current_password=current_pw,
            new_password=new_pw,
            current_jti=jti,
        )
        return _ok(
            data={
                "access_token":  result["access_token"],
                "refresh_token": result["refresh_token"],
            },
            message=result["message"],
        )
    except AuthError as exc:
        return _handle_auth_error(exc)
    except Exception as exc:
        _rollback()
        logger.error("Unexpected error in change_password: %s", exc, exc_info=True)
        return _error("Password change failed.", code=500)


@jwt_required(fresh=True)
def delete_account() -> Tuple[Response, int]:
    
    if (err := _require_json()):
        return err

    body = _get_body()
    password = body.get("password", "")

    if not password:
        return _error("password is required to confirm account deletion.", code=422)

    try:
        user_id: str = get_jwt_identity()
        jti: str     = get_jwt()["jti"]
        result = auth_svc.delete_account(
            user_id=user_id,
            password=password,
            current_jti=jti,
        )
        return _ok(message=result["message"])
    except AuthError as exc:
        return _handle_auth_error(exc)
    except Exception as exc:
        _rollback()
        logger.error("Unexpected error in delete_account: %s", exc, exc_info=True)
        return _error("Account deletion failed.", code=500)

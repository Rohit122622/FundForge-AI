

import logging
from functools import wraps
from http import HTTPStatus
from typing import Callable, Dict, Optional, Set, TypeVar

from flask import g, jsonify
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
    verify_jwt_in_request,
)

logger = logging.getLogger("fundforge.utils.jwt_manager")

jwt: JWTManager = JWTManager()

F = TypeVar("F", bound=Callable)










_REVOKED_TOKENS: Set[str] = set()






def init_jwt(app) -> None:
    
    jwt.init_app(app)
    _register_jwt_callbacks(jwt)
    logger.info("JWT Manager initialised.")


def _register_jwt_callbacks(jwt_manager: JWTManager) -> None:
    

    @jwt_manager.token_in_blocklist_loader
    def check_if_token_revoked(_jwt_header: dict, jwt_payload: dict) -> bool:
        
        jti: str = jwt_payload.get("jti", "")
        revoked = jti in _REVOKED_TOKENS
        if revoked:
            logger.warning("Blocked revoked JWT: jti=%s", jti)
        return revoked

    @jwt_manager.expired_token_loader
    def expired_token_callback(_jwt_header: dict, _jwt_payload: dict):
        return (
            jsonify({
                "success": False,
                "error": {
                    "code": 401,
                    "status": "Unauthorized",
                    "message": "Your session has expired. Please log in again.",
                },
            }),
            HTTPStatus.UNAUTHORIZED.value,
        )

    @jwt_manager.invalid_token_loader
    def invalid_token_callback(error: str):
        return (
            jsonify({
                "success": False,
                "error": {
                    "code": 401,
                    "status": "Unauthorized",
                    "message": f"Invalid token: {error}",
                },
            }),
            HTTPStatus.UNAUTHORIZED.value,
        )

    @jwt_manager.unauthorized_loader
    def missing_token_callback(error: str):
        return (
            jsonify({
                "success": False,
                "error": {
                    "code": 401,
                    "status": "Unauthorized",
                    "message": "Authentication required. Please provide a valid Bearer token.",
                },
            }),
            HTTPStatus.UNAUTHORIZED.value,
        )

    @jwt_manager.revoked_token_loader
    def revoked_token_callback(_jwt_header: dict, _jwt_payload: dict):
        return (
            jsonify({
                "success": False,
                "error": {
                    "code": 401,
                    "status": "Unauthorized",
                    "message": "Token has been revoked. Please log in again.",
                },
            }),
            HTTPStatus.UNAUTHORIZED.value,
        )

    @jwt_manager.needs_fresh_token_loader
    def needs_fresh_token_callback(_jwt_header: dict, _jwt_payload: dict):
        return (
            jsonify({
                "success": False,
                "error": {
                    "code": 401,
                    "status": "Unauthorized",
                    "message": "A fresh token is required for this action.",
                },
            }),
            HTTPStatus.UNAUTHORIZED.value,
        )

    @jwt_manager.user_identity_loader
    def user_identity_lookup(user) -> str:
        
        if hasattr(user, "id"):
            return str(user.id)
        return str(user)

    @jwt_manager.user_lookup_loader
    def user_lookup_callback(_jwt_header: dict, jwt_payload: dict):
        
        from backend.models import User
        from backend.models.user import UserStatus
        from backend.app import db

        identity: str = jwt_payload.get("sub")
        try:
            user = db.session.get(User, identity)
            if user is None or user.is_deleted or user.status == UserStatus.SUSPENDED:
                logger.warning(
                    "JWT user lookup failed: identity=%s (not found / suspended)",
                    identity,
                )
                return None
            return user
        except Exception as exc:
            logger.error("JWT user lookup error: %s", exc, exc_info=True)
            return None

    logger.debug("JWT callbacks registered.")






def create_tokens(user) -> Dict[str, str]:
    
    additional_claims = {
        "email": user.email,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "type": "access",
    }

    access_token: str = create_access_token(
        identity=str(user.id),
        additional_claims=additional_claims,
        fresh=True,
    )
    refresh_token: str = create_refresh_token(
        identity=str(user.id),
        additional_claims={"type": "refresh"},
    )

    logger.debug("Tokens created for user: %s", user.id)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


def create_access_token_only(user) -> str:
    
    additional_claims = {
        "email": user.email,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "type": "access",
    }
    return create_access_token(
        identity=str(user.id),
        additional_claims=additional_claims,
        fresh=False,
    )






def revoke_token(jti: str) -> None:
    
    _REVOKED_TOKENS.add(jti)
    logger.info("Token revoked: jti=%s  (total blacklisted: %d)", jti, len(_REVOKED_TOKENS))


def revoke_all_user_tokens(user_id: str) -> None:
    
    logger.warning(
        "revoke_all_user_tokens called for user=%s — "
        "full invalidation requires a Redis-backed blacklist in production.",
        user_id,
    )


def is_token_revoked(jti: str) -> bool:
    
    return jti in _REVOKED_TOKENS






def roles_required(*required_roles: str) -> Callable:
    
    def decorator(fn: F) -> F:
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            claims = get_jwt()
            caller_role: str = claims.get("role", "")
            if caller_role not in required_roles:
                logger.warning(
                    "Access denied: user role '%s' not in required %s  [path=%s]",
                    caller_role,
                    required_roles,
                    g.get("request_id", "?"),
                )
                return (
                    jsonify({
                        "success": False,
                        "error": {
                            "code": 403,
                            "status": "Forbidden",
                            "message": (
                                f"This action requires one of the following roles: "
                                f"{', '.join(required_roles)}."
                            ),
                        },
                    }),
                    HTTPStatus.FORBIDDEN.value,
                )
            return fn(*args, **kwargs)
        return wrapper  
    return decorator


def admin_required(fn: F) -> F:
    
    return roles_required("admin")(fn)


def founder_required(fn: F) -> F:
    
    return roles_required("founder")(fn)


def get_current_user_id() -> Optional[str]:
    
    try:
        verify_jwt_in_request(optional=True)
        return get_jwt_identity()
    except Exception:
        return None


def get_current_role() -> Optional[str]:
    
    try:
        verify_jwt_in_request(optional=True)
        return get_jwt().get("role")
    except Exception:
        return None



import logging

from flask import Blueprint

from backend.controllers import auth_controller as ctrl

logger = logging.getLogger("fundforge.routes.auth")





auth_bp: Blueprint = Blueprint("auth", __name__)





auth_bp.add_url_rule(
    "/register",
    endpoint="auth_register",
    view_func=ctrl.register,
    methods=["POST"],
)

auth_bp.add_url_rule(
    "/login",
    endpoint="auth_login",
    view_func=ctrl.login,
    methods=["POST"],
)

auth_bp.add_url_rule(
    "/forgot-password",
    endpoint="auth_forgot_password",
    view_func=ctrl.forgot_password,
    methods=["POST"],
)

auth_bp.add_url_rule(
    "/reset-password",
    endpoint="auth_reset_password",
    view_func=ctrl.reset_password,
    methods=["POST"],
)

auth_bp.add_url_rule(
    "/verify-email",
    endpoint="auth_verify_email",
    view_func=ctrl.verify_email,
    methods=["POST"],
)





auth_bp.add_url_rule(
    "/logout",
    endpoint="auth_logout",
    view_func=ctrl.logout,
    methods=["POST"],
)

auth_bp.add_url_rule(
    "/resend-verification",
    endpoint="auth_resend_verification",
    view_func=ctrl.resend_verification,
    methods=["POST"],
)

auth_bp.add_url_rule(
    "/me",
    endpoint="auth_me_get",
    view_func=ctrl.get_current_user,
    methods=["GET"],
)

auth_bp.add_url_rule(
    "/me",
    endpoint="auth_me_patch",
    view_func=ctrl.update_profile,
    methods=["PATCH"],
)





auth_bp.add_url_rule(
    "/refresh",
    endpoint="auth_refresh",
    view_func=ctrl.refresh_token,
    methods=["POST"],
)





auth_bp.add_url_rule(
    "/change-password",
    endpoint="auth_change_password",
    view_func=ctrl.change_password,
    methods=["POST"],
)

auth_bp.add_url_rule(
    "/me",
    endpoint="auth_me_delete",
    view_func=ctrl.delete_account,
    methods=["DELETE"],
)

logger.debug("Auth blueprint routes registered.")

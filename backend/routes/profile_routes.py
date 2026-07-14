

import logging

from flask import Blueprint

from backend.controllers import profile_controller as ctrl

logger = logging.getLogger("fundforge.routes.profile")





profile_bp: Blueprint = Blueprint("profile", __name__)





profile_bp.add_url_rule(
    "/",
    endpoint="profile_create",
    view_func=ctrl.create_profile,
    methods=["POST"],
)

profile_bp.add_url_rule(
    "/",
    endpoint="profile_get",
    view_func=ctrl.get_profile,
    methods=["GET"],
)

profile_bp.add_url_rule(
    "/",
    endpoint="profile_update",
    view_func=ctrl.update_profile,
    methods=["PATCH"],
)

profile_bp.add_url_rule(
    "/",
    endpoint="profile_delete",
    view_func=ctrl.delete_profile,
    methods=["DELETE"],
)





profile_bp.add_url_rule(
    "/<string:profile_id>",
    endpoint="profile_get_by_id",
    view_func=ctrl.get_profile_by_id,
    methods=["GET"],
)

logger.debug("Profile blueprint routes registered.")

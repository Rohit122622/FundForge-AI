

import logging

from flask import Blueprint

from backend.controllers import grant_controller as ctrl

logger = logging.getLogger("fundforge.routes.grants")





grants_bp: Blueprint = Blueprint("grants", __name__)





grants_bp.add_url_rule(
    "/",
    endpoint="grants_list",
    view_func=ctrl.list_grants,
    methods=["GET"],
)

grants_bp.add_url_rule(
    "/catalog",
    endpoint="grants_catalog",
    view_func=ctrl.list_catalog,
    methods=["GET"],
)

grants_bp.add_url_rule(
    "/categories",
    endpoint="grants_categories",
    view_func=ctrl.get_categories,
    methods=["GET"],
)

grants_bp.add_url_rule(
    "/<string:grant_id>",
    endpoint="grants_get",
    view_func=ctrl.get_grant,
    methods=["GET"],
)





grants_bp.add_url_rule(
    "/saved",
    endpoint="grants_list_saved",
    view_func=ctrl.list_saved_grants,
    methods=["GET"],
)

grants_bp.add_url_rule(
    "/<string:grant_id>/save",
    endpoint="grants_save",
    view_func=ctrl.save_grant,
    methods=["POST", "DELETE"],
)

grants_bp.add_url_rule(
    "/recommend",
    endpoint="grants_recommend",
    view_func=ctrl.recommend,
    methods=["POST"],
)

grants_bp.add_url_rule(
    "/eligibility-check",
    endpoint="grants_eligibility_check",
    view_func=ctrl.quick_eligibility_check,
    methods=["POST"],
)

logger.debug("Grant blueprint routes registered.")

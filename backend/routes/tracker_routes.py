

import logging

from flask import Blueprint

from backend.controllers import tracker_controller as ctrl

logger = logging.getLogger("fundforge.routes.tracker")





tracker_bp: Blueprint = Blueprint("tracker", __name__)





tracker_bp.add_url_rule(
    "/",
    endpoint="tracker_create",
    view_func=ctrl.create_application,
    methods=["POST"],
)

tracker_bp.add_url_rule(
    "/",
    endpoint="tracker_list",
    view_func=ctrl.list_applications,
    methods=["GET"],
)

tracker_bp.add_url_rule(
    "/stats",
    endpoint="tracker_stats",
    view_func=ctrl.get_application_stats,
    methods=["GET"],
)





tracker_bp.add_url_rule(
    "/<string:application_id>",
    endpoint="tracker_get",
    view_func=ctrl.get_application,
    methods=["GET"],
)

tracker_bp.add_url_rule(
    "/<string:application_id>",
    endpoint="tracker_update",
    view_func=ctrl.update_application,
    methods=["PATCH"],
)

tracker_bp.add_url_rule(
    "/<string:application_id>",
    endpoint="tracker_delete",
    view_func=ctrl.delete_application,
    methods=["DELETE"],
)





tracker_bp.add_url_rule(
    "/<string:application_id>/transition",
    endpoint="tracker_transition",
    view_func=ctrl.transition_status,
    methods=["POST"],
)

logger.debug("Tracker blueprint routes registered.")

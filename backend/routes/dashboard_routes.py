

import logging

from flask import Blueprint

from backend.controllers import dashboard_controller as ctrl

logger = logging.getLogger("fundforge.routes.dashboard")





dashboard_bp: Blueprint = Blueprint("dashboard", __name__)





dashboard_bp.add_url_rule(
    "/summary",
    endpoint="dashboard_summary",
    view_func=ctrl.get_user_summary,
    methods=["GET"],
)





dashboard_bp.add_url_rule(
    "/stats",
    endpoint="dashboard_stats",
    view_func=ctrl.get_platform_stats,
    methods=["GET"],
)

dashboard_bp.add_url_rule(
    "/catalog/summary",
    endpoint="dashboard_catalog_summary",
    view_func=ctrl.get_catalog_summary,
    methods=["GET"],
)

logger.debug("Dashboard blueprint routes registered.")



import logging
from flask import Blueprint
from backend.controllers import system_controller as ctrl

logger = logging.getLogger("fundforge.routes.system")

system_bp: Blueprint = Blueprint("system", __name__)

system_bp.add_url_rule(
    "/ai-status",
    endpoint="ai_status",
    view_func=ctrl.get_ai_status,
    methods=["GET"],
)

logger.debug("System blueprint routes registered.")

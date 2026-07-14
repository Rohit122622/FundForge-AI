

import logging

from flask import Blueprint

from backend.controllers import search_controller as ctrl

logger = logging.getLogger("fundforge.routes.search")





search_bp: Blueprint = Blueprint("search", __name__)





search_bp.add_url_rule(
    "/",
    endpoint="search_query",
    view_func=ctrl.unified_search,
    methods=["GET"],
)

search_bp.add_url_rule(
    "/suggestions",
    endpoint="search_suggestions",
    view_func=ctrl.search_suggestions,
    methods=["GET"],
)

logger.debug("Search blueprint routes registered.")

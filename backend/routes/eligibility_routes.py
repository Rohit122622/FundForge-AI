

import logging

from flask import Blueprint

from backend.controllers import eligibility_controller as ctrl

logger = logging.getLogger("fundforge.routes.eligibility")





eligibility_bp: Blueprint = Blueprint("eligibility", __name__)





eligibility_bp.add_url_rule(
    "/check",
    endpoint="eligibility_check",
    view_func=ctrl.check_eligibility,
    methods=["POST"],
)

eligibility_bp.add_url_rule(
    "/readiness",
    endpoint="eligibility_readiness",
    view_func=ctrl.check_readiness,
    methods=["POST"],
)

eligibility_bp.add_url_rule(
    "/recommend",
    endpoint="eligibility_recommend",
    view_func=ctrl.eligible_recommendations,
    methods=["POST"],
)

eligibility_bp.add_url_rule(
    "/documents/check",
    endpoint="eligibility_documents_check",
    view_func=ctrl.check_documents,
    methods=["POST"],
)





eligibility_bp.add_url_rule(
    "/documents/<string:grant_id>",
    endpoint="eligibility_documents_get",
    view_func=ctrl.get_document_requirements,
    methods=["GET"],
)

eligibility_bp.add_url_rule(
    "/rules",
    endpoint="eligibility_rules",
    view_func=ctrl.list_rules,
    methods=["GET"],
)

logger.debug("Eligibility blueprint routes registered.")

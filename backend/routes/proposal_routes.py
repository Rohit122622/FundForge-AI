

import logging

from flask import Blueprint

from backend.controllers import proposal_controller as ctrl

logger = logging.getLogger("fundforge.routes.proposals")





proposals_bp: Blueprint = Blueprint("proposals", __name__)





proposals_bp.add_url_rule(
    "/generate",
    endpoint="proposals_generate",
    view_func=ctrl.generate_proposal,
    methods=["POST"],
)

proposals_bp.add_url_rule(
    "/generate/section",
    endpoint="proposals_generate_section",
    view_func=ctrl.generate_section,
    methods=["POST"],
)





proposals_bp.add_url_rule(
    "/",
    endpoint="proposals_list",
    view_func=ctrl.list_proposals,
    methods=["GET"],
)





proposals_bp.add_url_rule(
    "/templates",
    endpoint="proposals_templates",
    view_func=ctrl.list_templates,
    methods=["GET"],
)

proposals_bp.add_url_rule(
    "/readiness",
    endpoint="proposals_readiness",
    view_func=ctrl.get_proposal_readiness,
    methods=["POST"],
)





proposals_bp.add_url_rule(
    "/<string:proposal_id>",
    endpoint="proposals_get",
    view_func=ctrl.get_proposal,
    methods=["GET"],
)

proposals_bp.add_url_rule(
    "/<string:proposal_id>",
    endpoint="proposals_update",
    view_func=ctrl.update_proposal,
    methods=["PATCH"],
)

proposals_bp.add_url_rule(
    "/<string:proposal_id>",
    endpoint="proposals_delete",
    view_func=ctrl.delete_proposal,
    methods=["DELETE"],
)





proposals_bp.add_url_rule(
    "/<string:proposal_id>/export",
    endpoint="proposals_export",
    view_func=ctrl.export_proposal,
    methods=["GET"],
)

proposals_bp.add_url_rule(
    "/<string:proposal_id>/review",
    endpoint="proposals_review",
    view_func=ctrl.review_proposal,
    methods=["POST"],
)

logger.debug("Proposal blueprint routes registered.")

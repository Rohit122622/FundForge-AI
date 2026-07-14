

import logging

from flask import Blueprint

from backend.controllers import rag_controller as ctrl

logger = logging.getLogger("fundforge.routes.rag")





rag_bp: Blueprint = Blueprint("rag", __name__)





rag_bp.add_url_rule(
    "/retrieve",
    endpoint="rag_retrieve",
    view_func=ctrl.retrieve,
    methods=["POST"],
)

rag_bp.add_url_rule(
    "/retrieve/profile",
    endpoint="rag_retrieve_profile",
    view_func=ctrl.retrieve_for_profile,
    methods=["POST"],
)

rag_bp.add_url_rule(
    "/qa",
    endpoint="rag_qa",
    view_func=ctrl.question_answer,
    methods=["POST"],
)

rag_bp.add_url_rule(
    "/stream-qa",
    endpoint="rag_stream_qa",
    view_func=ctrl.stream_qa,
    methods=["POST"],
)





rag_bp.add_url_rule(
    "/health",
    endpoint="rag_health",
    view_func=ctrl.rag_health,
    methods=["GET"],
)

logger.debug("RAG blueprint routes registered.")



import logging

from flask import Blueprint

from backend.controllers import document_controller as ctrl

logger = logging.getLogger("fundforge.routes.documents")





documents_bp: Blueprint = Blueprint("documents", __name__)





documents_bp.add_url_rule(
    "/upload",
    endpoint="documents_upload",
    view_func=ctrl.upload,
    methods=["POST"],
)





documents_bp.add_url_rule(
    "/",
    endpoint="documents_list",
    view_func=ctrl.list_documents,
    methods=["GET"],
)





documents_bp.add_url_rule(
    "/generate-pdf",
    endpoint="documents_generate_pdf",
    view_func=ctrl.generate_pdf,
    methods=["POST"],
)





documents_bp.add_url_rule(
    "/<string:document_id>",
    endpoint="documents_get_metadata",
    view_func=ctrl.get_metadata,
    methods=["GET"],
)

documents_bp.add_url_rule(
    "/<string:document_id>",
    endpoint="documents_update_metadata",
    view_func=ctrl.update_metadata,
    methods=["PATCH"],
)

documents_bp.add_url_rule(
    "/<string:document_id>",
    endpoint="documents_delete",
    view_func=ctrl.delete,
    methods=["DELETE"],
)





documents_bp.add_url_rule(
    "/<string:document_id>/download",
    endpoint="documents_download",
    view_func=ctrl.download,
    methods=["GET"],
)

logger.debug("Document blueprint routes registered.")

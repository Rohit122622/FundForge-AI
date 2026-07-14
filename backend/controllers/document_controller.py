

import logging
from http import HTTPStatus
from typing import Any, Dict, Optional, Tuple

from flask import Response, g, jsonify, request, send_file
from flask_jwt_extended import get_jwt_identity, jwt_required

import backend.services.document_service as doc_svc
from backend.services.document_service import (
    DocumentError,
)

logger = logging.getLogger("fundforge.controllers.document")






def _ok(data: Any = None, message: str = "", status: int = 200) -> Tuple[Response, int]:
    payload: Dict[str, Any] = {"success": True}
    if message:
        payload["message"] = message
    if data is not None:
        payload["data"] = data
    return jsonify(payload), status


def _created(data: Any = None, message: str = "") -> Tuple[Response, int]:
    return _ok(data=data, message=message, status=HTTPStatus.CREATED.value)


def _error(
    message: str,
    code: int = 400,
    error_code: Optional[str] = None,
) -> Tuple[Response, int]:
    payload: Dict[str, Any] = {
        "success": False,
        "error": {"code": code, "message": message},
    }
    if error_code:
        payload["error"]["error_code"] = error_code
    payload["request_id"] = getattr(g, "request_id", None)
    return jsonify(payload), code


def _handle_doc_error(exc: DocumentError) -> Tuple[Response, int]:
    logger.warning(
        "Document error [%s]: %s [request_id=%s]",
        exc.error_code, exc.message, getattr(g, "request_id", "?"),
    )
    return _error(message=exc.message, code=exc.http_status, error_code=exc.error_code)






@jwt_required()
def upload() -> Tuple[Response, int]:
    
    if "file" not in request.files:
        return _error("No file part in request. Send as multipart/form-data with key 'file'.", code=400)

    file = request.files["file"]
    if not file or not file.filename:
        return _error("No file selected.", code=400)

    user_id: str = get_jwt_identity()

    try:
        result = doc_svc.upload_document(
            file=file,
            user_id=user_id,
            document_type=request.form.get("document_type", "supporting_doc"),
            display_name=request.form.get("display_name"),
            description=request.form.get("description"),
            startup_id=request.form.get("startup_id"),
            proposal_id=request.form.get("proposal_id"),
            application_id=request.form.get("application_id"),
        )
        return _created(
            data={"document": result["document"], "download_url": result["download_url"]},
            message=result["message"],
        )
    except DocumentError as exc:
        return _handle_doc_error(exc)
    except Exception as exc:
        logger.error("Unexpected error during upload: %s", exc, exc_info=True)
        return _error("File upload failed due to an unexpected error.", code=500)






@jwt_required()
def download(document_id: str) -> Any:
    
    user_id: str = get_jwt_identity()
    try:
        stream, mime_type, filename = doc_svc.download_document(
            document_id=document_id,
            user_id=user_id,
        )
        preview_mode = request.args.get("preview") in ("true", "1", "True")
        return send_file(
            stream,
            mimetype=mime_type,
            as_attachment=not preview_mode,
            download_name=filename,
        )
    except DocumentError as exc:
        return _handle_doc_error(exc)
    except Exception as exc:
        logger.error("Unexpected error during download: %s", exc, exc_info=True)
        return _error("Download failed.", code=500)






@jwt_required()
def delete(document_id: str) -> Tuple[Response, int]:
    
    user_id: str = get_jwt_identity()
    try:
        result = doc_svc.delete_document(document_id=document_id, user_id=user_id)
        return _ok(message=result["message"])
    except DocumentError as exc:
        return _handle_doc_error(exc)
    except Exception as exc:
        logger.error("Unexpected error during delete: %s", exc, exc_info=True)
        return _error("Delete failed.", code=500)






@jwt_required()
def list_documents() -> Tuple[Response, int]:
    
    user_id: str = get_jwt_identity()
    try:
        result = doc_svc.list_documents(
            user_id=user_id,
            document_type=request.args.get("document_type"),
            startup_id=request.args.get("startup_id"),
            proposal_id=request.args.get("proposal_id"),
            application_id=request.args.get("application_id"),
            status=request.args.get("status"),
            page=int(request.args.get("page", 1)),
            per_page=int(request.args.get("per_page", 20)),
        )
        return _ok(data=result)
    except ValueError:
        return _error("Invalid pagination parameters.", code=400)
    except DocumentError as exc:
        return _handle_doc_error(exc)
    except Exception as exc:
        logger.error("Unexpected error listing documents: %s", exc, exc_info=True)
        return _error("Failed to list documents.", code=500)






@jwt_required()
def get_metadata(document_id: str) -> Tuple[Response, int]:
    
    user_id: str = get_jwt_identity()
    try:
        result = doc_svc.get_document_metadata(
            document_id=document_id, user_id=user_id
        )
        return _ok(data=result)
    except DocumentError as exc:
        return _handle_doc_error(exc)
    except Exception as exc:
        logger.error("Unexpected error fetching metadata: %s", exc, exc_info=True)
        return _error("Failed to retrieve document.", code=500)


@jwt_required()
def update_metadata(document_id: str) -> Tuple[Response, int]:
    
    user_id: str = get_jwt_identity()
    body = request.get_json(silent=True) or {}
    try:
        result = doc_svc.update_metadata(
            document_id=document_id,
            user_id=user_id,
            display_name=body.get("display_name"),
            description=body.get("description"),
        )
        return _ok(data={"document": result["document"]}, message=result["message"])
    except DocumentError as exc:
        return _handle_doc_error(exc)
    except Exception as exc:
        logger.error("Unexpected error updating metadata: %s", exc, exc_info=True)
        return _error("Metadata update failed.", code=500)






@jwt_required()
def generate_pdf() -> Tuple[Response, int]:
    
    if not request.is_json:
        return _error("Request body must be JSON.", code=400)

    body = request.get_json(silent=True) or {}
    pdf_type = body.get("pdf_type", "").strip()

    if not pdf_type:
        return _error("pdf_type is required.", code=422)

    user_id: str = get_jwt_identity()
    try:
        result = doc_svc.generate_and_store_pdf(
            pdf_type=pdf_type,
            user_id=user_id,
            data=body.get("data", {}),
            startup_id=body.get("startup_id"),
            proposal_id=body.get("proposal_id"),
            application_id=body.get("application_id"),
        )
        return _created(
            data={"document": result["document"], "download_url": result["download_url"]},
            message=result["message"],
        )
    except DocumentError as exc:
        return _handle_doc_error(exc)
    except Exception as exc:
        logger.error("Unexpected error generating PDF: %s", exc, exc_info=True)
        return _error("PDF generation failed.", code=500)

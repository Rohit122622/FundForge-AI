

import logging
from http import HTTPStatus
from typing import Any, Dict, List, Optional, Tuple

from flask import Response, g, jsonify

logger = logging.getLogger("fundforge.utils.response")


def ok(
    data: Any = None,
    message: str = "",
    status: int = 200,
) -> Tuple[Response, int]:
    
    payload: Dict[str, Any] = {"success": True}
    if message:
        payload["message"] = message
    if data is not None:
        payload["data"] = data
    payload["request_id"] = getattr(g, "request_id", None)
    return jsonify(payload), status


def created(data: Any = None, message: str = "") -> Tuple[Response, int]:
    
    return ok(data=data, message=message, status=HTTPStatus.CREATED.value)


def no_content() -> Tuple[Response, int]:
    
    return Response(status=204), 204


def error(
    message: str,
    code:       int = 400,
    error_code: Optional[str] = None,
    details:    Optional[Any] = None,
) -> Tuple[Response, int]:
    
    payload: Dict[str, Any] = {
        "success": False,
        "error": {"code": code, "message": message},
    }
    if error_code:
        payload["error"]["error_code"] = error_code
    if details is not None:
        payload["error"]["details"] = details
    payload["request_id"] = getattr(g, "request_id", None)
    return jsonify(payload), code


def paginated(
    items:      List[Any],
    total:      int,
    page:       int,
    per_page:   int,
    message:    str = "",
) -> Tuple[Response, int]:
    
    import math
    total_pages = math.ceil(total / per_page) if per_page > 0 else 1
    payload: Dict[str, Any] = {
        "success": True,
        "data": items,
        "pagination": {
            "page":        page,
            "per_page":    per_page,
            "total":       total,
            "total_pages": total_pages,
            "has_next":    page < total_pages,
            "has_prev":    page > 1,
        },
    }
    if message:
        payload["message"] = message
    payload["request_id"] = getattr(g, "request_id", None)
    return jsonify(payload), 200


def require_json(request) -> Optional[Tuple[Response, int]]:
    
    if not request.is_json:
        return error("Request body must be JSON (Content-Type: application/json).", code=400)
    return None


def get_pagination_params(request, default_per_page: int = 20) -> Tuple[int, int]:
    
    try:
        page     = max(1, int(request.args.get("page", 1)))
        per_page = min(100, max(1, int(request.args.get("per_page", default_per_page))))
    except (TypeError, ValueError):
        page, per_page = 1, default_per_page
    return page, per_page

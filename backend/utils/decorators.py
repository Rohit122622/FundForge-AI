

import functools
import logging
from typing import Callable

from flask import request

logger = logging.getLogger("fundforge.utils.decorators")


def validate_json(fn: Callable) -> Callable:
    
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if not request.is_json:
            from backend.utils.response import error
            return error(
                "Request body must be JSON (Content-Type: application/json).",
                code=400,
                error_code="INVALID_CONTENT_TYPE",
            )
        return fn(*args, **kwargs)
    return wrapper

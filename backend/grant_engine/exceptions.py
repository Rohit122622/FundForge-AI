

from typing import Any, Dict, List, Optional


class GrantEngineError(Exception):
    

    http_status: int = 500
    error_code: str = "GRANT_ENGINE_ERROR"

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_code": self.error_code,
            "message":    self.message,
            "details":    self.details,
        }


class InsufficientProfileError(GrantEngineError):
    
    http_status = 422
    error_code  = "INSUFFICIENT_PROFILE"

    def __init__(self, message: str, missing_fields: Optional[List[str]] = None):
        super().__init__(message, details={"missing_fields": missing_fields or []})
        self.missing_fields: List[str] = missing_fields or []


class NoGrantsFoundError(GrantEngineError):
    
    http_status = 404
    error_code  = "NO_GRANTS_FOUND"


class ScoringError(GrantEngineError):
    
    http_status = 500
    error_code  = "SCORING_ERROR"


class FilterError(GrantEngineError):
    
    http_status = 500
    error_code  = "FILTER_ERROR"


class CatalogError(GrantEngineError):
    
    http_status = 500
    error_code  = "CATALOG_ERROR"


from typing import Any, Dict, List, Optional


class EligibilityError(Exception):
    

    http_status: int = 500
    error_code:  str = "ELIGIBILITY_ERROR"

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details: Dict[str, Any] = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {"error_code": self.error_code, "message": self.message, "details": self.details}


class InsufficientProfileError(EligibilityError):
    
    http_status = 422
    error_code  = "INSUFFICIENT_PROFILE"

    def __init__(self, message: str, missing_fields: Optional[List[str]] = None) -> None:
        super().__init__(message, details={"missing_fields": missing_fields or []})
        self.missing_fields: List[str] = missing_fields or []


class RuleEngineError(EligibilityError):
    
    http_status = 500
    error_code  = "RULE_ENGINE_ERROR"


class DocumentCheckError(EligibilityError):
    
    http_status = 500
    error_code  = "DOCUMENT_CHECK_ERROR"


class ReadinessScoreError(EligibilityError):
    
    http_status = 500
    error_code  = "READINESS_SCORE_ERROR"

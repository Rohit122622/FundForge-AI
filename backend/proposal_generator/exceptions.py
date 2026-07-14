

from typing import Any, Dict, List, Optional


class ProposalError(Exception):
    

    http_status: int = 500
    error_code:  str = "PROPOSAL_ERROR"

    def __init__(
        self,
        message:  str,
        details:  Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details: Dict[str, Any] = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_code": self.error_code,
            "message":    self.message,
            "details":    self.details,
        }


class ProposalValidationError(ProposalError):
    
    http_status = 422
    error_code  = "PROPOSAL_VALIDATION_ERROR"

    def __init__(
        self,
        message:        str,
        missing_fields: Optional[List[str]] = None,
        violations:     Optional[List[str]] = None,
    ) -> None:
        super().__init__(
            message,
            details={
                "missing_fields": missing_fields or [],
                "violations":     violations or [],
            },
        )
        self.missing_fields: List[str] = missing_fields or []
        self.violations:     List[str] = violations or []


class InsufficientDataError(ProposalValidationError):
    
    error_code = "INSUFFICIENT_DATA"


class SectionGenerationError(ProposalError):
    
    http_status = 500
    error_code  = "SECTION_GENERATION_ERROR"

    def __init__(
        self,
        message:      str,
        section_name: str = "",
        details:      Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, details=details)
        self.section_name = section_name


class TemplateNotFoundError(ProposalError):
    
    http_status = 404
    error_code  = "TEMPLATE_NOT_FOUND"

    def __init__(self, template_id: str) -> None:
        super().__init__(
            f"Proposal template '{template_id}' not found.",
            details={"template_id": template_id},
        )
        self.template_id = template_id


class ProposalBuildError(ProposalError):
    
    http_status = 500
    error_code  = "PROPOSAL_BUILD_ERROR"


class ReviewError(ProposalError):
    
    http_status = 500
    error_code  = "REVIEW_ERROR"


class ExportError(ProposalError):
    
    http_status = 500
    error_code  = "EXPORT_ERROR"

    def __init__(
        self,
        message:       str,
        export_format: str = "",
        details:       Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, details=details)
        self.export_format = export_format

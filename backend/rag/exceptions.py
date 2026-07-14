

from typing import Any, Dict, Optional


class RAGError(Exception):
    

    http_status: int = 500
    error_code: str  = "RAG_ERROR"

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
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


class RetrievalError(RAGError):
    
    http_status = 502
    error_code  = "RETRIEVAL_ERROR"

    def __init__(
        self,
        message: str,
        query: str = "",
        provider: str = "ibm",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, details=details)
        self.query    = query
        self.provider = provider


class RetrievalTimeoutError(RetrievalError):
    
    http_status = 504
    error_code  = "RETRIEVAL_TIMEOUT"


class RetrievalUnavailableError(RetrievalError):
    
    http_status = 503
    error_code  = "RETRIEVAL_UNAVAILABLE"


class ContextBuildError(RAGError):
    
    http_status = 500
    error_code  = "CONTEXT_BUILD_ERROR"


class ChunkRankingError(RAGError):
    
    http_status = 500
    error_code  = "CHUNK_RANKING_ERROR"


class DocumentParseError(RAGError):
    
    http_status = 422
    error_code  = "DOCUMENT_PARSE_ERROR"

    def __init__(
        self,
        message: str,
        chunk_id: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, details=details)
        self.chunk_id = chunk_id


class CitationError(RAGError):
    
    http_status = 500
    error_code  = "CITATION_ERROR"


class TokenBudgetExceededError(RAGError):
    
    http_status = 422
    error_code  = "TOKEN_BUDGET_EXCEEDED"

    def __init__(
        self,
        message: str,
        budget: int = 0,
        requested: int = 0,
    ) -> None:
        super().__init__(
            message,
            details={"budget": budget, "requested": requested},
        )
        self.budget    = budget
        self.requested = requested

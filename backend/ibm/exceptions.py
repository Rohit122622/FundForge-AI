

from typing import Any, Dict, Optional


class AIProviderError(Exception):
    

    http_status: int = 502
    error_code: str = "AI_PROVIDER_ERROR"

    def __init__(
        self,
        message: str,
        provider: str = "unknown",
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.status_code = status_code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        
        return {
            "error_code":   self.error_code,
            "message":      self.message,
            "provider":     self.provider,
            "status_code":  self.status_code,
            "details":      self.details,
        }

    def __str__(self) -> str:
        return (
            f"[{self.error_code}] {self.provider}: {self.message}"
            + (f" (HTTP {self.status_code})" if self.status_code else "")
        )






class AIAuthError(AIProviderError):
    
    http_status = 401
    error_code = "AI_AUTH_ERROR"


class AITokenExpiredError(AIAuthError):
    
    http_status = 401
    error_code = "AI_TOKEN_EXPIRED"


class AITokenRefreshError(AIAuthError):
    
    http_status = 401
    error_code = "AI_TOKEN_REFRESH_FAILED"






class AIRateLimitError(AIProviderError):
    
    http_status = 429
    error_code = "AI_RATE_LIMIT"

    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after






class AITimeoutError(AIProviderError):
    
    http_status = 504
    error_code = "AI_TIMEOUT"


class AIConnectionError(AIProviderError):
    
    http_status = 502
    error_code = "AI_CONNECTION_ERROR"






class AIModelError(AIProviderError):
    
    http_status = 502
    error_code = "AI_MODEL_ERROR"


class AIModelNotFoundError(AIModelError):
    
    http_status = 404
    error_code = "AI_MODEL_NOT_FOUND"


class AIContentFilterError(AIModelError):
    
    http_status = 422
    error_code = "AI_CONTENT_FILTER"






class AIVectorIndexError(AIProviderError):
    
    http_status = 502
    error_code = "AI_VECTOR_INDEX_ERROR"


class AIVectorIndexNotFoundError(AIVectorIndexError):
    
    http_status = 404
    error_code = "AI_VECTOR_INDEX_NOT_FOUND"






class AIEmbeddingError(AIProviderError):
    
    http_status = 502
    error_code = "AI_EMBEDDING_ERROR"






class AIConfigError(AIProviderError):
    
    http_status = 500
    error_code = "AI_CONFIG_ERROR"






class AICircuitOpenError(AIProviderError):
    
    http_status = 503
    error_code = "AI_CIRCUIT_OPEN"

    def __init__(self, message: str, reset_after: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.reset_after = reset_after

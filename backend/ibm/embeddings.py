

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.ibm.exceptions import AIConfigError, AIEmbeddingError, AIProviderError

logger = logging.getLogger("fundforge.ibm.embeddings")





_DEFAULT_EMBEDDING_MODEL: str = os.getenv(
    "IBM_EMBEDDING_MODEL_ID", "ibm/slate-125m-english-rtrvr"
)
_IBM_API_VERSION: str = os.getenv("IBM_API_VERSION", "2024-05-31")
_EMBEDDINGS_PATH: str = "/ml/v1/text/embeddings"
_MAX_BATCH_SIZE: int = int(os.getenv("IBM_EMBEDDING_BATCH_SIZE", "25"))
_MAX_INPUT_CHARS: int = int(os.getenv("IBM_EMBEDDING_MAX_CHARS", "8000"))






@dataclass
class EmbeddingResult:
    
    embeddings: List[List[float]] = field(default_factory=list)
    model_id: str = ""
    input_tokens: int = 0
    dimensions: int = 0

    @property
    def count(self) -> int:
        
        return len(self.embeddings)

    def get(self, index: int) -> List[float]:
        
        if index >= len(self.embeddings):
            raise IndexError(
                f"Embedding index {index} out of range (count={self.count})."
            )
        return self.embeddings[index]






class EmbeddingProvider(ABC):
    

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    def embed(self, texts: List[str]) -> EmbeddingResult:
        pass

    @abstractmethod
    def embed_single(self, text: str) -> List[float]:
        pass

    @abstractmethod
    def is_healthy(self) -> bool:
        pass






class IBMEmbeddingProvider(EmbeddingProvider):
    

    def __init__(
        self,
        model_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ):
        from backend.ibm.client import get_ibm_client

        self._model_id    = (model_id or _DEFAULT_EMBEDDING_MODEL).strip()
        self._project_id  = (project_id or os.getenv("IBM_PROJECT_ID", "")).strip()
        self._client      = get_ibm_client()

        if not self._project_id:
            raise AIConfigError(
                "IBM_PROJECT_ID is required for embeddings.",
                provider="ibm",
            )

        logger.info(
            "IBMEmbeddingProvider initialised: model=%s", self._model_id
        )

    
    @property
    def provider_name(self) -> str:
        return "ibm"

    def embed(self, texts: List[str]) -> EmbeddingResult:
        
        if not texts:
            return EmbeddingResult(model_id=self._model_id)

        
        cleaned = [self._truncate(t) for t in texts]

        all_embeddings: List[List[float]] = []
        total_tokens: int = 0

        
        for i in range(0, len(cleaned), _MAX_BATCH_SIZE):
            batch = cleaned[i: i + _MAX_BATCH_SIZE]
            result = self._embed_batch(batch)
            all_embeddings.extend(result.embeddings)
            total_tokens += result.input_tokens

        dims = len(all_embeddings[0]) if all_embeddings else 0

        logger.debug(
            "Embeddings generated: count=%d dims=%d total_tokens=%d model=%s",
            len(all_embeddings), dims, total_tokens, self._model_id,
        )

        return EmbeddingResult(
            embeddings=all_embeddings,
            model_id=self._model_id,
            input_tokens=total_tokens,
            dimensions=dims,
        )

    def embed_single(self, text: str) -> List[float]:
        
        result = self.embed([text])
        if not result.embeddings:
            raise AIEmbeddingError(
                "No embedding returned for single-text request.",
                provider="ibm",
            )
        return result.embeddings[0]

    def is_healthy(self) -> bool:
        
        try:
            self._embed_batch(["health check"])
            return True
        except Exception:
            return False

    
    def _embed_batch(self, texts: List[str]) -> EmbeddingResult:
        
        payload: Dict[str, Any] = {
            "model_id":   self._model_id,
            "project_id": self._project_id,
            "inputs":     texts,
        }

        try:
            response = self._client.post(
                _EMBEDDINGS_PATH,
                json=payload,
                params={"version": _IBM_API_VERSION},
            )
            body = response.json()
            results = body.get("results", [])
            embeddings = [r["embedding"] for r in results if "embedding" in r]
            token_count = body.get("input_token_count", 0)

            if len(embeddings) != len(texts):
                raise AIEmbeddingError(
                    f"IBM returned {len(embeddings)} embeddings for "
                    f"{len(texts)} inputs.",
                    provider="ibm",
                )

            return EmbeddingResult(
                embeddings=embeddings,
                model_id=self._model_id,
                input_tokens=token_count,
                dimensions=len(embeddings[0]) if embeddings else 0,
            )
        except AIProviderError:
            raise
        except Exception as exc:
            raise AIEmbeddingError(
                f"Embedding batch failed: {exc}",
                provider="ibm",
            ) from exc

    @staticmethod
    def _truncate(text: str) -> str:
        
        cleaned = " ".join(text.split())
        return cleaned[:_MAX_INPUT_CHARS] if len(cleaned) > _MAX_INPUT_CHARS else cleaned






_embedding_instance: Optional[EmbeddingProvider] = None
_embedding_lock = __import__("threading").Lock()


def get_embedding_provider(
    provider_name: Optional[str] = None,
    **kwargs: Any,
) -> EmbeddingProvider:
    
    global _embedding_instance
    with _embedding_lock:
        if _embedding_instance is None:
            name = (
                provider_name or os.getenv("EMBEDDING_PROVIDER", "ibm")
            ).lower()
            if name == "ibm":
                _embedding_instance = IBMEmbeddingProvider(**kwargs)
            else:
                raise AIConfigError(
                    f"Embedding provider '{name}' is not registered.",
                    provider=name,
                )
        return _embedding_instance


def reset_embedding_provider() -> None:
    
    global _embedding_instance
    with _embedding_lock:
        _embedding_instance = None

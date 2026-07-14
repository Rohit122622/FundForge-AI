

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.ibm.exceptions import (
    AIConfigError,
    AIProviderError,
    AIVectorIndexError,
    AIVectorIndexNotFoundError,
)

logger = logging.getLogger("fundforge.ibm.vector_search")





_IBM_API_VERSION: str    = os.getenv("IBM_API_VERSION", "2024-05-31")
_VECTOR_INDEX_ID: str    = os.getenv("VECTOR_INDEX_ID", "")
_VECTOR_INSTANCE_ID: str = os.getenv("VECTOR_INDEX_INSTANCE_ID", "")
_DEFAULT_TOP_K: int      = int(os.getenv("RAG_TOP_K", "5"))
_SIM_THRESHOLD: float    = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.65"))


_SEARCH_PATH_TMPL: str = "/ml/v1-beta/vector_stores/{index_id}/search"
_INDEX_LIST_PATH: str  = "/ml/v1-beta/vector_stores"






@dataclass
class SearchResult:
    
    text: str
    score: float = 0.0
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunk_id: str = ""

    @property
    def is_relevant(self) -> bool:
        
        return self.score >= _SIM_THRESHOLD


@dataclass
class VectorSearchResponse:
    
    results: List[SearchResult] = field(default_factory=list)
    query: str = ""
    total_found: int = 0
    index_id: str = ""
    provider: str = "ibm"

    @property
    def relevant_results(self) -> List[SearchResult]:
        
        return [r for r in self.results if r.is_relevant]

    def as_context(self, max_chars: int = 12000) -> str:
        
        parts = []
        total = 0
        for i, r in enumerate(self.relevant_results, start=1):
            block = f"[Source {i}: {r.source or 'grant_kb'}]\n{r.text}\n"
            if total + len(block) > max_chars:
                break
            parts.append(block)
            total += len(block)
        return "\n".join(parts)






class VectorSearchProvider(ABC):
    

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    def search(
        self,
        query: str,
        top_k: int = _DEFAULT_TOP_K,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> VectorSearchResponse:
        pass

    @abstractmethod
    def search_by_vector(
        self,
        vector: List[float],
        top_k: int = _DEFAULT_TOP_K,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> VectorSearchResponse:
        pass

    @abstractmethod
    def is_healthy(self) -> bool:
        pass






class IBMVectorSearchProvider(VectorSearchProvider):
    

    def __init__(
        self,
        index_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ):
        from backend.ibm.client import get_ibm_client

        self._index_id   = (index_id or _VECTOR_INDEX_ID).strip()
        self._project_id = (project_id or os.getenv("IBM_PROJECT_ID", "")).strip()
        self._client     = get_ibm_client()

        if not self._index_id:
            raise AIConfigError(
                "VECTOR_INDEX_ID is not set. Cannot initialise IBMVectorSearchProvider.",
                provider="ibm",
            )
        if not self._project_id:
            raise AIConfigError(
                "IBM_PROJECT_ID is required for vector search.",
                provider="ibm",
            )

        logger.info(
            "IBMVectorSearchProvider initialised: index_id=%s", self._index_id[:8] + "..."
        )

    
    @property
    def provider_name(self) -> str:
        return "ibm"

    def search(
        self,
        query: str,
        top_k: int = _DEFAULT_TOP_K,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> VectorSearchResponse:
        
        path = _SEARCH_PATH_TMPL.format(index_id=self._index_id)

        payload: Dict[str, Any] = {
            "query":      query,
            "limit":      top_k,
            "project_id": self._project_id,
        }
        if filter_metadata:
            payload["filter"] = filter_metadata

        logger.debug(
            "Vector search: index=%s query_chars=%d top_k=%d",
            self._index_id[:8], len(query), top_k,
        )

        try:
            response = self._client.post(
                path,
                json=payload,
                params={"version": _IBM_API_VERSION},
            )
            return self._parse_response(response.json(), query)

        except AIProviderError as exc:
            if exc.status_code == 404:
                raise AIVectorIndexNotFoundError(
                    f"Vector index '{self._index_id}' not found.",
                    provider="ibm",
                    status_code=404,
                ) from exc
            raise AIVectorIndexError(
                f"Vector search failed: {exc.message}",
                provider="ibm",
                status_code=exc.status_code,
            ) from exc
        except Exception as exc:
            raise AIVectorIndexError(
                f"Unexpected error during vector search: {exc}",
                provider="ibm",
            ) from exc

    def search_by_vector(
        self,
        vector: List[float],
        top_k: int = _DEFAULT_TOP_K,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> VectorSearchResponse:
        
        path = _SEARCH_PATH_TMPL.format(index_id=self._index_id)

        payload: Dict[str, Any] = {
            "vector":     vector,
            "limit":      top_k,
            "project_id": self._project_id,
        }
        if filter_metadata:
            payload["filter"] = filter_metadata

        logger.debug(
            "Vector search (by vector): index=%s dims=%d top_k=%d",
            self._index_id[:8], len(vector), top_k,
        )

        try:
            response = self._client.post(
                path,
                json=payload,
                params={"version": _IBM_API_VERSION},
            )
            return self._parse_response(response.json(), query="<vector>")
        except AIProviderError as exc:
            raise AIVectorIndexError(
                f"Vector search (by vector) failed: {exc.message}",
                provider="ibm",
                status_code=exc.status_code,
            ) from exc
        except Exception as exc:
            raise AIVectorIndexError(
                f"Unexpected error during vector search: {exc}",
                provider="ibm",
            ) from exc

    def is_healthy(self) -> bool:
        
        try:
            resp = self.search(query="health check", top_k=1)
            return True
        except AIVectorIndexNotFoundError:
            logger.warning("Vector index not found during health check.")
            return False
        except Exception as exc:
            logger.warning("Vector index health check failed: %s", exc)
            return False

    def list_indexes(self) -> List[Dict[str, Any]]:
        
        try:
            response = self._client.get(
                _INDEX_LIST_PATH,
                params={
                    "version": _IBM_API_VERSION,
                    "project_id": self._project_id,
                },
            )
            data = response.json()
            return data.get("resources", [])
        except AIProviderError as exc:
            raise AIVectorIndexError(
                f"Failed to list vector indexes: {exc.message}",
                provider="ibm",
            ) from exc

    
    def _parse_response(
        self,
        body: Dict[str, Any],
        query: str,
    ) -> VectorSearchResponse:
        
        raw_results = body.get("results", body.get("documents", []))
        parsed: List[SearchResult] = []

        for item in raw_results:
            
            text = (
                item.get("text")
                or item.get("document", {}).get("text")
                or item.get("content")
                or ""
            )
            score = float(
                item.get("score")
                or item.get("relevance")
                or item.get("distance", 0.0)
            )
            source = (
                item.get("source")
                or item.get("document", {}).get("metadata", {}).get("source")
                or item.get("id", "")
            )
            metadata = item.get("metadata") or item.get("document", {}).get("metadata") or {}
            chunk_id = item.get("id") or item.get("chunk_id") or ""

            parsed.append(SearchResult(
                text=str(text).strip(),
                score=score,
                source=str(source),
                metadata=metadata,
                chunk_id=str(chunk_id),
            ))

        logger.debug(
            "Vector search parsed: %d results, %d above threshold (%.2f)",
            len(parsed),
            sum(1 for r in parsed if r.is_relevant),
            _SIM_THRESHOLD,
        )

        return VectorSearchResponse(
            results=parsed,
            query=query,
            total_found=body.get("total_count", len(parsed)),
            index_id=self._index_id,
            provider=self.provider_name,
        )


class MockVectorSearchProvider(VectorSearchProvider):
    
    @property
    def provider_name(self) -> str:
        return "mock"

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> VectorSearchResponse:
        logger.info("MockVectorSearchProvider.search called with query: %s", query)
        results = [
            SearchResult(
                text="Startup India Seed Fund Scheme (SISFS) provides financial assistance up to INR 20 Lakhs for proof of concept/prototype development, and up to INR 50 Lakhs for commercialisation through DPIIT-recognised incubators.",
                score=0.92,
                source="sisfs_guidelines.pdf",
                chunk_id="chunk_1",
            ),
            SearchResult(
                text="To be eligible for Startup India Seed Fund Scheme, a startup must be DPIIT-recognised, incorporated not more than 2 years ago, and have a business plan with potential for scaling.",
                score=0.88,
                source="eligibility_rules.docx",
                chunk_id="chunk_2",
            ),
        ]
        return VectorSearchResponse(results=results, query=query, total_found=2, index_id="mock_index")

    def search_by_vector(
        self,
        vector: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> VectorSearchResponse:
        return self.search(query="<vector>", top_k=top_k, filter_metadata=filter_metadata)

    def is_healthy(self) -> bool:
        return True






_vector_instance: Optional[VectorSearchProvider] = None
_vector_lock = __import__("threading").Lock()


def get_vector_search_provider(
    provider_name: Optional[str] = None,
    **kwargs: Any,
) -> VectorSearchProvider:
    
    global _vector_instance
    with _vector_lock:
        if _vector_instance is None:
            name = (
                provider_name or os.getenv("VECTOR_SEARCH_PROVIDER", "ibm")
            ).lower()
            if name == "ibm":
                try:
                    _vector_instance = IBMVectorSearchProvider(**kwargs)
                except AIConfigError as exc:
                    logger.warning("Failed to configure IBMVectorSearchProvider: %s. Falling back to MockVectorSearchProvider.", exc)
                    _vector_instance = MockVectorSearchProvider()
            elif name == "mock":
                _vector_instance = MockVectorSearchProvider()
            else:
                raise AIConfigError(
                    f"Vector search provider '{name}' is not registered.",
                    provider=name,
                )
        return _vector_instance


def reset_vector_search_provider() -> None:
    
    global _vector_instance
    with _vector_lock:
        _vector_instance = None

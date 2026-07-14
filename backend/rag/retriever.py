

import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from backend.ibm.vector_search import (
    VectorSearchProvider,
    VectorSearchResponse,
)
from backend.rag.document_parser import DocumentParser, ParsedChunk
from backend.rag.exceptions import (
    RetrievalError,
    RetrievalUnavailableError,
)

logger = logging.getLogger("fundforge.rag.retriever")





_DEFAULT_TOP_K: int     = int(os.getenv("RAG_TOP_K", "8"))
_SIM_THRESHOLD: float   = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.65"))
_MAX_TOP_K: int         = 25    






class RetrieverInterface(ABC):
    

    @abstractmethod
    def retrieve(
        self,
        query: str,
        top_k: int = _DEFAULT_TOP_K,
        score_threshold: float = _SIM_THRESHOLD,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[ParsedChunk]:
        pass

    @abstractmethod
    def retrieve_by_vector(
        self,
        vector: List[float],
        top_k: int = _DEFAULT_TOP_K,
        score_threshold: float = _SIM_THRESHOLD,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[ParsedChunk]:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass






class Retriever(RetrieverInterface):
    

    def __init__(
        self,
        vector_provider: VectorSearchProvider,
        parser:          Optional[DocumentParser] = None,
        default_top_k:   int   = _DEFAULT_TOP_K,
        default_threshold: float = _SIM_THRESHOLD,
    ) -> None:
        self._provider  = vector_provider
        self._parser    = parser or DocumentParser()
        self._default_k = min(default_top_k, _MAX_TOP_K)
        self._threshold = default_threshold

    
    @property
    def provider_name(self) -> str:
        return getattr(self._provider, "provider_name", "unknown")

    def retrieve(
        self,
        query: str,
        top_k: int = _DEFAULT_TOP_K,
        score_threshold: float = _SIM_THRESHOLD,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[ParsedChunk]:
        
        if not query or not query.strip():
            logger.warning("Retriever.retrieve called with empty query — returning empty.")
            return []

        effective_k = min(int(top_k), _MAX_TOP_K)
        effective_k = max(1, effective_k)

        logger.debug(
            "Retriever: text query | top_k=%d threshold=%.2f provider=%s",
            effective_k, score_threshold, self.provider_name,
        )

        try:
            response: VectorSearchResponse = self._provider.search(
                query           = query.strip(),
                top_k           = effective_k,
                filter_metadata = metadata_filter,
            )
        except Exception as exc:
            
            err_str = str(exc).lower()
            if any(k in err_str for k in ("not set", "config", "unavailable", "not found")):
                raise RetrievalUnavailableError(
                    f"Vector store is not available: {exc}",
                    query=query,
                    provider=self.provider_name,
                ) from exc
            raise RetrievalError(
                f"Vector search failed: {exc}",
                query=query,
                provider=self.provider_name,
            ) from exc

        return self._process_response(response, score_threshold)

    def retrieve_by_vector(
        self,
        vector: List[float],
        top_k: int = _DEFAULT_TOP_K,
        score_threshold: float = _SIM_THRESHOLD,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[ParsedChunk]:
        
        effective_k = min(max(1, int(top_k)), _MAX_TOP_K)

        logger.debug(
            "Retriever: vector query | dims=%d top_k=%d provider=%s",
            len(vector), effective_k, self.provider_name,
        )

        try:
            response = self._provider.search_by_vector(
                vector          = vector,
                top_k           = effective_k,
                filter_metadata = metadata_filter,
            )
        except Exception as exc:
            raise RetrievalError(
                f"Vector-based search failed: {exc}",
                query="<vector>",
                provider=self.provider_name,
            ) from exc

        return self._process_response(response, score_threshold)

    def retrieve_for_profile(
        self,
        profile_dict: Dict[str, Any],
        top_k: int = _DEFAULT_TOP_K,
        score_threshold: float = _SIM_THRESHOLD,
    ) -> List[ParsedChunk]:
        
        query = self._build_profile_query(profile_dict)
        logger.info(
            "Retriever: profile query | company=%s sector=%s stage=%s",
            profile_dict.get("company_name", "?"),
            profile_dict.get("sector") or profile_dict.get("industry", "?"),
            profile_dict.get("stage", "?"),
        )
        return self.retrieve(
            query           = query,
            top_k           = top_k,
            score_threshold = score_threshold,
        )

    def is_available(self) -> bool:
        
        try:
            return self._provider.is_healthy()
        except Exception as exc:
            logger.warning("Retriever availability check failed: %s", exc)
            return False

    
    def _process_response(
        self,
        response: VectorSearchResponse,
        score_threshold: float,
    ) -> List[ParsedChunk]:
        
        
        relevant = [r for r in response.results if r.score >= score_threshold]

        if not relevant:
            logger.info(
                "Retriever: 0 of %d results passed threshold %.2f.",
                len(response.results), score_threshold,
            )
            return []

        chunks = self._parser.parse_batch(relevant)

        logger.info(
            "Retriever: %d/%d results above threshold %.2f → %d chunks parsed",
            len(relevant), len(response.results), score_threshold, len(chunks),
        )
        return chunks

    @staticmethod
    def _build_profile_query(profile: Dict[str, Any]) -> str:
        
        parts: List[str] = []

        company = profile.get("company_name", "")
        if company:
            parts.append(f"Grants for {company}.")

        
        sector = profile.get("sector") or profile.get("industry", "")
        if sector:
            parts.append(f"Indian startup in the {sector.replace('_', ' ')} sector.")

        
        stage = profile.get("stage", "")
        if stage:
            parts.append(f"Currently at {stage.replace('_', ' ')} stage.")

        
        tech = profile.get("tech_focus", "")
        if tech and tech != "none":
            parts.append(f"Technology focus: {tech.replace('_', ' ')}.")

        
        desc = (profile.get("description") or "")[:300]
        if desc:
            parts.append(desc)

        
        funding = profile.get("funding_needed", "")
        if funding:
            parts.append(f"Funding needed: {funding}.")

        
        if profile.get("is_dpiit_recognised"):
            parts.append("DPIIT recognised startup.")

        
        state = profile.get("state") or profile.get("state_province", "")
        if state:
            parts.append(f"Located in {state.replace('_', ' ').title()}, India.")

        query = " ".join(parts).strip()

        
        if not query:
            query = "Indian startup grant eligibility funding scheme"

        return query

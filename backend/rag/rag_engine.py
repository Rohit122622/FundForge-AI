

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.rag.chunk_ranker import ChunkRanker, RankedChunk
from backend.rag.citation_builder import CitationBuilder, CitationList
from backend.rag.context_builder import ContextBuilder, ContextWindow
from backend.rag.document_parser import DocumentParser, ParsedChunk
from backend.rag.exceptions import (
    RetrievalError,
    RetrievalUnavailableError,
    TokenBudgetExceededError,
)
from backend.rag.retriever import Retriever, RetrieverInterface

logger = logging.getLogger("fundforge.rag.rag_engine")





_DEFAULT_TOP_K:     int   = int(os.getenv("RAG_TOP_K", "8"))
_DEFAULT_THRESHOLD: float = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.65"))
_DEFAULT_MAX_TOKENS: int  = int(os.getenv("RAG_MAX_CONTEXT_TOKENS", "3500"))
_ENGINE_VERSION:    str   = "1.0.0"






@dataclass
class RAGResult:
    
    query:               str
    context_window:      ContextWindow
    ranked_chunks:       List[RankedChunk]     = field(default_factory=list)
    ready_prompt:        Optional[str]         = None
    retrieval_count:     int                   = 0
    included_count:      int                   = 0
    processing_time_ms:  float                 = 0.0
    provider:            str                   = "ibm"
    engine_version:      str                   = _ENGINE_VERSION
    fallback_used:       bool                  = False

    @property
    def context_text(self) -> str:
        
        return self.context_window.context_text

    @property
    def full_context(self) -> str:
        
        return self.context_window.full_context()

    @property
    def citations(self) -> CitationList:
        return self.context_window.citation_list

    @property
    def has_context(self) -> bool:
        
        return self.included_count > 0

    @property
    def token_utilisation(self) -> float:
        return self.context_window.utilisation_pct

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query":               self.query,
            "context":             self.context_window.to_dict(),
            "retrieval_count":     self.retrieval_count,
            "included_count":      self.included_count,
            "processing_time_ms":  round(self.processing_time_ms, 1),
            "token_utilisation":   self.token_utilisation,
            "provider":            self.provider,
            "engine_version":      self.engine_version,
            "fallback_used":       self.fallback_used,
            "citations":           self.citations.to_dict_list(),
        }


@dataclass
class RAGRetrievalConfig:
    
    top_k:              int                       = _DEFAULT_TOP_K
    score_threshold:    float                     = _DEFAULT_THRESHOLD
    max_tokens:         int                       = _DEFAULT_MAX_TOKENS
    metadata_filter:    Optional[Dict[str, Any]]  = None
    build_prompt:       bool                      = False
    enable_compression: bool                      = True






class RAGEngine:
    

    ENGINE_VERSION = _ENGINE_VERSION

    def __init__(
        self,
        retriever:        RetrieverInterface,
        ranker:           Optional[ChunkRanker]       = None,
        context_builder:  Optional[ContextBuilder]    = None,
        citation_builder: Optional[CitationBuilder]   = None,
        prompt_builder:   Any                         = None,
    ) -> None:
        self._retriever        = retriever
        self._ranker           = ranker or ChunkRanker()
        self._citation_builder = citation_builder or CitationBuilder()
        self._context_builder  = context_builder or ContextBuilder(
            citation_builder=self._citation_builder
        )
        self._prompt_builder   = prompt_builder

        logger.info(
            "RAGEngine v%s initialised | provider=%s",
            self.ENGINE_VERSION,
            getattr(retriever, "provider_name", "unknown"),
        )

    
    def retrieve_context(
        self,
        query: str,
        config: Optional[RAGRetrievalConfig] = None,
    ) -> RAGResult:
        
        cfg = config or RAGRetrievalConfig()
        return self._run_pipeline(
            query=query,
            retrieve_fn=lambda: self._retriever.retrieve(
                query           = query,
                top_k           = cfg.top_k,
                score_threshold = cfg.score_threshold,
                metadata_filter = cfg.metadata_filter,
            ),
            config=cfg,
        )

    def retrieve_for_profile(
        self,
        profile_dict: Dict[str, Any],
        config: Optional[RAGRetrievalConfig] = None,
    ) -> RAGResult:
        
        cfg = config or RAGRetrievalConfig()
        query = self._retriever._build_profile_query(profile_dict)  

        return self._run_pipeline(
            query=query,
            retrieve_fn=lambda: self._retriever.retrieve_for_profile(
                profile_dict    = profile_dict,
                top_k           = cfg.top_k,
                score_threshold = cfg.score_threshold,
            ),
            config=cfg,
        )

    def retrieve_by_vector(
        self,
        vector: List[float],
        query_label: str = "<vector>",
        config: Optional[RAGRetrievalConfig] = None,
    ) -> RAGResult:
        
        cfg = config or RAGRetrievalConfig()
        return self._run_pipeline(
            query=query_label,
            retrieve_fn=lambda: self._retriever.retrieve_by_vector(
                vector          = vector,
                top_k           = cfg.top_k,
                score_threshold = cfg.score_threshold,
                metadata_filter = cfg.metadata_filter,
            ),
            config=cfg,
        )

    
    def _run_pipeline(
        self,
        query: str,
        retrieve_fn,
        config: RAGRetrievalConfig,
    ) -> RAGResult:
        
        start_time = time.monotonic()
        fallback   = False

        
        try:
            raw_chunks: List[ParsedChunk] = retrieve_fn()
        except RetrievalUnavailableError as exc:
            logger.warning(
                "RAG retrieval unavailable (%s) — returning empty context.", exc.message
            )
            raw_chunks = []
            fallback   = True
        except RetrievalError as exc:
            logger.error("RAG retrieval failed: %s", exc.message)
            raw_chunks = []
            fallback   = True

        retrieval_count = len(raw_chunks)

        
        ranked: List[RankedChunk] = []
        if raw_chunks:
            try:
                ranked = self._ranker.rank(
                    chunks  = raw_chunks,
                    query   = query,
                    top_k   = config.top_k,
                )
            except Exception as exc:
                logger.error("Chunk ranking failed: %s — using raw order.", exc)
                
                ranked = self._fallback_ranked(raw_chunks)

        
        context_window: ContextWindow
        if ranked:
            try:
                context_window = self._context_builder.build(
                    ranked_chunks = ranked,
                    query         = query,
                    max_tokens    = config.max_tokens,
                )
            except TokenBudgetExceededError:
                logger.warning(
                    "Token budget exceeded — increasing budget by 50%% and retrying."
                )
                try:
                    context_window = self._context_builder.build(
                        ranked_chunks = ranked,
                        query         = query,
                        max_tokens    = config.max_tokens * 2,
                    )
                except Exception as exc2:
                    logger.error("Context build retry failed: %s", exc2)
                    context_window = self._empty_context_window(config.max_tokens)
            except Exception as exc:
                logger.error("Context build failed: %s — returning empty context.", exc)
                context_window = self._empty_context_window(config.max_tokens)
        else:
            context_window = self._empty_context_window(config.max_tokens)

        included_count = context_window.chunks_included

        
        ready_prompt: Optional[str] = None
        if config.build_prompt and self._prompt_builder:
            try:
                ready_prompt = self._prompt_builder.build_qa_prompt(
                    question = query,
                    context  = context_window.full_context(),
                )
            except Exception as exc:
                logger.warning("Prompt build failed: %s — prompt set to None.", exc)

        elapsed_ms = (time.monotonic() - start_time) * 1000

        result = RAGResult(
            query               = query,
            context_window      = context_window,
            ranked_chunks       = ranked,
            ready_prompt        = ready_prompt,
            retrieval_count     = retrieval_count,
            included_count      = included_count,
            processing_time_ms  = elapsed_ms,
            provider            = getattr(self._retriever, "provider_name", "unknown"),
            engine_version      = self.ENGINE_VERSION,
            fallback_used       = fallback,
        )

        logger.info(
            "RAG pipeline complete: retrieved=%d ranked=%d included=%d "
            "tokens=%d/%.0f time=%.1fms fallback=%s",
            retrieval_count,
            len(ranked),
            included_count,
            context_window.total_tokens_used,
            config.max_tokens,
            elapsed_ms,
            fallback,
        )
        return result

    
    def is_available(self) -> bool:
        
        return self._retriever.is_available()

    def get_health(self) -> Dict[str, Any]:
        
        available = self.is_available()
        return {
            "engine_version": self.ENGINE_VERSION,
            "provider":       getattr(self._retriever, "provider_name", "unknown"),
            "available":      available,
            "status":         "healthy" if available else "degraded",
        }

    
    @staticmethod
    def _empty_context_window(max_tokens: int) -> ContextWindow:
        
        from backend.rag.citation_builder import CitationList
        return ContextWindow(
            context_text      = "",
            citation_list     = CitationList(),
            total_tokens_used = 0,
            token_budget      = max_tokens,
        )

    @staticmethod
    def _fallback_ranked(chunks: List[ParsedChunk]) -> List[RankedChunk]:
        
        from backend.rag.chunk_ranker import RankedChunk
        chunks_sorted = sorted(chunks, key=lambda c: -c.vector_score)
        return [
            RankedChunk(chunk=c, rank_score=c.vector_score, rank=i + 1)
            for i, c in enumerate(chunks_sorted)
        ]






_engine_singleton: Optional[RAGEngine] = None
_engine_lock = __import__("threading").Lock()


def get_rag_engine(
    vector_provider=None,
    top_k: int = _DEFAULT_TOP_K,
    max_tokens: int = _DEFAULT_MAX_TOKENS,
    prompt_builder=None,
    **kwargs,
) -> RAGEngine:
    
    global _engine_singleton
    with _engine_lock:
        if _engine_singleton is None:
            if vector_provider is None:
                from backend.ibm.vector_search import get_vector_search_provider
                vector_provider = get_vector_search_provider()

            retriever = Retriever(
                vector_provider   = vector_provider,
                parser            = DocumentParser(),
                default_top_k     = top_k,
            )
            citation_builder = CitationBuilder()
            context_builder  = ContextBuilder(
                max_tokens       = max_tokens,
                citation_builder = citation_builder,
            )
            _engine_singleton = RAGEngine(
                retriever        = retriever,
                ranker           = ChunkRanker(),
                context_builder  = context_builder,
                citation_builder = citation_builder,
                prompt_builder   = prompt_builder,
            )
        return _engine_singleton


def reset_rag_engine() -> None:
    
    global _engine_singleton
    with _engine_lock:
        _engine_singleton = None

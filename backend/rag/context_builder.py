

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from backend.rag.chunk_ranker import RankedChunk
from backend.rag.citation_builder import CitationBuilder, CitationList
from backend.rag.document_parser import ParsedChunk
from backend.rag.exceptions import ContextBuildError, TokenBudgetExceededError

logger = logging.getLogger("fundforge.rag.context_builder")






_DEFAULT_MAX_TOKENS:    int  = 3500    
_DEFAULT_CHUNK_HEADER:  bool = True    
_DEFAULT_COMPRESSION:   bool = True    
_COMPRESSION_THRESHOLD: int  = 200     






@dataclass
class ContextWindow:
    
    context_text:       str
    citation_list:      CitationList
    included_chunks:    List[ParsedChunk]  = field(default_factory=list)
    excluded_chunks:    List[ParsedChunk]  = field(default_factory=list)
    total_tokens_used:  int                = 0
    token_budget:       int                = _DEFAULT_MAX_TOKENS
    reference_block:    str                = ""
    query:              str                = ""

    @property
    def utilisation_pct(self) -> float:
        
        if self.token_budget == 0:
            return 0.0
        return round(100 * self.total_tokens_used / self.token_budget, 1)

    @property
    def is_full(self) -> bool:
        
        return self.utilisation_pct >= 95.0

    @property
    def chunks_included(self) -> int:
        return len(self.included_chunks)

    @property
    def chunks_excluded(self) -> int:
        return len(self.excluded_chunks)

    def full_context(self) -> str:
        
        if self.reference_block:
            return f"{self.context_text}\n{self.reference_block}"
        return self.context_text

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_text":      self.context_text,
            "citations":         self.citation_list.to_dict_list(),
            "chunks_included":   self.chunks_included,
            "chunks_excluded":   self.chunks_excluded,
            "total_tokens_used": self.total_tokens_used,
            "token_budget":      self.token_budget,
            "utilisation_pct":   self.utilisation_pct,
            "query":             self.query,
        }






class ContextBuilder:
    

    def __init__(
        self,
        max_tokens:          int = _DEFAULT_MAX_TOKENS,
        include_headers:     bool = _DEFAULT_CHUNK_HEADER,
        enable_compression:  bool = _DEFAULT_COMPRESSION,
        citation_builder:    Optional[CitationBuilder] = None,
    ) -> None:
        self._max_tokens          = max_tokens
        self._include_headers     = include_headers
        self._enable_compression  = enable_compression
        self._citation_builder    = citation_builder or CitationBuilder()

    
    def build(
        self,
        ranked_chunks: List[RankedChunk],
        query: str,
        max_tokens: Optional[int] = None,
    ) -> ContextWindow:
        
        budget = max_tokens if max_tokens is not None else self._max_tokens

        if not ranked_chunks:
            return ContextWindow(
                context_text      = "",
                citation_list     = CitationList(),
                token_budget      = budget,
                query             = query,
            )

        try:
            query_tokens = self._keyword_set(query)
            included: List[ParsedChunk] = []
            excluded: List[ParsedChunk] = []
            text_blocks: List[str]      = []
            remaining                   = budget

            for rc in ranked_chunks:
                chunk = rc.chunk
                chunk_tokens = chunk.token_estimate

                if chunk_tokens <= remaining:
                    
                    included.append(chunk)
                    remaining -= chunk_tokens

                elif (
                    self._enable_compression
                    and chunk_tokens > _COMPRESSION_THRESHOLD
                    and remaining >= _COMPRESSION_THRESHOLD // 2
                ):
                    
                    compressed_text = self._compress(chunk.text, remaining, query_tokens)
                    if compressed_text:
                        compressed_tokens = self._estimate_tokens(compressed_text)
                        if compressed_tokens <= remaining:
                            
                            compressed_chunk = self._clone_with_text(chunk, compressed_text)
                            included.append(compressed_chunk)
                            remaining -= compressed_tokens
                            logger.debug(
                                "Compressed chunk %s: %d → %d tokens",
                                chunk.chunk_id[:12], chunk_tokens, compressed_tokens,
                            )
                            continue

                    
                    excluded.append(chunk)
                else:
                    excluded.append(chunk)

            
            if not included and ranked_chunks:
                raise TokenBudgetExceededError(
                    "No chunks fit within the token budget. "
                    "Increase max_tokens or reduce chunk sizes.",
                    budget=budget,
                    requested=ranked_chunks[0].chunk.token_estimate,
                )

            
            citation_list = self._citation_builder.build(included)

            
            for chunk in included:
                block = self._format_chunk_block(chunk, citation_list)
                text_blocks.append(block)

            context_text   = "\n\n".join(text_blocks)
            reference_block = citation_list.format_reference_list()
            tokens_used     = budget - remaining

            window = ContextWindow(
                context_text      = context_text,
                citation_list     = citation_list,
                included_chunks   = included,
                excluded_chunks   = excluded,
                total_tokens_used = tokens_used,
                token_budget      = budget,
                reference_block   = reference_block,
                query             = query,
            )

            logger.info(
                "ContextWindow built: %d/%d chunks included | %d/%d tokens | %.1f%% utilisation",
                window.chunks_included,
                len(ranked_chunks),
                tokens_used,
                budget,
                window.utilisation_pct,
            )
            return window

        except (ContextBuildError, TokenBudgetExceededError):
            raise
        except Exception as exc:
            raise ContextBuildError(f"Context build failed: {exc}") from exc

    
    def _format_chunk_block(
        self,
        chunk: ParsedChunk,
        citation_list: CitationList,
    ) -> str:
        
        inline_ref = citation_list.get_inline_ref(chunk.chunk_id)
        parts = []

        if self._include_headers and inline_ref:
            parts.append(inline_ref)

        text = chunk.text.strip()
        parts.append(text)

        return "\n".join(parts)

    @staticmethod
    def _compress(text: str, token_budget: int, query_tokens: Set[str]) -> str:
        
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        if len(sentences) <= 1:
            return ""  

        
        scored = []
        for i, sent in enumerate(sentences):
            sent_tokens = set(re.findall(r"\b[a-z]{3,}\b", sent.lower()))
            kw_hits = len(sent_tokens & query_tokens) if query_tokens else 0
            length_pref = min(1.0, len(sent.split()) / 25)  
            score = kw_hits * 1.5 + length_pref
            scored.append((score, i, sent))

        
        scored.sort(key=lambda x: -x[0])
        remaining = token_budget
        selected_indices: List[int] = []

        for score, idx, sent in scored:
            est = ContextBuilder._estimate_tokens(sent)
            if est <= remaining:
                selected_indices.append(idx)
                remaining -= est
            if remaining <= 0:
                break

        if not selected_indices:
            return ""

        
        selected_indices.sort()
        return " ".join(sentences[i] for i in selected_indices)

    @staticmethod
    def _keyword_set(query: str) -> Set[str]:
        
        _STOP = frozenset({"the", "and", "for", "are", "what", "how", "who", "when"})
        tokens = re.findall(r"\b[a-z]{3,}\b", query.lower())
        return {t for t in tokens if t not in _STOP}

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        
        return max(1, round(len(text.split()) * 1.35))

    @staticmethod
    def _clone_with_text(chunk: ParsedChunk, new_text: str) -> ParsedChunk:
        
        import copy
        c = copy.copy(chunk)
        c.text           = new_text
        c.token_estimate = ContextBuilder._estimate_tokens(new_text)
        return c

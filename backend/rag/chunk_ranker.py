

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from backend.rag.document_parser import ContentType, ParsedChunk
from backend.rag.exceptions import ChunkRankingError

logger = logging.getLogger("fundforge.rag.chunk_ranker")







_W_VECTOR   = 0.50
_W_KEYWORD  = 0.25
_W_TYPE     = 0.12
_W_LENGTH   = 0.08
_W_FRESH    = 0.05


_TYPE_PRIORITY: Dict[str, float] = {
    ContentType.ELIGIBILITY:         1.0,
    ContentType.FINANCIAL_INFO:      0.9,
    ContentType.APPLICATION_GUIDE:   0.85,
    ContentType.EVALUATION_CRITERIA: 0.80,
    ContentType.GRANT_DESCRIPTION:   0.75,
    ContentType.TIMELINE:            0.65,
    ContentType.GENERAL:             0.55,
    ContentType.CONTACT_INFO:        0.40,
    ContentType.UNKNOWN:             0.30,
}


_IDEAL_MIN_TOKENS = 50
_IDEAL_MAX_TOKENS = 350


_DUPLICATE_THRESHOLD = 0.85


_FRESHNESS_DAYS = 180






@dataclass
class RankedChunk:
    
    chunk:       ParsedChunk
    rank_score:  float
    rank:        int = 0
    is_duplicate: bool = False

    @property
    def chunk_id(self) -> str:
        return self.chunk.chunk_id

    @property
    def text(self) -> str:
        return self.chunk.text

    def to_dict(self) -> dict:
        d = self.chunk.to_dict()
        d["rank_score"]    = round(self.rank_score, 4)
        d["rank"]          = self.rank
        d["is_duplicate"]  = self.is_duplicate
        return d






class ChunkRanker:
    

    def __init__(
        self,
        duplicate_threshold: float = _DUPLICATE_THRESHOLD,
        remove_duplicates: bool = True,
    ) -> None:
        self._dup_threshold    = duplicate_threshold
        self._remove_duplicates = remove_duplicates

    
    def rank(
        self,
        chunks: List[ParsedChunk],
        query: str,
        top_k: Optional[int] = None,
    ) -> List[RankedChunk]:
        
        if not chunks:
            return []

        try:
            query_tokens = self._tokenise(query)
            scored: List[RankedChunk] = []

            for chunk in chunks:
                rs = self._compute_rank_score(chunk, query_tokens)
                
                chunk.rank_score = rs
                scored.append(RankedChunk(chunk=chunk, rank_score=rs))

            
            scored.sort(key=lambda rc: -rc.rank_score)

            
            if self._remove_duplicates:
                scored = self._deduplicate(scored)

            
            for i, rc in enumerate(scored):
                rc.rank = i + 1

            result = scored[:top_k] if top_k else scored

            logger.debug(
                "ChunkRanker: %d → %d chunks after dedup | top_score=%.3f | query_tokens=%d",
                len(chunks), len(result),
                result[0].rank_score if result else 0.0,
                len(query_tokens),
            )
            return result

        except Exception as exc:
            raise ChunkRankingError(f"Chunk ranking failed: {exc}") from exc

    
    def _compute_rank_score(
        self,
        chunk: ParsedChunk,
        query_tokens: Set[str],
    ) -> float:
        
        v  = self._signal_vector(chunk)
        kw = self._signal_keyword(chunk, query_tokens)
        tp = self._signal_type_priority(chunk)
        ln = self._signal_length(chunk)
        fr = self._signal_freshness(chunk)

        score = (
            v  * _W_VECTOR
            + kw * _W_KEYWORD
            + tp * _W_TYPE
            + ln * _W_LENGTH
            + fr * _W_FRESH
        )
        return round(min(1.0, max(0.0, score)), 4)

    @staticmethod
    def _signal_vector(chunk: ParsedChunk) -> float:
        
        return min(1.0, max(0.0, float(chunk.vector_score)))

    @staticmethod
    def _signal_keyword(chunk: ParsedChunk, query_tokens: Set[str]) -> float:
        
        if not query_tokens:
            return 0.5  
        chunk_tokens = ChunkRanker._tokenise(chunk.text)
        if not chunk_tokens:
            return 0.0
        hits = query_tokens.intersection(chunk_tokens)
        return min(1.0, len(hits) / len(query_tokens))

    @staticmethod
    def _signal_type_priority(chunk: ParsedChunk) -> float:
        
        return _TYPE_PRIORITY.get(chunk.content_type, 0.30)

    @staticmethod
    def _signal_length(chunk: ParsedChunk) -> float:
        
        t = chunk.token_estimate
        if _IDEAL_MIN_TOKENS <= t <= _IDEAL_MAX_TOKENS:
            return 1.0
        if t < _IDEAL_MIN_TOKENS:
            return max(0.0, t / _IDEAL_MIN_TOKENS)
        
        excess = t - _IDEAL_MAX_TOKENS
        return max(0.2, 1.0 - (excess / (_IDEAL_MAX_TOKENS * 3)))

    @staticmethod
    def _signal_freshness(chunk: ParsedChunk) -> float:
        
        if chunk.indexed_at is None:
            return 0.5  
        try:
            now  = datetime.now(tz=timezone.utc)
            ts   = chunk.indexed_at
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age_days = (now - ts).days
            if age_days <= _FRESHNESS_DAYS:
                return 1.0 - (age_days / _FRESHNESS_DAYS) * 0.5
            return 0.2
        except Exception:
            return 0.5

    
    def _deduplicate(self, ranked: List[RankedChunk]) -> List[RankedChunk]:
        
        kept: List[RankedChunk] = []
        ngram_sets: List[Set[str]] = []

        for rc in ranked:
            ngrams = self._ngrams(rc.chunk.text, n=4)
            is_dup = False

            for existing_ngrams in ngram_sets:
                j = self._jaccard(ngrams, existing_ngrams)
                if j >= self._dup_threshold:
                    is_dup = True
                    rc.is_duplicate = True
                    logger.debug(
                        "Duplicate chunk dropped: id=%s jaccard=%.3f",
                        rc.chunk_id[:12], j,
                    )
                    break

            if not is_dup:
                kept.append(rc)
                ngram_sets.append(ngrams)

        return kept

    
    @staticmethod
    def _tokenise(text: str) -> Set[str]:
        
        _STOP = frozenset({
            "the", "and", "for", "are", "was", "has", "have", "this",
            "that", "with", "will", "can", "its", "from", "not", "all",
        })
        tokens = re.findall(r"\b[a-z]{3,}\b", text.lower())
        return {t for t in tokens if t not in _STOP}

    @staticmethod
    def _ngrams(text: str, n: int = 4) -> Set[str]:
        
        cleaned = re.sub(r"\s+", " ", text.lower().strip())
        if len(cleaned) < n:
            return {cleaned}
        return {cleaned[i: i + n] for i in range(len(cleaned) - n + 1)}

    @staticmethod
    def _jaccard(set_a: Set[str], set_b: Set[str]) -> float:
        
        if not set_a or not set_b:
            return 0.0
        inter = set_a & set_b
        union = set_a | set_b
        return len(inter) / len(union) if union else 0.0

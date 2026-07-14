

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.rag.exceptions import DocumentParseError

logger = logging.getLogger("fundforge.rag.document_parser")






class ContentType:
    
    GRANT_DESCRIPTION  = "grant_description"
    ELIGIBILITY        = "eligibility"
    APPLICATION_GUIDE  = "application_guide"
    EVALUATION_CRITERIA= "evaluation_criteria"
    FINANCIAL_INFO     = "financial_info"
    TIMELINE           = "timeline"
    CONTACT_INFO       = "contact_info"
    GENERAL            = "general"
    UNKNOWN            = "unknown"



_CONTENT_TYPE_KEYWORDS: Dict[str, List[str]] = {
    ContentType.ELIGIBILITY: [
        "eligible", "eligibility", "must be", "must have", "require",
        "criteria", "qualify", "applicant", "who can apply",
    ],
    ContentType.APPLICATION_GUIDE: [
        "application", "apply", "submit", "submission", "form",
        "portal", "how to apply", "deadline", "procedure",
    ],
    ContentType.EVALUATION_CRITERIA: [
        "evaluation", "scoring", "assessment", "judged", "selected",
        "review committee", "criteria", "merit",
    ],
    ContentType.FINANCIAL_INFO: [
        "amount", "lakh", "crore", "inr", "funding", "grant amount",
        "award", "budget", "disbursed", "disbursement",
    ],
    ContentType.TIMELINE: [
        "timeline", "phase", "milestone", "schedule", "period",
        "duration", "months", "year 1", "year 2",
    ],
    ContentType.CONTACT_INFO: [
        "contact", "email", "phone", "helpdesk", "enquiry", "nodal",
    ],
}






@dataclass
class ParsedChunk:
    
    chunk_id:       str
    text:           str
    source:         str          = ""
    document_name:  str          = ""
    page_number:    int          = 0
    section:        str          = ""
    content_type:   str          = ContentType.UNKNOWN
    vector_score:   float        = 0.0
    rank_score:     float        = 0.0
    token_estimate: int          = 0
    metadata:       Dict[str, Any] = field(default_factory=dict)
    indexed_at:     Optional[datetime] = None

    @property
    def display_source(self) -> str:
        
        if self.document_name:
            return self.document_name
        if self.source:
            
            base = self.source.rsplit(".", 1)[0].replace("_", " ").replace("-", " ")
            return base.title()
        return "Grant Knowledge Base"

    @property
    def page_label(self) -> str:
        
        return f"p. {self.page_number}" if self.page_number > 0 else ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id":       self.chunk_id,
            "text":           self.text,
            "source":         self.source,
            "document_name":  self.document_name,
            "page_number":    self.page_number,
            "section":        self.section,
            "content_type":   self.content_type,
            "vector_score":   round(self.vector_score, 4),
            "rank_score":     round(self.rank_score, 4),
            "token_estimate": self.token_estimate,
        }






class DocumentParser:
    

    
    _PAGE_RE = re.compile(
        r"(?:page|pg\.?|p\.)\s*(\d{1,4})",
        re.IGNORECASE,
    )
    
    _CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")

    def parse(self, search_result: Any) -> ParsedChunk:
        
        try:
            chunk_id = search_result.chunk_id or self._compute_id(search_result.text)
            text     = self._clean_text(search_result.text)
            metadata = search_result.metadata or {}

            document_name = self._extract_document_name(search_result.source, metadata)
            page_number   = self._extract_page_number(text, metadata)
            section       = self._extract_section(metadata)
            content_type  = self._classify_content(text)
            token_est     = self._estimate_tokens(text)
            indexed_at    = self._parse_date(metadata.get("indexed_at") or metadata.get("created_at"))

            chunk = ParsedChunk(
                chunk_id       = chunk_id,
                text           = text,
                source         = search_result.source or "",
                document_name  = document_name,
                page_number    = page_number,
                section        = section,
                content_type   = content_type,
                vector_score   = float(search_result.score),
                rank_score     = float(search_result.score),  
                token_estimate = token_est,
                metadata       = metadata,
                indexed_at     = indexed_at,
            )

            logger.debug(
                "Chunk parsed: id=%s source=%s type=%s tokens=%d score=%.3f",
                chunk_id[:12], search_result.source or "?",
                content_type, token_est, search_result.score,
            )
            return chunk

        except Exception as exc:
            cid = getattr(search_result, "chunk_id", "")
            raise DocumentParseError(
                f"Failed to parse chunk: {exc}",
                chunk_id=cid,
            ) from exc

    def parse_batch(self, search_results: List[Any]) -> List[ParsedChunk]:
        
        chunks: List[ParsedChunk] = []
        for sr in search_results:
            try:
                chunks.append(self.parse(sr))
            except DocumentParseError as exc:
                logger.warning("Skipping unparseable chunk %s: %s", exc.chunk_id, exc.message)
        return chunks

    
    @staticmethod
    def _clean_text(text: str) -> str:
        
        cleaned = DocumentParser._CTRL_RE.sub(" ", text or "")
        cleaned = re.sub(r" {2,}", " ", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    @staticmethod
    def _compute_id(text: str) -> str:
        
        return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:24]

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        
        return max(1, round(len((text or "").split()) * 1.35))

    @staticmethod
    def _extract_document_name(source: str, metadata: Dict[str, Any]) -> str:
        
        
        for key in ("document_title", "title", "document_name", "filename", "name"):
            value = metadata.get(key, "")
            if value:
                return str(value).strip()
        
        if source:
            basename = source.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
            return basename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()
        return ""

    @classmethod
    def _extract_page_number(cls, text: str, metadata: Dict[str, Any]) -> int:
        
        
        for key in ("page", "page_number", "page_num", "pg"):
            raw = metadata.get(key)
            if raw is not None:
                try:
                    return max(0, int(raw))
                except (TypeError, ValueError):
                    pass
        
        match = cls._PAGE_RE.search(text[:200])   
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass
        return 0

    @staticmethod
    def _extract_section(metadata: Dict[str, Any]) -> str:
        
        for key in ("section", "section_title", "heading", "chapter"):
            value = metadata.get(key, "")
            if value:
                return str(value).strip()
        return ""

    @classmethod
    def _classify_content(cls, text: str) -> str:
        
        text_lower = text.lower()
        for content_type, keywords in _CONTENT_TYPE_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                return content_type
        
        if len(text.split()) > 30:
            return ContentType.GENERAL
        return ContentType.UNKNOWN

    @staticmethod
    def _parse_date(value: Any) -> Optional[datetime]:
        
        if value is None:
            return None
        try:
            if isinstance(value, datetime):
                return value
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None

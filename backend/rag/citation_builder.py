

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.rag.document_parser import ParsedChunk
from backend.rag.exceptions import CitationError

logger = logging.getLogger("fundforge.rag.citation_builder")






@dataclass
class Citation:
    
    index:         int
    chunk_ids:     List[str] = field(default_factory=list)
    document_name: str       = ""
    source:        str       = ""
    page_number:   int       = 0
    section:       str       = ""
    content_type:  str       = ""
    indexed_at:    Optional[datetime] = None

    @property
    def label(self) -> str:
        
        parts = [self.document_name or self.source or "Grant Knowledge Base"]
        if self.page_number > 0:
            parts.append(f"p. {self.page_number}")
        if self.section:
            parts.append(f"§ {self.section}")
        return ", ".join(parts)

    @property
    def inline_ref(self) -> str:
        
        return f"[Source {self.index}: {self.label}]"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index":         self.index,
            "chunk_ids":     self.chunk_ids,
            "document_name": self.document_name,
            "source":        self.source,
            "page_number":   self.page_number,
            "section":       self.section,
            "content_type":  self.content_type,
            "label":         self.label,
            "inline_ref":    self.inline_ref,
            "indexed_at":    self.indexed_at.isoformat() if self.indexed_at else None,
        }


@dataclass
class CitationList:
    
    citations:     List[Citation]  = field(default_factory=list)
    chunk_to_idx:  Dict[str, int]  = field(default_factory=dict)

    @property
    def count(self) -> int:
        return len(self.citations)

    def get_inline_ref(self, chunk_id: str) -> str:
        
        idx = self.chunk_to_idx.get(chunk_id)
        if idx is None:
            return ""
        return self.citations[idx - 1].inline_ref  

    def format_reference_list(self) -> str:
        
        if not self.citations:
            return ""

        lines = ["", "References", "----------"]
        for cit in self.citations:
            line = f"[{cit.index}] {cit.document_name or cit.source or 'Unknown Source'}"
            if cit.page_number > 0:
                line += f" — Page {cit.page_number}"
            if cit.section:
                line += f" (§ {cit.section})"
            line += f"."
            if cit.source and cit.source != cit.document_name:
                line += f"\n     File: {cit.source}"
            if cit.indexed_at:
                line += f" | Indexed: {cit.indexed_at.strftime('%Y-%m-%d')}"
            lines.append(line)
        return "\n".join(lines)

    def to_dict_list(self) -> List[Dict[str, Any]]:
        
        return [c.to_dict() for c in self.citations]






class CitationBuilder:
    

    def build(self, chunks: List[ParsedChunk]) -> CitationList:
        
        if not chunks:
            return CitationList()

        try:
            
            
            seen: Dict[tuple, Citation] = {}
            citation_list: List[Citation] = []
            chunk_to_idx: Dict[str, int] = {}
            counter = 1

            for chunk in chunks:
                key = (
                    (chunk.source or chunk.document_name or "").lower(),
                    chunk.page_number,
                )

                if key in seen:
                    
                    existing = seen[key]
                    existing.chunk_ids.append(chunk.chunk_id)
                    chunk_to_idx[chunk.chunk_id] = existing.index
                else:
                    cit = Citation(
                        index         = counter,
                        chunk_ids     = [chunk.chunk_id],
                        document_name = chunk.document_name,
                        source        = chunk.source,
                        page_number   = chunk.page_number,
                        section       = chunk.section,
                        content_type  = chunk.content_type,
                        indexed_at    = chunk.indexed_at,
                    )
                    seen[key]                     = cit
                    chunk_to_idx[chunk.chunk_id] = counter
                    citation_list.append(cit)
                    counter += 1

            result = CitationList(
                citations    = citation_list,
                chunk_to_idx = chunk_to_idx,
            )

            logger.debug(
                "CitationBuilder: %d chunks → %d citations",
                len(chunks), result.count,
            )
            return result

        except Exception as exc:
            raise CitationError(f"Citation building failed: {exc}") from exc

    def format_inline(
        self,
        text: str,
        chunk: ParsedChunk,
        citation_list: CitationList,
    ) -> str:
        
        ref = citation_list.get_inline_ref(chunk.chunk_id)
        if ref:
            text = text.rstrip()
            if not text.endswith((".", "?", "!", ":")):
                text += "."
            text += f" {ref}"
        return text

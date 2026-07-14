

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from backend.proposal_generator.exceptions import (
    InsufficientDataError,
    ProposalValidationError,
)
from backend.proposal_generator.template_manager import ProposalTemplate, SectionSpec

logger = logging.getLogger("fundforge.proposal_generator.validator")






@dataclass
class SectionQuality:
    
    key:         str
    score:       float
    word_count:  int          = 0
    issues:      List[str]    = field(default_factory=list)
    suggestions: List[str]    = field(default_factory=list)

    @property
    def grade(self) -> str:
        
        if self.score >= 0.85: return "A"
        if self.score >= 0.70: return "B"
        if self.score >= 0.55: return "C"
        if self.score >= 0.40: return "D"
        return "F"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key":         self.key,
            "score":       round(self.score, 3),
            "grade":       self.grade,
            "word_count":  self.word_count,
            "issues":      self.issues,
            "suggestions": self.suggestions,
        }


@dataclass
class ProposalValidationResult:
    
    is_valid:            bool
    completeness_score:  int
    section_qualities:   List[SectionQuality]   = field(default_factory=list)
    missing_fields:      List[str]               = field(default_factory=list)
    hard_violations:     List[str]               = field(default_factory=list)
    warnings:            List[str]               = field(default_factory=list)
    review_suggestions:  List[str]               = field(default_factory=list)

    @property
    def quality_band(self) -> str:
        
        if self.completeness_score >= 80: return "Excellent"
        if self.completeness_score >= 65: return "Good"
        if self.completeness_score >= 50: return "Fair"
        if self.completeness_score >= 35: return "Needs Improvement"
        return "Poor"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid":           self.is_valid,
            "completeness_score": self.completeness_score,
            "quality_band":       self.quality_band,
            "section_qualities":  [sq.to_dict() for sq in self.section_qualities],
            "missing_fields":     self.missing_fields,
            "hard_violations":    self.hard_violations,
            "warnings":           self.warnings,
            "review_suggestions": self.review_suggestions,
        }






class Validator:
    

    
    _REQUIRED_PROFILE_FIELDS: List[str] = [
        "company_name", "description", "industry", "stage",
    ]

    
    _ADVISORY_PROFILE_FIELDS: List[Tuple[str, str]] = [
        ("problem_statement",  "Problem statement"),
        ("solution_statement", "Solution description"),
        ("impact_statement",   "Impact statement"),
        ("founding_year",      "Year of incorporation"),
        ("team_size",          "Team size"),
        ("funding_needed",     "Funding amount needed"),
        ("state_province",     "Indian state of operations"),
        ("technology_stack",   "Technology stack"),
    ]

    
    _REQUIRED_GRANT_FIELDS: List[str] = ["name", "description"]

    def validate_request(
        self,
        startup_profile: Dict[str, Any],
        grant_data: Dict[str, Any],
    ) -> None:
        
        missing_profile = []
        for f in self._REQUIRED_PROFILE_FIELDS:
            val = startup_profile.get(f)
            if f == "industry" and not val:
                val = startup_profile.get("sector")
            if not val:
                missing_profile.append(f)

        missing_grant = [
            f for f in self._REQUIRED_GRANT_FIELDS
            if not grant_data.get(f, "")
        ]

        if missing_profile:
            raise InsufficientDataError(
                f"Startup profile is missing required fields for proposal generation: "
                f"{', '.join(missing_profile)}.",
                missing_fields=missing_profile,
            )

        if missing_grant:
            raise ProposalValidationError(
                f"Grant data is missing required fields: {', '.join(missing_grant)}.",
                missing_fields=missing_grant,
            )

        logger.debug(
            "Request validation passed: company=%s grant=%s",
            startup_profile.get("company_name", "?"),
            grant_data.get("name", "?"),
        )

    def detect_missing_fields(
        self,
        startup_profile: Dict[str, Any],
    ) -> List[str]:
        
        return [
            label
            for field_key, label in self._ADVISORY_PROFILE_FIELDS
            if not startup_profile.get(field_key, "")
        ]

    def score_section(
        self,
        key:        str,
        text:       str,
        spec:       SectionSpec,
        profile:    Optional[Dict[str, Any]] = None,
    ) -> SectionQuality:
        
        issues:      List[str] = []
        suggestions: List[str] = []

        if not text or not text.strip():
            return SectionQuality(
                key=key, score=0.0, word_count=0,
                issues=["Section is empty."],
                suggestions=[f"Generate the '{spec.title}' section."],
            )

        word_count = len(text.split())

        
        length_score = self._score_length(word_count, spec.min_words, spec.max_words)
        if word_count < spec.min_words:
            issues.append(f"Too short ({word_count} words; minimum {spec.min_words}).")
            suggestions.append(f"Expand '{spec.title}' with more detail.")
        elif word_count > spec.max_words * 1.5:
            issues.append(f"Too long ({word_count} words; maximum ~{spec.max_words}).")
            suggestions.append(f"Trim '{spec.title}' for conciseness.")

        
        structure_score = self._score_structure(text)
        if structure_score < 0.5:
            issues.append("Section lacks clear paragraph structure.")
            suggestions.append("Break into 2–3 paragraphs with clear topic sentences.")

        
        specificity_score = self._score_specificity(text)
        if specificity_score < 0.4:
            issues.append("Section is vague — lacks numbers, metrics, or named entities.")
            suggestions.append("Add specific data points: team size, funding ask, market size.")

        
        keyword_score = self._score_keyword_coverage(text, spec, profile)
        if keyword_score < 0.4:
            suggestions.append(f"Ensure '{spec.title}' addresses: {spec.emphasis[:80]}...")

        
        composite = (
            length_score      * 0.30
            + structure_score * 0.25
            + specificity_score * 0.25
            + keyword_score   * 0.20
        )
        composite = round(min(1.0, max(0.0, composite)), 3)

        return SectionQuality(
            key         = key,
            score       = composite,
            word_count  = word_count,
            issues      = issues,
            suggestions = suggestions,
        )

    def validate_proposal(
        self,
        sections:   Dict[str, str],
        template:   ProposalTemplate,
        profile:    Optional[Dict[str, Any]] = None,
    ) -> ProposalValidationResult:
        
        section_qualities: List[SectionQuality] = []
        hard_violations:   List[str]            = []
        warnings:          List[str]            = []

        
        for spec in sorted(template.sections, key=lambda s: s.order):
            text = sections.get(spec.key, "")
            sq = self.score_section(spec.key, text, spec, profile)
            section_qualities.append(sq)

            
            if spec.required and not text.strip():
                hard_violations.append(f"Required section '{spec.title}' is missing.")
            elif spec.required and sq.word_count < max(20, spec.min_words // 3):
                hard_violations.append(
                    f"Required section '{spec.title}' is critically short "
                    f"({sq.word_count} words)."
                )

        
        req_scores = [
            sq.score for sq in section_qualities
            if template.get_section(sq.key) and
               (template.get_section(sq.key).required)  
        ]
        if req_scores:
            avg = sum(req_scores) / len(req_scores)
            completeness = min(100, max(0, round(avg * 100)))
        else:
            completeness = 0

        
        for sq in section_qualities:
            if sq.score < 0.45 and sq.word_count > 0:
                warnings.append(f"Section '{sq.key}' quality is below 45% — review needed.")

        
        missing = self.detect_missing_fields(profile or {})

        
        suggestions = self._build_review_suggestions(
            section_qualities, hard_violations, missing
        )

        return ProposalValidationResult(
            is_valid           = len(hard_violations) == 0,
            completeness_score = completeness,
            section_qualities  = section_qualities,
            missing_fields     = missing,
            hard_violations    = hard_violations,
            warnings           = warnings,
            review_suggestions = suggestions,
        )

    
    @staticmethod
    def _score_length(count: int, min_w: int, max_w: int) -> float:
        if count >= min_w and count <= max_w:
            return 1.0
        if count < min_w:
            return max(0.0, count / min_w)
        
        excess_ratio = (count - max_w) / max(1, max_w)
        return max(0.4, 1.0 - excess_ratio * 0.3)

    @staticmethod
    def _score_structure(text: str) -> float:
        
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        sentences  = re.split(r"(?<=[.!?])\s+", text)
        n_para     = len(paragraphs)
        n_sent     = len(sentences)

        score = 0.0
        if n_para >= 2:   score += 0.4
        elif n_para == 1: score += 0.2
        if n_sent >= 4:   score += 0.4
        elif n_sent >= 2: score += 0.2
        
        if text[:1].isupper(): score += 0.2
        return min(1.0, score)

    @staticmethod
    def _score_specificity(text: str) -> float:
        
        signals = 0
        
        signals += min(3, len(re.findall(r"\b\d+(?:\.\d+)?[%₹]?\b", text)))
        
        signals += min(2, len(re.findall(r"(?:₹|inr|lakh|crore)", text, re.IGNORECASE)))
        
        signals += min(2, len(re.findall(r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)+\b", text)))
        return min(1.0, signals / 6.0)

    @staticmethod
    def _score_keyword_coverage(
        text:    str,
        spec:    SectionSpec,
        profile: Optional[Dict[str, Any]],
    ) -> float:
        
        if not spec.emphasis:
            return 0.7  
        text_lower = text.lower()
        emphasis_words = set(re.findall(r"\b[a-z]{4,}\b", spec.emphasis.lower()))
        if not emphasis_words:
            return 0.7
        hits = sum(1 for w in emphasis_words if w in text_lower)
        return min(1.0, hits / max(1, len(emphasis_words)))

    @staticmethod
    def _build_review_suggestions(
        section_qualities: List[SectionQuality],
        hard_violations:   List[str],
        missing_fields:    List[str],
    ) -> List[str]:
        
        suggestions: List[str] = []

        
        for v in hard_violations[:3]:
            suggestions.append(f"[Required] {v}")

        
        weak = sorted(
            [sq for sq in section_qualities if sq.score < 0.55 and sq.word_count > 0],
            key=lambda sq: sq.score,
        )
        for sq in weak[:4]:
            for sug in sq.suggestions[:1]:
                suggestions.append(f"[Quality] {sug}")

        
        for f in missing_fields[:3]:
            suggestions.append(f"[Profile] Add '{f}' to improve proposal specificity.")

        return suggestions[:10]

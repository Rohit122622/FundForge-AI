

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.proposal_generator.exceptions import ReviewError
from backend.proposal_generator.proposal_builder import ProposalDraft
from backend.proposal_generator.template_manager import ProposalTemplate
from backend.proposal_generator.validator import (
    ProposalValidationResult,
    Validator,
)

logger = logging.getLogger("fundforge.proposal_generator.review_engine")






@dataclass
class SectionReview:
    
    key:         str
    title:       str
    score:       float        
    grade:       str          
    word_count:  int
    issues:      List[str]    = field(default_factory=list)
    suggestions: List[str]    = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key":         self.key,
            "title":       self.title,
            "score":       round(self.score, 3),
            "grade":       self.grade,
            "word_count":  self.word_count,
            "issues":      self.issues,
            "suggestions": self.suggestions,
        }


@dataclass
class ReviewReport:
    
    proposal_id:           str
    version:               int
    quality_score:         int
    readiness_band:        str
    section_reviews:       List[SectionReview]   = field(default_factory=list)
    strength_highlights:   List[str]             = field(default_factory=list)
    improvement_areas:     List[str]             = field(default_factory=list)
    actionable_steps:      List[str]             = field(default_factory=list)
    mandatory_check:       Dict[str, bool]       = field(default_factory=dict)
    missing_profile_fields:List[str]             = field(default_factory=list)
    ai_feedback:           Optional[str]         = None
    completeness_pct:      float                 = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id":            self.proposal_id,
            "version":                self.version,
            "quality_score":          self.quality_score,
            "readiness_band":         self.readiness_band,
            "section_reviews":        [sr.to_dict() for sr in self.section_reviews],
            "strength_highlights":    self.strength_highlights,
            "improvement_areas":      self.improvement_areas,
            "actionable_steps":       self.actionable_steps,
            "mandatory_check":        self.mandatory_check,
            "missing_profile_fields": self.missing_profile_fields,
            "ai_feedback":            self.ai_feedback,
            "completeness_pct":       self.completeness_pct,
        }






class ReviewEngine:
    

    def __init__(
        self,
        validator:   Optional[Validator] = None,
        ai_provider: Any = None,
    ) -> None:
        self._validator   = validator or Validator()
        self._ai_provider = ai_provider

    
    def review(
        self,
        draft:          ProposalDraft,
        template:       ProposalTemplate,
        startup_profile:Optional[Dict[str, Any]] = None,
        use_ai:         bool = False,
    ) -> ReviewReport:
        
        try:
            
            val_result: ProposalValidationResult = self._validator.validate_proposal(
                sections = draft.sections,
                template = template,
                profile  = startup_profile,
            )

            
            section_reviews = self._build_section_reviews(val_result, template)

            
            mandatory_check = self._check_mandatory_elements(draft, template)

            
            quality_score = self._compute_quality_score(
                val_result, mandatory_check, draft
            )

            
            readiness_band = self._readiness_band(quality_score, val_result)

            
            strengths = self._extract_strengths(section_reviews)
            improvements = self._extract_improvements(section_reviews)

            
            actions = self._build_actions(
                val_result, mandatory_check, draft, startup_profile or {}
            )

            
            ai_feedback: Optional[str] = None
            if use_ai and self._ai_provider:
                ai_feedback = self._run_ai_review(draft, template)

            report = ReviewReport(
                proposal_id            = draft.proposal_id,
                version                = draft.version,
                quality_score          = quality_score,
                readiness_band         = readiness_band,
                section_reviews        = section_reviews,
                strength_highlights    = strengths,
                improvement_areas      = improvements,
                actionable_steps       = actions,
                mandatory_check        = mandatory_check,
                missing_profile_fields = val_result.missing_fields,
                ai_feedback            = ai_feedback,
                completeness_pct       = draft.completeness_pct,
            )

            logger.info(
                "ReviewReport: proposal=%s v%d score=%d/%s completeness=%.0f%%",
                draft.proposal_id[:8], draft.version,
                quality_score, readiness_band, draft.completeness_pct,
            )
            return report

        except ReviewError:
            raise
        except Exception as exc:
            raise ReviewError(f"Proposal review failed: {exc}") from exc

    
    def _build_section_reviews(
        self,
        val_result: ProposalValidationResult,
        template:   ProposalTemplate,
    ) -> List[SectionReview]:
        
        reviews: List[SectionReview] = []
        for sq in val_result.section_qualities:
            spec  = template.get_section(sq.key)
            title = spec.title if spec else sq.key.replace("_", " ").title()
            reviews.append(SectionReview(
                key        = sq.key,
                title      = title,
                score      = sq.score,
                grade      = sq.grade,
                word_count = sq.word_count,
                issues     = sq.issues,
                suggestions= sq.suggestions,
            ))
        return reviews

    @staticmethod
    def _check_mandatory_elements(
        draft:    ProposalDraft,
        template: ProposalTemplate,
    ) -> Dict[str, bool]:
        
        full_text_lower = draft.full_text_md.lower()
        result: Dict[str, bool] = {}

        for element in template.mandatory_elements:
            
            keywords = re.findall(r"\b[a-z]{4,}\b", element.lower())
            found    = any(kw in full_text_lower for kw in keywords[:3])
            result[element] = found

        return result

    @staticmethod
    def _compute_quality_score(
        val_result:      ProposalValidationResult,
        mandatory_check: Dict[str, bool],
        draft:           ProposalDraft,
    ) -> int:
        
        base = val_result.completeness_score      

        
        if mandatory_check:
            met   = sum(1 for v in mandatory_check.values() if v)
            total = len(mandatory_check)
            mandatory_ratio = met / total
            
            mandatory_adj = round((mandatory_ratio - 0.5) * 20)
        else:
            mandatory_adj = 0

        
        fallback_penalty = len(draft.fallback_sections) * 6

        
        hard_penalty = min(20, len(val_result.hard_violations) * 5)

        
        richness_adj = 0
        word_count = draft.word_count
        if word_count < 1500:
            richness_adj = -15
        elif word_count > 3000:
            richness_adj = 10

        score = base + mandatory_adj - fallback_penalty - hard_penalty + richness_adj
        return min(100, max(0, score))

    @staticmethod
    def _readiness_band(score: int, val_result: ProposalValidationResult) -> str:
        
        if val_result.hard_violations:
            return "Major Work Required"
        if score >= 70:
            return "Ready to Submit"
        if score >= 45:
            return "Needs Revision"
        return "Major Work Required"

    @staticmethod
    def _extract_strengths(section_reviews: List[SectionReview]) -> List[str]:
        
        strong = sorted(
            [sr for sr in section_reviews if sr.score >= 0.70],
            key=lambda sr: -sr.score,
        )[:3]
        return [
            f"{sr.title} ({sr.grade}) — {sr.word_count} words, well-structured."
            for sr in strong
        ]

    @staticmethod
    def _extract_improvements(section_reviews: List[SectionReview]) -> List[str]:
        
        weak = sorted(
            [sr for sr in section_reviews if sr.score < 0.60 and sr.word_count > 0],
            key=lambda sr: sr.score,
        )[:3]
        return [
            f"{sr.title} (Grade {sr.grade}) — " + (sr.issues[0] if sr.issues else "Needs improvement.")
            for sr in weak
        ]

    @staticmethod
    def _build_actions(
        val_result:     ProposalValidationResult,
        mandatory_check:Dict[str, bool],
        draft:          ProposalDraft,
        profile:        Dict[str, Any],
    ) -> List[str]:
        
        actions: List[str] = []

        
        for v in val_result.hard_violations[:2]:
            actions.append(f"[Critical] {v}")

        
        for key in draft.fallback_sections[:3]:
            actions.append(
                f"[Required] Regenerate or manually write the "
                f"'{key.replace('_', ' ').title()}' section — it currently uses a placeholder."
            )

        
        missing_mandatory = [k for k, v in mandatory_check.items() if not v]
        for elem in missing_mandatory[:3]:
            actions.append(f"[Mandatory] Ensure '{elem}' is addressed in the proposal.")

        
        for sug in val_result.review_suggestions[:3]:
            if sug not in actions:
                actions.append(sug)

        
        for f in val_result.missing_fields[:2]:
            actions.append(f"[Profile] Add '{f}' to your startup profile for better specificity.")

        return actions[:10]

    def _run_ai_review(
        self,
        draft:    ProposalDraft,
        template: ProposalTemplate,
    ) -> Optional[str]:
        
        try:
            from backend.ibm.prompt_builder import PromptBuilder
            builder = PromptBuilder()

            review_prompt = (
                f"You are a grant review expert for Indian government funding schemes.\n\n"
                f"Review the following grant proposal for '{draft.grant_name}' by "
                f"'{draft.company_name}'. Provide:\n"
                f"1. Overall quality assessment (1–2 sentences)\n"
                f"2. Top 2 strengths\n"
                f"3. Top 2 areas for improvement\n"
                f"4. One specific actionable recommendation\n\n"
                f"PROPOSAL (first 2000 chars):\n{draft.full_text_md[:2000]}\n\n"
                f"Be concise, specific, and constructive."
            )

            from backend.ibm.foundation_models import GenerationParameters
            params = GenerationParameters(
                max_new_tokens=400, min_new_tokens=50,
                temperature=0.4, top_p=0.9, top_k=30,
            )
            result = self._ai_provider.generate_text(
                prompt=review_prompt, params=params
            )
            return result.text.strip()

        except Exception as exc:
            logger.warning("AI-assisted review failed: %s", exc)
            return None

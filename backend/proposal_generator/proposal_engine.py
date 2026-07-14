

import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Optional

from backend.proposal_generator.export_manager import ExportManager, ExportResult
from backend.proposal_generator.proposal_builder import ProposalBuilder, ProposalDraft
from backend.proposal_generator.review_engine import ReviewEngine, ReviewReport
from backend.proposal_generator.section_generator import (
    GeneratedSection,
    SectionGenerator,
)
from backend.proposal_generator.template_manager import (
    ProposalTemplate,
    TemplateManager,
    get_template_manager,
)
from backend.proposal_generator.validator import Validator
from backend.ibm.prompt_builder import GrantProposalPromptData
from backend.ibm.foundation_models import AIProvider, GenerationParameters

logger = logging.getLogger("fundforge.proposal_generator.proposal_engine")

_ENGINE_VERSION = "1.0.0"






@dataclass
class ProposalRequest:
    
    startup_profile:   Dict[str, Any]
    grant_data:        Dict[str, Any]
    sections:          Optional[List[str]]              = None
    tone:              Optional[str]                    = None
    user_instructions: str                              = ""
    use_rag:           bool                             = True
    use_ai_review:     bool                             = False
    version:           int                              = 1
    proposal_id:       Optional[str]                   = None
    params:            Optional[GenerationParameters]   = None


@dataclass
class ProposalResult:
    
    proposal_id:          str
    version:              int
    draft:                ProposalDraft
    review:               ReviewReport
    sections_generated:   int              = 0
    sections_fallback:    int              = 0
    rag_chunks_used:      int              = 0
    processing_time_ms:   float            = 0.0
    engine_version:       str              = _ENGINE_VERSION
    status:               str              = "complete"

    @property
    def quality_score(self) -> int:
        return self.review.quality_score

    @property
    def readiness_band(self) -> str:
        return self.review.readiness_band

    @property
    def is_ready(self) -> bool:
        return self.review.readiness_band == "Ready to Submit"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id":        self.proposal_id,
            "version":            self.version,
            "status":             self.status,
            "quality_score":      self.quality_score,
            "readiness_band":     self.readiness_band,
            "sections_generated": self.sections_generated,
            "sections_fallback":  self.sections_fallback,
            "rag_chunks_used":    self.rag_chunks_used,
            "processing_time_ms": round(self.processing_time_ms, 1),
            "engine_version":     self.engine_version,
            "draft":              self.draft.to_dict(),
            "review":             self.review.to_dict(),
        }






class ProposalEngine:
    

    ENGINE_VERSION = _ENGINE_VERSION

    def __init__(
        self,
        ai_provider:       AIProvider,
        template_manager:  Optional[TemplateManager]   = None,
        section_generator: Optional[SectionGenerator]  = None,
        proposal_builder:  Optional[ProposalBuilder]   = None,
        review_engine:     Optional[ReviewEngine]      = None,
        export_manager:    Optional[ExportManager]     = None,
        validator:         Optional[Validator]         = None,
        rag_engine:        Any                         = None,
    ) -> None:
        self._ai_provider   = ai_provider
        self._templates     = template_manager  or get_template_manager()
        self._section_gen   = section_generator or SectionGenerator(ai_provider=ai_provider)
        self._builder       = proposal_builder  or ProposalBuilder()
        self._validator     = validator         or Validator()
        self._reviewer      = review_engine     or ReviewEngine(
            validator=self._validator, ai_provider=ai_provider
        )
        self._exporter      = export_manager    or ExportManager()
        self._rag_engine    = rag_engine

        logger.info(
            "ProposalEngine v%s initialised | provider=%s | rag=%s",
            self.ENGINE_VERSION,
            getattr(ai_provider, "provider_name", "unknown"),
            "enabled" if rag_engine else "disabled",
        )

    
    def generate(self, request: ProposalRequest) -> ProposalResult:
        
        start_time  = time.monotonic()
        proposal_id = request.proposal_id or str(uuid.uuid4())

        
        self._validator.validate_request(
            startup_profile = request.startup_profile,
            grant_data      = request.grant_data,
        )

        
        grant_id = (
            request.grant_data.get("id")
            or request.grant_data.get("short_name", "").lower().replace(" ", "_")
            or "default"
        )
        template: ProposalTemplate = self._templates.resolve_for_grant(grant_id)

        
        if request.tone:
            template.tone = request.tone

        
        if request.sections:
            specs = [
                spec for spec in template.sections
                if spec.key in request.sections
            ]
        else:
            specs = list(template.sections)

        
        specs = sorted(specs, key=lambda s: s.order)

        
        prompt_data = self._build_prompt_data(
            startup_profile   = request.startup_profile,
            grant_data        = request.grant_data,
            tone              = template.tone,
            user_instructions = request.user_instructions,
        )

        
        rag_context = ""
        rag_chunks  = 0
        if request.use_rag and self._rag_engine is not None:
            try:
                rag_result = self._rag_engine.retrieve_for_profile(
                    request.startup_profile
                )
                rag_context = rag_result.context_text
                rag_chunks  = rag_result.included_count
                logger.info(
                    "RAG context retrieved: %d chunks for proposal", rag_chunks
                )
            except Exception as exc:
                logger.warning("RAG retrieval failed for proposal: %s", exc)

        
        generated_sections: List[GeneratedSection] = self._section_gen.generate_batch(
            sections    = specs,
            prompt_data = prompt_data,
            rag_context = rag_context,
            params      = request.params,
        )

        
        draft: ProposalDraft = self._builder.build(
            generated_sections = generated_sections,
            template           = template,
            startup_profile    = request.startup_profile,
            grant_data         = request.grant_data,
            proposal_id        = proposal_id,
            version            = request.version,
            user_instructions  = request.user_instructions,
        )

        
        review: ReviewReport = self._reviewer.review(
            draft           = draft,
            template        = template,
            startup_profile = request.startup_profile,
            use_ai          = request.use_ai_review,
        )

        elapsed_ms = (time.monotonic() - start_time) * 1000

        
        if len(draft.fallback_sections) == len(specs):
            status = "failed"
        elif draft.fallback_sections:
            status = "partial"
        else:
            status = "complete"

        result = ProposalResult(
            proposal_id        = proposal_id,
            version            = request.version,
            draft              = draft,
            review             = review,
            sections_generated = len(generated_sections) - len(draft.fallback_sections),
            sections_fallback  = len(draft.fallback_sections),
            rag_chunks_used    = rag_chunks,
            processing_time_ms = elapsed_ms,
            engine_version     = self.ENGINE_VERSION,
            status             = status,
        )

        logger.info(
            "Proposal generation complete: id=%s v%d quality=%d/%s "
            "sections=%d/%d fallbacks=%d rag=%d time=%.0fms",
            proposal_id[:8], request.version,
            review.quality_score, review.readiness_band,
            result.sections_generated, len(specs),
            result.sections_fallback, rag_chunks,
            elapsed_ms,
        )
        return result

    def generate_section(
        self,
        section_key:        str,
        startup_profile:    Dict[str, Any],
        grant_data:         Dict[str, Any],
        user_instructions:  str = "",
        use_rag:            bool = True,
        params:             Optional[GenerationParameters] = None,
    ) -> GeneratedSection:
        
        grant_id = grant_data.get("id", "default")
        template = self._templates.resolve_for_grant(grant_id)
        spec     = template.get_section(section_key)

        if spec is None:
            
            from backend.proposal_generator.template_manager import SectionSpec
            spec = SectionSpec(
                key       = section_key,
                title     = section_key.replace("_", " ").title(),
                prompt_key= section_key,
                order     = 99,
            )

        prompt_data = self._build_prompt_data(
            startup_profile   = startup_profile,
            grant_data        = grant_data,
            tone              = template.tone,
            user_instructions = user_instructions,
        )

        rag_context = ""
        if use_rag and self._rag_engine is not None:
            try:
                rag_result  = self._rag_engine.retrieve_for_profile(startup_profile)
                rag_context = rag_result.context_text
            except Exception as exc:
                logger.warning("RAG retrieval failed for single section: %s", exc)

        return self._section_gen.generate(
            section_key = section_key,
            spec        = spec,
            prompt_data = prompt_data,
            rag_context = rag_context,
            params      = params,
        )

    def stream_section(
        self,
        section_key:        str,
        startup_profile:    Dict[str, Any],
        grant_data:         Dict[str, Any],
        user_instructions:  str = "",
        params:             Optional[GenerationParameters] = None,
    ) -> Iterator[str]:
        
        grant_id = grant_data.get("id", "default")
        template = self._templates.resolve_for_grant(grant_id)
        spec     = template.get_section(section_key)

        if spec is None:
            from backend.proposal_generator.template_manager import SectionSpec
            spec = SectionSpec(
                key=section_key,
                title=section_key.replace("_", " ").title(),
                prompt_key=section_key,
                order=99,
            )

        prompt_data = self._build_prompt_data(
            startup_profile = startup_profile,
            grant_data      = grant_data,
            tone            = template.tone,
            user_instructions=user_instructions,
        )
        return self._section_gen.stream_section(
            section_key = section_key,
            spec        = spec,
            prompt_data = prompt_data,
            params      = params,
        )

    def export(
        self,
        draft:         ProposalDraft,
        format:        str = "markdown",
    ) -> ExportResult:
        
        return self._exporter.export(draft, format=format)

    def get_readiness_report(
        self,
        startup_profile: Dict[str, Any],
    ) -> Dict[str, Any]:
        
        missing = self._validator.detect_missing_fields(startup_profile)
        required_missing = [
            f for f in self._validator._REQUIRED_PROFILE_FIELDS
            if not startup_profile.get(f, "")
        ]
        return {
            "ready":                len(required_missing) == 0,
            "required_missing":     required_missing,
            "advisory_missing":     missing,
            "completeness_hints":   [
                f"Add '{label}' to improve proposal quality."
                for label in missing[:5]
            ],
        }

    
    @staticmethod
    def _build_prompt_data(
        startup_profile:   Dict[str, Any],
        grant_data:        Dict[str, Any],
        tone:              str = "professional",
        user_instructions: str = "",
    ) -> GrantProposalPromptData:
        
        p = startup_profile
        g = grant_data

        
        location_parts = []
        if p.get("city"):         location_parts.append(p["city"])
        if p.get("state_province"): location_parts.append(p["state_province"].replace("_", " ").title())
        location_parts.append("India")
        location = ", ".join(location_parts)

        
        max_award = ""
        if g.get("max_amount_inr"):
            amt = float(g["max_amount_inr"])
            if amt >= 1_00_00_000:
                max_award = f"INR {amt / 1_00_00_000:.1f} Crore"
            else:
                max_award = f"INR {amt / 1_00_000:.0f} Lakh"
        elif g.get("typical_amount_inr"):
            amt = float(g["typical_amount_inr"])
            max_award = f"INR {amt / 1_00_000:.0f} Lakh (typical)"

        return GrantProposalPromptData(
            company_name        = p.get("company_name", ""),
            tagline             = p.get("tagline", ""),
            industry            = (p.get("industry") or p.get("sector", "")).replace("_", " ").title(),
            stage               = p.get("stage", "").replace("_", " ").title(),
            description         = p.get("description", ""),
            problem_statement   = p.get("problem_statement", ""),
            solution_statement  = p.get("solution_statement", ""),
            impact_statement    = p.get("impact_statement", ""),
            team_size           = int(p.get("team_size", 1) or 1),
            founding_year       = p.get("founding_year"),
            location            = location,
            funding_needed      = p.get("funding_needed", ""),
            grant_title         = g.get("name", ""),
            grant_organization  = g.get("administering_body", g.get("organization_name", "")),
            grant_description   = g.get("description", ""),
            grant_requirements  = " | ".join(g.get("eligibility_summary", [])) if isinstance(g.get("eligibility_summary"), list) else g.get("eligibility_criteria", ""),
            grant_deadline      = str(g.get("deadline", "Rolling")) if g.get("deadline") else "Rolling / Continuous",
            max_award           = max_award,
            user_instructions   = user_instructions,
            tone                = tone,
        )






_engine_singleton: Optional[ProposalEngine] = None
_engine_lock = __import__("threading").Lock()


def get_proposal_engine(
    ai_provider:  Optional[AIProvider] = None,
    rag_engine:   Any = None,
    **kwargs: Any,
) -> ProposalEngine:
    
    global _engine_singleton
    with _engine_lock:
        if _engine_singleton is None:
            if ai_provider is None:
                from backend.ibm.foundation_models import get_ai_provider
                ai_provider = get_ai_provider()
            _engine_singleton = ProposalEngine(
                ai_provider = ai_provider,
                rag_engine  = rag_engine,
                **kwargs,
            )
        return _engine_singleton


def reset_proposal_engine() -> None:
    
    global _engine_singleton
    with _engine_lock:
        _engine_singleton = None

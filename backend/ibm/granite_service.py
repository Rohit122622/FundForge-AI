

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional

from backend.ibm.exceptions import AIProviderError
from backend.ibm.foundation_models import (
    AIProvider,
    GenerationParameters,
    GenerationResult,
    get_ai_provider,
)
from backend.ibm.prompt_builder import (
    PromptBuilder,
    GrantProposalPromptData,
    GrantMatchPromptData,
    EligibilityPromptData,
)

logger = logging.getLogger("fundforge.ibm.granite_service")





_DEFAULT_MODEL: str = os.getenv("IBM_GRANITE_MODEL_ID", "ibm/granite-13b-instruct-v2")

_PARAMS_PROPOSAL = GenerationParameters(
    model_id=_DEFAULT_MODEL,
    max_new_tokens=1200,
    min_new_tokens=100,
    temperature=0.7,
    top_p=0.92,
    top_k=50,
    repetition_penalty=1.15,
)

_PARAMS_SCORING = GenerationParameters(
    model_id=_DEFAULT_MODEL,
    max_new_tokens=256,
    min_new_tokens=5,
    temperature=0.1,   
    top_p=0.95,
    top_k=5,
    repetition_penalty=1.1,
)

_PARAMS_SUMMARY = GenerationParameters(
    model_id=_DEFAULT_MODEL,
    max_new_tokens=400,
    min_new_tokens=50,
    temperature=0.4,
    top_p=0.9,
    top_k=30,
    repetition_penalty=1.1,
)

_PARAMS_CHAT = GenerationParameters(
    model_id=_DEFAULT_MODEL,
    max_new_tokens=800,
    min_new_tokens=20,
    temperature=0.6,
    top_p=0.92,
    top_k=50,
    repetition_penalty=1.1,
)






@dataclass
class ProposalSectionResult:
    
    section_name: str
    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    model_id: str = ""


@dataclass
class FullProposalResult:
    
    sections: Dict[str, str] = field(default_factory=dict)
    full_text: str = ""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    model_id: str = ""

    @property
    def word_count(self) -> int:
        return len(self.full_text.split())


@dataclass
class GrantMatchScoreResult:
    
    score: int               
    rationale: str           
    strengths: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)
    recommendation: str = ""
    model_id: str = ""


@dataclass
class EligibilityResult:
    
    is_eligible: bool
    confidence: str          
    summary: str
    met_criteria: List[str] = field(default_factory=list)
    unmet_criteria: List[str] = field(default_factory=list)
    notes: str = ""
    model_id: str = ""






class GraniteService:
    

    def __init__(self, provider: Optional[AIProvider] = None):
        self._provider = provider or get_ai_provider()
        self._builder = PromptBuilder()
        logger.info(
            "GraniteService initialised — provider=%s",
            self._provider.provider_name,
        )

    
    def generate_proposal_section(
        self,
        section_name: str,
        prompt_data: GrantProposalPromptData,
        params: Optional[GenerationParameters] = None,
    ) -> ProposalSectionResult:
        
        prompt = self._builder.build_proposal_section_prompt(
            section_name=section_name,
            data=prompt_data,
        )
        eff_params = params or _PARAMS_PROPOSAL

        logger.info(
            "Generating proposal section: %s | model=%s",
            section_name, eff_params.model_id or _DEFAULT_MODEL,
        )

        result = self._provider.generate_text(prompt=prompt, params=eff_params)

        return ProposalSectionResult(
            section_name=section_name,
            content=result.text.strip(),
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            model_id=result.model_id,
        )

    def generate_full_proposal(
        self,
        prompt_data: GrantProposalPromptData,
        params: Optional[GenerationParameters] = None,
    ) -> FullProposalResult:
        
        section_names = [
            "executive_summary",
            "problem_statement",
            "proposed_solution",
            "impact_statement",
            "budget_narrative",
            "timeline",
            "team_qualifications",
        ]

        full = FullProposalResult(model_id=params.model_id if params else _DEFAULT_MODEL)

        for section in section_names:
            try:
                sec_result = self.generate_proposal_section(
                    section_name=section,
                    prompt_data=prompt_data,
                    params=params,
                )
                full.sections[section] = sec_result.content
                full.total_input_tokens  += sec_result.input_tokens
                full.total_output_tokens += sec_result.output_tokens
            except AIProviderError as exc:
                logger.error(
                    "Failed to generate section '%s': %s", section, exc
                )
                full.sections[section] = ""

        section_labels = {
            "executive_summary":  "Executive Summary",
            "problem_statement":  "Problem Statement",
            "proposed_solution":  "Proposed Solution",
            "impact_statement":   "Impact & Outcomes",
            "budget_narrative":   "Budget Narrative",
            "timeline":           "Project Timeline",
            "team_qualifications":"Team Qualifications",
        }

        parts = []
        for key, label in section_labels.items():
            content = full.sections.get(key, "").strip()
            if content:
                parts.append(f"## {label}\n\n{content}")

        full.full_text = "\n\n".join(parts)
        return full

    def stream_proposal_section(
        self,
        section_name: str,
        prompt_data: GrantProposalPromptData,
        params: Optional[GenerationParameters] = None,
    ) -> Iterator[str]:
        
        prompt = self._builder.build_proposal_section_prompt(
            section_name=section_name,
            data=prompt_data,
        )
        eff_params = params or _PARAMS_PROPOSAL
        return self._provider.generate_text_stream(prompt=prompt, params=eff_params)

    
    def score_grant_match(
        self,
        match_data: GrantMatchPromptData,
        params: Optional[GenerationParameters] = None,
    ) -> GrantMatchScoreResult:
        
        prompt = self._builder.build_grant_match_prompt(data=match_data)
        eff_params = params or _PARAMS_SCORING

        logger.info("Scoring grant match: model=%s", eff_params.model_id or _DEFAULT_MODEL)

        result = self._provider.generate_text(prompt=prompt, params=eff_params)
        return self._parse_match_score(result)

    
    def summarise_grant(
        self,
        grant_data: Dict[str, Any],
        params: Optional[GenerationParameters] = None,
    ) -> str:
        
        prompt = self._builder.build_grant_summary_prompt(grant_data)
        eff_params = params or _PARAMS_SUMMARY
        result = self._provider.generate_text(prompt=prompt, params=eff_params)
        return result.text.strip()

    
    def assess_eligibility(
        self,
        elig_data: EligibilityPromptData,
        params: Optional[GenerationParameters] = None,
    ) -> EligibilityResult:
        
        prompt = self._builder.build_eligibility_prompt(data=elig_data)
        eff_params = params or _PARAMS_SCORING
        result = self._provider.generate_text(prompt=prompt, params=eff_params)
        return self._parse_eligibility(result)

    
    def chat(
        self,
        message: str,
        system_context: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        params: Optional[GenerationParameters] = None,
    ) -> str:
        
        prompt = self._builder.build_chat_prompt(
            message=message,
            system_context=system_context,
            history=history or [],
        )
        eff_params = params or _PARAMS_CHAT
        result = self._provider.generate_text(prompt=prompt, params=eff_params)
        return result.text.strip()

    def answer_question(
        self,
        question: str,
        context: str,
        params: Optional[GenerationParameters] = None,
    ) -> str:
        
        prompt = self._builder.build_qa_prompt(question=question, context=context)
        eff_params = params or _PARAMS_CHAT
        result = self._provider.generate_text(prompt=prompt, params=eff_params)
        return result.text.strip()

    
    @staticmethod
    def _parse_match_score(result: GenerationResult) -> GrantMatchScoreResult:
        
        text = result.text.strip()

        def _extract(pattern: str, default: str = "") -> str:
            m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            return m.group(1).strip() if m else default

        raw_score = _extract(r"SCORE[:\s]+(\d{1,3})", "0")
        try:
            score = max(0, min(100, int(raw_score)))
        except ValueError:
            score = 0

        strengths_raw = _extract(r"STRENGTHS[:\s]+(.+)")
        gaps_raw      = _extract(r"GAPS[:\s]+(.+)")

        return GrantMatchScoreResult(
            score=score,
            rationale=_extract(r"RATIONALE[:\s]+(.+)"),
            strengths=[s.strip() for s in strengths_raw.split(",") if s.strip()],
            gaps=[g.strip() for g in gaps_raw.split(",") if g.strip()],
            recommendation=_extract(r"RECOMMENDATION[:\s]+(.+)"),
            model_id=result.model_id,
        )

    @staticmethod
    def _parse_eligibility(result: GenerationResult) -> EligibilityResult:
        
        text = result.text.strip()

        def _extract(pattern: str, default: str = "") -> str:
            m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            return m.group(1).strip() if m else default

        eligible_raw = _extract(r"ELIGIBLE[:\s]+(YES|NO)", "NO")
        confidence   = _extract(r"CONFIDENCE[:\s]+(HIGH|MEDIUM|LOW)", "low").lower()
        met_raw      = _extract(r"MET[:\s]+(.+)")
        unmet_raw    = _extract(r"UNMET[:\s]+(.+)")

        return EligibilityResult(
            is_eligible=eligible_raw.upper() == "YES",
            confidence=confidence,
            summary=_extract(r"SUMMARY[:\s]+(.+)"),
            met_criteria=[c.strip() for c in met_raw.split(",") if c.strip()],
            unmet_criteria=[c.strip() for c in unmet_raw.split(",") if c.strip()],
            notes=_extract(r"NOTES[:\s]+(.+)"),
            model_id=result.model_id,
        )






_service_singleton: Optional[GraniteService] = None
_service_lock = __import__("threading").Lock()


def get_granite_service(provider: Optional[AIProvider] = None) -> GraniteService:
    
    global _service_singleton
    with _service_lock:
        if _service_singleton is None:
            _service_singleton = GraniteService(provider=provider)
        return _service_singleton


def reset_granite_service() -> None:
    
    global _service_singleton
    with _service_lock:
        _service_singleton = None

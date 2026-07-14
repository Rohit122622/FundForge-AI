

import logging
import textwrap
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("fundforge.ibm.prompt_builder")





_SYS_OPEN  = "<|system|>"
_SYS_CLOSE = "<|/system|>"
_USER_OPEN  = "<|user|>"
_USER_CLOSE = "<|/user|>"
_ASST_OPEN  = "<|assistant|>"

_SYSTEM_PERSONA = (
    "You are FundForge AI, an expert grant writing assistant and funding "
    "strategist. You help startups and small businesses discover, evaluate, "
    "and apply for grants and funding opportunities. You are precise, "
    "professional, and evidence-based. You do not invent information — "
    "if you are uncertain, you say so."
)






@dataclass
class GrantProposalPromptData:
    
    company_name: str = ""
    tagline: str = ""
    industry: str = ""
    stage: str = ""
    description: str = ""
    problem_statement: str = ""
    solution_statement: str = ""
    impact_statement: str = ""
    team_size: int = 1
    founding_year: Optional[int] = None
    location: str = ""
    funding_needed: str = ""
    grant_title: str = ""
    grant_organization: str = ""
    grant_description: str = ""
    grant_requirements: str = ""
    grant_deadline: str = ""
    max_award: str = ""
    user_instructions: str = ""
    tone: str = "professional"

    def company_context(self) -> str:
        
        parts = [f"Company: {self.company_name}"]
        if self.tagline:
            parts.append(f"Tagline: {self.tagline}")
        if self.industry:
            parts.append(f"Industry: {self.industry}")
        if self.stage:
            parts.append(f"Stage: {self.stage}")
        if self.location:
            parts.append(f"Location: {self.location}")
        if self.team_size:
            parts.append(f"Team Size: {self.team_size}")
        if self.founding_year:
            parts.append(f"Founded: {self.founding_year}")
        if self.funding_needed:
            parts.append(f"Funding Needed: {self.funding_needed}")
        if self.description:
            parts.append(f"\nCompany Description:\n{self.description}")
        if self.problem_statement:
            parts.append(f"\nProblem Statement:\n{self.problem_statement}")
        if self.solution_statement:
            parts.append(f"\nSolution:\n{self.solution_statement}")
        if self.impact_statement:
            parts.append(f"\nImpact:\n{self.impact_statement}")
        return "\n".join(parts)

    def grant_context(self) -> str:
        
        parts = [f"Grant: {self.grant_title}"]
        if self.grant_organization:
            parts.append(f"Organisation: {self.grant_organization}")
        if self.max_award:
            parts.append(f"Maximum Award: {self.max_award}")
        if self.grant_deadline:
            parts.append(f"Deadline: {self.grant_deadline}")
        if self.grant_description:
            parts.append(f"\nGrant Description:\n{self.grant_description}")
        if self.grant_requirements:
            parts.append(f"\nApplication Requirements:\n{self.grant_requirements}")
        return "\n".join(parts)


@dataclass
class GrantMatchPromptData:
    
    company_name: str = ""
    company_description: str = ""
    industry: str = ""
    stage: str = ""
    location: str = ""
    team_size: int = 1
    funding_needed: str = ""
    grant_title: str = ""
    grant_description: str = ""
    grant_eligibility: str = ""
    grant_sector: str = ""
    grant_type: str = ""
    grant_country: str = ""
    max_award: str = ""


@dataclass
class EligibilityPromptData:
    
    company_name: str = ""
    company_description: str = ""
    industry: str = ""
    stage: str = ""
    location: str = ""
    country: str = ""
    team_size: int = 1
    founding_year: Optional[int] = None
    grant_title: str = ""
    grant_eligibility_criteria: str = ""
    grant_requirements: str = ""
    grant_country: str = ""
    grant_sector: str = ""






class PromptBuilder:
    

    
    _SECTION_INSTRUCTIONS: Dict[str, str] = {
        "executive_summary": (
            "Write a compelling Executive Summary section and a concluding Conclusion section. "
            "Your output must start with a '### Executive Summary' heading containing a clear, "
            "highly professional overview of the company, mission, problem, and value proposition. "
            "Then, end with a '### Conclusion' heading synthesizing the proposal ask and long-term vision. "
            "Use realistic numbers and professional business formatting."
        ),
        "problem_statement": (
            "Write a detailed Problem Statement and Market Analysis. "
            "Start with a '### Problem Statement' heading detailing the urgent pain point, target demographic, and "
            "limitations of current market alternatives. Then, write a '### Market Analysis' heading including "
            "concrete market sizing metrics (e.g. realistic Indian TAM/SAM/SOM numbers in INR, market growth rate). "
            "Avoid repetitions."
        ),
        "proposed_solution": (
            "Write the Solution and Innovation sections. "
            "Start with a '### Solution' heading describing the technical product or service workflow and "
            "commercialization strategy. Then, write a '### Innovation' heading detailing the unique proprietary "
            "technology stack, technical breakthrough, and patent/IP status."
        ),
        "impact_statement": (
            "Write the Expected Impact and Risk Mitigation sections. "
            "Start with a '### Expected Impact' heading quantifying the social, economic, or environmental outcomes "
            "expected in the Indian ecosystem with realistic target metrics. Then, write a '### Risk Mitigation' heading "
            "detailing technical, operational, and financial risks and specific mitigation countermeasures."
        ),
        "budget_narrative": (
            "Write a detailed Budget Utilization section. "
            "Start with a '### Budget Utilization' heading. You must include a markdown table justifying the fund allocation "
            "across key areas like R&D, equipment, personnel, marketing, and operations. Use realistic INR amounts matching the "
            "grant target ceiling."
        ),
        "timeline": (
            "Write the Implementation Plan and Timeline. "
            "Start with a '### Implementation Plan' heading explaining the operational roadmap. "
            "Then, write a '### Timeline' heading detailing phased milestone quarters (e.g. Phase 1 (M1-M3): R&D, Phase 2 (M4-M6): PoC, etc.) "
            "with realistic deliverables."
        ),
        "team_qualifications": (
            "Write a detailed Team Qualifications and Overview section. "
            "Start with a '### Team Overview' heading. Introduce key founders, their credentials, domain advisors, and "
            "organizational partners. Show why this team is exceptionally qualified to execute the project successfully."
        ),
    }

    def build_proposal_section_prompt(
        self,
        section_name: str,
        data: GrantProposalPromptData,
    ) -> str:
        
        instruction = self._SECTION_INSTRUCTIONS.get(section_name)
        if not instruction:
            raise ValueError(
                f"Unknown section '{section_name}'. "
                f"Valid sections: {list(self._SECTION_INSTRUCTIONS.keys())}"
            )

        tone_note = f"Write in a {data.tone} tone." if data.tone else ""
        user_note = (
            f"\nAdditional instructions from the applicant:\n{data.user_instructions}"
            if data.user_instructions else ""
        )

        user_block = textwrap.dedent(f"""
            You are helping write a grant proposal for the following organisation.

            --- APPLICANT CONTEXT ---
            {data.company_context()}

            --- GRANT CONTEXT ---
            {data.grant_context()}

            --- YOUR TASK ---
            {instruction}
            {tone_note}
            {user_note}

            Write only the section content. Do not include section headings,
            preamble, or explanatory text about what you are doing.
            Begin writing the section directly.
        """).strip()

        return self._format_instruction_prompt(system=_SYSTEM_PERSONA, user=user_block)

    
    def build_grant_match_prompt(self, data: GrantMatchPromptData) -> str:
        
        user_block = textwrap.dedent(f"""
            Evaluate how well the following startup matches this grant opportunity.
            Respond ONLY using the structured format below. Be precise and evidence-based.

            --- STARTUP ---
            Company: {data.company_name}
            Industry: {data.industry}
            Stage: {data.stage}
            Location: {data.location}
            Team Size: {data.team_size}
            Funding Needed: {data.funding_needed}
            Description: {data.company_description}

            --- GRANT ---
            Title: {data.grant_title}
            Organisation Sector: {data.grant_sector}
            Type: {data.grant_type}
            Country: {data.grant_country}
            Maximum Award: {data.max_award}
            Description: {data.grant_description}
            Eligibility: {data.grant_eligibility}

            --- REQUIRED OUTPUT FORMAT (use exactly these labels) ---
            SCORE: [integer 0-100]
            RATIONALE: [one sentence explaining the score]
            STRENGTHS: [comma-separated list of matching factors]
            GAPS: [comma-separated list of mismatches or missing criteria]
            RECOMMENDATION: [one sentence: apply now / research further / skip]
        """).strip()

        return self._format_instruction_prompt(system=_SYSTEM_PERSONA, user=user_block)

    
    def build_eligibility_prompt(self, data: EligibilityPromptData) -> str:
        
        user_block = textwrap.dedent(f"""
            Assess whether the following startup is eligible for this grant.
            Review each eligibility criterion carefully against the startup's profile.
            Respond ONLY using the structured format below.

            --- STARTUP ---
            Company: {data.company_name}
            Industry: {data.industry}
            Stage: {data.stage}
            Country: {data.country}
            Team Size: {data.team_size}
            Founded: {data.founding_year or 'Unknown'}
            Description: {data.company_description}

            --- GRANT ---
            Title: {data.grant_title}
            Country: {data.grant_country}
            Sector: {data.grant_sector}
            Eligibility Criteria:
            {data.grant_eligibility_criteria}
            Application Requirements:
            {data.grant_requirements}

            --- REQUIRED OUTPUT FORMAT ---
            ELIGIBLE: [YES or NO]
            CONFIDENCE: [HIGH, MEDIUM, or LOW]
            SUMMARY: [one sentence overall assessment]
            MET: [comma-separated list of met criteria]
            UNMET: [comma-separated list of unmet or unclear criteria]
            NOTES: [any important caveats or recommendations]
        """).strip()

        return self._format_instruction_prompt(system=_SYSTEM_PERSONA, user=user_block)

    
    def build_grant_summary_prompt(self, grant_data: Dict[str, Any]) -> str:
        
        title  = grant_data.get("title", "")
        org    = grant_data.get("organization_name", "")
        desc   = grant_data.get("description", "")
        elig   = grant_data.get("eligibility_criteria", "")
        amount = grant_data.get("max_funding_amount") or grant_data.get("typical_award_amount") or ""
        sector = grant_data.get("sector", "")

        user_block = textwrap.dedent(f"""
            Write a concise, informative one-paragraph summary (4–6 sentences) of
            the following grant opportunity. The summary should help a startup founder
            quickly understand: what the grant is for, who can apply, how much
            funding is available, and what the key requirements are.

            Title: {title}
            Organisation: {org}
            Sector: {sector}
            Maximum Award: {amount}
            Description: {desc}
            Eligibility: {elig}

            Write only the summary paragraph. No headings or bullet points.
        """).strip()

        return self._format_instruction_prompt(system=_SYSTEM_PERSONA, user=user_block)

    
    def build_chat_prompt(
        self,
        message: str,
        system_context: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        
        system = _SYSTEM_PERSONA
        if system_context:
            system = f"{system}\n\nContext:\n{system_context}"

        lines = [f"{_SYS_OPEN}\n{system}\n{_SYS_CLOSE}"]

        for turn in (history or []):
            role    = turn.get("role", "user").lower()
            content = turn.get("content", "").strip()
            if not content:
                continue
            if role == "assistant":
                lines.append(f"{_ASST_OPEN}\n{content}")
            else:
                lines.append(f"{_USER_OPEN}\n{content}\n{_USER_CLOSE}")

        lines.append(f"{_USER_OPEN}\n{message}\n{_USER_CLOSE}")
        lines.append(_ASST_OPEN)

        return "\n".join(lines)

    def build_qa_prompt(self, question: str, context: str) -> str:
        
        user_block = textwrap.dedent(f"""
            Answer the following question using the provided context.
            If the question is about a specific grant or document, use ONLY the information in the context.
            If the question is a general startup, business, or funding question, you may answer it using your general knowledge even if the answer is absent from the context.
            If you do not know the answer at all, say "I don't have enough information to answer that."

            --- CONTEXT ---
            {context}

            --- QUESTION ---
            {question}

            Provide a clear, concise answer. Cite relevant details from the context if applicable.
        """).strip()

        return self._format_instruction_prompt(system=_SYSTEM_PERSONA, user=user_block)

    def build_embedding_input(self, text: str, max_chars: int = 8000) -> str:
        
        cleaned = " ".join(text.split())  
        if len(cleaned) > max_chars:
            cleaned = cleaned[:max_chars]
            logger.debug(
                "Embedding input truncated to %d chars.", max_chars
            )
        return cleaned

    
    @staticmethod
    def _format_instruction_prompt(system: str, user: str) -> str:
        
        return (
            f"{_SYS_OPEN}\n{system}\n{_SYS_CLOSE}\n"
            f"{_USER_OPEN}\n{user}\n{_USER_CLOSE}\n"
            f"{_ASST_OPEN}"
        )

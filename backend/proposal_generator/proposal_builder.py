

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List

from backend.proposal_generator.section_generator import GeneratedSection
from backend.proposal_generator.template_manager import ProposalTemplate
from backend.proposal_generator.exceptions import ProposalBuildError

logger = logging.getLogger("fundforge.proposal_generator.proposal_builder")






@dataclass
class ProposalDraft:
    
    proposal_id:         str
    version:             int
    company_name:        str
    grant_name:          str
    grant_id:            str
    template_id:         str
    tone:                str
    sections:            Dict[str, str]   = field(default_factory=dict)
    section_order:       List[str]        = field(default_factory=list)
    full_text_md:        str              = ""
    full_text_plain:     str              = ""
    word_count:          int              = 0
    total_input_tokens:  int              = 0
    total_output_tokens: int              = 0
    fallback_sections:   List[str]        = field(default_factory=list)
    generated_at:        datetime         = field(default_factory=lambda: datetime.utcnow())
    user_instructions:   str              = ""
    industry:            str              = ""
    stage:               str              = ""
    location:            str              = ""
    website:             str              = ""
    founding_year:       str              = ""
    team_size:           str              = ""

    @property
    def has_fallbacks(self) -> bool:
        
        return len(self.fallback_sections) > 0

    @property
    def is_complete(self) -> bool:
        
        return bool(self.sections) and all(v.strip() for v in self.sections.values())

    @property
    def completeness_pct(self) -> float:
        
        if not self.sections:
            return 0.0
        filled = sum(1 for v in self.sections.values() if v.strip())
        return round(100.0 * filled / len(self.sections), 1)

    def get_section(self, key: str) -> str:
        
        return self.sections.get(key, "")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id":         self.proposal_id,
            "version":             self.version,
            "company_name":        self.company_name,
            "grant_name":          self.grant_name,
            "grant_id":            self.grant_id,
            "template_id":         self.template_id,
            "tone":                self.tone,
            "sections":            self.sections,
            "section_order":       self.section_order,
            "full_text_md":        self.full_text_md,
            "word_count":          self.word_count,
            "total_input_tokens":  self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "fallback_sections":   self.fallback_sections,
            "generated_at":        self.generated_at.isoformat(),
            "has_fallbacks":       self.has_fallbacks,
            "completeness_pct":    self.completeness_pct,
        }

    def to_model_dict(self) -> Dict[str, Any]:
        
        return {
            "executive_summary":  self.sections.get("executive_summary", ""),
            "problem_statement":  self.sections.get("problem_statement", ""),
            "proposed_solution":  self.sections.get("proposed_solution", ""),
            "impact_statement":   self.sections.get("impact_statement", ""),
            "budget_narrative":   self.sections.get("budget_narrative", ""),
            "timeline":           self.sections.get("timeline", ""),
            "team_qualifications":self.sections.get("team_qualifications", ""),
            "full_text":          self.full_text_md,
            "quality_score":      None,  
            "model_id":           None,  
            "version":            self.version,
            "tone":               self.tone,
        }


def parse_sections_from_markdown(markdown_text: str) -> dict:
    if not markdown_text:
        return {}
    sections = {}
    current_key = None
    current_content = []
    
    header_mapping = {
        "executive summary": "executive_summary",
        "problem statement": "problem_statement",
        "proposed solution": "proposed_solution",
        "scientific solution": "proposed_solution",
        "technology solution": "proposed_solution",
        "agri-tech solution": "proposed_solution",
        "innovation concept": "proposed_solution",
        "solution": "proposed_solution",
        "innovation & technology": "innovation_technology",
        "innovation & ip": "innovation_technology",
        "innovation & tech stack": "innovation_technology",
        "technology details": "innovation_technology",
        "innovation": "innovation_technology",
        "market opportunity": "market_opportunity",
        "market analysis": "market_opportunity",
        "competitive advantage": "competitive_advantage",
        "implementation plan": "implementation_plan",
        "budget utilisation": "budget_narrative",
        "budget & milestones": "budget_narrative",
        "poc budget": "budget_narrative",
        "budget": "budget_narrative",
        "financial plan": "financial_plan",
        "financial projections": "financial_plan",
        "team overview": "team_qualifications",
        "team & institutional support": "team_qualifications",
        "innovator profile": "team_qualifications",
        "team qualifications": "team_qualifications",
        "key performance indicators": "kpis",
        "kpis": "kpis",
        "risk analysis & mitigation": "risk_mitigation",
        "expected impact": "impact_statement",
        "expected outcomes and metrics": "impact_statement",
        "expected outcomes": "impact_statement",
        "impact": "impact_statement",
        "implementation timeline": "timeline",
        "research timeline": "timeline",
        "product roadmap": "timeline",
        "timeline": "timeline",
        "conclusion": "conclusion",
        "sustainability plan": "sustainability",
        "sustainability": "sustainability"
    }

    lines = markdown_text.split("\n")
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## ") or stripped.startswith("### "):
            title = stripped.lstrip("#").strip().lower()
            key = header_mapping.get(title)
            if not key:
                for k, v in header_mapping.items():
                    if k in title or title in k:
                        key = v
                        break
            
            if key:
                if current_key:
                    sections[current_key] = "\n".join(current_content).strip()
                current_key = key
                current_content = []
            else:
                if current_key:
                    current_content.append(line)
        elif stripped.startswith("# ") and not current_key:
            continue
        else:
            if current_key:
                current_content.append(line)
                
    if current_key:
        sections[current_key] = "\n".join(current_content).strip()
        
    return sections






class ProposalBuilder:
    

    
    _HEADING_LEVEL: Dict[str, str] = {
        "executive_summary": "##",
        "problem_statement": "##",
        "proposed_solution": "##",
        "innovation_technology": "##",
        "market_opportunity": "##",
        "competitive_advantage": "##",
        "implementation_plan": "##",
        "budget_narrative": "##",
        "financial_plan": "##",
        "kpis": "##",
        "risk_mitigation": "##",
        "impact_statement": "##",
        "timeline": "##",
        "conclusion": "##",
    }

    def build(
        self,
        generated_sections: List[GeneratedSection],
        template:           ProposalTemplate,
        startup_profile:    Dict[str, Any],
        grant_data:         Dict[str, Any],
        proposal_id:        str,
        version:            int = 1,
        user_instructions:  str = "",
    ) -> ProposalDraft:
        
        try:
            company_name = startup_profile.get("company_name", "Startup")
            grant_name   = grant_data.get("name") or grant_data.get("short_name", "Grant")

            
            sections:         Dict[str, str] = {}
            fallback_sections: List[str]     = []
            total_input  = 0
            total_output = 0

            for gs in generated_sections:
                sections[gs.key]  = gs.content
                total_input      += gs.input_tokens
                total_output     += gs.output_tokens
                if gs.fallback_used:
                    fallback_sections.append(gs.key)

            
            section_order = [
                spec.key for spec in sorted(template.sections, key=lambda s: s.order)
                if spec.key in sections
            ]

            
            full_text_md    = self._format_markdown(
                section_order, sections, template, company_name, grant_name, version
            )
            full_text_plain = self._format_plain(
                section_order, sections, template, company_name, grant_name
            )
            word_count = sum(len(v.split()) for v in sections.values())

            draft = ProposalDraft(
                proposal_id         = proposal_id,
                version             = version,
                company_name        = company_name,
                grant_name          = grant_name,
                grant_id            = grant_data.get("id", ""),
                template_id         = template.template_id,
                tone                = template.tone,
                sections            = sections,
                section_order       = section_order,
                full_text_md        = full_text_md,
                full_text_plain     = full_text_plain,
                word_count          = word_count,
                total_input_tokens  = total_input,
                total_output_tokens = total_output,
                fallback_sections   = fallback_sections,
                user_instructions   = user_instructions,
            )

            logger.info(
                "ProposalDraft assembled: company=%s grant=%s v%d "
                "sections=%d words=%d fallbacks=%d",
                company_name, grant_name, version,
                len(sections), word_count, len(fallback_sections),
            )
            return draft

        except Exception as exc:
            raise ProposalBuildError(
                f"Proposal assembly failed: {exc}"
            ) from exc

    
    def _format_markdown(
        self,
        section_order: List[str],
        sections:      Dict[str, str],
        template:      ProposalTemplate,
        company_name:  str,
        grant_name:    str,
        version:       int,
    ) -> str:
        
        lines: List[str] = []

        
        lines.append(f"# Grant Proposal")
        lines.append(f"")
        lines.append(f"**Applicant:** {company_name}  ")
        lines.append(f"**Grant:** {grant_name}  ")
        lines.append(f"**Administering Body:** {template.grant_body}  ")
        lines.append(f"**Version:** {version}  ")
        lines.append(f"**Date:** {date.today().strftime('%d %B %Y')}  ")
        lines.append(f"")

        if template.cover_note:
            lines.append(f"*{template.cover_note}*")
            lines.append(f"")

        lines.append("---")
        lines.append("")

        
        for key in section_order:
            content = sections.get(key, "").strip()
            if not content:
                continue
            spec = template.get_section(key)
            title = spec.title if spec else key.replace("_", " ").title()
            heading = self._HEADING_LEVEL.get(key, "##")
            lines.append(f"{heading} {title}")
            lines.append("")
            lines.append(content)
            lines.append("")

        return "\n".join(lines)

    def _format_plain(
        self,
        section_order: List[str],
        sections:      Dict[str, str],
        template:      ProposalTemplate,
        company_name:  str,
        grant_name:    str,
    ) -> str:
        
        lines: List[str] = []
        lines.append("GRANT PROPOSAL")
        lines.append("=" * 60)
        lines.append(f"Applicant : {company_name}")
        lines.append(f"Grant     : {grant_name}")
        lines.append(f"Date      : {date.today().strftime('%d %B %Y')}")
        lines.append("=" * 60)
        lines.append("")

        for key in section_order:
            content = sections.get(key, "").strip()
            if not content:
                continue
            spec  = template.get_section(key)
            title = spec.title if spec else key.replace("_", " ").title()
            lines.append(title.upper())
            lines.append("-" * len(title))
            lines.append(content)
            lines.append("")

        return "\n".join(lines)

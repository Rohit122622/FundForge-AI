

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.proposal_generator.exceptions import TemplateNotFoundError

logger = logging.getLogger("fundforge.proposal_generator.template_manager")






@dataclass
class SectionSpec:
    
    key:        str
    title:      str
    prompt_key: str
    required:   bool = True
    min_words:  int  = 150
    max_words:  int  = 400
    emphasis:   str  = ""
    order:      int  = 0






@dataclass
class ProposalTemplate:
    
    template_id:          str
    name:                 str
    grant_body:           str                    = ""
    sections:             List[SectionSpec]       = field(default_factory=list)
    tone:                 str                     = "professional"
    cover_note:           str                     = ""
    mandatory_elements:   List[str]               = field(default_factory=list)
    custom_instructions:  str                     = ""
    max_total_words:      int                     = 4000

    @property
    def section_keys(self) -> List[str]:
        return [s.key for s in self.sections]

    @property
    def required_sections(self) -> List[SectionSpec]:
        return [s for s in self.sections if s.required]

    def get_section(self, key: str) -> Optional[SectionSpec]:
        
        return next((s for s in self.sections if s.key == key), None)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id":         self.template_id,
            "name":                self.name,
            "grant_body":          self.grant_body,
            "tone":                self.tone,
            "max_total_words":     self.max_total_words,
            "section_count":       len(self.sections),
            "required_sections":   [s.key for s in self.required_sections],
            "mandatory_elements":  self.mandatory_elements,
        }






def _s(
    key: str,
    title: str,
    prompt_key: str,
    order: int,
    emphasis: str = "",
    min_words: int = 150,
    max_words: int = 400,
    required: bool = True,
) -> SectionSpec:
    return SectionSpec(
        key=key, title=title, prompt_key=prompt_key, order=order,
        emphasis=emphasis, min_words=min_words, max_words=max_words, required=required,
    )



_STANDARD_SECTIONS: List[SectionSpec] = [
    _s("executive_summary",    "Executive Summary",          "executive_summary",    1,
       "Provide a compelling 2–3 paragraph overview of the company, problem, solution, and ask.", 150, 350),
    _s("problem_statement",    "Problem Statement",          "problem_statement",    2,
       "Articulate the Indian market problem with data and urgency.", 200, 400),
    _s("proposed_solution",    "Proposed Solution",          "proposed_solution",    3,
       "Describe the product/service, its innovation, and go-to-market approach.", 200, 400),
    _s("innovation_technology","Innovation & Technology",     "innovation_technology",4,
       "Detail the core technology stack, IP/patents, and technical differentiation.", 150, 350),
    _s("market_opportunity",   "Market Opportunity",          "market_opportunity",   5,
       "Quantify the TAM/SAM/SOM for the Indian market with credible data points.", 150, 300),
    _s("competitive_advantage","Competitive Advantage",       "competitive_advantage",6,
       "Explain your competitive moat, pricing, and technical edge in India.", 150, 300),
    _s("implementation_plan",  "Implementation Plan",         "implementation_plan",  7,
       "Detail your product design, prototyping phases, and testing strategies.", 150, 350),
    _s("budget_narrative",     "Budget Utilisation",          "budget_narrative",     8,
       "Justify grant fund allocation across people, tech, operations, and overhead.", 150, 350),
    _s("financial_plan",       "Financial Projections",       "financial_plan",       9,
       "Present a 3-year revenue/expense forecast and funding utilisation plan.", 150, 350),
    _s("kpis",                 "Key Performance Indicators",  "kpis",                 10,
       "Detail specific milestones, user growth, and technical KPIs.", 150, 300),
    _s("risk_mitigation",      "Risk Analysis & Mitigation",  "risk_mitigation",      11,
       "Outline technical, market, regulatory risks and mitigation plans.", 150, 300),
    _s("impact_statement",     "Expected Impact",             "impact_statement",     12,
       "Quantify social, economic, and environmental outcomes for India.", 150, 300),
    _s("timeline",             "Implementation Timeline",     "timeline",             13,
       "Provide a phased milestone timeline across the grant period.", 150, 300),
    _s("conclusion",           "Conclusion",                  "conclusion",           14,
       "Summarise the application value proposition and final pitch.", 150, 300),
]






def _build_registry() -> Dict[str, ProposalTemplate]:
    

    reg: Dict[str, ProposalTemplate] = {}

    
    reg["default"] = ProposalTemplate(
        template_id="default",
        name="Generic Indian Grant Proposal",
        grant_body="Various Indian Government Bodies",
        sections=list(_STANDARD_SECTIONS),
        tone="professional",
        cover_note=(
            "This proposal is submitted in response to the listed Indian startup "
            "funding scheme. All information is accurate as of the submission date."
        ),
        mandatory_elements=[
            "DPIIT recognition status",
            "Team composition and credentials",
            "Use of grant funds breakdown",
            "Expected outcomes and metrics",
        ],
        max_total_words=4500,
    )

    
    reg["sisfs"] = ProposalTemplate(
        template_id="sisfs",
        name="Startup India Seed Fund Scheme (SISFS)",
        grant_body="DPIIT, Ministry of Commerce & Industry",
        sections=list(_STANDARD_SECTIONS),
        tone="professional",
        mandatory_elements=[
            "DPIIT recognition certificate reference",
            "Incubator name and affiliation",
            "Funding tranches and milestones",
            "Prototype completion plan",
        ],
        custom_instructions=(
            "This is a DPIIT Seed Fund application. Emphasise DPIIT recognition, "
            "incubator support, and proof-of-concept milestones. Keep each section "
            "concise and evidence-based. Avoid buzzwords."
        ),
        max_total_words=3000,
    )

    
    reg["birac_big"] = ProposalTemplate(
        template_id="birac_big",
        name="BIRAC Biotechnology Ignition Grant (BIG)",
        grant_body="BIRAC — Biotechnology Industry Research Assistance Council",
        sections=list(_STANDARD_SECTIONS),
        tone="technical",
        mandatory_elements=[
            "Scientific rationale and hypothesis",
            "BIRAC-recognised incubator or BIONEST affiliation",
            "18-month research plan",
            "Translational pathway post-PoC",
        ],
        custom_instructions=(
            "This is a BIRAC BIG application for biotechnology research. Use scientific "
            "language appropriate for a government research council review committee. "
            "Clearly state the hypothesis, experimental design, and translational value."
        ),
        max_total_words=4000,
    )

    
    reg["tide_2"] = ProposalTemplate(
        template_id="tide_2",
        name="TIDE 2.0 — Technology Incubation & Development of Entrepreneurs",
        grant_body="MeitY — Ministry of Electronics and Information Technology",
        sections=list(_STANDARD_SECTIONS),
        tone="technical",
        mandatory_elements=[
            "ICT / technology focus (AI, IoT, Blockchain, AR/VR)",
            "MeitY TIC affiliation",
            "Product demo milestone plan",
            "Digital India alignment statement",
        ],
        custom_instructions=(
            "This is a MeitY TIDE 2.0 application. Emphasise the ICT innovation, "
            "alignment with Digital India goals, and the MeitY Technology Incubation "
            "Centre involvement. Use clear technical language."
        ),
        max_total_words=3500,
    )

    
    reg["rkvy_raftaar"] = ProposalTemplate(
        template_id="rkvy_raftaar",
        name="RKVY-RAFTAAR Agri-Business Incubation Programme",
        grant_body="Ministry of Agriculture & Farmers Welfare / ICAR",
        sections=list(_STANDARD_SECTIONS),
        tone="narrative",
        mandatory_elements=[
            "Alignment with Indian agriculture and rural economy",
            "Farmer / FPO beneficiary statement",
            "R-BI incubator affiliation",
            "Post-incubation revenue plan",
        ],
        custom_instructions=(
            "This is an RKVY-RAFTAAR agri-business incubation application. Write in a "
            "compelling, narrative style. Centre the proposal around farmer benefit "
            "and rural India impact. Use INR amounts and Indian agriculture data."
        ),
        max_total_words=3500,
    )

    
    reg["agrisure"] = ProposalTemplate(
        template_id="agrisure",
        name="AgriSURE Fund — NABARD",
        grant_body="NABARD — National Bank for Agriculture and Rural Development",
        sections=list(_STANDARD_SECTIONS),
        tone="professional",
        mandatory_elements=[
            "Agri-tech or rural enterprise focus",
            "DPIIT recognition (preferred)",
            "Farm-to-fork technology description",
            "Revenue model for financial sustainability",
        ],
        custom_instructions=(
            "This is a NABARD AgriSURE application. Emphasise technology solutions "
            "for Indian agriculture, FPO/farmer integration, and financial sustainability "
            "as NABARD evaluates both social and financial returns."
        ),
        max_total_words=4000,
    )

    
    reg["nidhi_prayas"] = ProposalTemplate(
        template_id="nidhi_prayas",
        name="NIDHI-PRAYAS — DST Innovator Grant",
        grant_body="DST — Department of Science and Technology",
        sections=list(_STANDARD_SECTIONS),
        tone="technical",
        mandatory_elements=[
            "DST-recognised TBI affiliation",
            "Technology PoC plan",
            "Hardware/prototype deliverable",
        ],
        custom_instructions=(
            "This is a NIDHI-PRAYAS application for an individual innovator or early team. "
            "Focus entirely on the technology concept, PoC deliverable, and TBI support. "
            "Keep language clear and technical."
        ),
        max_total_words=2500,
    )

    
    reg["samridh"] = ProposalTemplate(
        template_id="samridh",
        name="SAMRIDH — MeitY Startup Accelerator",
        grant_body="MeitY",
        sections=list(_STANDARD_SECTIONS),
        tone="persuasive",
        mandatory_elements=[
            "DPIIT recognition status",
            "MeitY-empanelled accelerator partner",
            "Product revenue traction or pilot users",
            "Scaling plan post-acceleration",
        ],
        custom_instructions=(
            "SAMRIDH is a MeitY accelerator grant for product-stage ICT startups. "
            "Emphasise existing product traction, user metrics, scaling strategy, "
            "and how the accelerator grant (₹40 lakh) will accelerate growth."
        ),
        max_total_words=4000,
    )

    return reg






class TemplateManager:
    

    def __init__(self) -> None:
        self._registry: Dict[str, ProposalTemplate] = _build_registry()
        logger.info(
            "TemplateManager loaded: %d templates.", len(self._registry)
        )

    
    def get(self, template_id: str) -> ProposalTemplate:
        
        tmpl = self._registry.get(template_id)
        if tmpl is None:
            logger.debug(
                "Template '%s' not found — using 'default'.", template_id
            )
            tmpl = self._registry["default"]
        return tmpl

    def get_strict(self, template_id: str) -> ProposalTemplate:
        
        tmpl = self._registry.get(template_id)
        if tmpl is None:
            raise TemplateNotFoundError(template_id)
        return tmpl

    def resolve_for_grant(self, grant_id: str) -> ProposalTemplate:
        
        return self.get(grant_id)

    def list_templates(self) -> List[Dict[str, Any]]:
        
        return [t.to_dict() for t in self._registry.values()]

    def register(self, template: ProposalTemplate) -> None:
        
        if not template.template_id:
            raise ValueError("ProposalTemplate.template_id must not be blank.")
        self._registry[template.template_id] = template
        logger.info("Custom template registered: %s", template.template_id)

    @property
    def count(self) -> int:
        return len(self._registry)






_manager_singleton: Optional[TemplateManager] = None


def get_template_manager() -> TemplateManager:
    
    global _manager_singleton
    if _manager_singleton is None:
        _manager_singleton = TemplateManager()
    return _manager_singleton

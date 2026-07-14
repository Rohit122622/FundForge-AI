

import logging
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Optional

from backend.ibm.foundation_models import AIProvider, GenerationParameters
from backend.ibm.prompt_builder import GrantProposalPromptData, PromptBuilder
from backend.proposal_generator.exceptions import SectionGenerationError
from backend.proposal_generator.template_manager import SectionSpec

logger = logging.getLogger("fundforge.proposal_generator.section_generator")






_PARAMS_STANDARD = GenerationParameters(
    max_new_tokens    = 900,
    min_new_tokens    = 80,
    temperature       = 0.70,
    top_p             = 0.92,
    top_k             = 50,
    repetition_penalty= 1.15,
)

_PARAMS_TECHNICAL = GenerationParameters(
    max_new_tokens    = 700,
    min_new_tokens    = 60,
    temperature       = 0.40,
    top_p             = 0.90,
    top_k             = 20,
    repetition_penalty= 1.1,
)

_PARAMS_FINANCIAL = GenerationParameters(
    max_new_tokens    = 600,
    min_new_tokens    = 60,
    temperature       = 0.30,
    top_p             = 0.88,
    top_k             = 15,
    repetition_penalty= 1.1,
)


_SECTION_PARAMS: Dict[str, GenerationParameters] = {
    "innovation_technology": _PARAMS_TECHNICAL,
    "financial_plan":        _PARAMS_FINANCIAL,
    "budget_narrative":      _PARAMS_FINANCIAL,
    "timeline":              _PARAMS_FINANCIAL,
    "implementation_plan":   _PARAMS_TECHNICAL,
    "kpis":                  _PARAMS_FINANCIAL,
}






class _ExtendedPromptBuilder(PromptBuilder):
    

    _SYSTEM_PERSONA = (
        "You are FundForge AI, an expert grant writing assistant for Indian startups. "
        "You write professional, evidence-based grant proposals for Indian government "
        "funding schemes. You are precise, concise, and never invent facts."
    )

    _EXTENDED_INSTRUCTIONS: Dict[str, str] = {
        "innovation_technology": (
            "Write the Innovation & Technology section. Describe the core technology "
            "stack, technical architecture, proprietary components, patents or IP filed, "
            "and what makes this innovation technically differentiated from existing "
            "solutions in the Indian market. Be specific about the technology."
        ),
        "market_opportunity": (
            "Write the Market Opportunity section. Quantify the Total Addressable Market "
            "(TAM), Serviceable Addressable Market (SAM), and Serviceable Obtainable Market "
            "(SOM) for the Indian context. Use credible data from government reports, NASSCOM, "
            "IBEF, or industry sources. Describe the target customer segment clearly."
        ),
        "business_model": (
            "Write the Business Model section. Explain the revenue streams, pricing strategy, "
            "customer acquisition approach, sales channels, and unit economics. Describe how "
            "the startup generates and sustains revenue in the Indian market."
        ),
        "financial_plan": (
            "Write the Financial Plan section. Present a 3-year revenue and expense forecast. "
            "Break down the grant fund utilisation across key cost heads (technology, people, "
            "marketing, operations). Show path to financial sustainability. Use INR amounts."
        ),
        "sustainability": (
            "Write the Sustainability Plan section. Explain how the venture will remain "
            "financially and operationally sustainable beyond the grant period. Describe the "
            "revenue model, customer retention strategy, and long-term social impact plan."
        ),
        "competitive_advantage": (
            "Write the Competitive Advantage section. Explain the startup's unique selling proposition (USP), "
            "competitive moat, entry barriers, pricing advantages, and technical or operational superiority "
            "over existing incumbents and direct/indirect competitors in the Indian market. Use clear examples."
        ),
        "implementation_plan": (
            "Write the Implementation Plan section. Detail the research and development roadmap, product design phases, "
            "engineering requirements, prototyping, field trials, quality testing, and pilot roll-out strategy. "
            "Explain how the technical milestones will be achieved step-by-step."
        ),
        "kpis": (
            "Write the Key Performance Indicators (KPIs) section. Detail specific, measurable metrics for success. "
            "Include technical KPIs (performance, scale, latency), user KPIs (acquisition, retention, active usage), "
            "and business KPIs (monthly recurring revenue, CAC, conversion rates). Highlight milestone metrics."
        ),
        "risk_mitigation": (
            "Write the Risk Analysis & Mitigation section. Outline critical risks facing the startup: technical risks "
            "(scalability, security, tech stack), market risks (competition, user adoption), regulatory/compliance risks, "
            "and operational risks. Provide realistic, clear mitigation plans for each risk."
        ),
        "conclusion": (
            "Write the Conclusion section. Summarise the overall grant proposal value proposition, the strategic "
            "importance of the innovation to India, team commitment, and the final pitch to the grant committee. "
            "Provide a strong, inspiring, and professional closing statement."
        ),
    }

    def build_extended_section_prompt(
        self,
        section_key: str,
        data:        GrantProposalPromptData,
        spec:        SectionSpec,
        rag_context: str = "",
    ) -> str:
        
        import textwrap

        instruction = self._EXTENDED_INSTRUCTIONS.get(section_key, "")
        if not instruction:
            
            instruction = (
                f"Write the '{spec.title}' section for this grant proposal. "
                f"{spec.emphasis}"
            )

        context_block = ""
        if rag_context:
            context_block = f"\n--- GRANT KNOWLEDGE BASE CONTEXT ---\n{rag_context[:1500]}\n"

        user_block = textwrap.dedent(f"""
            You are helping write a grant proposal for an Indian startup.

            --- APPLICANT CONTEXT ---
            {data.company_context()}

            --- GRANT CONTEXT ---
            {data.grant_context()}
            {context_block}
            --- YOUR TASK ---
            {instruction}

            Write only the section content (no headings, no preamble).
            Use INR amounts where relevant. Keep to {spec.min_words}–{spec.max_words} words.
            Begin writing directly.
        """).strip()

        return self._format_instruction_prompt(system=self._SYSTEM_PERSONA, user=user_block)

    def build_base_section_with_rag(
        self,
        section_key: str,
        data:        GrantProposalPromptData,
        rag_context: str = "",
    ) -> str:
        
        base = self.build_proposal_section_prompt(section_key, data)
        if not rag_context:
            return base
        
        rag_block = f"\n--- GRANT KNOWLEDGE BASE CONTEXT ---\n{rag_context[:1500]}"
        return base.replace("<|user|>", f"<|user|>{rag_block}")






@dataclass
class GeneratedSection:
    
    key:           str
    title:         str
    content:       str   = ""
    word_count:    int   = 0
    input_tokens:  int   = 0
    output_tokens: int   = 0
    model_id:      str   = ""
    fallback_used: bool  = False
    error:         str   = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key":           self.key,
            "title":         self.title,
            "content":       self.content,
            "word_count":    self.word_count,
            "fallback_used": self.fallback_used,
            "error":         self.error,
        }






class SectionGenerator:
    

    
    _BASE_SECTIONS = frozenset({
        "executive_summary",
        "problem_statement",
        "proposed_solution",
        "impact_statement",
        "budget_narrative",
        "timeline",
        "team_qualifications",
    })

    
    _EXTENDED_SECTIONS = frozenset({
        "innovation_technology",
        "market_opportunity",
        "business_model",
        "financial_plan",
        "sustainability",
        "competitive_advantage",
        "implementation_plan",
        "kpis",
        "risk_mitigation",
        "conclusion",
    })

    def __init__(
        self,
        ai_provider:      AIProvider,
        prompt_builder:   Optional[_ExtendedPromptBuilder] = None,
        fallback_enabled: bool = True,
    ) -> None:
        self._provider         = ai_provider
        self._builder          = prompt_builder or _ExtendedPromptBuilder()
        self._fallback_enabled = fallback_enabled

    
    def generate(
        self,
        section_key:  str,
        spec:         SectionSpec,
        prompt_data:  GrantProposalPromptData,
        rag_context:  str = "",
        params:       Optional[GenerationParameters] = None,
    ) -> GeneratedSection:
        
        eff_params = params or _SECTION_PARAMS.get(section_key, _PARAMS_STANDARD)

        try:
            if section_key in self._BASE_SECTIONS:
                prompt = self._builder.build_base_section_with_rag(
                    section_key, prompt_data, rag_context
                )
            elif section_key in self._EXTENDED_SECTIONS:
                prompt = self._builder.build_extended_section_prompt(
                    section_key, prompt_data, spec, rag_context
                )
            else:
                
                prompt = self._builder.build_extended_section_prompt(
                    section_key, prompt_data, spec, rag_context
                )

            result = self._provider.generate_text(prompt=prompt, params=eff_params)
            content = result.text.strip()

            logger.info(
                "Section generated: key=%s words=%d tokens_in=%d tokens_out=%d",
                section_key, len(content.split()),
                result.input_tokens, result.output_tokens,
            )

            return GeneratedSection(
                key           = section_key,
                title         = spec.title,
                content       = content,
                word_count    = len(content.split()),
                input_tokens  = result.input_tokens,
                output_tokens = result.output_tokens,
                model_id      = result.model_id,
            )

        except Exception as exc:
            logger.error(
                "Section generation failed: key=%s error=%s", section_key, exc
            )
            if self._fallback_enabled:
                fallback = self._build_fallback(section_key, spec, prompt_data)
                return GeneratedSection(
                    key           = section_key,
                    title         = spec.title,
                    content       = fallback,
                    word_count    = len(fallback.split()),
                    fallback_used = True,
                    error         = str(exc),
                )
            raise SectionGenerationError(
                f"Failed to generate section '{section_key}': {exc}",
                section_name=section_key,
            ) from exc

    def generate_batch(
        self,
        sections:    List[SectionSpec],
        prompt_data: GrantProposalPromptData,
        rag_context: str = "",
        params:      Optional[GenerationParameters] = None,
    ) -> List[GeneratedSection]:
        
        results: List[GeneratedSection] = []
        for spec in sections:
            gs = self.generate(
                section_key = spec.key,
                spec        = spec,
                prompt_data = prompt_data,
                rag_context = rag_context,
                params      = params,
            )
            results.append(gs)
        return results

    def stream_section(
        self,
        section_key:  str,
        spec:         SectionSpec,
        prompt_data:  GrantProposalPromptData,
        rag_context:  str = "",
        params:       Optional[GenerationParameters] = None,
    ) -> Iterator[str]:
        
        eff_params = params or _SECTION_PARAMS.get(section_key, _PARAMS_STANDARD)
        if section_key in self._BASE_SECTIONS:
            prompt = self._builder.build_base_section_with_rag(
                section_key, prompt_data, rag_context
            )
        else:
            prompt = self._builder.build_extended_section_prompt(
                section_key, prompt_data, spec, rag_context
            )
        return self._provider.generate_text_stream(prompt=prompt, params=eff_params)

    
    @staticmethod
    def _build_fallback(
        key:         str,
        spec:        SectionSpec,
        prompt_data: GrantProposalPromptData,
    ) -> str:
        
        company = prompt_data.company_name or "Our startup"
        grant   = prompt_data.grant_title or "the government funding scheme"
        org     = prompt_data.grant_organization or "the government department"
        industry = prompt_data.industry or "technology"
        stage    = prompt_data.stage or "early"
        location = prompt_data.location or "India"
        team_size = prompt_data.team_size or 5
        founding_year = prompt_data.founding_year or 2023
        funding_needed = prompt_data.funding_needed or "INR 50 Lakhs"
        
        desc = prompt_data.description or f"a pioneering venture operating in the {industry} domain to build next-generation solutions for the Indian market"
        prob = prompt_data.problem_statement or f"the significant lack of localized, efficient, and scalable tools available to address critical challenges in the {industry} sector in India"
        sol = prompt_data.solution_statement or f"an AI-driven platform that integrates advanced capabilities to streamline operations and provide actionable insights"
        impact = prompt_data.impact_statement or f"democratizing access to technology, boosting employment, and contributing to the digital transformation of India's economy"
        
        stubs: Dict[str, str] = {
            "executive_summary": (
                f"{company} is a leading-edge {industry} startup founded in {founding_year} and based in {location}. "
                f"We are formally applying for the prestigious {grant} program administered by {org} to accelerate "
                f"the development and commercialization of our innovative technology. Currently operating at the "
                f"{stage} stage with a dedicated team of {team_size} professionals, {company} is developing solutions "
                f"specifically tailored to address major bottlenecks in India. The grant funding of {funding_needed} "
                f"will be key to expanding our technical capability, completing field trials, and preparing for national scale. "
                f"Our vision is to build a highly sustainable, high-impact enterprise that aligns with national development priorities."
            ),
            "problem_statement": (
                f"The target market in India faces a critical challenge regarding {prob}. "
                f"Existing options are highly fragmented, import-dependent, and lack the scalability required for Indian conditions. "
                f"Consequently, millions of users and small enterprises suffer from high operating costs, low operational efficiency, "
                f"and limited access to modern digital infrastructure. As a result, productivity across the {industry} value chain "
                f"remains suppressed. Addressing this market gap requires a localized, cost-effective, and highly scalable technological "
                f"solution designed from the ground up for Indian users. Without intervention, this systemic gap will continue to hinder growth "
                f"and digital inclusion in this critical sector."
            ),
            "proposed_solution": (
                f"To solve this problem, {company} proposes {sol}. "
                f"Our proprietary platform utilizes state-of-the-art architectures to deliver reliable, real-time performance. "
                f"Unlike conventional alternatives, our solution offers a seamless user experience, localized language support, "
                f"and low-bandwidth optimization. We have successfully developed a functional prototype and validated it in pre-pilot phases. "
                f"With the support of {grant}, we will scale our product deployment, optimize core algorithms, and deploy native integrations "
                f"to provide a comprehensive solution that meets the unique requirements of the Indian market."
            ),
            "innovation_technology": (
                f"{company}'s core innovation lies in our proprietary tech stack, which utilizes advanced algorithms, "
                f"optimized database layers, and custom APIs designed to scale. Our architecture is built using modern cloud-native "
                f"frameworks, ensuring high availability, robust security protocols, and easy integration with existing legacy systems. "
                f"We are actively securing intellectual property rights for our unique data processing pipelines and algorithmic models. "
                f"This technical differentiation allows our platform to process information faster, consume fewer resources, and cost significantly "
                f"less than international competing solutions, making it highly competitive for Indian enterprise use."
            ),
            "market_opportunity": (
                f"The market opportunity for {company} is substantial. Across India, the Total Addressable Market (TAM) "
                f"for the {industry} sector is estimated at several thousand crores, driven by rapid digitization and favorable policy frameworks. "
                f"Our initial Serviceable Addressable Market (SAM) focuses on tier-1 and tier-2 Indian cities, representing a high-density "
                f"customer segment ready for immediate adoption. Our Serviceable Obtainable Market (SOM) targets capturing a significant "
                f"share of active users within the next 24 months. We have identified clear customer acquisition channels, strategic channel "
                f"partnerships, and digital marketing strategies to acquire customers cost-effectively."
            ),
            "business_model": (
                f"We operate a diversified business model designed for long-term scalability and robust unit economics. "
                f"Our primary revenue streams include a subscription-based Software-as-a-Service (SaaS) model for enterprises, "
                f"complemented by transactional fees and value-added consulting services. By leveraging automated onboarding "
                f"and digital self-service tools, we maintain a very low Customer Acquisition Cost (CAC) and high Customer Lifetime Value (LTV). "
                f"Our pricing is structured to match the budget constraints of Indian MSMEs and startups, ensuring rapid market penetration "
                f"while maintaining healthy gross margins above seventy percent."
            ),
            "financial_plan": (
                f"Over the next three years, {company} projects robust financial growth. The revenue forecast shows a path to "
                f"profitability by year two, driven by enterprise customer onboarding and scaling transactional volume. "
                f"Operational expenses will be dominated by technical headcount and product engineering, followed by sales and marketing "
                f"to secure our market share. We have planned a detailed allocation of the requested {grant} funds across key operational heads: "
                f"product development, pilot deployment, and quality assurance. This capital injection will provide the runway needed to achieve "
                f"positive cash flows and secure institutional funding."
            ),
            "team_qualifications": (
                f"The founding team at {company} possesses deep domain expertise in {industry} and digital technologies. "
                f"With a combined experience of over fifteen years in product engineering, business development, and scaling startups, "
                f"our leadership is fully equipped to execute this project successfully. Our technical team is composed of seasoned software "
                f"engineers and data scientists, while our operations team brings expertise in regulatory compliance, customer success, "
                f"and partner relations. We also maintain an active advisory board comprising industry veterans and academic experts "
                f"who guide our strategic direction."
            ),
            "impact_statement": (
                f"The socioeconomic impact of our project is aligned with the core objectives of {org}. "
                f"By deploying our solution, we expect to contribute directly to {impact}. "
                f"We will monitor key performance indicators (KPIs) to measure progress: target audience reached, "
                f"cost savings realized by our clients, and green-technology adoption rates. Furthermore, our expansion will create "
                f"skilled employment opportunities in tech-product engineering, customer operations, and field marketing across India, "
                f"driving regional economic growth."
            ),
            "timeline": (
                f"We have structured the implementation timeline into four clear quarters. Quarter one will focus on core tech enhancement "
                f"and database optimization. Quarter two will center on initial pilot deployments, user feedback collection, and performance "
                f"tuning. Quarter three will see the launch of enterprise modules and localized support. Quarter four will be dedicated to "
                f"full commercial launch, partner integrations, and final compliance audit. Each milestone has defined deliverables "
                f"including API documentation, pilot reports, and security certificates."
            ),
            "budget_narrative": (
                f"The grant funding of {funding_needed} will be deployed meticulously to achieve key technical and commercial milestones. "
                f"Approximately forty percent will fund core engineering salaries to complete product development. "
                f"Thirty percent is allocated for cloud infrastructure, testing suites, and data security compliance. "
                f"Twenty percent will support pilot deployment, localized user onboarding, and technical training programs. "
                f"The remaining ten percent is reserved for administrative overhead, travel for pilot implementations, and contingency funds, "
                f"ensuring zero leakages and maximum efficiency."
            ),
            "sustainability": (
                f"Post-grant sustainability is built directly into our operational model. By establishing early revenue streams "
                f"through B2B pilot contracts, we will transition smoothly from grant funding to self-sustained commercial operations. "
                f"Our customer success framework will drive high retention rates and recurring subscription revenues, reducing dependency "
                f"on external capital. Any operating surplus will be reinvested in product R&D and market expansion, ensuring the venture "
                f"remains commercially viable, scalable, and socially impactful for years to come."
            ),
            "competitive_advantage": (
                f"{company} possesses a distinct competitive advantage in the Indian {industry} space. "
                f"Our primary technical edge is our proprietary algorithm which allows for high processing speeds "
                f"and robust offline functionality, key for Indian semi-urban and rural deployments. "
                f"Additionally, our localized pricing model and deep API integrations create high switching costs "
                f"for existing clients. Unlike foreign incumbents, our customer support is deeply integrated "
                f"with local business networks, enabling a faster feedback loop and agility in product updates."
            ),
            "implementation_plan": (
                f"Our implementation plan is structured to minimize technical risks and ensure high deployment efficiency. "
                f"Phase one focuses on final database optimization, cloud migration, and internal testing. "
                f"Phase two involves deploying our functional prototype to a selected group of early adopters for beta testing. "
                f"Phase three targets pilot roll-outs in three key regional hubs, integrating local partner feedback. "
                f"Finally, phase four moves into full commercial deployment, establishing system audits and service level agreements."
            ),
            "kpis": (
                f"To monitor execution progress, {company} has defined a comprehensive set of KPIs. "
                f"Technical KPIs include keeping server latency below two hundred milliseconds and maintaining a ninety-nine point nine percent uptime. "
                f"User acquisition KPIs target onboarding over five thousand active users in the first six months, "
                f"with a monthly retention rate exceeding eighty percent. "
                f"Business metrics focus on keeping our customer acquisition cost low and reaching cash-flow positivity by the third quarter of phase two."
            ),
            "risk_mitigation": (
                f"We have identified key operational risks and established corresponding mitigation strategies. "
                f"Technical risks regarding cloud scalability are mitigated by using load balancers and auto-scaling groups. "
                f"User adoption risks are addressed by providing a clean user experience, local language onboarding, and extensive tutorials. "
                f"Regulatory and compliance risks are mitigated by auditing our data pipelines regularly with third-party security firms, "
                f"ensuring compliance with all local laws and data protection directives."
            ),
            "conclusion": (
                f"In conclusion, {company}'s proposal represents a highly viable, innovative, and scalable solution for the Indian market. "
                f"With our qualified team, validated prototype, and clear market opportunity, we are uniquely positioned "
                f"to execute this project successfully. The grant support from {org} under the {grant} program "
                f"will be catalytic, accelerating our deployment and ensuring technology access for critical sectors. "
                f"We are fully committed to achieving these milestones and driving technology growth across India."
            ),
        }
        text = stubs.get(key, f"This is the official {spec.title} section of the proposal. We will implement key project objectives under the {grant} program to build scalable solutions for {company}. Our goals include executing the timeline, scaling our team, and deploying our technology to achieve national impact.")
        words = text.split()
        if len(words) < spec.min_words:
            paddings = [
                f" We are committed to maintaining the highest standard of operational excellence, compliance, and technological innovation as we implement this program under the {grant} guidelines.",
                " Our strategy focuses on solving core inefficiencies through a combination of localization, scalable software design, and deep customer engagement.",
                " We have planned comprehensive milestones to validate our technical capabilities, refine product features based on field trials, and build long-term value.",
                " By working closely with incubation partners and industry advisors, we aim to accelerate our go-to-market timeline and ensure smooth adoption.",
                " Every aspect of our roadmap has been designed to address structural gaps, promote local manufacturing and tech capabilities, and create new jobs.",
                " This initiative will not only yield commercial returns but will also establish a strong foundation for technical leadership in the Indian startup ecosystem."
            ]
            idx = 0
            while len(text.split()) < spec.min_words and idx < len(paddings):
                text += paddings[idx]
                idx += 1
        return text

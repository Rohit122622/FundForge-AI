

import logging
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Dict, List, Optional, Set

from backend.grant_engine.startup_profiler import FundingStage, IndianSector, TechFocus

logger = logging.getLogger("fundforge.grant_engine.grant_catalog")






class GrantInstrument(str, Enum):
    
    GRANT            = "grant"
    EQUITY_FUND      = "equity_fund"
    SOFT_LOAN        = "soft_loan"
    CREDIT_GUARANTEE = "credit_guarantee"
    INCUBATION       = "incubation"
    FELLOWSHIP       = "fellowship"
    PRIZE            = "prize"
    SUBSIDY          = "subsidy"


@dataclass
class IndianGrant:
    
    id:                       str
    name:                     str
    short_name:               str
    administering_body:       str
    instrument:               GrantInstrument
    target_sectors:           Set[IndianSector]
    excluded_sectors:         Set[IndianSector] = field(default_factory=set)
    target_tech_focus:        Set[TechFocus] = field(default_factory=set)
    eligible_stages:          Set[FundingStage] = field(default_factory=set)
    min_amount_inr:           Optional[float] = None
    max_amount_inr:           Optional[float] = None
    typical_amount_inr:       Optional[float] = None
    deadline:                 Optional[date] = None
    is_rolling:               bool = True
    requires_dpiit:           bool = True
    requires_incorporation:   bool = True
    max_team_size:            Optional[int] = None
    min_team_size:            int = 1
    max_funding_raised:       Optional[float] = None   
    indian_states:            Set[str] = field(default_factory=set)  
    women_led_preference:     bool = False
    requires_patent:          bool = False
    innovation_keywords:      Set[str] = field(default_factory=set)
    description:              str = ""
    eligibility_summary:      List[str] = field(default_factory=list)
    application_url:          str = ""
    max_company_age_years:    Optional[int] = None
    tags:                     Set[str] = field(default_factory=set)

    @property
    def is_open(self) -> bool:
        
        if self.deadline is None:
            return self.is_rolling
        return date.today() <= self.deadline

    def to_dict(self) -> dict:
        return {
            "id":                 self.id,
            "name":               self.name,
            "short_name":         self.short_name,
            "administering_body": self.administering_body,
            "instrument":         self.instrument.value,
            "min_amount_inr":     self.min_amount_inr,
            "max_amount_inr":     self.max_amount_inr,
            "typical_amount_inr": self.typical_amount_inr,
            "deadline":           self.deadline.isoformat() if self.deadline else None,
            "is_rolling":         self.is_rolling,
            "requires_dpiit":     self.requires_dpiit,
            "description":        self.description,
            "eligibility_summary":self.eligibility_summary,
            "application_url":    self.application_url,
            "is_open":            self.is_open,
            "tags":               list(self.tags),
            "target_sectors":     [s.value for s in self.target_sectors],
            "eligible_stages":    [s.value for s in self.eligible_stages],
        }






_L  = 1_00_000          
_CR = 1_00_00_000       


def _build_catalog() -> List[IndianGrant]:
    
    ALL_SECTORS   = set(IndianSector)
    TECH_SECTORS  = {IndianSector.ICT, IndianSector.DEEPTECH, IndianSector.FINTECH,
                     IndianSector.HEALTHTECH, IndianSector.EDTECH, IndianSector.AGRITECH,
                     IndianSector.CLEAN_ENERGY, IndianSector.MANUFACTURING, IndianSector.BIOTECH}

    catalog: List[IndianGrant] = [

        
        IndianGrant(
            id="sisfs",
            name="Startup India Seed Fund Scheme",
            short_name="SISFS",
            administering_body="DPIIT, Ministry of Commerce & Industry",
            instrument=GrantInstrument.GRANT,
            target_sectors=ALL_SECTORS,
            eligible_stages={FundingStage.IDEATION, FundingStage.PROOF_OF_CONCEPT,
                             FundingStage.EARLY_TRACTION},
            min_amount_inr=5 * _L,
            max_amount_inr=20 * _L,
            typical_amount_inr=15 * _L,
            is_rolling=True,
            requires_dpiit=True,
            max_funding_raised=10 * _CR,
            max_company_age_years=2,
            women_led_preference=True,
            description=(
                "Startup India Seed Fund Scheme (SISFS) provides financial assistance "
                "to startups for proof of concept, prototype development, product "
                "trials, market entry, and commercialisation. Grants are disbursed "
                "through DPIIT-recognised incubators across India."
            ),
            eligibility_summary=[
                "DPIIT recognised startup",
                "Incorporated not more than 2 years ago",
                "Not received more than ₹10 crore in total funding",
                "Not a subsidiary or spinoff of another company",
                "Must be registered with a DPIIT-recognised incubator",
            ],
            application_url="https://seedfund.startupindia.gov.in/",
            tags={"seed", "dpiit", "incubator", "prototype", "proof-of-concept",
                  "early-stage", "all-sectors"},
        ),

        
        IndianGrant(
            id="ffs_sidbi",
            name="Fund of Funds for Startups",
            short_name="FFS",
            administering_body="SIDBI (Small Industries Development Bank of India)",
            instrument=GrantInstrument.EQUITY_FUND,
            target_sectors=ALL_SECTORS,
            eligible_stages={FundingStage.EARLY_TRACTION, FundingStage.GROWTH,
                             FundingStage.MATURE},
            min_amount_inr=25 * _L,
            max_amount_inr=50 * _CR,
            typical_amount_inr=5 * _CR,
            is_rolling=True,
            requires_dpiit=True,
            description=(
                "FFS is a ₹10,000 Crore fund managed by SIDBI to invest in SEBI-registered "
                "AIFs (Alternate Investment Funds) that in turn invest in Indian startups. "
                "Supports growth-stage startups across all sectors."
            ),
            eligibility_summary=[
                "DPIIT recognised startup",
                "Registered as AIF under SEBI or investee of registered AIF",
                "Growth or expansion stage",
                "Incorporated in India",
            ],
            application_url="https://www.sidbi.in/en/initiatives/fund-of-funds",
            tags={"equity", "growth", "sidbi", "aif", "sebi", "all-sectors"},
        ),

        
        IndianGrant(
            id="cgss",
            name="Credit Guarantee Scheme for Startups",
            short_name="CGSS",
            administering_body="DPIIT / NCGTC",
            instrument=GrantInstrument.CREDIT_GUARANTEE,
            target_sectors=ALL_SECTORS,
            eligible_stages={FundingStage.EARLY_TRACTION, FundingStage.GROWTH},
            min_amount_inr=10 * _L,
            max_amount_inr=10 * _CR,
            typical_amount_inr=1 * _CR,
            is_rolling=True,
            requires_dpiit=True,
            description=(
                "CGSS provides credit guarantees to scheduled commercial banks, "
                "NBFCs, and SEBI-registered AIFs for loans / investments made to "
                "DPIIT-recognised startups. Reduces collateral burden on startups."
            ),
            eligibility_summary=[
                "DPIIT recognised startup",
                "Loan taken from a member lending institution",
                "Maximum guarantee cover ₹10 crore per startup",
            ],
            application_url="https://www.startupindia.gov.in/content/sih/en/government-schemes.html",
            tags={"credit", "guarantee", "loan", "collateral-free", "dpiit"},
        ),

        
        IndianGrant(
            id="nidhi_prayas",
            name="NIDHI-PRAYAS (Promoting and Accelerating Young and Aspiring Innovators)",
            short_name="NIDHI-PRAYAS",
            administering_body="DST (Department of Science and Technology)",
            instrument=GrantInstrument.GRANT,
            target_sectors=TECH_SECTORS,
            eligible_stages={FundingStage.IDEATION, FundingStage.PROOF_OF_CONCEPT},
            min_amount_inr=2 * _L,
            max_amount_inr=10 * _L,
            typical_amount_inr=10 * _L,
            is_rolling=True,
            requires_dpiit=False,
            max_company_age_years=1,
            description=(
                "NIDHI-PRAYAS supports individuals and early-stage innovators in "
                "developing and validating a technological proof of concept or prototype. "
                "Disbursed through Technology Business Incubators (TBIs) hosted in NITs, IITs, and IISc."
            ),
            eligibility_summary=[
                "Indian individual or team with innovative idea",
                "Technology / product concept stage",
                "Support provided through DST-recognised TBIs",
                "Up to ₹10 lakh grant for PoC development",
            ],
            application_url="https://nidhi.dst.gov.in/nidhi-prayas",
            innovation_keywords={"prototype", "poc", "technology", "innovation", "hardware"},
            tags={"dst", "tbi", "poc", "ideation", "prototype", "technology", "innovation"},
        ),

        
        IndianGrant(
            id="nidhi_eir",
            name="NIDHI Entrepreneur-In-Residence Programme",
            short_name="NIDHI-EIR",
            administering_body="DST (Department of Science and Technology)",
            instrument=GrantInstrument.FELLOWSHIP,
            target_sectors=TECH_SECTORS,
            eligible_stages={FundingStage.IDEATION},
            min_amount_inr=30_000,
            max_amount_inr=30_000,
            typical_amount_inr=30_000,   
            is_rolling=True,
            requires_dpiit=False,
            max_team_size=1,
            description=(
                "NIDHI-EIR provides ₹30,000/month fellowship for up to 12 months to "
                "technology innovators working on a startup idea. Fellows are hosted "
                "at DST-recognised Technology Business Incubators."
            ),
            eligibility_summary=[
                "Individual innovator (not a registered company)",
                "Technology / deep-tech focus",
                "Hosted at a DST TBI",
                "Fellowship of ₹30,000/month for up to 12 months",
            ],
            application_url="https://nidhi.dst.gov.in/",
            tags={"fellowship", "stipend", "ideation", "individual", "dst"},
        ),

        
        IndianGrant(
            id="birac_big",
            name="BIRAC Biotechnology Ignition Grant",
            short_name="BIRAC-BIG",
            administering_body="BIRAC (Biotechnology Industry Research Assistance Council)",
            instrument=GrantInstrument.GRANT,
            target_sectors={IndianSector.BIOTECH, IndianSector.HEALTHTECH,
                            IndianSector.MEDTECH, IndianSector.AGRITECH},
            eligible_stages={FundingStage.IDEATION, FundingStage.PROOF_OF_CONCEPT},
            min_amount_inr=50 * _L,
            max_amount_inr=50 * _L,
            typical_amount_inr=50 * _L,
            is_rolling=False,
            requires_dpiit=False,
            target_tech_focus={TechFocus.BIOTECH, TechFocus.MEDTECH},
            description=(
                "BIRAC-BIG provides ₹50 lakh grant to early-stage biotech startups "
                "and innovators for proof-of-concept research. Supports translational "
                "research in biotech, medtech, agricultural biotech, and diagnostics."
            ),
            eligibility_summary=[
                "Indian entity (startup, SME, or researcher)",
                "Biotechnology / biomedical / agricultural biotech focus",
                "Early-stage / PoC phase",
                "Maximum ₹50 lakh for 18 months",
                "Must work with a BIRAC-supported incubator or BIONEST",
            ],
            application_url="https://birac.nic.in/big.php",
            innovation_keywords={"biotechnology", "medtech", "diagnostics", "therapeutic", "drug"},
            tags={"birac", "biotech", "medtech", "health", "agri-biotech", "poc"},
        ),

        
        IndianGrant(
            id="birac_seed",
            name="BIRAC SEED Fund",
            short_name="BIRAC-SEED",
            administering_body="BIRAC",
            instrument=GrantInstrument.GRANT,
            target_sectors={IndianSector.BIOTECH, IndianSector.HEALTHTECH, IndianSector.MEDTECH},
            eligible_stages={FundingStage.PROOF_OF_CONCEPT, FundingStage.EARLY_TRACTION},
            min_amount_inr=50 * _L,
            max_amount_inr=5 * _CR,
            typical_amount_inr=2 * _CR,
            is_rolling=True,
            requires_dpiit=True,
            target_tech_focus={TechFocus.BIOTECH, TechFocus.MEDTECH},
            description=(
                "BIRAC SEED Fund bridges early-stage biotech startups from PoC to "
                "product development and first sales. Larger grants (up to ₹5 crore) "
                "for translational research and clinical validation."
            ),
            eligibility_summary=[
                "DPIIT recognised startup",
                "Biotech / medtech sector",
                "Proof of concept completed",
                "Up to ₹5 crore for 2–3 years",
            ],
            application_url="https://birac.nic.in/",
            tags={"birac", "biotech", "medtech", "seed", "translational"},
        ),

        
        IndianGrant(
            id="tide_2",
            name="Technology Incubation and Development of Entrepreneurs 2.0",
            short_name="TIDE 2.0",
            administering_body="MeitY (Ministry of Electronics and Information Technology)",
            instrument=GrantInstrument.GRANT,
            target_sectors={IndianSector.ICT, IndianSector.DEEPTECH, IndianSector.FINTECH,
                            IndianSector.HEALTHTECH, IndianSector.EDTECH, IndianSector.AGRITECH},
            eligible_stages={FundingStage.IDEATION, FundingStage.PROOF_OF_CONCEPT,
                             FundingStage.EARLY_TRACTION},
            min_amount_inr=5 * _L,
            max_amount_inr=50 * _L,
            typical_amount_inr=15 * _L,
            is_rolling=True,
            requires_dpiit=False,
            target_tech_focus={TechFocus.AI_ML, TechFocus.HARDWARE_IOT, TechFocus.BLOCKCHAIN,
                               TechFocus.SOFTWARE_SAAS},
            description=(
                "TIDE 2.0 promotes tech entrepreneurship by providing grants and soft "
                "loans through MeitY-supported Technology Incubation Centres (TICs) "
                "across India. Focus on ICT-based innovations across sectors."
            ),
            eligibility_summary=[
                "ICT or technology-based startup",
                "Hosted at a MeitY TIC",
                "Up to ₹50 lakh grant per startup",
                "AI, IoT, Blockchain, AR/VR focus areas",
            ],
            application_url="https://tide.meity.gov.in/",
            innovation_keywords={"iot", "ai", "blockchain", "arvr", "fintech", "digital"},
            tags={"meity", "ict", "ai", "iot", "blockchain", "incubation", "digital"},
        ),

        
        IndianGrant(
            id="samridh",
            name="Startup Accelerators of MeitY for pRoduct Innovation, Development and Growth",
            short_name="SAMRIDH",
            administering_body="MeitY",
            instrument=GrantInstrument.GRANT,
            target_sectors={IndianSector.ICT, IndianSector.DEEPTECH, IndianSector.FINTECH,
                            IndianSector.HEALTHTECH, IndianSector.EDTECH},
            eligible_stages={FundingStage.EARLY_TRACTION, FundingStage.GROWTH},
            min_amount_inr=40 * _L,
            max_amount_inr=40 * _L,
            typical_amount_inr=40 * _L,
            is_rolling=True,
            requires_dpiit=True,
            target_tech_focus={TechFocus.AI_ML, TechFocus.SOFTWARE_SAAS, TechFocus.HARDWARE_IOT},
            description=(
                "SAMRIDH provides ₹40 lakh to tech startups through empanelled "
                "accelerator organisations. Focuses on product development, scaling, "
                "and market access for ICT-based startups."
            ),
            eligibility_summary=[
                "DPIIT recognised startup",
                "ICT / tech product focus",
                "In acceleration programme with MeitY-empanelled accelerator",
                "Up to ₹40 lakh per startup",
            ],
            application_url="https://samridh.meity.gov.in/",
            tags={"meity", "accelerator", "ict", "product", "scaling", "samridh"},
        ),

        
        IndianGrant(
            id="stpi_ngis",
            name="STPI Next Generation Incubation Scheme",
            short_name="STPI-NGIS",
            administering_body="STPI (Software Technology Parks of India)",
            instrument=GrantInstrument.INCUBATION,
            target_sectors={IndianSector.ICT, IndianSector.DEEPTECH, IndianSector.FINTECH,
                            IndianSector.HEALTHTECH, IndianSector.EDTECH},
            eligible_stages={FundingStage.IDEATION, FundingStage.PROOF_OF_CONCEPT,
                             FundingStage.EARLY_TRACTION},
            min_amount_inr=15 * _L,
            max_amount_inr=25 * _L,
            typical_amount_inr=20 * _L,
            is_rolling=True,
            requires_dpiit=False,
            target_tech_focus={TechFocus.AI_ML, TechFocus.HARDWARE_IOT, TechFocus.BLOCKCHAIN,
                               TechFocus.DRONE, TechFocus.SOFTWARE_SAAS},
            description=(
                "STPI NGIS provides grants, mentoring, cloud credits, and co-working "
                "space to tech startups hosted at STPI centres across India. Focus on "
                "deep-tech and emerging technologies."
            ),
            eligibility_summary=[
                "Product / tech startup",
                "Hosted at an STPI incubation centre",
                "Deep-tech focus preferred",
                "Up to ₹25 lakh in grant support",
            ],
            application_url="https://www.stpi.in/",
            tags={"stpi", "incubation", "deeptech", "cloud", "ict", "emerging-tech"},
        ),

        
        IndianGrant(
            id="agrisure",
            name="AgriSURE Fund (Agri-tech Startups and Rural Enterprise Fund)",
            short_name="AgriSURE",
            administering_body="NABARD (National Bank for Agriculture and Rural Development)",
            instrument=GrantInstrument.EQUITY_FUND,
            target_sectors={IndianSector.AGRITECH, IndianSector.FOODTECH,
                            IndianSector.RURAL_TECH},
            eligible_stages={FundingStage.EARLY_TRACTION, FundingStage.GROWTH},
            min_amount_inr=50 * _L,
            max_amount_inr=10 * _CR,
            typical_amount_inr=2 * _CR,
            is_rolling=True,
            requires_dpiit=True,
            description=(
                "AgriSURE is a ₹750 crore blended fund by NABARD to support agri-tech "
                "startups, FPOs, and rural enterprises. Provides equity/debt to "
                "startups building technology solutions for Indian agriculture."
            ),
            eligibility_summary=[
                "Agri-tech / rural enterprise startup",
                "DPIIT recognised preferred",
                "Early-traction or growth stage",
                "Focus on farm-to-fork technology solutions",
            ],
            application_url="https://www.nabard.org/agrisure",
            innovation_keywords={"agritech", "farmer", "agriculture", "fpo", "rural", "crop"},
            tags={"nabard", "agritech", "rural", "farm", "fpo", "agrisure"},
        ),

        
        IndianGrant(
            id="rkvy_raftaar",
            name="RKVY-RAFTAAR Agri-Business Incubation Programme",
            short_name="RKVY-RAFTAAR",
            administering_body="Ministry of Agriculture & Farmers Welfare (ICAR)",
            instrument=GrantInstrument.GRANT,
            target_sectors={IndianSector.AGRITECH, IndianSector.FOODTECH,
                            IndianSector.RURAL_TECH},
            eligible_stages={FundingStage.IDEATION, FundingStage.PROOF_OF_CONCEPT,
                             FundingStage.EARLY_TRACTION},
            min_amount_inr=5 * _L,
            max_amount_inr=25 * _L,
            typical_amount_inr=20 * _L,
            is_rolling=True,
            requires_dpiit=False,
            women_led_preference=True,
            description=(
                "RKVY-RAFTAAR provides agri-business incubation and grant funding to "
                "agricultural entrepreneurs through R-BI (RKVY-RAFTAAR Business "
                "Incubators) hosted at ICAR institutes and SAUs. Supports pre-seed "
                "and seed agri-tech startups."
            ),
            eligibility_summary=[
                "Agriculture / food / rural entrepreneur",
                "Indian citizen or Indian registered entity",
                "Selected through R-BI at ICAR / SAU",
                "Up to ₹25 lakh grant",
            ],
            application_url="https://rkvy.nic.in/",
            innovation_keywords={"agriculture", "farmer", "crop", "dairy", "food", "rural"},
            tags={"rkvy", "agriculture", "icar", "incubation", "rural", "food"},
        ),

        
        IndianGrant(
            id="msme_tus",
            name="MSME Technology Upgradation Scheme (CLCSS / ATUFS)",
            short_name="MSME-TUS",
            administering_body="Ministry of MSME",
            instrument=GrantInstrument.SUBSIDY,
            target_sectors={IndianSector.MANUFACTURING, IndianSector.ICT,
                            IndianSector.AGRITECH, IndianSector.FOODTECH},
            eligible_stages={FundingStage.EARLY_TRACTION, FundingStage.GROWTH,
                             FundingStage.MATURE},
            min_amount_inr=10 * _L,
            max_amount_inr=1 * _CR,
            typical_amount_inr=50 * _L,
            is_rolling=True,
            requires_dpiit=False,
            description=(
                "Capital subsidy scheme to help MSMEs upgrade technology and plant "
                "& machinery. 15% capital subsidy (up to ₹1 crore) on institutional "
                "credit for technology upgradation."
            ),
            eligibility_summary=[
                "Registered MSME (Udyam registration)",
                "Manufacturing or services sector",
                "Technology upgrade or new machinery investment",
                "Loan from eligible bank / SIDBI",
            ],
            application_url="https://msme.gov.in/",
            tags={"msme", "manufacturing", "capital-subsidy", "technology-upgrade"},
        ),

        
        IndianGrant(
            id="sidbi_startup_mitra",
            name="SIDBI Startup Mitra — Soft Loan Scheme",
            short_name="SIDBI-Mitra",
            administering_body="SIDBI",
            instrument=GrantInstrument.SOFT_LOAN,
            target_sectors=ALL_SECTORS,
            eligible_stages={FundingStage.EARLY_TRACTION, FundingStage.GROWTH},
            min_amount_inr=25 * _L,
            max_amount_inr=5 * _CR,
            typical_amount_inr=1 * _CR,
            is_rolling=True,
            requires_dpiit=True,
            description=(
                "SIDBI provides collateral-free soft loans (quasi-equity) to DPIIT-recognised "
                "startups at concessional interest rates. Supports working capital, "
                "product development, and market expansion."
            ),
            eligibility_summary=[
                "DPIIT recognised startup",
                "Revenue generating or near-revenue stage",
                "Collateral-free loan up to ₹5 crore",
                "Concessional interest rate",
            ],
            application_url="https://www.sidbi.in/en/startups",
            tags={"sidbi", "soft-loan", "working-capital", "collateral-free"},
        ),

        
        IndianGrant(
            id="dst_women_scientist",
            name="DST Women Scientists Scheme (WOS-A)",
            short_name="DST-WOS",
            administering_body="DST",
            instrument=GrantInstrument.GRANT,
            target_sectors={IndianSector.DEEPTECH, IndianSector.BIOTECH,
                            IndianSector.HEALTHTECH, IndianSector.CLEAN_ENERGY},
            eligible_stages={FundingStage.IDEATION, FundingStage.PROOF_OF_CONCEPT},
            min_amount_inr=30 * _L,
            max_amount_inr=60 * _L,
            typical_amount_inr=30 * _L,
            is_rolling=True,
            requires_dpiit=False,
            women_led_preference=True,
            description=(
                "DST WOS-A supports women scientists and technologists to pursue "
                "basic and applied research, leading to commercialisable products. "
                "Preference for women-led deep-tech ventures."
            ),
            eligibility_summary=[
                "Women scientist / innovator",
                "S&T / deep-tech area",
                "Age 30–57 years",
                "Break-in-career or returnee preferred",
            ],
            application_url="https://www.dst.gov.in/scientific-programmes/women-scientist-programmes",
            tags={"dst", "women-led", "research", "deeptech", "biotech", "gender"},
        ),

        
        IndianGrant(
            id="meity_ai",
            name="MeitY AI & Emerging Technologies Grand Challenge",
            short_name="MeitY-AI",
            administering_body="MeitY",
            instrument=GrantInstrument.PRIZE,
            target_sectors={IndianSector.ICT, IndianSector.DEEPTECH, IndianSector.HEALTHTECH,
                            IndianSector.AGRITECH, IndianSector.MANUFACTURING},
            eligible_stages={FundingStage.PROOF_OF_CONCEPT, FundingStage.EARLY_TRACTION},
            min_amount_inr=25 * _L,
            max_amount_inr=5 * _CR,
            typical_amount_inr=1 * _CR,
            is_rolling=False,
            requires_dpiit=True,
            target_tech_focus={TechFocus.AI_ML, TechFocus.HARDWARE_IOT, TechFocus.BLOCKCHAIN,
                               TechFocus.ROBOTICS, TechFocus.DRONE},
            description=(
                "MeitY's AI Grand Challenge provides grants up to ₹5 crore to startups "
                "developing AI, Machine Learning, IoT, and emerging tech solutions "
                "for national priority areas including healthcare, agriculture, and education."
            ),
            eligibility_summary=[
                "DPIIT recognised startup",
                "AI / ML / IoT / emerging tech focus",
                "Product must address national priority domain",
                "Up to ₹5 crore competitive grant",
            ],
            application_url="https://www.meity.gov.in/",
            innovation_keywords={"artificial intelligence", "machine learning", "deep learning",
                                "neural", "nlp", "computer vision"},
            tags={"meity", "ai", "ml", "emerging-tech", "grand-challenge", "deeptech"},
        ),

        
        IndianGrant(
            id="istart_rajasthan",
            name="iStart Rajasthan Startup Scheme",
            short_name="iStart",
            administering_body="Rajasthan Government (DoIT&C)",
            instrument=GrantInstrument.GRANT,
            target_sectors=ALL_SECTORS,
            eligible_stages={FundingStage.IDEATION, FundingStage.PROOF_OF_CONCEPT,
                             FundingStage.EARLY_TRACTION},
            min_amount_inr=5 * _L,
            max_amount_inr=20 * _L,
            typical_amount_inr=10 * _L,
            is_rolling=True,
            requires_dpiit=False,
            indian_states={"rajasthan"},
            description=(
                "iStart is Rajasthan's flagship startup scheme providing seed grants, "
                "incubation, mentoring, and market access support to Rajasthan-based startups."
            ),
            eligibility_summary=[
                "Startup incorporated / operating in Rajasthan",
                "Less than 7 years old",
                "Annual turnover < ₹100 crore",
            ],
            application_url="https://istart.rajasthan.gov.in/",
            tags={"rajasthan", "state-scheme", "seed", "incubation"},
        ),

        
        IndianGrant(
            id="dst_tbi",
            name="DST Technology Business Incubator Programme",
            short_name="DST-TBI",
            administering_body="DST / NS-NIDHI",
            instrument=GrantInstrument.INCUBATION,
            target_sectors=TECH_SECTORS,
            eligible_stages={FundingStage.IDEATION, FundingStage.PROOF_OF_CONCEPT,
                             FundingStage.EARLY_TRACTION},
            min_amount_inr=2 * _L,
            max_amount_inr=50 * _L,
            typical_amount_inr=10 * _L,
            is_rolling=True,
            requires_dpiit=False,
            description=(
                "DST supports Technology Business Incubators (TBIs) at academic institutions. "
                "Startups hosted at TBIs receive funding, mentoring, lab access, and "
                "network access as part of the NIDHI ecosystem."
            ),
            eligibility_summary=[
                "Technology / deep-tech startup",
                "Hosted at a DST-recognised TBI",
                "Early-stage or PoC phase",
            ],
            application_url="https://nidhi.dst.gov.in/",
            tags={"dst", "tbi", "incubation", "technology", "nidhi"},
        ),

        
        IndianGrant(
            id="pmegp",
            name="Prime Minister's Employment Generation Programme",
            short_name="PMEGP",
            administering_body="Ministry of MSME / KVIC",
            instrument=GrantInstrument.SUBSIDY,
            target_sectors={IndianSector.MANUFACTURING, IndianSector.RURAL_TECH,
                            IndianSector.AGRITECH, IndianSector.FOODTECH,
                            IndianSector.SOCIAL_IMPACT},
            eligible_stages={FundingStage.IDEATION, FundingStage.PROOF_OF_CONCEPT},
            min_amount_inr=10 * _L,
            max_amount_inr=50 * _L,
            typical_amount_inr=25 * _L,
            is_rolling=True,
            requires_dpiit=False,
            women_led_preference=True,
            description=(
                "PMEGP is a credit-linked subsidy scheme to generate employment through "
                "establishing new micro enterprises in non-farm sector. 15–35% capital "
                "subsidy (higher for women and SC/ST/OBC applicants)."
            ),
            eligibility_summary=[
                "Indian citizen 18+",
                "No existing bank loan or subsidy on same project",
                "Minimum 8th pass for projects > ₹10 lakh",
                "Manufacturing or service enterprise (non-farm)",
            ],
            application_url="https://www.kviconline.gov.in/pmegpeportal/",
            tags={"pmegp", "msme", "kvic", "employment", "manufacturing", "rural"},
        ),

        
        IndianGrant(
            id="social_alpha",
            name="Social Alpha Innovation Fund",
            short_name="Social Alpha",
            administering_body="Social Alpha (Tata Trusts backed)",
            instrument=GrantInstrument.EQUITY_FUND,
            target_sectors={IndianSector.SOCIAL_IMPACT, IndianSector.HEALTHTECH,
                            IndianSector.AGRITECH, IndianSector.CLEAN_ENERGY,
                            IndianSector.EDTECH, IndianSector.WATER_SANITATION},
            eligible_stages={FundingStage.PROOF_OF_CONCEPT, FundingStage.EARLY_TRACTION},
            min_amount_inr=20 * _L,
            max_amount_inr=5 * _CR,
            typical_amount_inr=1 * _CR,
            is_rolling=True,
            requires_dpiit=True,
            women_led_preference=True,
            description=(
                "Social Alpha supports social innovators and deep-science-driven startups "
                "working on mission-critical challenges in health, clean energy, education, "
                "water, and agriculture. Backed by Tata Trusts."
            ),
            eligibility_summary=[
                "Social impact focus",
                "Deep tech or science-based innovation",
                "DPIIT recognised preferred",
                "Addressable market in India",
            ],
            application_url="https://www.socialalpha.org/",
            innovation_keywords={"social", "impact", "bharat", "rural", "clean", "health"},
            tags={"social-impact", "tata", "deeptech", "health", "agriculture", "clean-energy"},
        ),

        
        IndianGrant(
            id="digital_india_genesis",
            name="Gen-Next Support for Innovative Startups (GENESIS)",
            short_name="GENESIS",
            administering_body="MeitY (Ministry of Electronics and Information Technology)",
            instrument=GrantInstrument.GRANT,
            target_sectors={IndianSector.ICT, IndianSector.DEEPTECH},
            eligible_stages={FundingStage.PROOF_OF_CONCEPT, FundingStage.EARLY_TRACTION},
            min_amount_inr=5 * _L,
            max_amount_inr=25 * _L,
            typical_amount_inr=15 * _L,
            is_rolling=True,
            requires_dpiit=True,
            description=(
                "GENESIS is a national deep-tech and digital startup program aimed at "
                "supporting tech startups in Tier-II and Tier-III cities of India, "
                "focusing on collaborative innovation, product development, and scaling."
            ),
            eligibility_summary=[
                "DPIIT recognized startup",
                "Located in or operating from Tier-II/III locations in India",
                "Focus on digital technologies, SaaS, or deep-tech"
            ],
            application_url="https://genesis.meity.gov.in/",
            tags={"genesis", "meity", "tier-2", "tier-3", "digital", "deeptech"},
        ),

        
        IndianGrant(
            id="idex_prime",
            name="iDEX Prime (Innovations for Defence Excellence Prime)",
            short_name="iDEX Prime",
            administering_body="Ministry of Defence / DIO",
            instrument=GrantInstrument.GRANT,
            target_sectors={IndianSector.DEFENCE, IndianSector.DEEPTECH, IndianSector.SPACE_TECH},
            eligible_stages={FundingStage.PROOF_OF_CONCEPT, FundingStage.EARLY_TRACTION},
            min_amount_inr=50 * _L,
            max_amount_inr=150 * _L,
            typical_amount_inr=150 * _L,
            is_rolling=False,
            requires_dpiit=True,
            description=(
                "iDEX Prime aims to support startups working on challenges with higher funding "
                "requirements in the defence and aerospace sectors, allowing innovators to scale "
                "military grade systems."
            ),
            eligibility_summary=[
                "DPIIT recognized startup",
                "Must address specific iDEX Prime Defence challenges",
                "High technology readiness level required"
            ],
            application_url="https://idex.gov.in/",
            tags={"defence", "military", "aerospace", "idex", "deeptech"},
        ),

        
        IndianGrant(
            id="idex_disc",
            name="iDEX Defence India Startup Challenge (DISC)",
            short_name="iDEX-DISC",
            administering_body="Ministry of Defence",
            instrument=GrantInstrument.GRANT,
            target_sectors={IndianSector.DEFENCE, IndianSector.DEEPTECH},
            eligible_stages={FundingStage.IDEATION, FundingStage.PROOF_OF_CONCEPT},
            min_amount_inr=10 * _L,
            max_amount_inr=150 * _L,
            typical_amount_inr=100 * _L,
            is_rolling=False,
            requires_dpiit=True,
            description=(
                "Defence India Startup Challenge (DISC) invites startups and innovators "
                "to solve specific technological challenges faced by the Indian Armed Forces "
                "and Defence Public Sector Undertakings."
            ),
            eligibility_summary=[
                "Individual innovators or DPIIT recognized startups",
                "Must submit proposals addressing armed forces challenge statements",
                "IP rights remain with the startup/innovator"
            ],
            application_url="https://idex.gov.in/",
            tags={"defence", "disc", "challenge", "military", "innovation"},
        ),

        
        IndianGrant(
            id="birac_sparsh",
            name="BIRAC SPARSH Social Innovation Fellowship & Grants",
            short_name="SPARSH",
            administering_body="BIRAC",
            instrument=GrantInstrument.GRANT,
            target_sectors={IndianSector.BIOTECH, IndianSector.HEALTHTECH, IndianSector.SOCIAL_IMPACT},
            eligible_stages={FundingStage.IDEATION, FundingStage.PROOF_OF_CONCEPT},
            min_amount_inr=5 * _L,
            max_amount_inr=50 * _L,
            typical_amount_inr=30 * _L,
            is_rolling=True,
            requires_dpiit=False,
            description=(
                "SPARSH is a social innovation program of BIRAC targeting affordable and "
                "relevant solutions for societal health and wellness challenges in India. "
                "Supports both individual fellows and early-stage companies."
            ),
            eligibility_summary=[
                "Indian citizen or startup working on social health innovations",
                "Focus on maternal & child health, aging, waste management, or sanitation",
                "Collaborate with SPARSH partner centers"
            ],
            application_url="https://birac.nic.in/",
            tags={"birac", "sparsh", "social", "health", "biotech", "sanitation"},
        ),

        
        IndianGrant(
            id="aim_aic",
            name="Atal Incubation Centre (AIC) Support Scheme",
            short_name="AIC-Support",
            administering_body="Atal Innovation Mission, NITI Aayog",
            instrument=GrantInstrument.INCUBATION,
            target_sectors=ALL_SECTORS,
            eligible_stages={FundingStage.IDEATION, FundingStage.PROOF_OF_CONCEPT},
            min_amount_inr=2 * _L,
            max_amount_inr=10 * _L,
            typical_amount_inr=5 * _L,
            is_rolling=True,
            requires_dpiit=False,
            description=(
                "Atal Innovation Mission provides incubation and funding support to startups "
                "admitted to Atal Incubation Centres (AICs) across India. Offers state-of-the-art "
                "lab access, mentorship, and seed money."
            ),
            eligibility_summary=[
                "Incubated startup at a recognized AIC",
                "Early stage or proof of concept phase",
                "Open to all technology and manufacturing sectors"
            ],
            application_url="https://aim.gov.in/",
            tags={"aim", "aic", "niti-aayog", "incubation", "mentorship", "all-sectors"},
        ),

        
        IndianGrant(
            id="aim_anic",
            name="Atal New India Challenge (ANIC)",
            short_name="ANIC",
            administering_body="Atal Innovation Mission, NITI Aayog",
            instrument=GrantInstrument.GRANT,
            target_sectors={IndianSector.AGRITECH, IndianSector.CLEAN_ENERGY, IndianSector.MOBILITY, IndianSector.WATER_SANITATION},
            eligible_stages={FundingStage.PROOF_OF_CONCEPT, FundingStage.EARLY_TRACTION},
            min_amount_inr=50 * _L,
            max_amount_inr=100 * _L,
            typical_amount_inr=100 * _L,
            is_rolling=False,
            requires_dpiit=True,
            description=(
                "Atal New India Challenge (ANIC) aims to support technology-driven innovations "
                "that solve critical national problems in sectors like agriculture, sanitation, "
                "clean energy, waste management, and road transport."
            ),
            eligibility_summary=[
                "DPIIT recognized startup or MSME",
                "Product must address designated ANIC challenge areas",
                "Prototype or minimum viable product (MVP) must be ready"
            ],
            application_url="https://aim.gov.in/anic.php",
            tags={"aim", "anic", "national-challenge", "niti-aayog", "sustainability"},
        ),

        
        IndianGrant(
            id="msme_idea_hackathon",
            name="MSME Idea Hackathon (under MSME Innovative Scheme)",
            short_name="MSME-Hackathon",
            administering_body="Ministry of MSME",
            instrument=GrantInstrument.GRANT,
            target_sectors=ALL_SECTORS,
            eligible_stages={FundingStage.IDEATION, FundingStage.PROOF_OF_CONCEPT},
            min_amount_inr=5 * _L,
            max_amount_inr=15 * _L,
            typical_amount_inr=15 * _L,
            is_rolling=False,
            requires_dpiit=False,
            description=(
                "MSME Idea Hackathon invites students, innovators, and MSMEs to submit "
                "innovative proposals. Approved ideas receive funding of up to Rs. 15 Lakh "
                "per idea to convert them into commercial products."
            ),
            eligibility_summary=[
                "Students, individual innovators, or registered MSMEs",
                "Selected through recognized Host Institutions (HIs)",
                "Focus on technology, sustainability, and manufacturing"
            ],
            application_url="https://innovative.msme.gov.in/",
            tags={"msme", "hackathon", "idea", "students", "innovative", "all-sectors"},
        ),

        
        IndianGrant(
            id="nidhi_seed_support",
            name="NIDHI Seed Support System (NIDHI-SSS)",
            short_name="NIDHI-SSS",
            administering_body="DST (Department of Science and Technology)",
            instrument=GrantInstrument.EQUITY_FUND,
            target_sectors=TECH_SECTORS,
            eligible_stages={FundingStage.PROOF_OF_CONCEPT, FundingStage.EARLY_TRACTION},
            min_amount_inr=10 * _L,
            max_amount_inr=100 * _L,
            typical_amount_inr=25 * _L,
            is_rolling=True,
            requires_dpiit=True,
            description=(
                "NIDHI-SSS provides early-stage funding to startups incubated in DST-supported "
                "incubators. Funds can be utilized for prototype refinement, product testing, "
                "hiring key talent, and market entry."
            ),
            eligibility_summary=[
                "Incubated at a DST-supported incubator for at least 3 months",
                "DPIIT recognized startup",
                "Technology or product-focused venture"
            ],
            application_url="https://nidhi.dst.gov.in/",
            tags={"dst", "nidhi", "seed-support", "incubator-funding", "technology"},
        ),

        
        IndianGrant(
            id="stpi_leap_ahead",
            name="STPI LEAP-AHEAD Initiative (Launchpad for Tech Startups)",
            short_name="LEAP-AHEAD",
            administering_body="STPI",
            instrument=GrantInstrument.EQUITY_FUND,
            target_sectors={IndianSector.ICT, IndianSector.DEEPTECH, IndianSector.FINTECH},
            eligible_stages={FundingStage.EARLY_TRACTION, FundingStage.GROWTH},
            min_amount_inr=25 * _L,
            max_amount_inr=100 * _L,
            typical_amount_inr=100 * _L,
            is_rolling=False,
            requires_dpiit=True,
            description=(
                "LEAP-AHEAD is a joint initiative to invest in high-potential technology startups "
                "across India, offering funding, global mentorship, and access to international "
                "markets."
            ),
            eligibility_summary=[
                "DPIIT recognized startup in ICT/Software/Fintech sectors",
                "Commercial product launched with early revenue or customer base",
                "Willingness to join the STPI acceleration cohort"
            ],
            application_url="https://www.stpi.in/",
            tags={"stpi", "leap-ahead", "equity", "accelerator", "global-scaling"},
        ),

        
        IndianGrant(
            id="karnataka_elevate",
            name="ELEVATE Karnataka (Startup Karnataka)",
            short_name="ELEVATE",
            administering_body="Department of IT, BT and S&T, Government of Karnataka",
            instrument=GrantInstrument.GRANT,
            target_sectors=ALL_SECTORS,
            eligible_stages={FundingStage.IDEATION, FundingStage.PROOF_OF_CONCEPT, FundingStage.EARLY_TRACTION},
            min_amount_inr=5 * _L,
            max_amount_inr=50 * _L,
            typical_amount_inr=20 * _L,
            is_rolling=False,
            requires_dpiit=False,
            indian_states={"karnataka"},
            description=(
                "ELEVATE is the flagship startup grant scheme of Karnataka, providing funding, "
                "incubation, and mentoring to promising early-stage startups based in Karnataka."
            ),
            eligibility_summary=[
                "Registered startup in Karnataka",
                "At least 50% ownership by Karnataka-based founders",
                "High preference for women-led, rural, and deeptech startups"
            ],
            application_url="https://startup.karnataka.gov.in/",
            tags={"karnataka", "elevate", "state-scheme", "grant", "early-stage"},
        ),

        
        IndianGrant(
            id="maharashtra_msins",
            name="Maharashtra State Innovation Society (MSINS) Seed Grant",
            short_name="MSINS-Seed",
            administering_body="Government of Maharashtra",
            instrument=GrantInstrument.GRANT,
            target_sectors=ALL_SECTORS,
            eligible_stages={FundingStage.IDEATION, FundingStage.PROOF_OF_CONCEPT},
            min_amount_inr=5 * _L,
            max_amount_inr=15 * _L,
            typical_amount_inr=10 * _L,
            is_rolling=True,
            requires_dpiit=False,
            indian_states={"maharashtra"},
            description=(
                "MSINS provides financial support to early-stage startups in Maharashtra to "
                "develop prototypes, test markets, and cover initial operational expenses."
            ),
            eligibility_summary=[
                "Registered startup in Maharashtra",
                "Incorporated within last 7 years",
                "Innovative solution targeting social, tech, or industrial problems"
            ],
            application_url="https://msins.in/",
            tags={"maharashtra", "msins", "state-scheme", "seed-grant", "prototype"},
        ),

        
        IndianGrant(
            id="gujarat_startup_scheme",
            name="Gujarat Startup Assistance Scheme (under Gujarat Industrial Policy)",
            short_name="Gujarat-Startup",
            administering_body="Industries Commissionerate, Government of Gujarat",
            instrument=GrantInstrument.GRANT,
            target_sectors=ALL_SECTORS,
            eligible_stages={FundingStage.IDEATION, FundingStage.PROOF_OF_CONCEPT, FundingStage.EARLY_TRACTION},
            min_amount_inr=5 * _L,
            max_amount_inr=30 * _L,
            typical_amount_inr=15 * _L,
            is_rolling=True,
            requires_dpiit=False,
            indian_states={"gujarat"},
            description=(
                "Provides assistance to startups in Gujarat for developing prototypes, patents, "
                "and marketing products. Includes monthly stipends for individual innovators."
            ),
            eligibility_summary=[
                "Registered startup or student innovator in Gujarat",
                "Affiliated with a Gujarat-approved incubator",
                "Innovative idea with high commercial potential"
            ],
            application_url="https://startupgujarat.in/",
            tags={"gujarat", "state-scheme", "stipend", "prototype", "patent-support"},
        ),

        
        IndianGrant(
            id="kerala_ksum_seed",
            name="Kerala Startup Mission (KSUM) Seed Fund Scheme",
            short_name="KSUM-Seed",
            administering_body="Kerala Startup Mission, Government of Kerala",
            instrument=GrantInstrument.SOFT_LOAN,
            target_sectors=ALL_SECTORS,
            eligible_stages={FundingStage.PROOF_OF_CONCEPT, FundingStage.EARLY_TRACTION},
            min_amount_inr=5 * _L,
            max_amount_inr=15 * _L,
            typical_amount_inr=10 * _L,
            is_rolling=True,
            requires_dpiit=False,
            indian_states={"kerala"},
            description=(
                "KSUM provides soft loans to Kerala-based startups to build prototypes, "
                "acquire early traction, and cover hardware/software validation costs."
            ),
            eligibility_summary=[
                "Registered startup with Kerala Startup Mission (KSUM)",
                "Working product prototype or early customer base",
                "Repayable soft loan with minimal interest rates"
            ],
            application_url="https://startupmission.kerala.gov.in/",
            tags={"kerala", "ksum", "state-scheme", "soft-loan", "mvp"},
        ),

        
        IndianGrant(
            id="telangana_t_hub",
            name="T-Hub Innovation and Incubation Support Grant",
            short_name="T-Hub-Grant",
            administering_body="Government of Telangana / T-Hub",
            instrument=GrantInstrument.INCUBATION,
            target_sectors={IndianSector.DEEPTECH, IndianSector.ICT, IndianSector.FINTECH},
            eligible_stages={FundingStage.IDEATION, FundingStage.PROOF_OF_CONCEPT, FundingStage.EARLY_TRACTION},
            min_amount_inr=2 * _L,
            max_amount_inr=10 * _L,
            typical_amount_inr=5 * _L,
            is_rolling=True,
            requires_dpiit=False,
            indian_states={"telangana"},
            description=(
                "Offers incubation, technical resources, and innovation grants to startups "
                "incubated at T-Hub in Hyderabad. Focuses on DeepTech, IoT, and Enterprise SaaS."
            ),
            eligibility_summary=[
                "Incubated at T-Hub Hyderabad",
                "Based in Telangana or willing to relocate",
                "High technology innovation focus"
            ],
            application_url="https://t-hub.co/",
            tags={"telangana", "t-hub", "hyderabad", "incubation", "deeptech"},
        ),

        
        IndianGrant(
            id="up_startup_policy",
            name="Uttar Pradesh Startup Policy Seed Fund",
            short_name="UP-Seed",
            administering_body="Department of IT & Electronics, Government of Uttar Pradesh",
            instrument=GrantInstrument.GRANT,
            target_sectors=ALL_SECTORS,
            eligible_stages={FundingStage.IDEATION, FundingStage.PROOF_OF_CONCEPT},
            min_amount_inr=5 * _L,
            max_amount_inr=25 * _L,
            typical_amount_inr=15 * _L,
            is_rolling=True,
            requires_dpiit=False,
            indian_states={"uttar pradesh"},
            description=(
                "Provides seed capital assistance, marketing support, and prototype funding "
                "to startups in Uttar Pradesh to accelerate innovation in rural and urban areas."
            ),
            eligibility_summary=[
                "Registered startup in Uttar Pradesh",
                "Affiliated with a UP-recognized incubator",
                "Promotes local employment and tech innovation"
            ],
            application_url="https://startuninup.up.gov.in/",
            tags={"uttar-pradesh", "up", "state-scheme", "seed-fund", "local-employment"},
        ),

        
        IndianGrant(
            id="tamils_manv",
            name="Tamil Nadu Startup Seed Grant Fund (TANSEED)",
            short_name="TANSEED",
            administering_body="StartupTN, Government of Tamil Nadu",
            instrument=GrantInstrument.GRANT,
            target_sectors=ALL_SECTORS,
            eligible_stages={FundingStage.PROOF_OF_CONCEPT, FundingStage.EARLY_TRACTION},
            min_amount_inr=5 * _L,
            max_amount_inr=10 * _L,
            typical_amount_inr=10 * _L,
            is_rolling=False,
            requires_dpiit=False,
            indian_states={"tamil nadu"},
            description=(
                "TANSEED provides seed funds of up to Rs. 10 Lakh each to early-stage startups "
                "in Tamil Nadu to help bridge the funding gap during product launch and early scale."
            ),
            eligibility_summary=[
                "Registered startup in Tamil Nadu",
                "Working MVP or prototype",
                "High priority for women-led or socially impactful ventures"
            ],
            application_url="https://startuptn.in/",
            tags={"tamil-nadu", "tanseed", "state-scheme", "seed-grant", "mvp"},
        ),

        
        IndianGrant(
            id="dep_biotechnology_sbiri",
            name="Small Business Innovation Research Initiative (SBIRI)",
            short_name="DBT-SBIRI",
            administering_body="BIRAC / Department of Biotechnology",
            instrument=GrantInstrument.GRANT,
            target_sectors={IndianSector.BIOTECH, IndianSector.HEALTHTECH, IndianSector.AGRITECH},
            eligible_stages={FundingStage.PROOF_OF_CONCEPT, FundingStage.EARLY_TRACTION},
            min_amount_inr=25 * _L,
            max_amount_inr=100 * _L,
            typical_amount_inr=50 * _L,
            is_rolling=False,
            requires_dpiit=False,
            description=(
                "SBIRI supports high-risk pre-proof-of-concept research and early-stage "
                "product development in the biotechnology and healthcare domains by Indian small businesses."
            ),
            eligibility_summary=[
                "Indian biotech company with research capability",
                "Fewer than 500 employees",
                "Focus on biotech, diagnostic, vaccine, or agri-biotech product development"
            ],
            application_url="https://birac.nic.in/sbiri.php",
            tags={"birac", "sbiri", "dbt", "biotech", "research", "health"},
        ),

        
        IndianGrant(
            id="dep_biotechnology_bipp",
            name="Biotechnology Industry Partnership Programme (BIPP)",
            short_name="DBT-BIPP",
            administering_body="BIRAC / Department of Biotechnology",
            instrument=GrantInstrument.SOFT_LOAN,
            target_sectors={IndianSector.BIOTECH, IndianSector.HEALTHTECH, IndianSector.AGRITECH},
            eligible_stages={FundingStage.EARLY_TRACTION, FundingStage.GROWTH},
            min_amount_inr=50 * _L,
            max_amount_inr=200 * _L,
            typical_amount_inr=150 * _L,
            is_rolling=False,
            requires_dpiit=False,
            description=(
                "BIPP is a government-industry partnership program supporting research in high-value "
                "areas of national relevance like biopharmaceuticals, agriculture, and industrial biotech."
            ),
            eligibility_summary=[
                "Indian registered biotechnology companies",
                "Commercial scaling or clinical trials phase",
                "Matching contribution required from the industry partner"
            ],
            application_url="https://birac.nic.in/bipp.php",
            tags={"birac", "bipp", "dbt", "biotech", "clinical-trials", "partnership"},
        ),

        
        IndianGrant(
            id="ministry_textiles_tusts",
            name="Grant for Research and Entrepreneurship in Technical Textiles (GREAT)",
            short_name="GREAT-Textiles",
            administering_body="Ministry of Textiles, Government of India",
            instrument=GrantInstrument.GRANT,
            target_sectors={IndianSector.MANUFACTURING, IndianSector.DEEPTECH},
            eligible_stages={FundingStage.IDEATION, FundingStage.PROOF_OF_CONCEPT},
            min_amount_inr=10 * _L,
            max_amount_inr=50 * _L,
            typical_amount_inr=40 * _L,
            is_rolling=True,
            requires_dpiit=False,
            description=(
                "GREAT scheme supports individual innovators and startups working in technical textiles, "
                "offering grants to build prototypes, set up small pilot lines, and commercialize smart fibers."
            ),
            eligibility_summary=[
                "Indian citizen or registered startup in textiles/materials",
                "Innovative solution in medical, agricultural, defense, or smart textiles",
                "Affiliated with premier research institutions like IITs/NITs"
            ],
            application_url="https://www.technicaltextiles.gov.in/",
            tags={"textiles", "great", "materials", "manufacturing", "smart-fibers"},
        ),

        
        IndianGrant(
            id="isro_spacetech_challenge",
            name="ISRO Space Technology Startup Challenge",
            short_name="ISRO-Space",
            administering_body="ISRO / Department of Space, Government of India",
            instrument=GrantInstrument.GRANT,
            target_sectors={IndianSector.SPACE_TECH, IndianSector.DEEPTECH},
            eligible_stages={FundingStage.PROOF_OF_CONCEPT, FundingStage.EARLY_TRACTION},
            min_amount_inr=10 * _L,
            max_amount_inr=50 * _L,
            typical_amount_inr=25 * _L,
            is_rolling=False,
            requires_dpiit=True,
            description=(
                "Supports space-tech startups developing downstream satellite data applications, "
                "propulsion systems, sensors, payloads, and launch vehicle technologies in collaboration with ISRO."
            ),
            eligibility_summary=[
                "DPIIT recognized space-tech startup",
                "Focus on space downstream, launch systems, satellites, or electronics",
                "Allows access to ISRO testing and validation labs"
            ],
            application_url="https://www.isro.gov.in/Startups.html",
            tags={"isro", "space-tech", "satellite", "payload", "propulsion"},
        ),

        
        IndianGrant(
            id="sidbi_ubharte_sitare",
            name="SIDBI Ubharte Sitaare Programme for Export-oriented Startups",
            short_name="Ubharte-Sitaare",
            administering_body="SIDBI / EXIM Bank of India",
            instrument=GrantInstrument.EQUITY_FUND,
            target_sectors={IndianSector.MANUFACTURING, IndianSector.DEEPTECH, IndianSector.AGRITECH},
            eligible_stages={FundingStage.GROWTH, FundingStage.MATURE},
            min_amount_inr=100 * _L,
            max_amount_inr=500 * _L,
            typical_amount_inr=250 * _L,
            is_rolling=True,
            requires_dpiit=True,
            description=(
                "Identifies and invests in early-traction, export-oriented Indian companies "
                "and startups. Provides equity investment, debt funding, and technical assistance."
            ),
            eligibility_summary=[
                "DPIIT recognized startup or MSME with high export potential",
                "Established product and positive market reputation",
                "Minimum turnover and positive operating profits preferred"
            ],
            application_url="https://www.eximbankindia.in/ubharte-sitaare",
            tags={"sidbi", "exim-bank", "export", "growth", "equity-debt", "manufacturing"},
        ),

        
        IndianGrant(
            id="mhrd_ic_innovation",
            name="Ministry of Education Innovation Cell (MIC) Startup Grant",
            short_name="MIC-Grant",
            administering_body="Innovation Cell, Ministry of Education",
            instrument=GrantInstrument.GRANT,
            target_sectors={IndianSector.EDTECH, IndianSector.ICT},
            eligible_stages={FundingStage.IDEATION, FundingStage.PROOF_OF_CONCEPT},
            min_amount_inr=2 * _L,
            max_amount_inr=10 * _L,
            typical_amount_inr=5 * _L,
            is_rolling=True,
            requires_dpiit=False,
            description=(
                "Supports student-led startups and academic innovators across Indian universities "
                "to develop early-stage proof of concepts and software prototypes."
            ),
            eligibility_summary=[
                "Students, researchers, or faculty at recognized Indian universities",
                "Idea nominated by the university's Institution's Innovation Council (IIC)",
                "Working prototype or pilot phase"
            ],
            application_url="https://mic.gov.in/",
            tags={"education", "mic", "student-startup", "academic", "university"},
        ),

        
        IndianGrant(
            id="meity_samridh_cohort",
            name="SAMRIDH Startup Accelerator Cohort Scheme",
            short_name="SAMRIDH-Cohort",
            administering_body="MeitY / MeitY Startup Hub (MSH)",
            instrument=GrantInstrument.GRANT,
            target_sectors={IndianSector.ICT, IndianSector.FINTECH, IndianSector.HEALTHTECH},
            eligible_stages={FundingStage.EARLY_TRACTION, FundingStage.GROWTH},
            min_amount_inr=20 * _L,
            max_amount_inr=40 * _L,
            typical_amount_inr=40 * _L,
            is_rolling=False,
            requires_dpiit=True,
            description=(
                "Provides co-investment of up to Rs. 40 Lakh to select SaaS, Fintech, and HealthTech "
                "startups participating in the SAMRIDH accelerator program."
            ),
            eligibility_summary=[
                "DPIIT recognized startup",
                "Admitted to a SAMRIDH cohort accelerator program",
                "Customer traction and operational software product"
            ],
            application_url="https://meitystartuphub.in/",
            tags={"meity", "samridh", "accelerator", "saas", "fintech", "co-investment"},
        ),

        
        IndianGrant(
            id="nstebd_nidhi_gcc",
            name="NIDHI Climate Change Grand Challenge (NIDHI-GCC)",
            short_name="NIDHI-GCC",
            administering_body="NSTEDB / Department of Science and Technology",
            instrument=GrantInstrument.GRANT,
            target_sectors={IndianSector.CLEAN_ENERGY, IndianSector.WATER_SANITATION, IndianSector.MOBILITY},
            eligible_stages={FundingStage.PROOF_OF_CONCEPT, FundingStage.EARLY_TRACTION},
            min_amount_inr=10 * _L,
            max_amount_inr=50 * _L,
            typical_amount_inr=30 * _L,
            is_rolling=False,
            requires_dpiit=True,
            description=(
                "A grand challenge targeting clean energy, circular economy, waste-to-wealth, "
                "and green transport solutions to mitigate climate change impact in India."
            ),
            eligibility_summary=[
                "DPIIT recognized startup or technological innovator",
                "Focus on clean tech, climate change mitigation, or water treatment",
                "Must showcase a working prototype"
            ],
            application_url="https://nidhi.dst.gov.in/",
            tags={"dst", "nidhi", "climate-change", "clean-energy", "green-tech"},
        ),

        
        IndianGrant(
            id="swachh_bharat_grand_challenge",
            name="Swachh Bharat Grand Challenge for Waste Management",
            short_name="Swachh-Bharat",
            administering_body="DPIIT / Ministry of Housing & Urban Affairs",
            instrument=GrantInstrument.PRIZE,
            target_sectors={IndianSector.CLEAN_ENERGY, IndianSector.WATER_SANITATION, IndianSector.SOCIAL_IMPACT},
            eligible_stages={FundingStage.PROOF_OF_CONCEPT, FundingStage.EARLY_TRACTION},
            min_amount_inr=5 * _L,
            max_amount_inr=25 * _L,
            typical_amount_inr=15 * _L,
            is_rolling=False,
            requires_dpiit=True,
            description=(
                "Supports startups building innovative technologies for solid waste management, "
                "sewage treatment, plastic recycling, and circular economy."
            ),
            eligibility_summary=[
                "DPIIT recognized startup",
                "Addresses solid/liquid waste management or sanitation",
                "Provides scalable and cost-effective local community solutions"
            ],
            application_url="https://www.startupindia.gov.in/",
            tags={"dpiit", "swachh-bharat", "waste-management", "sanitation", "circular-economy"},
        ),

        
        IndianGrant(
            id="agri_infra_fund",
            name="Agriculture Infrastructure Fund (AIF) Interest Subvention",
            short_name="AIF-Subvention",
            administering_body="Ministry of Agriculture & Farmers Welfare, Government of India",
            instrument=GrantInstrument.CREDIT_GUARANTEE,
            target_sectors={IndianSector.AGRITECH, IndianSector.FOODTECH, IndianSector.RURAL_TECH},
            eligible_stages={FundingStage.EARLY_TRACTION, FundingStage.GROWTH},
            min_amount_inr=10 * _L,
            max_amount_inr=200 * _L,
            typical_amount_inr=50 * _L,
            is_rolling=True,
            requires_dpiit=False,
            description=(
                "Provides interest subvention of 3% per annum and credit guarantee coverage for post-harvest "
                "management infrastructure and community farming assets."
            ),
            eligibility_summary=[
                "Agritech startups, primary agricultural cooperative societies (PACs), or FPOs",
                "Builds post-harvest storage, cold chains, sorting/grading units",
                "Collateral-free credit cover up to Rs. 2 Crore under CGTMSE"
            ],
            application_url="https://agriinfra.dac.gov.in/",
            tags={"agri-infra", "interest-subvention", "agriculture", "cold-chain", "post-harvest"},
        ),
    ]

    return catalog






class GrantCatalog:
    

    def __init__(self):
        self._grants: List[IndianGrant] = _build_catalog()
        self._index: Dict[str, IndianGrant] = {g.id: g for g in self._grants}
        logger.info(
            "GrantCatalog loaded: %d Indian grants.", len(self._grants)
        )

    
    def all(self) -> List[IndianGrant]:
        
        return list(self._grants)

    def open_grants(self) -> List[IndianGrant]:
        
        return [g for g in self._grants if g.is_open]

    def get_by_id(self, grant_id: str) -> Optional[IndianGrant]:
        
        return self._index.get(grant_id)

    def by_sector(self, sector: IndianSector) -> List[IndianGrant]:
        
        return [g for g in self._grants if sector in g.target_sectors]

    def by_stage(self, stage: FundingStage) -> List[IndianGrant]:
        
        return [g for g in self._grants if stage in g.eligible_stages]

    def by_instrument(self, instrument: GrantInstrument) -> List[IndianGrant]:
        
        return [g for g in self._grants if g.instrument == instrument]

    def to_dict_list(self) -> List[dict]:
        
        return [g.to_dict() for g in self._grants]

    @property
    def count(self) -> int:
        
        return len(self._grants)






_catalog_singleton: Optional[GrantCatalog] = None


def get_grant_catalog() -> GrantCatalog:
    
    global _catalog_singleton
    if _catalog_singleton is None:
        _catalog_singleton = GrantCatalog()
    return _catalog_singleton

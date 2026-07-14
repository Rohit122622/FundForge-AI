

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set

logger = logging.getLogger("fundforge.grant_engine.startup_profiler")






class IndianSector(str, Enum):
    
    AGRITECH         = "agritech"
    BIOTECH          = "biotech"
    CLEAN_ENERGY     = "clean_energy"
    DEEPTECH         = "deeptech"
    DEFENCE          = "defence"
    EDTECH           = "edtech"
    FINTECH          = "fintech"
    FOODTECH         = "foodtech"
    HEALTHTECH       = "healthtech"
    ICT              = "ict"            
    MANUFACTURING    = "manufacturing"
    MEDTECH          = "medtech"
    MOBILITY         = "mobility"
    RURAL_TECH       = "rural_tech"
    SOCIAL_IMPACT    = "social_impact"
    SPACE_TECH       = "space_tech"
    WATER_SANITATION = "water_sanitation"
    WOMEN_LED        = "women_led"
    OTHER            = "other"


class FundingStage(str, Enum):
    
    IDEATION         = "ideation"         
    PROOF_OF_CONCEPT = "proof_of_concept" 
    EARLY_TRACTION   = "early_traction"   
    GROWTH           = "growth"           
    MATURE           = "mature"           


class TechFocus(str, Enum):
    
    AI_ML            = "ai_ml"
    BLOCKCHAIN       = "blockchain"
    BIOTECH          = "biotech"
    CLEANTECH        = "cleantech"
    CLOUD            = "cloud"
    CYBERSECURITY    = "cybersecurity"
    DRONE            = "drone"
    HARDWARE_IOT     = "hardware_iot"
    MEDTECH          = "medtech"
    NANOTECHNOLOGY   = "nanotechnology"
    ROBOTICS         = "robotics"
    SATELLITE        = "satellite"
    SOFTWARE_SAAS    = "software_saas"
    NONE             = "none"






_INDUSTRY_TO_SECTOR: Dict[str, IndianSector] = {
    "agriculture":          IndianSector.AGRITECH,
    "climate_tech":         IndianSector.CLEAN_ENERGY,
    "deep_tech":            IndianSector.DEEPTECH,
    "education":            IndianSector.EDTECH,
    "energy":               IndianSector.CLEAN_ENERGY,
    "fintech":              IndianSector.FINTECH,
    "govtech":              IndianSector.ICT,
    "health_tech":          IndianSector.HEALTHTECH,
    "logistics":            IndianSector.MOBILITY,
    "manufacturing":        IndianSector.MANUFACTURING,
    "media_entertainment":  IndianSector.OTHER,
    "real_estate":          IndianSector.OTHER,
    "retail":               IndianSector.OTHER,
    "saas":                 IndianSector.ICT,
    "social_impact":        IndianSector.SOCIAL_IMPACT,
    "other":                IndianSector.OTHER,
}

_STAGE_MAP: Dict[str, FundingStage] = {
    "idea":          FundingStage.IDEATION,
    "pre_seed":      FundingStage.PROOF_OF_CONCEPT,
    "seed":          FundingStage.EARLY_TRACTION,
    "series_a":      FundingStage.GROWTH,
    "series_b":      FundingStage.GROWTH,
    "series_c_plus": FundingStage.MATURE,
    "bootstrapped":  FundingStage.EARLY_TRACTION,
    "profitable":    FundingStage.MATURE,
}


_TECH_KEYWORDS: Dict[str, TechFocus] = {
    "artificial intelligence": TechFocus.AI_ML,
    "machine learning":        TechFocus.AI_ML,
    "deep learning":           TechFocus.AI_ML,
    "nlp":                     TechFocus.AI_ML,
    "blockchain":              TechFocus.BLOCKCHAIN,
    "web3":                    TechFocus.BLOCKCHAIN,
    "biotechnology":           TechFocus.BIOTECH,
    "genomics":                TechFocus.BIOTECH,
    "crispr":                  TechFocus.BIOTECH,
    "solar":                   TechFocus.CLEANTECH,
    "renewable":               TechFocus.CLEANTECH,
    "carbon":                  TechFocus.CLEANTECH,
    "cloud":                   TechFocus.CLOUD,
    "saas":                    TechFocus.SOFTWARE_SAAS,
    "cybersecurity":           TechFocus.CYBERSECURITY,
    "drone":                   TechFocus.DRONE,
    "uav":                     TechFocus.DRONE,
    "iot":                     TechFocus.HARDWARE_IOT,
    "hardware":                TechFocus.HARDWARE_IOT,
    "embedded":                TechFocus.HARDWARE_IOT,
    "medical device":          TechFocus.MEDTECH,
    "diagnostics":             TechFocus.MEDTECH,
    "nanotech":                TechFocus.NANOTECHNOLOGY,
    "nanoparticle":            TechFocus.NANOTECHNOLOGY,
    "robotics":                TechFocus.ROBOTICS,
    "automation":              TechFocus.ROBOTICS,
    "satellite":               TechFocus.SATELLITE,
    "space":                   TechFocus.SATELLITE,
}


_STATE_REGION: Dict[str, str] = {
    "andhra pradesh": "south", "telangana": "south", "karnataka": "south",
    "kerala": "south", "tamil nadu": "south",
    "maharashtra": "west", "gujarat": "west", "rajasthan": "west",
    "goa": "west",
    "delhi": "north", "haryana": "north", "punjab": "north",
    "uttar pradesh": "north", "uttarakhand": "north",
    "west bengal": "east", "odisha": "east", "bihar": "east",
    "jharkhand": "east", "assam": "northeast",
    "manipur": "northeast", "meghalaya": "northeast",
    "madhya pradesh": "central", "chhattisgarh": "central",
    "himachal pradesh": "north", "jammu and kashmir": "north",
}






@dataclass
class StartupAnalysis:
    
    company_name:        str = ""
    sector:              IndianSector = IndianSector.OTHER
    secondary_sector:    Optional[IndianSector] = None
    stage:               FundingStage = FundingStage.IDEATION
    tech_focus:          TechFocus = TechFocus.NONE
    is_dpiit_recognised: bool = False
    is_women_led:        bool = False
    state:               str = ""
    region:              str = ""
    team_size:           int = 1
    founding_year:       Optional[int] = None
    has_patent:          bool = False
    funding_needed_inr:  Optional[tuple] = None     
    readiness_score:     int = 0                     
    completeness_score:  int = 0                     
    missing_fields:      List[str] = field(default_factory=list)
    keywords:            Set[str] = field(default_factory=set)
    raw_industry:        str = ""
    raw_stage:           str = ""
    description:         str = ""

    def to_dict(self) -> dict:
        return {
            "company_name":        self.company_name,
            "sector":              self.sector.value,
            "secondary_sector":    self.secondary_sector.value if self.secondary_sector else None,
            "stage":               self.stage.value,
            "tech_focus":          self.tech_focus.value,
            "is_dpiit_recognised": self.is_dpiit_recognised,
            "is_women_led":        self.is_women_led,
            "state":               self.state,
            "region":              self.region,
            "team_size":           self.team_size,
            "founding_year":       self.founding_year,
            "has_patent":          self.has_patent,
            "readiness_score":     self.readiness_score,
            "completeness_score":  self.completeness_score,
            "missing_fields":      self.missing_fields,
            "keywords":            list(self.keywords),
        }






class StartupProfiler:
    

    
    _REQUIRED_FIELDS: List[str] = ["industry", "stage", "description"]

    
    _ADVISORY_FIELDS: List[tuple] = [
        ("problem_statement",  "Problem statement"),
        ("solution_statement", "Solution description"),
        ("impact_statement",   "Impact statement"),
        ("state_province",     "Indian state of operations"),
        ("funding_needed",     "Funding amount needed"),
        ("founding_year",      "Year of incorporation"),
        ("team_size",          "Team size"),
        ("website",            "Company website"),
        ("target_market",      "Target market description"),
        ("technology_stack",   "Technology stack"),
    ]

    def analyse(self, profile: dict) -> StartupAnalysis:
        
        from backend.grant_engine.exceptions import InsufficientProfileError

        
        missing_required = []
        for f in self._REQUIRED_FIELDS:
            val = profile.get(f)
            if f == "industry" and not val:
                val = profile.get("sector")
            if not val:
                missing_required.append(f)
                
        if missing_required:
            raise InsufficientProfileError(
                f"Startup profile is missing required fields for grant matching: "
                f"{', '.join(missing_required)}.",
                missing_fields=missing_required,
            )

        
        missing_advisory = [
            label for field_key, label in self._ADVISORY_FIELDS
            if not profile.get(field_key, "")
        ]

        
        raw_industry = (profile.get("industry") or profile.get("sector") or "other").lower()
        sector = _INDUSTRY_TO_SECTOR.get(raw_industry, IndianSector.OTHER)

        
        raw_secondary = profile.get("secondary_industry", "")
        secondary_sector = (
            _INDUSTRY_TO_SECTOR.get(raw_secondary.lower())
            if raw_secondary else None
        )

        
        raw_stage = profile.get("stage", "idea").lower()
        stage = _STAGE_MAP.get(raw_stage, FundingStage.IDEATION)

        
        description_text = " ".join(filter(None, [
            profile.get("description", ""),
            profile.get("technology_stack", ""),
            profile.get("solution_statement", ""),
        ])).lower()
        tech_focus = self._detect_tech_focus(description_text)

        
        state = (profile.get("state_province") or "").strip().lower()
        region = _STATE_REGION.get(state, "")

        
        is_women_led = "women" in description_text or "woman" in description_text
        has_patent = any(
            kw in description_text
            for kw in ["patent", "ipr", "intellectual property", "trademark"]
        )
        is_dpiit = profile.get("is_dpiit_recognised", False) or (
            "dpiit" in description_text or "startup india" in description_text
        )

        
        keywords = self._extract_keywords(description_text)

        
        funding_text = profile.get("funding_needed", "")
        from backend.grant_engine.scoring import _parse_inr_range
        funding_range = _parse_inr_range(funding_text)

        
        completeness = profile.get("profile_score", 0)
        readiness = self._compute_readiness(profile, stage, completeness)

        analysis = StartupAnalysis(
            company_name=profile.get("company_name", ""),
            sector=sector,
            secondary_sector=secondary_sector,
            stage=stage,
            tech_focus=tech_focus,
            is_dpiit_recognised=is_dpiit,
            is_women_led=is_women_led,
            state=state,
            region=region,
            team_size=int(profile.get("team_size", 1) or 1),
            founding_year=profile.get("founding_year"),
            has_patent=has_patent,
            funding_needed_inr=funding_range,
            readiness_score=readiness,
            completeness_score=completeness,
            missing_fields=missing_advisory,
            keywords=keywords,
            raw_industry=raw_industry,
            raw_stage=raw_stage,
            description=profile.get("description", ""),
        )

        logger.info(
            "Startup profiled: %s | sector=%s stage=%s tech=%s readiness=%d",
            analysis.company_name,
            analysis.sector.value,
            analysis.stage.value,
            analysis.tech_focus.value,
            analysis.readiness_score,
        )
        return analysis

    
    @staticmethod
    def _detect_tech_focus(text: str) -> TechFocus:
        
        for keyword, tech in _TECH_KEYWORDS.items():
            if keyword in text:
                return tech
        return TechFocus.NONE

    @staticmethod
    def _extract_keywords(text: str) -> Set[str]:
        
        import re
        _STOP_WORDS = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "is", "are", "was", "our", "we", "that",
            "this", "by", "from", "has", "have", "it", "be", "as", "its",
            "which", "will", "can", "into", "their", "they",
        }
        tokens = re.findall(r"\b[a-z][a-z\-]{3,}\b", text)
        return {t for t in tokens if t not in _STOP_WORDS}

    @staticmethod
    def _compute_readiness(
        profile: dict,
        stage: FundingStage,
        completeness: int,
    ) -> int:
        
        score = completeness * 0.5   

        
        stage_bonus = {
            FundingStage.IDEATION:         0,
            FundingStage.PROOF_OF_CONCEPT: 10,
            FundingStage.EARLY_TRACTION:   20,
            FundingStage.GROWTH:           25,
            FundingStage.MATURE:           20,   
        }
        score += stage_bonus.get(stage, 0)

        
        narrative_fields = [
            "problem_statement",
            "solution_statement",
            "impact_statement",
        ]
        filled = sum(1 for f in narrative_fields if profile.get(f, ""))
        score += filled * 5

        
        if profile.get("funding_needed"):
            score += 5
        if profile.get("annual_revenue"):
            score += 5

        return min(100, max(0, round(score)))

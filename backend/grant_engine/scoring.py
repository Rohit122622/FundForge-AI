

import logging
import os
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional

logger = logging.getLogger("fundforge.grant_engine.scoring")





def _w(env_key: str, default: float) -> float:
    try:
        return float(os.getenv(env_key, str(default)))
    except ValueError:
        return default


WEIGHTS: Dict[str, float] = {
    "eligibility":          _w("GRANT_WEIGHT_ELIGIBILITY",   30.0),
    "industry_match":       _w("GRANT_WEIGHT_INDUSTRY",      20.0),
    "stage_match":          _w("GRANT_WEIGHT_STAGE",         15.0),
    "funding_alignment":    _w("GRANT_WEIGHT_FUNDING",       10.0),
    "deadline_urgency":     _w("GRANT_WEIGHT_DEADLINE",       5.0),
    "technology_match":     _w("GRANT_WEIGHT_TECHNOLOGY",     8.0),
    "location_match":       _w("GRANT_WEIGHT_LOCATION",       5.0),
    "innovation_level":     _w("GRANT_WEIGHT_INNOVATION",     4.0),
    "profile_completeness": _w("GRANT_WEIGHT_COMPLETENESS",   3.0),
}

_TOTAL_WEIGHT: float = sum(WEIGHTS.values())






@dataclass
class RecommendationReason:
    
    dimension: str
    score: float
    title: str
    detail: str
    is_positive: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension":   self.dimension,
            "score":       round(self.score, 3),
            "title":       self.title,
            "detail":      self.detail,
            "is_positive": self.is_positive,
        }






@dataclass
class RecommendationScore:
    

    
    eligibility:          float = 0.0
    industry_match:       float = 0.0
    stage_match:          float = 0.0
    funding_alignment:    float = 0.0
    deadline_urgency:     float = 0.0
    technology_match:     float = 0.0
    location_match:       float = 0.0
    innovation_level:     float = 0.0
    profile_completeness: float = 0.0

    
    composite: int = 0            
    confidence: str = "low"       
    reasons: List[RecommendationReason] = field(default_factory=list)

    def compute_composite(self) -> "RecommendationScore":
        
        dimension_values = {
            "eligibility":          self.eligibility,
            "industry_match":       self.industry_match,
            "stage_match":          self.stage_match,
            "funding_alignment":    self.funding_alignment,
            "deadline_urgency":     self.deadline_urgency,
            "technology_match":     self.technology_match,
            "location_match":       self.location_match,
            "innovation_level":     self.innovation_level,
            "profile_completeness": self.profile_completeness,
        }

        weighted_sum = sum(
            dimension_values[dim] * weight
            for dim, weight in WEIGHTS.items()
        )
        raw = weighted_sum / _TOTAL_WEIGHT  
        self.composite = min(100, max(0, round(raw * 100)))

        
        if self.eligibility >= 0.8 and self.composite >= 70:
            self.confidence = "high"
        elif self.eligibility >= 0.5 and self.composite >= 45:
            self.confidence = "medium"
        else:
            self.confidence = "low"

        logger.debug(
            "Composite score computed: %d (%s) | dimensions=%s",
            self.composite,
            self.confidence,
            {k: round(v, 2) for k, v in dimension_values.items()},
        )
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "composite":           self.composite,
            "confidence":          self.confidence,
            "eligibility":         round(self.eligibility, 3),
            "industry_match":      round(self.industry_match, 3),
            "stage_match":         round(self.stage_match, 3),
            "funding_alignment":   round(self.funding_alignment, 3),
            "deadline_urgency":    round(self.deadline_urgency, 3),
            "technology_match":    round(self.technology_match, 3),
            "location_match":      round(self.location_match, 3),
            "innovation_level":    round(self.innovation_level, 3),
            "profile_completeness": round(self.profile_completeness, 3),
            "reasons":             [r.to_dict() for r in self.reasons],
        }






def score_deadline_urgency(deadline: Optional[date]) -> float:
    
    if deadline is None:
        return 0.6  
    today = date.today()
    if deadline < today:
        return 0.0  
    days_left = (deadline - today).days
    if days_left <= 30:
        return 0.9
    if days_left <= 60:
        return 0.75
    if days_left <= 120:
        return 0.85
    if days_left <= 180:
        return 0.7
    return 0.5


def score_funding_alignment(
    startup_need: Optional[str],
    grant_min: Optional[float],
    grant_max: Optional[float],
    grant_typical: Optional[float],
) -> float:
    
    if grant_min is None and grant_max is None:
        return 0.5   

    parsed_need = _parse_inr_range(startup_need)
    if parsed_need is None:
        return 0.5   

    need_low, need_high = parsed_need
    effective_max  = grant_max or grant_typical or grant_min or 0
    effective_min  = grant_min or 0

    
    if need_low <= effective_max and need_high >= effective_min:
        
        overlap_low  = max(need_low, effective_min)
        overlap_high = min(need_high, effective_max)
        overlap = overlap_high - overlap_low
        need_range = max(1, need_high - need_low)
        overlap_ratio = min(1.0, overlap / need_range)
        return 0.5 + 0.5 * overlap_ratio

    
    if need_low > effective_max:
        ratio = effective_max / need_low if need_low > 0 else 0
        return max(0.1, min(0.4, ratio))

    
    return 0.4


def score_profile_completeness(profile_score: int) -> float:
    
    return max(0.0, min(1.0, profile_score / 100.0))


def _parse_inr_range(text: Optional[str]) -> Optional[tuple]:
    
    import re
    if not text:
        return None

    text = text.lower().replace(",", "").replace("₹", "").replace("inr", "").strip()

    def _to_inr(value: float, unit: str) -> float:
        unit = unit.lower()
        if "cr" in unit or "crore" in unit:
            return value * 1_00_00_000
        if "l" in unit or "lakh" in unit:
            return value * 1_00_000
        if "k" in unit:
            return value * 1_000
        return value

    
    range_pattern = re.compile(
        r"(\d+(?:\.\d+)?)\s*(cr(?:ore)?s?|l(?:akh)?s?|k)?\s*(?:to|-|–)\s*(\d+(?:\.\d+)?)\s*(cr(?:ore)?s?|l(?:akh)?s?|k)?",
        re.IGNORECASE,
    )
    m = range_pattern.search(text)
    if m:
        low  = _to_inr(float(m.group(1)), m.group(2) or "")
        high = _to_inr(float(m.group(3)), m.group(4) or "")
        return (min(low, high), max(low, high))

    
    single_pattern = re.compile(
        r"(\d+(?:\.\d+)?)\s*(cr(?:ore)?s?|l(?:akh)?s?|k)?",
        re.IGNORECASE,
    )
    m = single_pattern.search(text)
    if m:
        val = _to_inr(float(m.group(1)), m.group(2) or "")
        return (val * 0.7, val * 1.3)  

    return None

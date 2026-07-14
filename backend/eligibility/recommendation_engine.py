

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("fundforge.eligibility.recommendation_engine")


@dataclass
class EligibleGrant:
    
    grant_id:          str
    grant_name:        str
    match_score:       int
    eligibility_score: int
    overall_score:     int
    is_eligible:       bool
    confidence:        str
    action_items:      List[str]        = field(default_factory=list)
    grant_meta:        Dict[str, Any]   = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "grant_id":          self.grant_id,
            "grant_name":        self.grant_name,
            "match_score":       self.match_score,
            "eligibility_score": self.eligibility_score,
            "overall_score":     self.overall_score,
            "is_eligible":       self.is_eligible,
            "confidence":        self.confidence,
            "action_items":      self.action_items,
            "grant_meta":        self.grant_meta,
        }


class EligibilityRecommendationEngine:
    

    def __init__(
        self,
        eligibility_checker=None,
        recommendation_engine=None,
    ) -> None:
        self._checker = eligibility_checker
        self._rec_engine = recommendation_engine

    def recommend_with_eligibility(
        self,
        startup_profile:    Dict[str, Any],
        uploaded_doc_names: Optional[List[str]] = None,
        top_n:              int = 10,
    ) -> List[EligibleGrant]:
        
        from backend.eligibility.eligibility_checker import EligibilityChecker
        from backend.grant_engine.recommendation_engine import get_recommendation_engine
        from backend.grant_engine.grant_catalog import get_grant_catalog

        checker  = self._checker or EligibilityChecker()
        rec_eng  = self._rec_engine or get_recommendation_engine(top_n=top_n)

        
        try:
            rec_result = rec_eng.recommend(startup_profile, top_n=top_n)
        except Exception as exc:
            logger.error("Recommendation engine error: %s", exc)
            return []

        catalog = get_grant_catalog()
        eligible_grants: List[EligibleGrant] = []

        for rec in rec_result.recommendations:
            grant_obj = catalog.get_by_id(rec.grant_id)
            grant_data = grant_obj.to_dict() if grant_obj else {"id": rec.grant_id, "name": rec.grant_name}
            
            if grant_obj:
                grant_data.update({
                    "requires_dpiit":      grant_obj.requires_dpiit,
                    "max_company_age_years":grant_obj.max_company_age_years,
                    "eligible_stages":     [s.value for s in grant_obj.eligible_stages],
                    "max_team_size":       grant_obj.max_team_size,
                    "min_team_size":       grant_obj.min_team_size,
                    "target_sectors":      list(grant_obj.target_sectors),
                    "excluded_sectors":    list(grant_obj.excluded_sectors),
                    "max_funding_raised":  grant_obj.max_funding_raised,
                })

            try:
                elig_report = checker.check(
                    startup_profile     = startup_profile,
                    grant_data          = grant_data,
                    uploaded_doc_names  = uploaded_doc_names,
                )
                elig_score = elig_report.score
                is_eligible = elig_report.overall_eligible
                confidence  = elig_report.confidence
                actions     = elig_report.action_items
            except Exception as exc:
                logger.warning("Eligibility check failed for grant %s: %s", rec.grant_id, exc)
                elig_score  = 50
                is_eligible = True
                confidence  = "low"
                actions     = []

            
            overall = min(100, round(rec.composite * 0.60 + elig_score * 0.40))

            eligible_grants.append(EligibleGrant(
                grant_id          = rec.grant_id,
                grant_name        = rec.grant_name,
                match_score       = rec.composite,
                eligibility_score = elig_score,
                overall_score     = overall,
                is_eligible       = is_eligible,
                confidence        = confidence,
                action_items      = actions,
                grant_meta        = grant_data,
            ))

        
        eligible_grants.sort(key=lambda g: -g.overall_score)
        return eligible_grants

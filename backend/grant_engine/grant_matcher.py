

import logging
from typing import List, Optional

from backend.grant_engine.grant_catalog import IndianGrant
from backend.grant_engine.grant_filter import FilterResult
from backend.grant_engine.startup_profiler import (
    FundingStage,
    IndianSector,
    StartupAnalysis,
    TechFocus,
)
from backend.grant_engine.scoring import (
    RecommendationScore,
    RecommendationReason,
    score_deadline_urgency,
    score_funding_alignment,
    score_profile_completeness,
)

logger = logging.getLogger("fundforge.grant_engine.grant_matcher")






_STAGE_ORDER = [
    FundingStage.IDEATION,
    FundingStage.PROOF_OF_CONCEPT,
    FundingStage.EARLY_TRACTION,
    FundingStage.GROWTH,
    FundingStage.MATURE,
]

_STAGE_SCORE_BY_DISTANCE = {
    0: 1.0,    
    1: 0.75,   
    2: 0.45,   
    3: 0.15,   
    4: 0.0,    
}






class GrantMatcher:
    

    def score(
        self,
        startup: StartupAnalysis,
        grant: IndianGrant,
        filter_result: Optional[FilterResult] = None,
    ) -> RecommendationScore:
        
        
        eligibility = (
            filter_result.eligibility_score
            if filter_result else 0.5
        )

        
        industry_score, industry_reasons = self._score_industry(startup, grant)

        
        stage_score, stage_reasons = self._score_stage(startup, grant)

        
        funding_score, funding_reasons = self._score_funding(startup, grant)

        
        deadline_score, deadline_reasons = self._score_deadline(grant)

        
        tech_score, tech_reasons = self._score_technology(startup, grant)

        
        location_score, location_reasons = self._score_location(startup, grant)

        
        innovation_score, innovation_reasons = self._score_innovation(startup, grant)

        
        completeness_score = score_profile_completeness(startup.completeness_score)
        completeness_reasons = [RecommendationReason(
            dimension="profile_completeness",
            score=completeness_score,
            title=f"Profile {startup.completeness_score}% complete",
            detail=(
                f"A more complete profile improves recommendation accuracy. "
                f"Missing: {', '.join(startup.missing_fields[:3])}"
            ) if startup.missing_fields else
            "Profile is well-completed — strong recommendation basis.",
            is_positive=completeness_score >= 0.6,
        )]

        
        eligibility_reasons = [RecommendationReason(
            dimension="eligibility",
            score=eligibility,
            title="Eligibility check",
            detail=self._eligibility_detail(filter_result, grant),
            is_positive=eligibility >= 0.5,
        )]

        all_reasons = (
            eligibility_reasons
            + industry_reasons
            + stage_reasons
            + funding_reasons
            + deadline_reasons
            + tech_reasons
            + location_reasons
            + innovation_reasons
            + completeness_reasons
        )

        score = RecommendationScore(
            eligibility          = eligibility,
            industry_match       = industry_score,
            stage_match          = stage_score,
            funding_alignment    = funding_score,
            deadline_urgency     = deadline_score,
            technology_match     = tech_score,
            location_match       = location_score,
            innovation_level     = innovation_score,
            profile_completeness = completeness_score,
            reasons              = all_reasons,
        ).compute_composite()

        logger.debug(
            "Match scored: startup=%s grant=%s composite=%d",
            startup.company_name, grant.id, score.composite,
        )
        return score

    def score_batch(
        self,
        startup: StartupAnalysis,
        grants: List[IndianGrant],
        filter_results: Optional[List[FilterResult]] = None,
    ) -> List[RecommendationScore]:
        
        filter_map = {}
        if filter_results:
            filter_map = {fr.grant_id: fr for fr in filter_results}

        scores = []
        for grant in grants:
            fr = filter_map.get(grant.id)
            scores.append(self.score(startup, grant, filter_result=fr))
        return scores

    
    @staticmethod
    def _score_industry(
        startup: StartupAnalysis,
        grant: IndianGrant,
    ) -> tuple:
        
        from backend.grant_engine.grant_catalog import IndianSector as _IS

        all_sectors = set(_IS)
        is_all_sectors_grant = len(grant.target_sectors) >= len(all_sectors) - 1

        if is_all_sectors_grant:
            s = 0.7  
            return s, [RecommendationReason(
                dimension="industry_match",
                score=s,
                title="Open to all sectors",
                detail=f"'{grant.short_name}' is open to all industries including yours.",
                is_positive=True,
            )]

        startup_sectors = {startup.sector}
        if startup.secondary_sector:
            startup_sectors.add(startup.secondary_sector)

        overlap = startup_sectors.intersection(grant.target_sectors)

        if startup.sector in grant.target_sectors:
            s = 1.0
            detail = f"Your primary sector '{startup.sector.value}' is a direct match."
        elif overlap:
            s = 0.85
            detail = f"Your secondary sector matches '{grant.short_name}'."
        else:
            s = 0.2
            detail = (
                f"Your sector '{startup.sector.value}' is not in the primary targets "
                f"for '{grant.short_name}'. May qualify if activities overlap."
            )

        return s, [RecommendationReason(
            dimension="industry_match",
            score=s,
            title="Sector alignment",
            detail=detail,
            is_positive=s >= 0.5,
        )]

    @staticmethod
    def _score_stage(
        startup: StartupAnalysis,
        grant: IndianGrant,
    ) -> tuple:
        
        if not grant.eligible_stages:
            return 0.7, []

        if startup.stage in grant.eligible_stages:
            s = 1.0
            detail = f"Your stage '{startup.stage.value}' is a perfect match."
        else:
            startup_idx = _STAGE_ORDER.index(startup.stage) if startup.stage in _STAGE_ORDER else 0
            min_dist = min(
                abs(startup_idx - _STAGE_ORDER.index(es))
                for es in grant.eligible_stages
                if es in _STAGE_ORDER
            )
            s = _STAGE_SCORE_BY_DISTANCE.get(min_dist, 0.0)
            detail = (
                f"Your stage ({startup.stage.value}) is {min_dist} step(s) away "
                f"from '{grant.short_name}' ideal stages."
            )

        return s, [RecommendationReason(
            dimension="stage_match",
            score=s,
            title="Stage match",
            detail=detail,
            is_positive=s >= 0.5,
        )]

    @staticmethod
    def _score_funding(
        startup: StartupAnalysis,
        grant: IndianGrant,
    ) -> tuple:
        
        need_low = need_high = None
        if startup.funding_needed_inr:
            need_low, need_high = startup.funding_needed_inr

        s = score_funding_alignment(
            startup_need=None if not startup.funding_needed_inr else
                         f"{need_low}-{need_high}",
            grant_min=grant.min_amount_inr,
            grant_max=grant.max_amount_inr,
            grant_typical=grant.typical_amount_inr,
        )

        if grant.max_amount_inr:
            amount_str = f"₹{grant.max_amount_inr / 1_00_000:.0f}L"
            detail = f"Grant offers up to {amount_str}."
        else:
            detail = "Grant amount not specified."

        return s, [RecommendationReason(
            dimension="funding_alignment",
            score=s,
            title="Funding alignment",
            detail=detail,
            is_positive=s >= 0.5,
        )]

    @staticmethod
    def _score_deadline(grant: IndianGrant) -> tuple:
        
        s = score_deadline_urgency(grant.deadline)
        if grant.deadline is None:
            detail = f"'{grant.short_name}' accepts rolling applications — apply anytime."
        else:
            from datetime import date
            days = (grant.deadline - date.today()).days
            detail = f"{days} days until the {grant.deadline} deadline."

        return s, [RecommendationReason(
            dimension="deadline_urgency",
            score=s,
            title="Deadline urgency",
            detail=detail,
            is_positive=s >= 0.5,
        )]

    @staticmethod
    def _score_technology(
        startup: StartupAnalysis,
        grant: IndianGrant,
    ) -> tuple:
        
        if not grant.target_tech_focus:
            return 0.6, []  

        from backend.grant_engine.startup_profiler import TechFocus as _TF
        if startup.tech_focus == _TF.NONE:
            s = 0.4
            detail = "No specific technology focus detected in your profile."
        elif startup.tech_focus in grant.target_tech_focus:
            s = 1.0
            detail = f"Your tech focus ({startup.tech_focus.value}) is a direct match."
        else:
            s = 0.35
            detail = (
                f"Your tech ({startup.tech_focus.value}) differs from "
                f"'{grant.short_name}' preferred technologies."
            )

        
        if grant.innovation_keywords and startup.keywords:
            overlap = startup.keywords.intersection(
                {k.lower() for k in grant.innovation_keywords}
            )
            if overlap:
                s = min(1.0, s + 0.1 * len(overlap))

        return s, [RecommendationReason(
            dimension="technology_match",
            score=s,
            title="Technology match",
            detail=detail,
            is_positive=s >= 0.5,
        )]

    @staticmethod
    def _score_location(
        startup: StartupAnalysis,
        grant: IndianGrant,
    ) -> tuple:
        
        if not grant.indian_states:
            return 0.85, []   

        if startup.state in grant.indian_states:
            s = 1.0
            detail = f"Your state ({startup.state.title()}) qualifies for this regional scheme."
        elif not startup.state:
            s = 0.5
            detail = "State not specified — cannot confirm location eligibility."
        else:
            s = 0.0
            detail = (
                f"'{grant.short_name}' is only for: "
                f"{', '.join(sorted(grant.indian_states)).title()}."
            )

        return s, [RecommendationReason(
            dimension="location_match",
            score=s,
            title="Location match",
            detail=detail,
            is_positive=s >= 0.5,
        )]

    @staticmethod
    def _score_innovation(
        startup: StartupAnalysis,
        grant: IndianGrant,
    ) -> tuple:
        
        innovation_signals = 0

        if startup.tech_focus != TechFocus.NONE:
            innovation_signals += 2
        if startup.has_patent:
            innovation_signals += 2
        if grant.innovation_keywords:
            keyword_hits = startup.keywords.intersection(
                {k.lower() for k in grant.innovation_keywords}
            )
            innovation_signals += min(3, len(keyword_hits))

        
        deep_tech_sectors = {
            IndianSector.DEEPTECH, IndianSector.BIOTECH,
            IndianSector.SPACE_TECH, IndianSector.CLEAN_ENERGY,
        }
        if startup.sector in deep_tech_sectors:
            innovation_signals += 1

        s = min(1.0, innovation_signals / 7.0)  

        detail = (
            f"Innovation signals detected: tech focus ({startup.tech_focus.value})"
            + (", patent filed" if startup.has_patent else "")
            + "."
        )

        return s, [RecommendationReason(
            dimension="innovation_level",
            score=s,
            title="Innovation level",
            detail=detail,
            is_positive=s >= 0.4,
        )]

    @staticmethod
    def _eligibility_detail(
        filter_result: Optional[FilterResult],
        grant: IndianGrant,
    ) -> str:
        
        if filter_result is None:
            return "Eligibility not fully verified."
        score = filter_result.eligibility_score
        if score >= 0.9:
            return f"Strongly eligible for '{grant.short_name}'. All criteria met."
        if score >= 0.7:
            return f"Likely eligible — minor requirements need confirmation."
        if score >= 0.5:
            hard_fails = filter_result.hard_fail_reasons
            soft_count = len([v for v in filter_result.verdicts
                              if v.verdict.value == "soft_fail"])
            return (
                f"{soft_count} eligibility item(s) need clarification for "
                f"'{grant.short_name}'."
            )
        return f"Limited eligibility: {'; '.join(filter_result.hard_fail_reasons[:2])}"

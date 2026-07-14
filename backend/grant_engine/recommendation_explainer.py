

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List

from backend.grant_engine.grant_catalog import IndianGrant
from backend.grant_engine.grant_ranker import RankedGrant
from backend.grant_engine.scoring import RecommendationReason, RecommendationScore
from backend.grant_engine.startup_profiler import StartupAnalysis

logger = logging.getLogger("fundforge.grant_engine.recommendation_explainer")






@dataclass
class GrantExplanation:
    
    grant_id:       str
    summary:        str
    strengths:      List[RecommendationReason] = field(default_factory=list)
    gaps:           List[RecommendationReason] = field(default_factory=list)
    action_items:   List[str] = field(default_factory=list)
    missing_fields: List[str] = field(default_factory=list)
    readiness_note: str = ""
    confidence_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "grant_id":        self.grant_id,
            "summary":         self.summary,
            "strengths":       [r.to_dict() for r in self.strengths],
            "gaps":            [r.to_dict() for r in self.gaps],
            "action_items":    self.action_items,
            "missing_fields":  self.missing_fields,
            "readiness_note":  self.readiness_note,
            "confidence_note": self.confidence_note,
        }






class RecommendationExplainer:
    

    def explain(
        self,
        startup: StartupAnalysis,
        ranked_grant: RankedGrant,
    ) -> GrantExplanation:
        
        grant = ranked_grant.grant
        score = ranked_grant.score

        strengths = sorted(
            [r for r in score.reasons if r.is_positive and r.score >= 0.6],
            key=lambda r: -r.score,
        )[:3]

        gaps = sorted(
            [r for r in score.reasons if not r.is_positive],
            key=lambda r: r.score,
        )[:3]

        summary     = self._build_summary(startup, grant, score, ranked_grant.rank)
        actions     = self._build_action_items(startup, grant, score, gaps)
        readiness   = self._build_readiness_note(startup)
        confidence  = self._build_confidence_note(score)
        missing     = startup.missing_fields[:5]

        expl = GrantExplanation(
            grant_id=grant.id,
            summary=summary,
            strengths=strengths,
            gaps=gaps,
            action_items=actions,
            missing_fields=missing,
            readiness_note=readiness,
            confidence_note=confidence,
        )

        logger.debug(
            "Explanation built: grant=%s score=%d strengths=%d gaps=%d",
            grant.id, score.composite, len(strengths), len(gaps),
        )
        return expl

    def explain_batch(
        self,
        startup: StartupAnalysis,
        ranked_grants: List[RankedGrant],
    ) -> List[GrantExplanation]:
        
        return [self.explain(startup, rg) for rg in ranked_grants]

    
    @staticmethod
    def _build_summary(
        startup: StartupAnalysis,
        grant: IndianGrant,
        score: RecommendationScore,
        rank: int,
    ) -> str:
        
        company = startup.company_name or "Your startup"
        gname   = grant.short_name or grant.name

        if score.composite >= 80:
            verdict = f"{company} is an excellent match for {gname} (score: {score.composite}/100)."
            action  = "We strongly recommend applying in the current cycle."
        elif score.composite >= 60:
            verdict = f"{company} is a strong candidate for {gname} (score: {score.composite}/100)."
            action  = "Prepare your application — this is a high-priority opportunity."
        elif score.composite >= 40:
            verdict = f"{company} has a moderate match with {gname} (score: {score.composite}/100)."
            action  = "Some criteria need attention before applying — review the gaps below."
        else:
            verdict = f"{company} has a partial match with {gname} (score: {score.composite}/100)."
            action  = "Address the listed gaps to strengthen your eligibility before applying."

        return f"{verdict} {action}"

    @staticmethod
    def _build_action_items(
        startup: StartupAnalysis,
        grant: IndianGrant,
        score: RecommendationScore,
        gaps: List[RecommendationReason],
    ) -> List[str]:
        
        actions: List[str] = []

        
        if grant.requires_dpiit and not startup.is_dpiit_recognised:
            actions.append(
                "Apply for DPIIT recognition at startupindia.gov.in — "
                f"it is required for {grant.short_name}."
            )

        
        if startup.completeness_score < 60:
            actions.append(
                "Complete your startup profile (currently "
                f"{startup.completeness_score}%) to unlock better recommendations."
            )

        
        if grant.indian_states and not startup.state:
            actions.append(
                f"Add your Indian state to confirm eligibility for the "
                f"{grant.short_name} regional scheme."
            )

        
        if grant.max_company_age_years and not startup.founding_year:
            actions.append(
                f"Add your founding year — {grant.short_name} has a "
                f"{grant.max_company_age_years}-year company age limit."
            )

        
        for gap in gaps:
            if gap.dimension == "eligibility" and gap.detail:
                actions.append(f"Eligibility: {gap.detail}")
            elif gap.dimension == "technology_match" and gap.detail:
                actions.append(f"Technology: {gap.detail}")

        
        actions.append(
            f"Visit the official application portal: {grant.application_url}"
        )

        return actions[:6]   

    @staticmethod
    def _build_readiness_note(startup: StartupAnalysis) -> str:
        
        r = startup.readiness_score
        if r >= 75:
            return (
                f"Funding readiness: {r}/100 — Strong. "
                "Your profile demonstrates clear problem-solution fit and traction."
            )
        if r >= 50:
            return (
                f"Funding readiness: {r}/100 — Moderate. "
                "Adding a problem statement and impact metrics will strengthen your applications."
            )
        return (
            f"Funding readiness: {r}/100 — Early stage. "
            "Complete your narrative sections (problem, solution, impact) to improve readiness."
        )

    @staticmethod
    def _build_confidence_note(score: RecommendationScore) -> str:
        
        conf_map = {
            "high": (
                "High confidence — eligibility criteria strongly met and sector/stage "
                "alignment is excellent. Recommendation is based on solid profile data."
            ),
            "medium": (
                "Medium confidence — most criteria are met but some information is "
                "missing or ambiguous. Complete your profile for a more accurate assessment."
            ),
            "low": (
                "Low confidence — limited profile information available. "
                "Complete your startup profile to receive higher-confidence recommendations."
            ),
        }
        return conf_map.get(score.confidence, "")



import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple

from backend.grant_engine.grant_catalog import IndianGrant
from backend.grant_engine.startup_profiler import FundingStage, StartupAnalysis

logger = logging.getLogger("fundforge.grant_engine.grant_filter")






class VerdictType(str, Enum):
    PASS      = "pass"
    SOFT_FAIL = "soft_fail"
    HARD_FAIL = "hard_fail"


@dataclass
class FilterVerdict:
    
    rule:    str
    verdict: VerdictType
    reason:  str = ""

    @property
    def passes(self) -> bool:
        return self.verdict != VerdictType.HARD_FAIL

    @property
    def is_hard_fail(self) -> bool:
        return self.verdict == VerdictType.HARD_FAIL


@dataclass
class FilterResult:
    
    grant_id:          str
    is_eligible:       bool
    eligibility_score: float
    verdicts:          List[FilterVerdict] = field(default_factory=list)
    hard_fail_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "grant_id":          self.grant_id,
            "is_eligible":       self.is_eligible,
            "eligibility_score": round(self.eligibility_score, 3),
            "hard_fail_reasons": self.hard_fail_reasons,
        }






class GrantFilter:
    

    def __init__(self, strict_mode: bool = False):
        self._strict = strict_mode

    
    def filter_catalog(
        self,
        startup: StartupAnalysis,
        grants: List[IndianGrant],
    ) -> Tuple[List[IndianGrant], List[FilterResult]]:
        
        eligible: List[IndianGrant] = []
        results:  List[FilterResult] = []

        for grant in grants:
            result = self.check_eligibility(startup, grant)
            results.append(result)
            if result.is_eligible:
                eligible.append(grant)

        logger.info(
            "Grant filter: %d/%d grants passed for %s",
            len(eligible), len(grants), startup.company_name,
        )
        return eligible, results

    def check_eligibility(
        self,
        startup: StartupAnalysis,
        grant: IndianGrant,
    ) -> FilterResult:
        
        verdicts: List[FilterVerdict] = []

        
        verdicts.append(self._rule_grant_open(grant))
        verdicts.append(self._rule_dpiit(startup, grant))
        verdicts.append(self._rule_company_age(startup, grant))
        verdicts.append(self._rule_stage(startup, grant))
        verdicts.append(self._rule_sector(startup, grant))
        verdicts.append(self._rule_funding_raised(startup, grant))
        verdicts.append(self._rule_location(startup, grant))
        verdicts.append(self._rule_team_size(startup, grant))

        
        hard_fails = [v for v in verdicts if v.is_hard_fail]
        soft_fails = [v for v in verdicts if v.verdict == VerdictType.SOFT_FAIL]

        
        if hard_fails and (self._strict or len(hard_fails) > 0):
            return FilterResult(
                grant_id=grant.id,
                is_eligible=False,
                eligibility_score=0.0,
                verdicts=verdicts,
                hard_fail_reasons=[v.reason for v in hard_fails],
            )

        
        passes   = len([v for v in verdicts if v.verdict == VerdictType.PASS])
        total    = len(verdicts)
        base_score = passes / total if total > 0 else 0.0
        
        soft_penalty = min(0.4, len(soft_fails) * 0.1)
        eligibility_score = max(0.0, base_score - soft_penalty)

        return FilterResult(
            grant_id=grant.id,
            is_eligible=True,
            eligibility_score=round(eligibility_score, 3),
            verdicts=verdicts,
        )

    
    @staticmethod
    def _rule_grant_open(grant: IndianGrant) -> FilterVerdict:
        
        if grant.is_open:
            return FilterVerdict(rule="grant_open", verdict=VerdictType.PASS)
        return FilterVerdict(
            rule="grant_open",
            verdict=VerdictType.HARD_FAIL,
            reason=f"Grant '{grant.short_name}' is closed or expired.",
        )

    @staticmethod
    def _rule_dpiit(startup: StartupAnalysis, grant: IndianGrant) -> FilterVerdict:
        
        if not grant.requires_dpiit:
            return FilterVerdict(rule="dpiit", verdict=VerdictType.PASS)
        if startup.is_dpiit_recognised:
            return FilterVerdict(rule="dpiit", verdict=VerdictType.PASS)
        
        return FilterVerdict(
            rule="dpiit",
            verdict=VerdictType.SOFT_FAIL,
            reason=f"'{grant.short_name}' requires DPIIT recognition. "
                   "Please confirm your DPIIT status.",
        )

    @staticmethod
    def _rule_company_age(startup: StartupAnalysis, grant: IndianGrant) -> FilterVerdict:
        
        if grant.max_company_age_years is None:
            return FilterVerdict(rule="company_age", verdict=VerdictType.PASS)
        if startup.founding_year is None:
            return FilterVerdict(
                rule="company_age",
                verdict=VerdictType.SOFT_FAIL,
                reason="Founding year not provided; cannot verify age eligibility.",
            )
        import datetime
        company_age = datetime.date.today().year - startup.founding_year
        if company_age <= grant.max_company_age_years:
            return FilterVerdict(rule="company_age", verdict=VerdictType.PASS)
        return FilterVerdict(
            rule="company_age",
            verdict=VerdictType.HARD_FAIL,
            reason=(
                f"Company is {company_age} years old; "
                f"'{grant.short_name}' requires max {grant.max_company_age_years} years."
            ),
        )

    @staticmethod
    def _rule_stage(startup: StartupAnalysis, grant: IndianGrant) -> FilterVerdict:
        
        if not grant.eligible_stages:
            return FilterVerdict(rule="stage", verdict=VerdictType.PASS)
        if startup.stage in grant.eligible_stages:
            return FilterVerdict(rule="stage", verdict=VerdictType.PASS)
        
        stage_order = [
            FundingStage.IDEATION,
            FundingStage.PROOF_OF_CONCEPT,
            FundingStage.EARLY_TRACTION,
            FundingStage.GROWTH,
            FundingStage.MATURE,
        ]
        startup_idx = stage_order.index(startup.stage) if startup.stage in stage_order else -1
        for eligible_stage in grant.eligible_stages:
            eligible_idx = stage_order.index(eligible_stage) if eligible_stage in stage_order else -1
            if abs(startup_idx - eligible_idx) == 1:
                return FilterVerdict(
                    rule="stage",
                    verdict=VerdictType.SOFT_FAIL,
                    reason=(
                        f"Your stage ({startup.stage.value}) is adjacent to "
                        f"'{grant.short_name}' eligible stages — may qualify."
                    ),
                )
        return FilterVerdict(
            rule="stage",
            verdict=VerdictType.HARD_FAIL,
            reason=(
                f"Stage mismatch: your stage '{startup.stage.value}' is not "
                f"eligible for '{grant.short_name}'."
            ),
        )

    @staticmethod
    def _rule_sector(startup: StartupAnalysis, grant: IndianGrant) -> FilterVerdict:
        
        if startup.sector in grant.excluded_sectors:
            return FilterVerdict(
                rule="sector",
                verdict=VerdictType.HARD_FAIL,
                reason=(
                    f"Sector '{startup.sector.value}' is explicitly excluded "
                    f"from '{grant.short_name}'."
                ),
            )

        from backend.grant_engine.grant_catalog import IndianSector as _IS
        
        if len(grant.target_sectors) >= len(_IS.__members__) - 1:
            return FilterVerdict(rule="sector", verdict=VerdictType.PASS)

        
        sectors_to_check = {startup.sector}
        if startup.secondary_sector:
            sectors_to_check.add(startup.secondary_sector)

        if sectors_to_check.intersection(grant.target_sectors):
            return FilterVerdict(rule="sector", verdict=VerdictType.PASS)

        return FilterVerdict(
            rule="sector",
            verdict=VerdictType.SOFT_FAIL,
            reason=(
                f"Your sector '{startup.sector.value}' is not in primary targets "
                f"for '{grant.short_name}' — may still apply if activities overlap."
            ),
        )

    @staticmethod
    def _rule_funding_raised(startup: StartupAnalysis, grant: IndianGrant) -> FilterVerdict:
        
        if grant.max_funding_raised is None:
            return FilterVerdict(rule="funding_raised", verdict=VerdictType.PASS)
        
        return FilterVerdict(
            rule="funding_raised",
            verdict=VerdictType.SOFT_FAIL,
            reason=(
                f"'{grant.short_name}' has a prior-funding cap of "
                f"₹{grant.max_funding_raised / 1_00_00_000:.0f} crore. "
                "Please verify your total funding raised."
            ),
        )

    @staticmethod
    def _rule_location(startup: StartupAnalysis, grant: IndianGrant) -> FilterVerdict:
        
        if not grant.indian_states:
            return FilterVerdict(rule="location", verdict=VerdictType.PASS)
        if startup.state in grant.indian_states:
            return FilterVerdict(rule="location", verdict=VerdictType.PASS)
        if not startup.state:
            return FilterVerdict(
                rule="location",
                verdict=VerdictType.SOFT_FAIL,
                reason=(
                    f"'{grant.short_name}' is restricted to: "
                    f"{', '.join(sorted(grant.indian_states))}. "
                    "Please confirm your state."
                ),
            )
        return FilterVerdict(
            rule="location",
            verdict=VerdictType.HARD_FAIL,
            reason=(
                f"'{grant.short_name}' is only available in "
                f"{', '.join(sorted(grant.indian_states))}. "
                f"Your registered state is '{startup.state}'."
            ),
        )

    @staticmethod
    def _rule_team_size(startup: StartupAnalysis, grant: IndianGrant) -> FilterVerdict:
        
        if grant.max_team_size is not None and startup.team_size > grant.max_team_size:
            return FilterVerdict(
                rule="team_size",
                verdict=VerdictType.HARD_FAIL,
                reason=(
                    f"'{grant.short_name}' is for max {grant.max_team_size} person(s); "
                    f"your team has {startup.team_size}."
                ),
            )
        if startup.team_size < grant.min_team_size:
            return FilterVerdict(
                rule="team_size",
                verdict=VerdictType.SOFT_FAIL,
                reason=(
                    f"'{grant.short_name}' prefers min {grant.min_team_size} person(s); "
                    f"your team has {startup.team_size}."
                ),
            )
        return FilterVerdict(rule="team_size", verdict=VerdictType.PASS)

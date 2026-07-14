

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("fundforge.eligibility.rule_engine")






class RuleVerdict(str, Enum):
    PASS    = "pass"
    FAIL    = "fail"
    WARN    = "warn"
    UNKNOWN = "unknown"


@dataclass
class RuleResult:
    
    rule_id:     str
    rule_name:   str
    verdict:     RuleVerdict
    message:     str        = ""
    suggestion:  str        = ""
    weight:      float      = 1.0    
    is_blocking: bool       = False  

    @property
    def passed(self) -> bool:
        return self.verdict == RuleVerdict.PASS

    @property
    def failed(self) -> bool:
        return self.verdict == RuleVerdict.FAIL

    @property
    def is_hard_fail(self) -> bool:
        return self.failed and self.is_blocking

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id":    self.rule_id,
            "rule_name":  self.rule_name,
            "verdict":    self.verdict.value,
            "message":    self.message,
            "suggestion": self.suggestion,
            "is_blocking":self.is_blocking,
        }






class BaseRule(ABC):
    

    rule_id:     str   = ""
    rule_name:   str   = ""
    weight:      float = 1.0
    is_blocking: bool  = False

    @abstractmethod
    def evaluate(
        self,
        profile:    Dict[str, Any],
        grant:      Optional[Dict[str, Any]] = None,
        documents:  Optional[List[str]] = None,
    ) -> RuleResult:
        pass

    def _pass(self, msg: str = "") -> RuleResult:
        return RuleResult(self.rule_id, self.rule_name, RuleVerdict.PASS, msg, weight=self.weight, is_blocking=self.is_blocking)

    def _fail(self, msg: str = "", suggestion: str = "") -> RuleResult:
        return RuleResult(self.rule_id, self.rule_name, RuleVerdict.FAIL, msg, suggestion, weight=self.weight, is_blocking=self.is_blocking)

    def _warn(self, msg: str = "", suggestion: str = "") -> RuleResult:
        return RuleResult(self.rule_id, self.rule_name, RuleVerdict.WARN, msg, suggestion, weight=self.weight, is_blocking=False)

    def _unknown(self, msg: str = "") -> RuleResult:
        return RuleResult(self.rule_id, self.rule_name, RuleVerdict.UNKNOWN, msg, weight=self.weight, is_blocking=False)






class IndiaIncorporationRule(BaseRule):
    rule_id = "india_incorporation"; rule_name = "India Incorporation"; is_blocking = True; weight = 2.0

    def evaluate(self, profile, grant=None, documents=None):
        country = (profile.get("country") or "").lower()
        if not country:
            return self._unknown("Country not specified — cannot verify Indian incorporation.")
        if "india" in country:
            return self._pass("Company is incorporated in India.")
        return self._fail(
            f"Company country '{country}' is not India.",
            "Indian government grants require incorporation in India.",
        )


class DPIITRecognitionRule(BaseRule):
    rule_id = "dpiit_recognition"; rule_name = "DPIIT Recognition"; weight = 1.8

    def evaluate(self, profile, grant=None, documents=None):
        requires_dpiit = (grant or {}).get("requires_dpiit", False)
        has_dpiit = profile.get("is_dpiit_recognised", False) or bool(profile.get("dpiit_number"))
        desc_lower = (profile.get("description", "") + " " + (profile.get("solution_statement") or "")).lower()
        inferred   = "dpiit" in desc_lower or "startup india" in desc_lower

        if not requires_dpiit:
            return self._pass("DPIIT recognition not required for this scheme.")
        if has_dpiit or inferred:
            return self._pass("DPIIT recognition confirmed.")
        return self._warn(
            "DPIIT recognition status not confirmed.",
            "Register at startupindia.gov.in to obtain DPIIT recognition.",
        )


class CompanyAgeRule(BaseRule):
    rule_id = "company_age"; rule_name = "Company Age Limit"; weight = 1.5

    def evaluate(self, profile, grant=None, documents=None):
        max_years = (grant or {}).get("max_company_age_years")
        founding_year = profile.get("founding_year")
        if max_years is None:
            return self._pass("No company age restriction for this scheme.")
        if founding_year is None:
            return self._warn(
                "Founding year not provided.",
                f"Add your founding year — this scheme has a {max_years}-year limit.",
            )
        try:
            age = date.today().year - int(founding_year)
        except (ValueError, TypeError):
            return self._warn(
                "Founding year is invalid.",
                f"Update your founding year with a valid year (e.g., 2023) — this scheme has a {max_years}-year limit.",
            )
        if age <= max_years:
            return self._pass(f"Company age ({age} years) is within the {max_years}-year limit.")
        return self._fail(
            f"Company is {age} years old; scheme requires max {max_years} years.",
            "This scheme targets early-stage startups. Consider newer schemes for mature companies.",
        )


class FundingStageRule(BaseRule):
    rule_id = "funding_stage"; rule_name = "Funding Stage Match"; weight = 1.5

    _STAGE_MAP = {
        "idea": "ideation", "pre_seed": "proof_of_concept", "seed": "early_traction",
        "series_a": "growth", "series_b": "growth", "series_c_plus": "mature",
        "bootstrapped": "early_traction", "profitable": "mature",
        
        "ideation": "ideation", "proof_of_concept": "proof_of_concept",
        "early_traction": "early_traction", "growth": "growth", "mature": "mature",
    }

    def evaluate(self, profile, grant=None, documents=None):
        raw_stage = (profile.get("stage") or "").lower()
        mapped    = self._STAGE_MAP.get(raw_stage, raw_stage)
        eligible  = (grant or {}).get("eligible_stages", [])

        if not eligible:
            return self._pass("No stage restriction for this scheme.")
        if not raw_stage:
            return self._warn("Funding stage not specified.", "Add your current funding stage.")

        if mapped in eligible or raw_stage in eligible:
            return self._pass(f"Stage '{raw_stage}' matches scheme eligibility.")
        return self._warn(
            f"Stage '{raw_stage}' may not match scheme eligible stages: {eligible}.",
            "Review scheme requirements; adjacent stages sometimes qualify.",
        )


class TeamSizeRule(BaseRule):
    rule_id = "team_size"; rule_name = "Team Size"; weight = 1.0

    def evaluate(self, profile, grant=None, documents=None):
        max_team = (grant or {}).get("max_team_size")
        min_team = (grant or {}).get("min_team_size", 1)
        try:
            team_size = int(profile.get("team_size") or 1)
        except (ValueError, TypeError):
            team_size = 1

        if max_team and team_size > max_team:
            return self._fail(
                f"Team size {team_size} exceeds scheme maximum of {max_team}.",
                "This scheme targets individual innovators or very small teams.",
            )
        if team_size < min_team:
            return self._warn(
                f"Team size {team_size} is below the preferred minimum of {min_team}.",
                "Consider strengthening the team before applying.",
            )
        return self._pass(f"Team size ({team_size}) meets scheme requirements.")


class SectorMatchRule(BaseRule):
    rule_id = "sector_match"; rule_name = "Sector Alignment"; weight = 1.3

    def evaluate(self, profile, grant=None, documents=None):
        target_sectors = set((grant or {}).get("target_sectors", []))
        excluded       = set((grant or {}).get("excluded_sectors", []))
        from backend.grant_engine.startup_profiler import _INDUSTRY_TO_SECTOR
        raw_industry   = (profile.get("industry") or profile.get("sector", "")).lower()
        mapped         = _INDUSTRY_TO_SECTOR.get(raw_industry)
        sector_val     = mapped.value if mapped else raw_industry

        if sector_val in {s.value if hasattr(s, "value") else s for s in excluded}:
            return self._fail(f"Sector '{raw_industry}' is explicitly excluded from this scheme.")
        if not target_sectors:
            return self._pass("Scheme is open to all sectors.")
        all_vals = {s.value if hasattr(s, "value") else s for s in target_sectors}
        
        if len(all_vals) >= 15:
            return self._pass("Scheme is open to all sectors.")
        if sector_val in all_vals or raw_industry in all_vals:
            return self._pass(f"Sector '{raw_industry}' is a direct match.")
        return self._warn(
            f"Sector '{raw_industry}' is not in primary target sectors.",
            "You may still qualify if your activities overlap with scheme objectives.",
        )


class PriorFundingRule(BaseRule):
    rule_id = "prior_funding"; rule_name = "Prior Funding Cap"; weight = 1.2

    def evaluate(self, profile, grant=None, documents=None):
        cap = (grant or {}).get("max_funding_raised") or (grant or {}).get("max_funding")
        if cap is None:
            return self._pass("No prior funding cap for this scheme.")
        try:
            cap_val = float(cap)
        except (ValueError, TypeError):
            return self._pass("No prior funding cap for this scheme.")
            
        funding_raised = profile.get("total_funding_raised") or profile.get("funding_raised")
        if funding_raised is None:
            return self._warn(
                f"Prior funding cap is ₹{cap_val:,.0f}, but total funding raised is not specified in profile.",
                "Disclose your total funding raised in your profile."
            )
        try:
            fund_val = float(funding_raised)
        except (ValueError, TypeError):
            return self._warn("Invalid funding raised value.", "Update total funding raised with a valid number.")
            
        if fund_val <= cap_val:
            return self._pass(f"Prior funding raised (₹{fund_val:,.0f}) is within the cap of ₹{cap_val:,.0f}.")
        return self._fail(f"Prior funding raised (₹{fund_val:,.0f}) exceeds the scheme limit of ₹{cap_val:,.0f}.", "Look for other schemes or private capital options.")


class PANValidationRule(BaseRule):
    rule_id = "pan_validation"; rule_name = "PAN Validation"; weight = 1.0

    def evaluate(self, profile, grant=None, documents=None):
        import re
        pan = profile.get("pan_number") or profile.get("pan") or profile.get("PAN")
        if not pan:
            return self._warn("PAN number is missing from your profile.", "Please add your PAN number in your startup profile.")
        pan = str(pan).strip().upper()
        if not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$", pan):
            return self._warn(f"Invalid PAN format: '{pan}'.", "Update your PAN number to match standard format (e.g. ABCDE1234F).")
        return self._pass("Valid PAN number confirmed.")


class GSTValidationRule(BaseRule):
    rule_id = "gst_validation"; rule_name = "GSTIN Validation"; weight = 1.0

    def evaluate(self, profile, grant=None, documents=None):
        import re
        gst = profile.get("gstin") or profile.get("gst") or profile.get("GST")
        if not gst:
            return self._warn("GSTIN is missing from your profile.", "Please add your GSTIN in your startup profile.")
        gst = str(gst).strip().upper()
        if not re.match(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$", gst):
            return self._warn(f"Invalid GSTIN format: '{gst}'.", "Update your GSTIN to match standard Indian format (e.g. 22AAAAA0000A1Z5).")
        return self._pass("Valid GSTIN confirmed.")


class WebsiteValidationRule(BaseRule):
    rule_id = "website_validation"; rule_name = "Website Validation"; weight = 0.8

    def evaluate(self, profile, grant=None, documents=None):
        website = profile.get("website")
        if not website:
            return self._warn("Website URL is missing from your profile.", "Please add your company website URL.")
        website = str(website).strip().lower()
        if not ("." in website and (website.startswith("http") or website.startswith("www") or len(website) > 4)):
            return self._warn(f"Invalid website URL: '{website}'.", "Please update with a valid company website link.")
        return self._pass("Valid website URL confirmed.")


class RevenueValidationRule(BaseRule):
    rule_id = "revenue_validation"; rule_name = "Revenue Cap Check"; weight = 1.2

    def evaluate(self, profile, grant=None, documents=None):
        revenue_val = profile.get("annual_revenue") or profile.get("revenue")
        max_revenue = (grant or {}).get("max_revenue_cap") or (grant or {}).get("max_revenue")
        if max_revenue is None:
            return self._pass("No revenue restrictions for this scheme.")
        if revenue_val is None:
            return self._warn("Annual revenue not specified.", f"Provide your annual revenue — this scheme has a limit of ₹{float(max_revenue):,.0f}.")
        try:
            rev = float(revenue_val)
            cap = float(max_revenue)
        except (ValueError, TypeError):
            return self._pass("No revenue restrictions for this scheme.")
        if rev <= cap:
            return self._pass(f"Annual revenue (₹{rev:,.0f}) is within the limits.")
        return self._fail(f"Annual revenue (₹{rev:,.0f}) exceeds the limit of ₹{cap:,.0f}.", "This scheme is designed for smaller startups.")


class SisfsComplianceRule(BaseRule):
    rule_id = "sisfs_compliance"; rule_name = "SISFS Compliance check"; weight = 2.0

    def evaluate(self, profile, grant=None, documents=None):
        g_id = (grant or {}).get("id") or (grant or {}).get("slug") or ""
        if "sisfs" not in str(g_id).lower():
            return self._pass("Not a SISFS scheme — compliance check not applicable.")
            
        
        
        has_dpiit = profile.get("is_dpiit_recognised") or bool(profile.get("dpiit_number")) or bool(profile.get("has_dpiit"))
        if not has_dpiit:
            return self._fail("DPIIT Recognition is mandatory for SISFS.", "Apply for DPIIT recognition on startupindia.gov.in.")
            
        
        founding_year = profile.get("founding_year") or profile.get("founded_year")
        if founding_year:
            try:
                age = date.today().year - int(founding_year)
                if age > 2:
                    return self._fail(f"Startup age is {age} years. SISFS requires startup age to be less than 2 years from incorporation.", "Check other funding options for older startups.")
            except Exception:
                pass
                
        
        funding_raised = profile.get("total_funding_raised") or profile.get("funding_raised")
        if funding_raised:
            try:
                fund = float(funding_raised)
                if fund > 1000000:
                    return self._warn(f"Total funding raised is ₹{fund:,.0f}. Under SISFS, startups must not have received > ₹10 Lakhs in monetary support under other Govt schemes.", "Verify if prior funding was from government schemes.")
            except Exception:
                pass
                
        return self._pass("Satisfies Startup India Seed Fund Scheme (SISFS) core compliance criteria.")


class ProfileCompletenessRule(BaseRule):
    rule_id = "profile_completeness"; rule_name = "Profile Completeness"; weight = 0.8

    def evaluate(self, profile, grant=None, documents=None):
        score = int(profile.get("profile_score", 0) or 0)
        if score >= 70:
            return self._pass(f"Profile completeness is {score}% — sufficient for a strong application.")
        if score >= 40:
            return self._warn(
                f"Profile completeness is {score}%. A more complete profile improves success rate.",
                "Add problem statement, solution description, and impact statement.",
            )
        return self._warn(
            f"Profile completeness is {score}% — very sparse.",
            "Complete at least 70% of your profile before applying.",
        )






@dataclass
class EligibilityDecision:
    
    grant_id:         str
    grant_name:       str
    is_eligible:      bool
    confidence:       str               
    eligibility_score:float             
    rule_results:     List[RuleResult]  = field(default_factory=list)
    blocking_fails:   List[str]         = field(default_factory=list)
    warnings:         List[str]         = field(default_factory=list)
    suggestions:      List[str]         = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "grant_id":          self.grant_id,
            "grant_name":        self.grant_name,
            "is_eligible":       self.is_eligible,
            "confidence":        self.confidence,
            "eligibility_score": round(self.eligibility_score, 3),
            "rule_results":      [r.to_dict() for r in self.rule_results],
            "blocking_fails":    self.blocking_fails,
            "warnings":          self.warnings,
            "suggestions":       self.suggestions,
        }






class RuleEngine:
    

    _DEFAULT_RULES: List[BaseRule] = [
        IndiaIncorporationRule(),
        DPIITRecognitionRule(),
        CompanyAgeRule(),
        FundingStageRule(),
        TeamSizeRule(),
        SectorMatchRule(),
        PriorFundingRule(),
        ProfileCompletenessRule(),
        PANValidationRule(),
        GSTValidationRule(),
        WebsiteValidationRule(),
        RevenueValidationRule(),
        SisfsComplianceRule(),
    ]

    def __init__(self, extra_rules: Optional[List[BaseRule]] = None) -> None:
        self._rules = list(self._DEFAULT_RULES)
        if extra_rules:
            self._rules.extend(extra_rules)

    def evaluate(
        self,
        profile:   Dict[str, Any],
        grant:     Optional[Dict[str, Any]] = None,
        documents: Optional[List[str]] = None,
    ) -> EligibilityDecision:
        
        grant = grant or {}
        documents = documents or []
        results: List[RuleResult] = []

        for rule in self._rules:
            try:
                result = rule.evaluate(profile, grant, documents)
                results.append(result)
            except Exception as exc:
                logger.warning("Rule %s failed with exception: %s", rule.rule_id, exc)
                results.append(RuleResult(
                    rule.rule_id, rule.rule_name, RuleVerdict.UNKNOWN,
                    f"Rule evaluation error: {exc}",
                ))

        
        blocking_fails = [r.message for r in results if r.is_hard_fail]
        warnings       = [r.message for r in results if r.verdict == RuleVerdict.WARN]
        suggestions    = list({r.suggestion for r in results if r.suggestion})

        is_eligible = len(blocking_fails) == 0

        
        total_weight = sum(r.weight for r in results)
        earned = sum(
            r.weight if r.verdict == RuleVerdict.PASS
            else r.weight * 0.5 if r.verdict == RuleVerdict.WARN
            else r.weight * 0.3 if r.verdict == RuleVerdict.UNKNOWN
            else 0.0
            for r in results
        )
        score = earned / total_weight if total_weight > 0 else 0.0

        if score >= 0.80 and is_eligible:
            confidence = "high"
        elif score >= 0.55 and is_eligible:
            confidence = "medium"
        else:
            confidence = "low"

        decision = EligibilityDecision(
            grant_id          = grant.get("id", ""),
            grant_name        = grant.get("name", ""),
            is_eligible       = is_eligible,
            confidence        = confidence,
            eligibility_score = round(score, 3),
            rule_results      = results,
            blocking_fails    = blocking_fails,
            warnings          = warnings,
            suggestions       = suggestions[:8],
        )

        logger.info(
            "Eligibility decision: grant=%s eligible=%s score=%.2f confidence=%s",
            decision.grant_id or "?", is_eligible, score, confidence,
        )
        return decision

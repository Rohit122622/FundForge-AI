

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.eligibility.rule_engine import EligibilityDecision, RuleEngine
from backend.eligibility.document_checker import DocumentCheckResult, DocumentChecker
from backend.eligibility.exceptions import InsufficientProfileError

logger = logging.getLogger("fundforge.eligibility.eligibility_checker")


@dataclass
class EligibilityReport:
    
    startup_name:     str
    grant_id:         str
    grant_name:       str
    decision:         EligibilityDecision
    doc_check:        DocumentCheckResult
    overall_eligible: bool
    confidence:       str
    score:            int
    explanation:      str              = ""
    action_items:     List[str]        = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "startup_name":     self.startup_name,
            "grant_id":         self.grant_id,
            "grant_name":       self.grant_name,
            "overall_eligible": self.overall_eligible,
            "confidence":       self.confidence,
            "score":            self.score,
            "explanation":      self.explanation,
            "action_items":     self.action_items,
            "rule_decision":    self.decision.to_dict(),
            "document_check":   self.doc_check.to_dict(),
        }


class EligibilityChecker:
    

    _REQUIRED_FIELDS = ["company_name", "industry", "stage"]

    def __init__(
        self,
        rule_engine:      Optional[RuleEngine]      = None,
        document_checker: Optional[DocumentChecker] = None,
    ) -> None:
        self._rules = rule_engine or RuleEngine()
        self._docs  = document_checker or DocumentChecker()

    def check(
        self,
        startup_profile:     Dict[str, Any],
        grant_data:          Dict[str, Any],
        uploaded_doc_names:  Optional[List[str]] = None,
    ) -> EligibilityReport:
        
        missing = []
        for f in self._REQUIRED_FIELDS:
            val = startup_profile.get(f)
            if f == "industry" and not val:
                val = startup_profile.get("sector")
            if not val:
                missing.append(f)
                
        if missing:
            raise InsufficientProfileError(
                f"Profile missing required fields for eligibility check: {', '.join(missing)}.",
                missing_fields=missing,
            )

        grant_id   = grant_data.get("id", "default")
        grant_name = grant_data.get("name", "")

        
        decision = self._rules.evaluate(
            profile   = startup_profile,
            grant     = grant_data,
            documents = uploaded_doc_names or [],
        )

        
        doc_check = self._docs.check(
            grant_id            = grant_id,
            uploaded_doc_names  = uploaded_doc_names or [],
        )

        
        mandatory_docs_ok = len(doc_check.mandatory_missing) == 0
        overall_eligible  = decision.is_eligible and mandatory_docs_ok

        
        doc_score = doc_check.completeness_pct / 100.0
        combined  = (decision.eligibility_score * 0.70) + (doc_score * 0.30)
        score     = min(100, max(0, round(combined * 100)))

        
        if decision.confidence == "high" and doc_check.completeness_pct >= 80:
            confidence = "high"
        elif decision.confidence in ("high", "medium") and doc_check.completeness_pct >= 50:
            confidence = "medium"
        else:
            confidence = "low"

        
        explanation = self._build_explanation(
            startup_profile, grant_name, decision, doc_check, overall_eligible, score
        )

        
        actions = self._build_actions(decision, doc_check, startup_profile, grant_data)

        report = EligibilityReport(
            startup_name     = startup_profile.get("company_name", ""),
            grant_id         = grant_id,
            grant_name       = grant_name,
            decision         = decision,
            doc_check        = doc_check,
            overall_eligible = overall_eligible,
            confidence       = confidence,
            score            = score,
            explanation      = explanation,
            action_items     = actions,
        )

        logger.info(
            "EligibilityReport: company=%s grant=%s eligible=%s score=%d confidence=%s",
            report.startup_name, grant_id, overall_eligible, score, confidence,
        )
        return report

    
    @staticmethod
    def _build_explanation(
        profile:    Dict[str, Any],
        grant_name: str,
        decision:   EligibilityDecision,
        doc_check:  DocumentCheckResult,
        eligible:   bool,
        score:      int,
    ) -> str:
        company = profile.get("company_name", "Your startup")
        if eligible and score >= 70:
            return (
                f"{company} appears eligible for {grant_name} (score: {score}/100). "
                f"All critical eligibility criteria are met and key documents are in order. "
                f"Proceed with the application."
            )
        if eligible:
            return (
                f"{company} meets the core eligibility criteria for {grant_name} (score: {score}/100), "
                f"but some items need attention before submitting. "
                f"Review the action items below."
            )
        blocking = "; ".join(decision.blocking_fails[:2])
        return (
            f"{company} does not currently meet all eligibility criteria for {grant_name} "
            f"(score: {score}/100). Blocking issue(s): {blocking or 'see action items'}. "
            f"Address the listed items to improve eligibility."
        )

    @staticmethod
    def _build_actions(
        decision:   EligibilityDecision,
        doc_check:  DocumentCheckResult,
        profile:    Dict[str, Any],
        grant_data: Dict[str, Any],
    ) -> List[str]:
        actions: List[str] = []

        
        for fail in decision.blocking_fails[:2]:
            actions.append(f"[Critical] {fail}")

        
        for status in doc_check.mandatory_missing[:3]:
            actions.append(
                f"[Document] Upload '{status.requirement.name}': {status.requirement.hint}"
            )

        
        for sug in decision.suggestions[:3]:
            if sug not in actions:
                actions.append(f"[Eligibility] {sug}")

        
        for sug in doc_check.suggestions[:2]:
            if sug not in actions:
                actions.append(f"[Document] {sug}")

        
        score = int(profile.get("profile_score", 0) or 0)
        if score < 60:
            actions.append(
                f"[Profile] Complete your startup profile ({score}% done). "
                "A complete profile strengthens your application."
            )

        return actions[:10]



import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List

logger = logging.getLogger("fundforge.eligibility.readiness_score")


@dataclass
class ReadinessDimension:
    
    name:        str
    score:       int       
    max_score:   int
    notes:       List[str] = field(default_factory=list)

    @property
    def pct(self) -> float:
        return round(100.0 * self.score / self.max_score, 1) if self.max_score else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "score": self.score, "max_score": self.max_score,
                "pct": self.pct, "notes": self.notes}


@dataclass
class ReadinessResult:
    
    total_score:     int
    band:            str
    dimensions:      List[ReadinessDimension] = field(default_factory=list)
    missing_fields:  List[str]                = field(default_factory=list)
    recommendations: List[str]                = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_score":    self.total_score,
            "band":           self.band,
            "dimensions":     [d.to_dict() for d in self.dimensions],
            "missing_fields": self.missing_fields,
            "recommendations":self.recommendations,
        }


class ReadinessScorer:
    

    def score(
        self,
        profile:           Dict[str, Any],
        doc_completeness:  float = 100.0,   
    ) -> ReadinessResult:
        
        dimensions: List[ReadinessDimension] = []

        d1 = self._score_profile_completeness(profile)
        d2 = self._score_narrative(profile)
        d3 = self._score_financials(profile)
        d4 = self._score_team(profile)
        d5 = self._score_documents(doc_completeness)
        d6 = self._score_legal(profile)
        d7 = self._score_technology(profile)

        dimensions = [d1, d2, d3, d4, d5, d6, d7]
        total = sum(d.score for d in dimensions)

        if total >= 80:   band = "Excellent"
        elif total >= 60: band = "Good"
        elif total >= 40: band = "Fair"
        else:             band = "Needs Work"

        missing, recs = self._build_recommendations(profile, dimensions)

        result = ReadinessResult(
            total_score     = total,
            band            = band,
            dimensions      = dimensions,
            missing_fields  = missing,
            recommendations = recs,
        )
        logger.info(
            "Readiness score: company=%s score=%d band=%s",
            profile.get("company_name", "?"), total, band,
        )
        return result

    
    @staticmethod
    def _score_profile_completeness(profile: Dict[str, Any]) -> ReadinessDimension:
        raw = int(profile.get("profile_score", 0) or 0)
        pts = round(raw * 25 / 100)
        notes = []
        if raw < 70:
            notes.append(f"Profile is {raw}% complete — aim for 70%+.")
        return ReadinessDimension("Profile Completeness", pts, 25, notes)

    @staticmethod
    def _score_narrative(profile: Dict[str, Any]) -> ReadinessDimension:
        fields = [("problem_statement", "Problem statement", 7),
                  ("solution_statement", "Solution description", 7),
                  ("impact_statement", "Impact statement", 6)]
        pts, notes = 0, []
        for key, label, weight in fields:
            if profile.get(key, ""):
                pts += weight
            else:
                notes.append(f"Add '{label}' to strengthen your narrative.")
        return ReadinessDimension("Narrative Quality", pts, 20, notes)

    @staticmethod
    def _score_financials(profile: Dict[str, Any]) -> ReadinessDimension:
        pts, notes = 0, []
        stage = (profile.get("stage") or "").lower()
        is_early = stage in ("idea", "pre_seed", "seed", "")
        
        funding_needed = profile.get("funding_needed")
        revenue = profile.get("annual_revenue") or profile.get("revenue")
        funding_raised = profile.get("total_funding_raised") or profile.get("funding_raised")
        
        if funding_needed:
            pts += 6
        else:
            notes.append("Specify funding amount needed.")
        if revenue or is_early:
            pts += 5
        else:
            notes.append("Add current annual revenue bracket.")
        if funding_raised is not None or is_early:
            pts += 4
        else:
            notes.append("Specify funding raised to date.")
        return ReadinessDimension("Financials Clarity", pts, 15, notes)

    @staticmethod
    def _score_team(profile: Dict[str, Any]) -> ReadinessDimension:
        pts, notes = 0, []
        team = int(profile.get("team_size", 0) or 0)
        if team >= 2:   pts += 7
        elif team == 1: pts += 3
        else: notes.append("Specify team size.")
        if profile.get("founding_year") or profile.get("founded_year"):
            pts += 5
        else:
            notes.append("Add founding year.")
        if profile.get("target_market"):
            pts += 3
        else:
            notes.append("Add target market description.")
        return ReadinessDimension("Team & Operations", pts, 15, notes)

    @staticmethod
    def _score_documents(completeness_pct: float) -> ReadinessDimension:
        pts = round(completeness_pct * 10 / 100)
        notes = []
        if completeness_pct < 80:
            notes.append(f"Document readiness is {completeness_pct:.0f}% — upload mandatory docs.")
        return ReadinessDimension("Document Readiness", pts, 10, notes)

    @staticmethod
    def _score_legal(profile: Dict[str, Any]) -> ReadinessDimension:
        pts, notes = 0, []
        has_dpiit = profile.get("is_dpiit_recognised") or bool(profile.get("dpiit_number")) or bool(profile.get("has_dpiit"))
        if has_dpiit:
            pts += 4
        else:
            notes.append("Obtain DPIIT recognition at startupindia.gov.in.")
        
        country = (profile.get("country") or "").lower()
        if "india" in country or not country:
            pts += 2
        else:
            notes.append("Obtaining local Indian incorporation is recommended.")

        pan = profile.get("pan_number") or profile.get("PAN") or profile.get("pan")
        gst = profile.get("gstin") or profile.get("GST") or profile.get("gst")
        if pan:
            pts += 1
        else:
            notes.append("Add PAN card number.")
        if gst:
            pts += 1
        else:
            notes.append("Add GSTIN details.")

        if (profile.get("entity_type") and profile["entity_type"] != "other") or has_dpiit:
            pts += 2
        else:
            notes.append("Specify your legal entity type.")
        return ReadinessDimension("Legal & DPIIT Status", pts, 10, notes)

    @staticmethod
    def _score_technology(profile: Dict[str, Any]) -> ReadinessDimension:
        pts, notes = 0, []
        if profile.get("technology_stack"):
            pts += 3
        else:
            notes.append("Add your technology stack.")
        if profile.get("website"):
            pts += 2
        else:
            notes.append("Add company website link.")
        return ReadinessDimension("Technology Definition", pts, 5, notes)

    @staticmethod
    def _build_recommendations(
        profile:    Dict[str, Any],
        dimensions: List[ReadinessDimension],
    ):
        missing = []
        for key, label in [
            ("problem_statement",  "Problem statement"),
            ("solution_statement", "Solution description"),
            ("impact_statement",   "Impact statement"),
            ("founding_year",      "Year of incorporation"),
            ("funding_needed",     "Funding amount needed"),
            ("technology_stack",   "Technology stack"),
        ]:
            val = profile.get(key)
            if key == "founding_year" and not val:
                val = profile.get("founded_year")
            elif key == "solution_statement" and not val:
                val = profile.get("solution")
            elif key == "impact_statement" and not val:
                val = profile.get("impact")
                
            if not val:
                missing.append(label)

        recs = []
        for d in sorted(dimensions, key=lambda x: x.pct):
            if d.notes:
                recs.extend(d.notes[:1])
        return missing[:6], recs[:8]

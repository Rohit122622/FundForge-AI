

import logging
from typing import Any, Dict, List, Optional

from backend.eligibility.eligibility_checker import EligibilityChecker, EligibilityReport
from backend.eligibility.document_checker import DocumentChecker, DocumentCheckResult
from backend.eligibility.readiness_score import ReadinessResult, ReadinessScorer
from backend.eligibility.recommendation_engine import (
    EligibilityRecommendationEngine, EligibleGrant,
)

logger = logging.getLogger("fundforge.eligibility.eligibility_engine")

_ENGINE_VERSION = "1.0.0"


class EligibilityEngine:
    

    ENGINE_VERSION = _ENGINE_VERSION

    def __init__(
        self,
        checker:     Optional[EligibilityChecker]               = None,
        doc_checker: Optional[DocumentChecker]                   = None,
        scorer:      Optional[ReadinessScorer]                   = None,
        rec_engine:  Optional[EligibilityRecommendationEngine]   = None,
    ) -> None:
        self._checker     = checker     or EligibilityChecker()
        self._doc_checker = doc_checker or DocumentChecker()
        self._scorer      = scorer      or ReadinessScorer()
        self._rec_engine  = rec_engine  or EligibilityRecommendationEngine()
        logger.info("EligibilityEngine v%s initialised.", self.ENGINE_VERSION)

    
    def check_for_grant(
        self,
        startup_profile:     Dict[str, Any],
        grant_data:          Dict[str, Any],
        uploaded_doc_names:  Optional[List[str]] = None,
    ) -> EligibilityReport:
        
        return self._checker.check(startup_profile, grant_data, uploaded_doc_names)

    def check_readiness(
        self,
        startup_profile:    Dict[str, Any],
        uploaded_doc_names: Optional[List[str]] = None,
    ) -> ReadinessResult:
        
        doc_completeness = 100.0
        if uploaded_doc_names is not None:
            
            doc_result = self._doc_checker.check("default", uploaded_doc_names)
            doc_completeness = doc_result.completeness_pct
        return self._scorer.score(startup_profile, doc_completeness)

    def get_missing_documents(
        self,
        grant_id:           str,
        uploaded_doc_names: Optional[List[str]] = None,
    ) -> DocumentCheckResult:
        
        return self._doc_checker.check(grant_id, uploaded_doc_names or [])

    def recommend_with_eligibility(
        self,
        startup_profile:    Dict[str, Any],
        uploaded_doc_names: Optional[List[str]] = None,
        top_n:              int = 10,
    ) -> List[EligibleGrant]:
        
        return self._rec_engine.recommend_with_eligibility(
            startup_profile, uploaded_doc_names, top_n
        )

    def get_document_requirements(self, grant_id: str) -> List[Dict[str, Any]]:
        
        reqs = self._doc_checker.get_requirements(grant_id)
        return [{"doc_id": r.doc_id, "name": r.name, "mandatory": r.mandatory,
                 "description": r.description, "hint": r.hint} for r in reqs]






_engine_singleton: Optional[EligibilityEngine] = None
_engine_lock = __import__("threading").Lock()


def get_eligibility_engine() -> EligibilityEngine:
    
    global _engine_singleton
    with _engine_lock:
        if _engine_singleton is None:
            _engine_singleton = EligibilityEngine()
        return _engine_singleton


def reset_eligibility_engine() -> None:
    
    global _engine_singleton
    with _engine_lock:
        _engine_singleton = None

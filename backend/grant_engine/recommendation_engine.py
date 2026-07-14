

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.grant_engine.exceptions import (
    FilterError,
    GrantEngineError,
    InsufficientProfileError,
    NoGrantsFoundError,
    ScoringError,
)
from backend.grant_engine.grant_catalog import GrantCatalog, get_grant_catalog
from backend.grant_engine.grant_filter import GrantFilter
from backend.grant_engine.grant_matcher import GrantMatcher
from backend.grant_engine.grant_ranker import GrantRanker, RankedGrant
from backend.grant_engine.recommendation_explainer import (
    GrantExplanation,
    RecommendationExplainer,
)
from backend.grant_engine.startup_profiler import StartupAnalysis, StartupProfiler

logger = logging.getLogger("fundforge.grant_engine.recommendation_engine")






@dataclass
class GrantRecommendation:
    
    rank:        int
    grant_id:    str
    grant_name:  str
    short_name:  str
    composite:   int
    confidence:  str
    score:       Dict[str, Any]
    explanation: Dict[str, Any]
    grant_meta:  Dict[str, Any]
    bonus_note:  Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank":        self.rank,
            "grant_id":    self.grant_id,
            "grant_name":  self.grant_name,
            "short_name":  self.short_name,
            "composite":   self.composite,
            "match_score": self.composite,
            "total_score": self.composite,
            "confidence":  self.confidence,
            "score":       self.score,
            "explanation": self.explanation,
            "grant_meta":  self.grant_meta,
            "bonus_note":  self.bonus_note,
        }


@dataclass
class RecommendationResult:
    
    startup_name:          str
    startup_analysis:      Dict[str, Any]
    recommendations:       List[GrantRecommendation] = field(default_factory=list)
    total_grants_scanned:  int = 0
    total_after_filter:    int = 0
    readiness_score:       int = 0
    missing_fields:        List[str] = field(default_factory=list)
    processing_time_ms:    float = 0.0
    engine_version:        str = "1.0.0"

    @property
    def top_recommendation(self) -> Optional[GrantRecommendation]:
        
        return self.recommendations[0] if self.recommendations else None

    @property
    def count(self) -> int:
        
        return len(self.recommendations)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "startup_name":         self.startup_name,
            "startup_analysis":     self.startup_analysis,
            "recommendations":      [r.to_dict() for r in self.recommendations],
            "total_grants_scanned": self.total_grants_scanned,
            "total_after_filter":   self.total_after_filter,
            "readiness_score":      self.readiness_score,
            "missing_fields":       self.missing_fields,
            "processing_time_ms":   round(self.processing_time_ms, 1),
            "engine_version":       self.engine_version,
            "count":                self.count,
        }






class RecommendationEngine:
    

    ENGINE_VERSION = "1.0.0"

    def __init__(
        self,
        catalog:   Optional[GrantCatalog]            = None,
        profiler:  Optional[StartupProfiler]          = None,
        filter_:   Optional[GrantFilter]              = None,
        matcher:   Optional[GrantMatcher]             = None,
        ranker:    Optional[GrantRanker]              = None,
        explainer: Optional[RecommendationExplainer]  = None,
        top_n:     int = 10,
    ):
        self._catalog   = catalog   or get_grant_catalog()
        self._profiler  = profiler  or StartupProfiler()
        self._filter    = filter_   or GrantFilter()
        self._matcher   = matcher   or GrantMatcher()
        self._ranker    = ranker    or GrantRanker(top_n=top_n)
        self._explainer = explainer or RecommendationExplainer()

        logger.info(
            "RecommendationEngine v%s initialised — catalog: %d grants",
            self.ENGINE_VERSION,
            self._catalog.count,
        )

    
    def recommend(
        self,
        startup_profile: dict,
        top_n: Optional[int] = None,
        include_closed: bool = False,
    ) -> RecommendationResult:
        
        start_time = time.monotonic()

        
        try:
            analysis: StartupAnalysis = self._profiler.analyse(startup_profile)
        except InsufficientProfileError:
            raise
        except Exception as exc:
            raise GrantEngineError(
                f"Startup profiling failed: {exc}"
            ) from exc

        logger.info(
            "Recommendation pipeline started: company=%s sector=%s stage=%s",
            analysis.company_name,
            analysis.sector.value,
            analysis.stage.value,
        )

        
        grants = (
            self._catalog.all()
            if include_closed
            else self._catalog.open_grants()
        )
        total_scanned = len(grants)

        if not grants:
            raise NoGrantsFoundError(
                "No open grants are currently available in the catalog."
            )

        
        try:
            eligible_grants, filter_results = self._filter.filter_catalog(
                startup=analysis,
                grants=grants,
            )
        except Exception as exc:
            raise FilterError(f"Eligibility filter failed: {exc}") from exc

        if not eligible_grants:
            raise NoGrantsFoundError(
                "No grants match your startup profile's eligibility criteria. "
                "Try completing your profile to improve recommendations."
            )

        
        filter_map = {fr.grant_id: fr for fr in filter_results}

        
        try:
            scored_pairs = []
            for grant in eligible_grants:
                fr = filter_map.get(grant.id)
                score = self._matcher.score(
                    startup=analysis,
                    grant=grant,
                    filter_result=fr,
                )
                scored_pairs.append((grant, score))
        except Exception as exc:
            raise ScoringError(f"Match scoring failed: {exc}") from exc

        
        if top_n is not None:
            self._ranker._top_n = top_n

        ranked: List[RankedGrant] = self._ranker.rank(
            startup=analysis,
            scored_pairs=scored_pairs,
        )

        
        explanations: List[GrantExplanation] = self._explainer.explain_batch(
            startup=analysis,
            ranked_grants=ranked,
        )

        
        recommendations = []
        for rg, expl in zip(ranked, explanations):
            recommendations.append(GrantRecommendation(
                rank=rg.rank,
                grant_id=rg.grant.id,
                grant_name=rg.grant.name,
                short_name=rg.grant.short_name,
                composite=rg.composite,
                confidence=rg.confidence,
                score=rg.score.to_dict(),
                explanation=expl.to_dict(),
                grant_meta=rg.grant.to_dict(),
                bonus_note=rg.bonus_note,
            ))

        elapsed_ms = (time.monotonic() - start_time) * 1000

        result = RecommendationResult(
            startup_name=analysis.company_name,
            startup_analysis=analysis.to_dict(),
            recommendations=recommendations,
            total_grants_scanned=total_scanned,
            total_after_filter=len(eligible_grants),
            readiness_score=analysis.readiness_score,
            missing_fields=analysis.missing_fields,
            processing_time_ms=elapsed_ms,
            engine_version=self.ENGINE_VERSION,
        )

        logger.info(
            "Recommendation complete: company=%s recs=%d scanned=%d "
            "filtered=%d top_score=%d time=%.1fms",
            analysis.company_name,
            result.count,
            total_scanned,
            len(eligible_grants),
            result.top_recommendation.composite if result.top_recommendation else 0,
            elapsed_ms,
        )

        return result

    
    def get_grant_by_id(self, grant_id: str) -> Optional[dict]:
        
        grant = self._catalog.get_by_id(grant_id)
        return grant.to_dict() if grant else None

    def list_all_grants(self) -> List[dict]:
        
        return [g.to_dict() for g in self._catalog.open_grants()]

    def get_readiness_report(self, startup_profile: dict) -> dict:
        
        try:
            analysis = self._profiler.analyse(startup_profile)
        except InsufficientProfileError as exc:
            return {
                "readiness_score":  0,
                "missing_fields":   exc.missing_fields,
                "suggestions":      [
                    f"Add your {f} to enable grant recommendations."
                    for f in exc.missing_fields
                ],
            }

        suggestions = [
            f"Add '{label}' to improve match accuracy."
            for field_key, label in self._profiler._ADVISORY_FIELDS
            if not startup_profile.get(field_key)
        ][:8]

        return {
            "readiness_score":  analysis.readiness_score,
            "completeness":     analysis.completeness_score,
            "missing_fields":   analysis.missing_fields,
            "suggestions":      suggestions,
            "startup_analysis": analysis.to_dict(),
        }






_engine_singleton: Optional[RecommendationEngine] = None
_engine_lock = __import__("threading").Lock()


def get_recommendation_engine(
    top_n: int = 10,
    **kwargs,
) -> RecommendationEngine:
    
    global _engine_singleton
    with _engine_lock:
        if _engine_singleton is None:
            _engine_singleton = RecommendationEngine(top_n=top_n, **kwargs)
        return _engine_singleton


def reset_recommendation_engine() -> None:
    
    global _engine_singleton
    with _engine_lock:
        _engine_singleton = None



import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from backend.grant_engine.grant_catalog import GrantInstrument, IndianGrant
from backend.grant_engine.scoring import RecommendationScore
from backend.grant_engine.startup_profiler import StartupAnalysis

logger = logging.getLogger("fundforge.grant_engine.grant_ranker")





_DEFAULT_TOP_N: int = 10
_MAX_PER_INSTRUMENT: int = 5     
_WOMEN_LED_BONUS: int = 5        
_MIN_COMPOSITE_THRESHOLD: int = 20  






@dataclass
class RankedGrant:
    

    rank:       int
    grant:      IndianGrant
    score:      RecommendationScore
    bonus_note: Optional[str] = None     

    @property
    def composite(self) -> int:
        return self.score.composite

    @property
    def confidence(self) -> str:
        return self.score.confidence

    def to_dict(self) -> Dict[str, Any]:
        d = self.grant.to_dict()
        d["rank"]        = self.rank
        d["score"]       = self.score.to_dict()
        d["bonus_note"]  = self.bonus_note
        return d






class GrantRanker:
    

    def __init__(
        self,
        top_n: int = _DEFAULT_TOP_N,
        max_per_instrument: int = _MAX_PER_INSTRUMENT,
        min_threshold: int = _MIN_COMPOSITE_THRESHOLD,
    ):
        self._top_n = top_n
        self._max_per_instrument = max_per_instrument
        self._min_threshold = min_threshold

    def rank(
        self,
        startup: StartupAnalysis,
        scored_pairs: List[Tuple[IndianGrant, RecommendationScore]],
    ) -> List[RankedGrant]:
        
        if not scored_pairs:
            logger.info("Ranker: no scored pairs to rank.")
            return []

        
        boosted = self._apply_boosts(startup, scored_pairs)

        
        filtered = [
            (g, s, note) for g, s, note in boosted
            if s.composite >= self._min_threshold
        ]

        
        sorted_pairs = sorted(
            filtered,
            key=lambda x: (
                -x[1].composite,
                -x[1].eligibility,
                -x[1].deadline_urgency,
            ),
        )

        
        instrument_count: Dict[GrantInstrument, int] = {}
        selected: List[Tuple[IndianGrant, RecommendationScore, Optional[str]]] = []

        for grant, score, note in sorted_pairs:
            instr = grant.instrument
            if instrument_count.get(instr, 0) >= self._max_per_instrument:
                continue
            instrument_count[instr] = instrument_count.get(instr, 0) + 1
            selected.append((grant, score, note))
            if len(selected) >= self._top_n:
                break

        result = [
            RankedGrant(rank=idx + 1, grant=g, score=s, bonus_note=note)
            for idx, (g, s, note) in enumerate(selected)
        ]

        logger.info(
            "Ranker: %d/%d grants selected for %s | top score: %d",
            len(result),
            len(scored_pairs),
            startup.company_name,
            result[0].composite if result else 0,
        )
        return result

    
    def _apply_boosts(
        self,
        startup: StartupAnalysis,
        scored_pairs: List[Tuple[IndianGrant, RecommendationScore]],
    ) -> List[Tuple[IndianGrant, RecommendationScore, Optional[str]]]:
        
        result = []
        for grant, score in scored_pairs:
            note: Optional[str] = None

            
            if startup.is_women_led and grant.women_led_preference:
                new_composite = min(100, score.composite + _WOMEN_LED_BONUS)
                score = _clone_score_with_composite(score, new_composite)
                note = f"+{_WOMEN_LED_BONUS} pts: Women-led startup preference applied."

            result.append((grant, score, note))
        return result


def _clone_score_with_composite(
    original: RecommendationScore,
    new_composite: int,
) -> RecommendationScore:
    
    import copy
    cloned = copy.copy(original)
    cloned.composite = new_composite
    return cloned



import logging
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("fundforge.ibm.health")





@dataclass
class ComponentHealth:
    

    component: str
    status: str = "unavailable"      
    latency_ms: float = -1.0
    detail: str = ""
    error: Optional[str] = None

    @property
    def is_healthy(self) -> bool:
        return self.status == "healthy"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class IBMHealthReport:
    

    overall_status: str = "unavailable"
    components: List[ComponentHealth] = field(default_factory=list)
    checked_at: str = ""
    environment: str = ""

    @property
    def is_healthy(self) -> bool:
        return self.overall_status == "healthy"

    @property
    def is_degraded(self) -> bool:
        return self.overall_status == "degraded"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_status": self.overall_status,
            "checked_at":     self.checked_at,
            "environment":    self.environment,
            "components":     [c.to_dict() for c in self.components],
        }






def _check_iam_token() -> ComponentHealth:
    
    start = time.monotonic()
    try:
        from backend.ibm.auth import get_token_manager
        manager = get_token_manager()
        token = manager.get_token()

        if token.is_expired:
            return ComponentHealth(
                component="ibm_iam",
                status="degraded",
                latency_ms=_ms(start),
                detail="Cached token is expired.",
            )

        secs_left = token.seconds_remaining()
        return ComponentHealth(
            component="ibm_iam",
            status="healthy",
            latency_ms=_ms(start),
            detail=f"Token valid. Expires in {secs_left:.0f}s.",
        )

    except Exception as exc:
        return ComponentHealth(
            component="ibm_iam",
            status="unavailable",
            latency_ms=_ms(start),
            detail="Failed to obtain IAM token.",
            error=str(exc),
        )


def _check_circuit_breaker() -> ComponentHealth:
    
    start = time.monotonic()
    try:
        from backend.ibm.client import get_ibm_client
        client = get_ibm_client()
        cb = client.circuit_breaker
        state = cb.state

        status = "healthy" if cb.is_closed else (
            "degraded" if state == "HALF_OPEN" else "unavailable"
        )

        return ComponentHealth(
            component="ibm_circuit_breaker",
            status=status,
            latency_ms=_ms(start),
            detail=f"Circuit breaker state: {state}.",
        )
    except Exception as exc:
        return ComponentHealth(
            component="ibm_circuit_breaker",
            status="unavailable",
            latency_ms=_ms(start),
            error=str(exc),
        )


def _check_foundation_model() -> ComponentHealth:
    
    start = time.monotonic()
    try:
        from backend.ibm.foundation_models import get_ai_provider
        provider = get_ai_provider()
        models = provider.list_models()
        return ComponentHealth(
            component="ibm_llm",
            status="healthy",
            latency_ms=_ms(start),
            detail=f"Foundation model API reachable. {len(models)} models available.",
        )
    except Exception as exc:
        return ComponentHealth(
            component="ibm_llm",
            status="unavailable",
            latency_ms=_ms(start),
            detail="Foundation model API is unreachable.",
            error=str(exc),
        )


def _check_embeddings() -> ComponentHealth:
    
    start = time.monotonic()
    try:
        from backend.ibm.embeddings import get_embedding_provider
        provider = get_embedding_provider()
        healthy = provider.is_healthy()

        if healthy:
            return ComponentHealth(
                component="ibm_embeddings",
                status="healthy",
                latency_ms=_ms(start),
                detail="Embedding endpoint reachable.",
            )
        return ComponentHealth(
            component="ibm_embeddings",
            status="unavailable",
            latency_ms=_ms(start),
            detail="Embedding probe returned no results.",
        )
    except Exception as exc:
        return ComponentHealth(
            component="ibm_embeddings",
            status="unavailable",
            latency_ms=_ms(start),
            error=str(exc),
        )


def _check_vector_index() -> ComponentHealth:
    
    start = time.monotonic()
    vector_id = os.getenv("VECTOR_INDEX_ID", "")
    if not vector_id:
        return ComponentHealth(
            component="ibm_vector_index",
            status="degraded",
            latency_ms=_ms(start),
            detail="VECTOR_INDEX_ID is not set — vector search disabled.",
        )
    try:
        from backend.ibm.vector_search import get_vector_search_provider
        provider = get_vector_search_provider()
        healthy = provider.is_healthy()

        return ComponentHealth(
            component="ibm_vector_index",
            status="healthy" if healthy else "unavailable",
            latency_ms=_ms(start),
            detail="Vector index reachable." if healthy else "Vector index probe failed.",
        )
    except Exception as exc:
        return ComponentHealth(
            component="ibm_vector_index",
            status="unavailable",
            latency_ms=_ms(start),
            error=str(exc),
        )


def _check_config() -> ComponentHealth:
    
    start = time.monotonic()
    required = {
        "IBM_API_KEY":    os.getenv("IBM_API_KEY", ""),
        "IBM_PROJECT_ID": os.getenv("IBM_PROJECT_ID", ""),
        "IBM_URL":        os.getenv("IBM_URL", ""),
    }
    missing = [k for k, v in required.items() if not v.strip()]

    if missing:
        return ComponentHealth(
            component="ibm_config",
            status="unavailable",
            latency_ms=_ms(start),
            detail=f"Missing required config: {', '.join(missing)}",
            error="Environment configuration incomplete.",
        )

    return ComponentHealth(
        component="ibm_config",
        status="healthy",
        latency_ms=_ms(start),
        detail="All required IBM environment variables are set.",
    )






def run_ibm_health_check(
    check_llm: bool = True,
    check_embeddings: bool = True,
    check_vector: bool = True,
) -> IBMHealthReport:
    
    from datetime import datetime, timezone

    components: List[ComponentHealth] = []

    
    components.append(_check_config())
    components.append(_check_iam_token())
    components.append(_check_circuit_breaker())

    
    if check_llm:
        components.append(_check_foundation_model())
    if check_embeddings:
        components.append(_check_embeddings())
    if check_vector:
        components.append(_check_vector_index())

    
    statuses = {c.status for c in components}
    if "unavailable" in statuses:
        overall = "unavailable"
    elif "degraded" in statuses:
        overall = "degraded"
    else:
        overall = "healthy"

    report = IBMHealthReport(
        overall_status=overall,
        components=components,
        checked_at=datetime.now(timezone.utc).isoformat(),
        environment=os.getenv("FLASK_ENV", "development"),
    )

    logger.info(
        "IBM health check complete: overall=%s components=[%s]",
        overall,
        ", ".join(f"{c.component}:{c.status}" for c in components),
    )

    return report


def get_ibm_status_summary() -> Dict[str, str]:
    
    summary: Dict[str, str] = {}

    try:
        from backend.ibm.auth import get_token_manager
        mgr = get_token_manager()
        tok = mgr._token
        summary["ibm_iam"] = (
            "healthy" if (tok and not tok.is_expired) else "unavailable"
        )
    except Exception:
        summary["ibm_iam"] = "unavailable"

    try:
        from backend.ibm.client import get_ibm_client
        cb = get_ibm_client().circuit_breaker
        summary["ibm_circuit_breaker"] = "healthy" if cb.is_closed else cb.state.lower()
    except Exception:
        summary["ibm_circuit_breaker"] = "unavailable"

    return summary






def _ms(start: float) -> float:
    
    return round((time.monotonic() - start) * 1000, 1)

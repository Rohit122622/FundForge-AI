

import logging
from typing import Dict, Tuple

from flask import Response
from flask_jwt_extended import jwt_required

from backend.utils.response import ok, error

logger = logging.getLogger("fundforge.controllers.dashboard")


@jwt_required()
def get_user_summary() -> Tuple[Response, int]:
    
    try:
        from backend.grant_engine.grant_catalog import get_grant_catalog

        catalog     = get_grant_catalog()
        open_grants = catalog.open_grants()

        
        by_instrument: Dict[str, int] = {}
        for g in open_grants:
            key = g.instrument.value
            by_instrument[key] = by_instrument.get(key, 0) + 1

        return ok(
            data={
                "catalog": {
                    "total_grants":   catalog.count,
                    "open_grants":    len(open_grants),
                    "by_instrument":  by_instrument,
                },
                "quick_links": [
                    {"label": "Browse Grants",       "path": "/api/v1/grants"},
                    {"label": "Get Recommendations", "path": "/api/v1/grants/recommend"},
                    {"label": "Check Eligibility",   "path": "/api/v1/eligibility/check"},
                    {"label": "Generate Proposal",   "path": "/api/v1/proposals/generate"},
                ],
                "engine_status": {
                    "grant_engine":     "online",
                    "eligibility":      "online",
                    "proposal_gen":     "online",
                },
            },
            message="Dashboard summary loaded.",
        )
    except Exception as exc:
        logger.error("get_user_summary error: %s", exc, exc_info=True)
        return error("Failed to load dashboard summary.", code=500)


def get_platform_stats() -> Tuple[Response, int]:
    
    try:
        from backend.grant_engine.grant_catalog import get_grant_catalog
        from backend.grant_engine.startup_profiler import IndianSector

        catalog = get_grant_catalog()
        grants  = catalog.all()

        sector_coverage = {}
        for sector in IndianSector:
            count = len([g for g in grants if sector in g.target_sectors])
            if count > 0:
                sector_coverage[sector.value] = count

        total_inr_min = sum(g.min_amount_inr or 0 for g in grants)
        total_inr_max = sum(g.max_amount_inr or 0 for g in grants)

        return ok(data={
            "grants": {
                "total":          catalog.count,
                "open":           len(catalog.open_grants()),
                "rolling":        sum(1 for g in grants if g.is_rolling),
                "sectors_covered":len(sector_coverage),
            },
            "funding": {
                "min_available_inr": total_inr_min,
                "max_available_inr": total_inr_max,
            },
            "sector_coverage": sector_coverage,
            "platform": {
                "name": "FundForge AI",
                "focus": "Indian Startup Grants",
                "schemes_tracked": catalog.count,
            },
        })
    except Exception as exc:
        logger.error("get_platform_stats error: %s", exc, exc_info=True)
        return error("Failed to load platform stats.", code=500)


def get_catalog_summary() -> Tuple[Response, int]:
    
    try:
        from backend.grant_engine.grant_catalog import get_grant_catalog
        catalog = get_grant_catalog()
        by_body: Dict[str, int] = {}
        for g in catalog.all():
            key = g.administering_body.split(",")[0].strip()
            by_body[key] = by_body.get(key, 0) + 1

        return ok(data={
            "total":          catalog.count,
            "open":           len(catalog.open_grants()),
            "by_body":        dict(sorted(by_body.items(), key=lambda x: -x[1])[:8]),
            "featured": [
                g.to_dict() for g in catalog.all()
                if g.id in ("sisfs", "birac_big", "tide_2", "agrisure", "samridh")
            ],
        })
    except Exception as exc:
        logger.error("get_catalog_summary error: %s", exc, exc_info=True)
        return error("Failed to load catalog summary.", code=500)

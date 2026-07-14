

import logging
from typing import Tuple

from flask import Response, request

from backend.utils.response import ok, error, get_pagination_params, paginated

logger = logging.getLogger("fundforge.controllers.search")


def unified_search() -> Tuple[Response, int]:
    
    query = (request.args.get("q") or "").strip().lower()
    search_type = request.args.get("type", "grants").lower()
    page, per_page = get_pagination_params(request)

    if not query or len(query) < 2:
        return error("Search query must be at least 2 characters.", code=422)

    try:
        if search_type == "grants":
            return _search_grants(query, page, per_page)
        else:
            return _search_grants(query, page, per_page)

    except Exception as exc:
        logger.error("unified_search error: %s", exc, exc_info=True)
        return error("Search failed.", code=500)


def search_suggestions() -> Tuple[Response, int]:
    
    prefix = (request.args.get("q") or "").strip().lower()

    if not prefix or len(prefix) < 1:
        return ok(data={"suggestions": []})

    try:
        from backend.grant_engine.grant_catalog import get_grant_catalog
        catalog = get_grant_catalog()

        suggestions = []
        seen = set()

        for grant in catalog.all():
            if prefix in grant.name.lower() and grant.name not in seen:
                suggestions.append({
                    "text": grant.name,
                    "type": "grant",
                    "id": grant.id,
                })
                seen.add(grant.name)

            if prefix in grant.short_name.lower() and grant.short_name not in seen:
                suggestions.append({
                    "text": grant.short_name,
                    "type": "grant_short",
                    "id": grant.id,
                })
                seen.add(grant.short_name)

            if prefix in grant.administering_body.lower() and grant.administering_body not in seen:
                suggestions.append({
                    "text": grant.administering_body,
                    "type": "organization",
                    "id": None,
                })
                seen.add(grant.administering_body)

            if len(suggestions) >= 10:
                break

        return ok(data={"suggestions": suggestions[:10]})

    except Exception as exc:
        logger.error("search_suggestions error: %s", exc, exc_info=True)
        return error("Failed to load suggestions.", code=500)


def _search_grants(query: str, page: int, per_page: int) -> Tuple[Response, int]:
    
    from backend.grant_engine.grant_catalog import get_grant_catalog

    catalog = get_grant_catalog()
    all_grants = catalog.all()

    sector_filter = request.args.get("sector")
    stage_filter = request.args.get("stage")
    instrument_filter = request.args.get("instrument")

    results = []
    for grant in all_grants:
        score = 0
        name_lower = grant.name.lower()
        short_lower = grant.short_name.lower()
        desc_lower = grant.description.lower()
        body_lower = grant.administering_body.lower()

        if query in name_lower:
            score += 10
        if query in short_lower:
            score += 8
        if query == short_lower:
            score += 15
        if query in desc_lower:
            score += 3
        if query in body_lower:
            score += 5
        if query in grant.id.lower():
            score += 12
        if any(query in tag.lower() for tag in grant.tags):
            score += 4
        if any(query in kw.lower() for kw in grant.innovation_keywords):
            score += 4
        if any(query in sec.value.lower() for sec in grant.target_sectors):
            score += 6

        keywords = query.split()
        for kw in keywords:
            if kw in name_lower or kw in desc_lower:
                score += 2
            if any(kw in tag.lower() for tag in grant.tags):
                score += 1
            if any(kw in ikw.lower() for ikw in grant.innovation_keywords):
                score += 1

        if score == 0:
            continue

        if sector_filter:
            try:
                from backend.grant_engine.startup_profiler import IndianSector
                sec = IndianSector(sector_filter.lower())
                if sec not in grant.target_sectors:
                    continue
            except ValueError:
                pass

        if stage_filter:
            try:
                from backend.grant_engine.startup_profiler import FundingStage
                stg = FundingStage(stage_filter.lower())
                if stg not in grant.eligible_stages:
                    continue
            except ValueError:
                pass

        if instrument_filter:
            if grant.instrument.value != instrument_filter.lower():
                continue

        results.append((score, grant))

    results.sort(key=lambda x: -x[0])

    total = len(results)
    start = (page - 1) * per_page
    page_items = [
        {**g.to_dict(), "relevance_score": s}
        for s, g in results[start: start + per_page]
    ]

    return paginated(
        items=page_items, total=total, page=page, per_page=per_page,
        message=f"{total} results for '{query}'.",
    )

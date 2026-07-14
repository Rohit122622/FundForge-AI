

import logging
from typing import Tuple

from flask import Response, request
from flask_jwt_extended import jwt_required

from backend.utils.response import ok, error, require_json

logger = logging.getLogger("fundforge.controllers.eligibility")


def _get_body() -> dict:
    return request.get_json(silent=True) or {}


def _normalize_profile(profile: dict) -> dict:
    from flask_jwt_extended import get_jwt_identity
    user_id = get_jwt_identity()
    
    db_dict = {}
    if user_id:
        try:
            from backend.app import db
            from backend.models.startup import StartupProfile
            db_profile = db.session.query(StartupProfile).filter_by(
                user_id=user_id, is_deleted=False
            ).first()
            if db_profile:
                db_dict = db_profile.to_dict()
        except Exception as e:
            logger.debug("Failed to load DB profile in eligibility controller: %s", e)

    req_profile = {}
    if profile:
        for k, v in profile.items():
            if v is not None and v != "" and v != []:
                req_profile[k] = v

    normalized = {**db_dict, **req_profile}
    
    
    dpiit_number = normalized.get("dpiit_number")
    has_dpiit = normalized.get("has_dpiit")
    if "is_dpiit_recognised" not in normalized:
        if has_dpiit is not None:
            normalized["is_dpiit_recognised"] = bool(has_dpiit)
        elif dpiit_number:
            normalized["is_dpiit_recognised"] = True
        else:
            normalized["is_dpiit_recognised"] = False
    else:
        if has_dpiit is not None:
            normalized["is_dpiit_recognised"] = bool(has_dpiit)
        elif dpiit_number:
            normalized["is_dpiit_recognised"] = True
        
    
    if "founding_year" not in normalized or normalized["founding_year"] is None:
        val = normalized.get("founded_year")
        if val:
            try:
                normalized["founding_year"] = int(val)
            except ValueError:
                pass
            
    
    if "team_size" in normalized:
        val = normalized.get("team_size")
        if val:
            try:
                normalized["team_size"] = int(val)
            except ValueError:
                normalized["team_size"] = 1
                
    
    if "state" in normalized:
        normalized["state_province"] = normalized.get("state")
        
    
    if "funding_raised" in normalized:
        normalized["total_funding_raised"] = normalized.get("funding_raised")
        
    
    c_val = normalized.get("country")
    if not c_val or not str(c_val).strip() or str(c_val).lower() == "united states":
        normalized["country"] = "India"
        
    
    sector_val = normalized.get("sector")
    if sector_val:
        if not normalized.get("industry") or normalized.get("industry") == "other":
            
            sector_mapping = {
                "artificial_intelligence": "deep_tech",
                "healthtech": "health_tech",
                "fintech": "fintech",
                "edtech": "education",
                "agritech": "agriculture",
                "cleantech": "climate_tech"
            }
            mapped_industry = sector_mapping.get(sector_val.lower(), sector_val)
            normalized["industry"] = mapped_industry
        normalized["sector"] = sector_val
        
    
    weights = {
        "company_name":        5,
        "description":         5,
        "industry":            5,
        "sector":              5,
        "stage":               5,
        "founding_year":       5,
        "team_size":           5,
        "country":             5,
        "state_province":      5,
        "city":                5,
        "is_dpiit_recognised": 5,
        "pan_number":          5,
        "gstin":               5,
        "website":             4,
        "total_funding_raised":4,
        "funding_needed":      4,
        "annual_revenue":      4,
        "problem_statement":   4,
        "solution_statement":  4,
        "impact_statement":    4,
        "technology_stack":    3,
        "target_market":       3,
    }
    total_weight = sum(weights.values())
    earned = 0
    for field, w in weights.items():
        val = normalized.get(field)
        if field == "industry" and not val:
            val = normalized.get("industry_name") or normalized.get("sector")
        elif field == "sector" and not val:
            val = normalized.get("industry")
        elif field == "founding_year" and not val:
            val = normalized.get("founded_year")
        elif field == "state_province" and not val:
            val = normalized.get("state")
        elif field == "is_dpiit_recognised" and not val:
            val = normalized.get("dpiit_number") or normalized.get("has_dpiit")
        elif field == "pan_number" and not val:
            val = normalized.get("PAN") or normalized.get("pan")
        elif field == "gstin" and not val:
            val = normalized.get("GST") or normalized.get("gst")
        elif field == "total_funding_raised" and not val:
            val = normalized.get("funding_raised")
        elif field == "annual_revenue" and not val:
            val = normalized.get("revenue")
        elif field == "solution_statement" and not val:
            val = normalized.get("solution")
        elif field == "impact_statement" and not val:
            val = normalized.get("impact")
        
        if bool(val):
            earned += w
            
    normalized["profile_score"] = min(100, round((earned / total_weight) * 100))
    return normalized


def _get_uploaded_document_names() -> list:
    from flask_jwt_extended import get_jwt_identity
    user_id = get_jwt_identity()
    if not user_id:
        return []
    try:
        from backend.app import db
        from backend.models.document import Document
        docs = db.session.query(Document).filter_by(
            user_id=user_id, is_deleted=False
        ).all()
        doc_names = []
        for doc in docs:
            if doc.original_filename:
                doc_names.append(doc.original_filename)
            if doc.display_name:
                doc_names.append(doc.display_name)
            if doc.document_type:
                doc_names.append(str(doc.document_type.value).replace("_", " ").title())
                doc_names.append(str(doc.document_type.value))
        return list(set(doc_names))
    except Exception as e:
        logger.debug("Failed to retrieve uploaded documents: %s", e)
        return []


@jwt_required()
def check_eligibility() -> Tuple[Response, int]:
    
    if (err := require_json(request)):
        return err

    body     = _get_body()
    profile  = _normalize_profile(body.get("startup_profile"))
    grant_d  = body.get("grant_data")
    grant_id = body.get("grant_id")
    docs     = body.get("uploaded_doc_names", [])

    if not profile:
        return error("startup_profile is required.", code=422)

    db_docs = _get_uploaded_document_names()
    merged_docs = list(set((docs or []) + db_docs))

    if not grant_d and grant_id:
        try:
            from backend.grant_engine.grant_catalog import get_grant_catalog
            g_obj = get_grant_catalog().get_by_id(grant_id)
            if not g_obj:
                return error(f"Grant '{grant_id}' not found.", code=404)
            grant_d = g_obj.to_dict()
            grant_d.update({
                "requires_dpiit":        g_obj.requires_dpiit,
                "max_company_age_years": g_obj.max_company_age_years,
                "eligible_stages":       [s.value for s in g_obj.eligible_stages],
                "max_team_size":         g_obj.max_team_size,
                "min_team_size":         g_obj.min_team_size,
                "target_sectors":        list(g_obj.target_sectors),
                "excluded_sectors":      list(g_obj.excluded_sectors),
                "max_funding_raised":    g_obj.max_funding_raised,
            })
        except Exception as exc:
            return error(f"Grant lookup failed: {exc}", code=500)

    if not grant_d:
        return error("grant_data or grant_id is required.", code=422)

    try:
        from backend.eligibility.eligibility_engine import get_eligibility_engine
        engine = get_eligibility_engine()
        report = engine.check_for_grant(profile, grant_d, merged_docs)
        return ok(
            data={"eligibility_report": report.to_dict()},
            message=f"Eligibility check complete. Score: {report.score}/100.",
        )
    except Exception as exc:
        from backend.eligibility.exceptions import InsufficientProfileError
        if isinstance(exc, InsufficientProfileError):
            return error(str(exc), code=422, error_code="INSUFFICIENT_PROFILE",
                         details={"missing_fields": exc.missing_fields})
        logger.error("check_eligibility error: %s", exc, exc_info=True)
        return error("Eligibility check failed.", code=500)


@jwt_required()
def check_readiness() -> Tuple[Response, int]:
    
    if (err := require_json(request)):
        return err

    body     = _get_body()
    profile  = _normalize_profile(body.get("startup_profile"))
    docs     = body.get("uploaded_doc_names", [])
    grant_id = body.get("grant_id")

    if not profile:
        return error("startup_profile is required.", code=422)

    db_docs = _get_uploaded_document_names()
    merged_docs = list(set((docs or []) + db_docs))

    try:
        from backend.eligibility.eligibility_engine import get_eligibility_engine
        engine = get_eligibility_engine()
        result = engine.check_readiness(profile, merged_docs)
        
        res_data = {"readiness": result.to_dict()}
        
        if grant_id:
            from backend.grant_engine.grant_catalog import get_grant_catalog
            g_obj = get_grant_catalog().get_by_id(grant_id)
            if g_obj:
                grant_d = g_obj.to_dict()
                grant_d.update({
                    "requires_dpiit":        g_obj.requires_dpiit,
                    "max_company_age_years": g_obj.max_company_age_years,
                    "eligible_stages":       [s.value for s in g_obj.eligible_stages],
                    "max_team_size":         g_obj.max_team_size,
                    "min_team_size":         g_obj.min_team_size,
                    "target_sectors":        list(g_obj.target_sectors),
                    "excluded_sectors":      list(g_obj.excluded_sectors),
                    "max_funding_raised":    g_obj.max_funding_raised,
                })
                report = engine.check_for_grant(profile, grant_d, merged_docs)
                res_data["eligibility_report"] = report.to_dict()
        
        return ok(
            data=res_data,
            message=f"Readiness score: {result.total_score}/100 — {result.band}.",
        )
    except Exception as exc:
        logger.error("check_readiness error: %s", exc, exc_info=True)
        return error("Readiness check failed.", code=500)


@jwt_required()
def eligible_recommendations() -> Tuple[Response, int]:
    
    if (err := require_json(request)):
        return err

    body    = _get_body()
    profile = _normalize_profile(body.get("startup_profile"))
    docs    = body.get("uploaded_doc_names", [])
    top_n   = int(body.get("top_n", 10))

    if not profile:
        return error("startup_profile is required.", code=422)

    db_docs = _get_uploaded_document_names()
    merged_docs = list(set((docs or []) + db_docs))

    try:
        from backend.eligibility.eligibility_engine import get_eligibility_engine
        engine = get_eligibility_engine()
        grants = engine.recommend_with_eligibility(profile, merged_docs, top_n)
        return ok(
            data={
                "recommendations": [g.to_dict() for g in grants],
                "total":           len(grants),
            },
            message=f"{len(grants)} eligible grants found.",
        )
    except Exception as exc:
        logger.error("eligible_recommendations error: %s", exc, exc_info=True)
        return error("Eligibility recommendation failed.", code=500)


def get_document_requirements(grant_id: str) -> Tuple[Response, int]:
    
    try:
        from backend.eligibility.eligibility_engine import get_eligibility_engine
        engine = get_eligibility_engine()
        reqs   = engine.get_document_requirements(grant_id)
        return ok(
            data={"grant_id": grant_id, "requirements": reqs, "total": len(reqs)},
            message=f"{len(reqs)} document requirements for grant '{grant_id}'.",
        )
    except Exception as exc:
        logger.error("get_document_requirements error: %s", exc, exc_info=True)
        return error("Failed to get document requirements.", code=500)


@jwt_required()
def check_documents() -> Tuple[Response, int]:
    
    if (err := require_json(request)):
        return err

    body     = _get_body()
    grant_id = body.get("grant_id", "default")
    docs     = body.get("uploaded_doc_names", [])

    db_docs = _get_uploaded_document_names()
    merged_docs = list(set((docs or []) + db_docs))

    try:
        from backend.eligibility.eligibility_engine import get_eligibility_engine
        engine = get_eligibility_engine()
        result = engine.get_missing_documents(grant_id, merged_docs)
        return ok(
            data={"document_check": result.to_dict()},
            message=f"Document readiness: {result.completeness_pct:.0f}%.",
        )
    except Exception as exc:
        logger.error("check_documents error: %s", exc, exc_info=True)
        return error("Document check failed.", code=500)


def list_rules() -> Tuple[Response, int]:
    
    try:
        from backend.eligibility.rule_engine import RuleEngine
        rules = RuleEngine()._rules
        data  = [{"rule_id": r.rule_id, "rule_name": r.rule_name,
                  "weight": r.weight, "is_blocking": r.is_blocking} for r in rules]
        return ok(data={"rules": data, "total": len(data)})
    except Exception as exc:
        logger.error("list_rules error: %s", exc, exc_info=True)
        return error("Failed to list rules.", code=500)

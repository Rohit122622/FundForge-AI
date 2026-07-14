

import logging
from typing import Tuple

from flask import Response, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from backend.utils.response import ok, created, error, no_content, require_json

logger = logging.getLogger("fundforge.controllers.profile")


@jwt_required()
def create_profile() -> Tuple[Response, int]:
    
    if (err := require_json(request)):
        return err

    user_id = get_jwt_identity()
    body = request.get_json(silent=True) or {}

    company_name = (body.get("company_name") or "").strip()
    if not company_name:
        return error("company_name is required.", code=422, error_code="MISSING_FIELD")

    try:
        from backend.app import db
        from backend.models.startup import StartupProfile, StartupStage, IndustryVertical, EntityType

        existing = db.session.query(StartupProfile).filter_by(
            user_id=user_id
        ).first()
        if existing and not existing.is_deleted:
            return error(
                "A startup profile already exists for this user. Use PATCH to update.",
                code=409, error_code="PROFILE_EXISTS",
            )

        industry_mapping = {
            "healthtech": "health_tech",
            "healthcare": "health_tech",
            "fintech": "fintech",
            "edtech": "education",
            "agritech": "agriculture",
            "cleantech": "climate_tech",
            "ecommerce": "retail",
            "saas": "saas",
            "deeptech": "deep_tech",
            "deep tech": "deep_tech",
            "climate tech": "climate_tech",
            "social impact": "social_impact",
        }
        stage_mapping = {
            "growth": "series_c_plus"
        }
        entity_mapping = {
            "private_limited": "llc",
            "llp": "llc",
            "partnership": "llc",
            "proprietorship": "sole_proprietorship"
        }

        stage_val = body.get("stage")
        stage = StartupStage.IDEA
        if stage_val and stage_val.strip():
            s_val = stage_val.lower().strip()
            s_mapped = stage_mapping.get(s_val, s_val)
            try:
                stage = StartupStage(s_mapped)
            except ValueError:
                stage = StartupStage.IDEA

        industry_val = body.get("industry") or body.get("sector") or "other"
        industry = IndustryVertical.OTHER
        if industry_val and industry_val.strip():
            i_val = industry_val.lower().strip()
            i_mapped = industry_mapping.get(i_val, i_val)
            try:
                industry = IndustryVertical(i_mapped)
            except ValueError:
                industry = IndustryVertical.OTHER

        entity_val = body.get("entity_type")
        entity_type = None
        if entity_val and entity_val.strip():
            e_val = entity_val.lower().strip()
            e_mapped = entity_mapping.get(e_val, e_val)
            try:
                entity_type = EntityType(e_mapped)
            except ValueError:
                entity_type = None

        def clean_int(val, default=None):
            if val is None or (isinstance(val, str) and val.strip() == ""):
                return default
            try:
                return int(val)
            except (ValueError, TypeError):
                return default

        founded_yr = clean_int(body.get("founded_year") or body.get("founding_year"))
        t_size = clean_int(body.get("team_size"), default=1)

        is_dpiit = body.get("is_dpiit_recognised")
        if is_dpiit is None:
            is_dpiit_val = bool(body.get("dpiit_number") and body.get("dpiit_number").strip())
        else:
            is_dpiit_val = is_dpiit in (True, "true", "True", 1, "1")

        country_val = body.get("country")
        if not country_val or not country_val.strip():
            country_val = "India"

        
        profile = existing if existing else StartupProfile(user_id=user_id)
        profile.is_deleted = False
        profile.company_name = company_name
        profile.industry = industry
        profile.stage = stage
        profile.entity_type = entity_type
        profile.city = body.get("city")
        profile.state_province = body.get("state") or body.get("state_province")
        profile.country = country_val
        profile.founding_year = founded_yr
        profile.team_size = t_size
        profile.description = body.get("description") or ""
        profile.website = body.get("website")
        profile.dpiit_number = body.get("dpiit_number")
        profile.is_dpiit_recognised = is_dpiit_val
        profile.annual_revenue = body.get("revenue") or body.get("annual_revenue")
        profile.total_funding_raised = body.get("funding_raised") or body.get("total_funding_raised")
        profile.sector = body.get("sector")
        profile.pan_number = body.get("PAN") or body.get("pan_number")
        profile.gstin = body.get("GST") or body.get("gstin")
        profile.tagline = body.get("tagline")
        profile.problem_statement = body.get("problem_statement")
        profile.solution_statement = body.get("solution_statement")
        profile.impact_statement = body.get("impact_statement")
        profile.technology_stack = body.get("technology_stack")
        profile.target_market = body.get("target_market")
        profile.funding_needed = body.get("funding_needed")

        profile.compute_profile_score()
        db.session.add(profile)
        db.session.commit()

        logger.info("Startup profile created/restored: %s (user=%s)", profile.id, user_id)
        return created(
            data={"profile": profile.to_dict()},
            message="Startup profile created successfully.",
        )

    except Exception as exc:
        from backend.app import db as _db
        _db.session.rollback()
        logger.error("create_profile error: %s", exc, exc_info=True)
        return error("Failed to create startup profile.", code=500)


@jwt_required()
def get_profile() -> Tuple[Response, int]:
    
    user_id = get_jwt_identity()
    try:
        from backend.app import db
        from backend.models.startup import StartupProfile

        profile = db.session.query(StartupProfile).filter_by(
            user_id=user_id, is_deleted=False
        ).first()

        if not profile:
            return error(
                "No startup profile found. Create one first.",
                code=404, error_code="PROFILE_NOT_FOUND",
            )
        return ok(data={"profile": profile.to_dict()})

    except Exception as exc:
        logger.error("get_profile error: %s", exc, exc_info=True)
        return error("Failed to retrieve profile.", code=500)


@jwt_required()
def update_profile() -> Tuple[Response, int]:
    
    if (err := require_json(request)):
        return err

    user_id = get_jwt_identity()
    body = request.get_json(silent=True) or {}

    if not body:
        return error("Request body is empty.", code=422)

    try:
        from backend.app import db
        from backend.models.startup import StartupProfile, StartupStage, IndustryVertical, EntityType

        profile = db.session.query(StartupProfile).filter_by(
            user_id=user_id, is_deleted=False
        ).first()

        if not profile:
            return error("No startup profile found.", code=404, error_code="PROFILE_NOT_FOUND")

        mapping = {
            "company_name": "company_name",
            "city": "city",
            "state": "state_province",
            "state_province": "state_province",
            "founded_year": "founding_year",
            "founding_year": "founding_year",
            "team_size": "team_size",
            "description": "description",
            "website": "website",
            "dpiit_number": "dpiit_number",
            "annual_revenue": "annual_revenue",
            "revenue": "annual_revenue",
            "funding_raised": "total_funding_raised",
            "total_funding_raised": "total_funding_raised",
            "sector": "sector",
            "pan_number": "pan_number",
            "PAN": "pan_number",
            "gstin": "gstin",
            "GST": "gstin",
            "tagline": "tagline",
            "problem_statement": "problem_statement",
            "solution_statement": "solution_statement",
            "impact_statement": "impact_statement",
            "technology_stack": "technology_stack",
            "target_market": "target_market",
            "country": "country",
            "is_dpiit_recognised": "is_dpiit_recognised",
            "funding_needed": "funding_needed",
        }

        def clean_int(val, default=None):
            if val is None or (isinstance(val, str) and val.strip() == ""):
                return default
            try:
                return int(val)
            except (ValueError, TypeError):
                return default

        for key, col in mapping.items():
            if key in body:
                val = body[key]
                if col in ("founding_year", "team_size"):
                    val = clean_int(val)
                    if col == "team_size" and val is None:
                        val = 1
                elif col == "is_dpiit_recognised":
                    val = val in (True, "true", "True", 1, "1")
                elif col == "country":
                    if not val or not str(val).strip():
                        val = "India"
                setattr(profile, col, val)

        industry_mapping = {
            "healthtech": "health_tech",
            "healthcare": "health_tech",
            "fintech": "fintech",
            "edtech": "education",
            "agritech": "agriculture",
            "cleantech": "climate_tech",
            "ecommerce": "retail",
            "saas": "saas",
            "deeptech": "deep_tech",
            "deep tech": "deep_tech",
            "climate tech": "climate_tech",
            "social impact": "social_impact",
        }
        stage_mapping = {
            "growth": "series_c_plus"
        }
        entity_mapping = {
            "private_limited": "llc",
            "llp": "llc",
            "partnership": "llc",
            "proprietorship": "sole_proprietorship"
        }

        if "stage" in body:
            s_val = body["stage"]
            if s_val and s_val.strip():
                s_val = s_val.lower().strip()
                s_mapped = stage_mapping.get(s_val, s_val)
                try:
                    profile.stage = StartupStage(s_mapped)
                except ValueError:
                    profile.stage = StartupStage.IDEA
            else:
                profile.stage = StartupStage.IDEA

        industry_val = body.get("industry") or body.get("sector")
        if industry_val:
            i_val = industry_val.lower().strip()
            i_mapped = industry_mapping.get(i_val, i_val)
            try:
                profile.industry = IndustryVertical(i_mapped)
            except ValueError:
                profile.industry = IndustryVertical.OTHER

        if "entity_type" in body:
            e_val = body["entity_type"]
            if e_val and e_val.strip():
                e_val = e_val.lower().strip()
                e_mapped = entity_mapping.get(e_val, e_val)
                try:
                    profile.entity_type = EntityType(e_mapped)
                except ValueError:
                    profile.entity_type = None
            else:
                profile.entity_type = None

        profile.compute_profile_score()
        db.session.add(profile)
        db.session.commit()
        logger.info("Startup profile updated: %s (user=%s)", profile.id, user_id)
        return ok(data={"profile": profile.to_dict()}, message="Profile updated successfully.")

    except Exception as exc:
        from backend.app import db as _db
        _db.session.rollback()
        logger.error("update_profile error: %s", exc, exc_info=True)
        return error("Failed to update profile.", code=500)


@jwt_required()
def delete_profile() -> Tuple[Response, int]:
    
    user_id = get_jwt_identity()
    try:
        from backend.app import db
        from backend.models.startup import StartupProfile

        profile = db.session.query(StartupProfile).filter_by(
            user_id=user_id, is_deleted=False
        ).first()

        if not profile:
            return error("No startup profile found.", code=404)

        profile.is_deleted = True
        db.session.commit()
        logger.info("Startup profile soft-deleted: %s (user=%s)", profile.id, user_id)
        return no_content()

    except Exception as exc:
        from backend.app import db as _db
        _db.session.rollback()
        logger.error("delete_profile error: %s", exc, exc_info=True)
        return error("Failed to delete profile.", code=500)


def get_profile_by_id(profile_id: str) -> Tuple[Response, int]:
    
    try:
        from backend.app import db
        from backend.models.startup import StartupProfile

        profile = db.session.query(StartupProfile).filter_by(
            id=profile_id, is_deleted=False
        ).first()

        if not profile:
            return error(f"Profile '{profile_id}' not found.", code=404)
        return ok(data={"profile": profile.to_dict()})

    except Exception as exc:
        logger.error("get_profile_by_id error: %s", exc, exc_info=True)
        return error("Failed to retrieve profile.", code=500)

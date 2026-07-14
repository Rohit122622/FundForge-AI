

from flask import jsonify
import logging
from typing import Tuple

from flask import Response, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from backend.utils.response import (
    ok, error, paginated, require_json,
    get_pagination_params,
)

logger = logging.getLogger("fundforge.controllers.grant")






def list_catalog() -> Tuple[Response, int]:
    
    try:
        from backend.grant_engine.grant_catalog import get_grant_catalog
        catalog = get_grant_catalog()
        return ok(
            data={"grants": catalog.to_dict_list(), "total": catalog.count},
            message=f"{catalog.count} Indian grants in the catalog.",
        )
    except Exception as exc:
        logger.error("list_catalog error: %s", exc, exc_info=True)
        return error("Failed to load grant catalog.", code=500)


def list_grants() -> Tuple[Response, int]:
    
    try:
        from backend.grant_engine.grant_catalog import get_grant_catalog
        from backend.grant_engine.startup_profiler import IndianSector, FundingStage

        catalog = get_grant_catalog()
        grants  = catalog.all()

        
        sector_filter     = request.args.get("sector")
        stage_filter      = request.args.get("stage")
        instrument_filter = request.args.get("instrument")
        is_open_filter    = request.args.get("is_open")
        search            = (request.args.get("search") or "").lower().strip()

        if sector_filter:
            try:
                sec = IndianSector(sector_filter.lower())
                grants = [g for g in grants if sec in g.target_sectors]
            except ValueError:
                pass

        if stage_filter:
            try:
                stg = FundingStage(stage_filter.lower())
                grants = [g for g in grants if stg in g.eligible_stages]
            except ValueError:
                pass

        if instrument_filter:
            grants = [g for g in grants if g.instrument.value == instrument_filter.lower()]

        if is_open_filter is not None:
            want_open = is_open_filter.lower() in ("true", "1", "yes")
            grants = [g for g in grants if g.is_open == want_open]

        if search:
            filtered_grants = []
            for g in grants:
                id_match = search in g.id.lower()
                name_match = (search in g.name.lower()) or (search in g.short_name.lower())
                desc_match = search in g.description.lower()
                org_match = search in g.administering_body.lower()
                sector_match = any(search in sec.value.lower() for sec in g.target_sectors)
                kw_match = any(search in kw.lower() for kw in g.innovation_keywords) or any(search in tag.lower() for tag in g.tags)
                
                if id_match or name_match or desc_match or org_match or sector_match or kw_match:
                    filtered_grants.append(g)
            grants = filtered_grants

        
        page, per_page = get_pagination_params(request)
        total = len(grants)
        start = (page - 1) * per_page
        items = [g.to_dict() for g in grants[start: start + per_page]]

        return paginated(items, total, page, per_page, f"{total} grants found.")

    except Exception as exc:
        logger.error("list_grants error: %s", exc, exc_info=True)
        return error("Failed to list grants.", code=500)


def get_grant(grant_id: str) -> Tuple[Response, int]:
    
    try:
        from backend.grant_engine.grant_catalog import get_grant_catalog
        grant_obj = get_grant_catalog().get_by_id(grant_id)
        if grant_obj:
            return ok(data={"grant": grant_obj.to_dict()})

        
        from backend.app import db
        from backend.models.grant import Grant
        import uuid

        db_grant = None
        try:
            val_uuid = uuid.UUID(grant_id)
            db_grant = db.session.query(Grant).filter_by(id=val_uuid).first()
        except ValueError:
            pass

        if not db_grant:
            db_grant = db.session.query(Grant).filter_by(slug=grant_id).first()

        if db_grant:
            if db_grant.slug:
                catalog_grant = get_grant_catalog().get_by_id(db_grant.slug)
                if catalog_grant:
                    return ok(data={"grant": catalog_grant.to_dict()})

            g_dict = db_grant.to_dict()
            g_dict["name"] = db_grant.title
            g_dict["short_name"] = db_grant.organization_acronym or db_grant.title
            g_dict["administering_body"] = db_grant.organization_name
            g_dict["instrument"] = db_grant.grant_type.value if db_grant.grant_type else "grant"
            g_dict["min_amount_inr"] = float(db_grant.min_funding_amount) if db_grant.min_funding_amount else None
            g_dict["max_amount_inr"] = float(db_grant.max_funding_amount) if db_grant.max_funding_amount else None
            g_dict["typical_amount_inr"] = g_dict["max_amount_inr"]
            g_dict["deadline"] = db_grant.deadline.isoformat() if db_grant.deadline else None
            g_dict["is_open"] = db_grant.is_active if db_grant.is_active is not None else True
            g_dict["description"] = db_grant.description or ""
            g_dict["eligibility_summary"] = [db_grant.eligibility_criteria] if db_grant.eligibility_criteria else []
            g_dict["application_url"] = db_grant.apply_url or ""
            g_dict["tags"] = [db_grant.sector.value] if db_grant.sector else []
            g_dict["target_sectors"] = [db_grant.sector.value] if db_grant.sector else ["other"]
            g_dict["eligible_stages"] = ["seed"]
            return ok(data={"grant": g_dict})

        return error(f"Grant '{grant_id}' not found.", code=404, error_code="NOT_FOUND")
    except Exception as exc:
        logger.error("get_grant error: %s", exc, exc_info=True)
        return error("Failed to retrieve grant.", code=500)


def get_categories() -> Tuple[Response, int]:
    
    try:
        from backend.grant_engine.startup_profiler import IndianSector, FundingStage
        from backend.grant_engine.grant_catalog import GrantInstrument
        return ok(data={
            "sectors":     [s.value for s in IndianSector],
            "stages":      [s.value for s in FundingStage],
            "instruments": [i.value for i in GrantInstrument],
        })
    except Exception as exc:
        logger.error("get_categories error: %s", exc, exc_info=True)
        return error("Failed to load categories.", code=500)






@jwt_required()
def recommend() -> Tuple[Response, int]:
    
    if (err := require_json(request)):
        return err

    body    = request.get_json(silent=True) or {}
    top_n   = int(body.get("top_n", 10))

    user_id = get_jwt_identity()
    try:
        from backend.app import db
        from backend.models.startup import StartupProfile

        db_profile = db.session.query(StartupProfile).filter_by(
            user_id=user_id, is_deleted=False
        ).first()

        if not db_profile:
            return error("Startup profile not found. Please create a profile first to receive recommendations.", code=404, error_code="PROFILE_NOT_FOUND")

        profile = db_profile.to_dict()
        
        
        if not profile.get("country") or profile.get("country").lower() == "united states":
            profile["country"] = "India"
        if "state" not in profile or not profile["state"]:
            profile["state"] = db_profile.state_province
        if "sector" not in profile or not profile["sector"]:
            profile["sector"] = db_profile.industry.value if db_profile.industry else "other"
        if "founded_year" not in profile or not profile["founded_year"]:
            profile["founded_year"] = db_profile.founding_year
        if "funding_raised" not in profile or not profile["funding_raised"]:
            profile["funding_raised"] = db_profile.total_funding_raised
        if "revenue" not in profile or not profile["revenue"]:
            profile["revenue"] = db_profile.annual_revenue

        from backend.grant_engine.recommendation_engine import get_recommendation_engine
        engine = get_recommendation_engine(top_n=top_n)
        result = engine.recommend(profile, top_n=top_n)
        return ok(
            data={
                "recommendations":    [r.to_dict() for r in result.recommendations],
                "total_grants_scanned": result.total_grants_scanned,
                "total_after_filter": result.total_after_filter,
                "readiness_score":    result.readiness_score,
                "missing_fields":     result.missing_fields,
                "processing_time_ms": result.processing_time_ms,
            },
            message=f"{result.count} grant recommendations found.",
        )
    except Exception as exc:
        from backend.grant_engine.exceptions import (
            InsufficientProfileError, NoGrantsFoundError
        )
        if isinstance(exc, InsufficientProfileError):
            return error(str(exc), code=422, error_code="INSUFFICIENT_PROFILE",
                         details={"missing_fields": exc.missing_fields})
        if isinstance(exc, NoGrantsFoundError):
            return error(str(exc), code=404, error_code="NO_GRANTS_FOUND")
        logger.error("recommend error: %s", exc, exc_info=True)
        return error("Recommendation engine error.", code=500)


@jwt_required()
def quick_eligibility_check() -> Tuple[Response, int]:
    
    if (err := require_json(request)):
        return err

    body    = request.get_json(silent=True) or {}
    profile = body.get("startup_profile") or {}
    grant_id = body.get("grant_id", "default")
    docs    = body.get("uploaded_doc_names", [])

    user_id = get_jwt_identity()
    try:
        from backend.app import db
        from backend.models.startup import StartupProfile

        db_profile = db.session.query(StartupProfile).filter_by(
            user_id=user_id, is_deleted=False
        ).first()

        if db_profile:
            db_dict = db_profile.to_dict()
            for k, v in db_dict.items():
                if v is not None:
                    if k not in profile or profile[k] == "" or profile[k] is None:
                        profile[k] = v
            if ("state" not in profile or profile["state"] == "") and db_dict.get("state_province"):
                profile["state"] = db_dict["state_province"]
            if ("sector" not in profile or profile["sector"] == "") and db_dict.get("industry"):
                profile["sector"] = db_dict["industry"]
            if ("founded_year" not in profile or profile["founded_year"] == "") and db_dict.get("founding_year"):
                profile["founded_year"] = db_dict["founding_year"]
            if ("funding_raised" not in profile or profile["funding_raised"] == "") and db_dict.get("total_funding_raised"):
                profile["funding_raised"] = db_dict["total_funding_raised"]

        if not profile or not profile.get("company_name"):
            return error("startup_profile is required.", code=422, error_code="MISSING_FIELD")

        from backend.grant_engine.grant_catalog import get_grant_catalog
        from backend.eligibility.eligibility_engine import get_eligibility_engine

        catalog   = get_grant_catalog()
        grant_obj = catalog.get_by_id(grant_id)
        if not grant_obj:
            return error(f"Grant '{grant_id}' not found.", code=404)

        grant_data = grant_obj.to_dict()
        grant_data.update({
            "requires_dpiit":        grant_obj.requires_dpiit,
            "max_company_age_years": grant_obj.max_company_age_years,
            "eligible_stages":       [s.value for s in grant_obj.eligible_stages],
            "max_team_size":         grant_obj.max_team_size,
            "min_team_size":         grant_obj.min_team_size,
            "target_sectors":        list(grant_obj.target_sectors),
            "excluded_sectors":      list(grant_obj.excluded_sectors),
            "max_funding_raised":    grant_obj.max_funding_raised,
        })

        engine = get_eligibility_engine()
        report = engine.check_for_grant(profile, grant_data, docs)
        return ok(data={"eligibility_report": report.to_dict()})

    except Exception as exc:
        from backend.eligibility.exceptions import InsufficientProfileError
        if isinstance(exc, InsufficientProfileError):
            return error(str(exc), code=422, error_code="INSUFFICIENT_PROFILE",
                         details={"missing_fields": exc.missing_fields})
        logger.error("quick_eligibility_check error: %s", exc, exc_info=True)
        return error("Eligibility check failed.", code=500)


@jwt_required()
def save_grant(grant_id: str) -> Tuple[Response, int]:
    
    user_id = get_jwt_identity()
    try:
        from backend.app import db
        from backend.models.startup import StartupProfile
        from backend.models.grant import Grant
        from backend.models.saved_grant import SavedGrant

        
        profile = db.session.query(StartupProfile).filter_by(
            user_id=user_id, is_deleted=False
        ).first()
        if not profile:
            return error("Startup profile not found. Please create a profile first.", code=404)

        
        import uuid
        is_uuid = False
        try:
            uuid.UUID(str(grant_id))
            is_uuid = True
        except ValueError:
            pass

        if is_uuid:
            db_grant = db.session.query(Grant).filter(
                (Grant.id == grant_id) | (Grant.slug == grant_id)
            ).first()
        else:
            db_grant = db.session.query(Grant).filter(
                Grant.slug == grant_id
            ).first()

        if not db_grant:
            
            from backend.grant_engine.grant_catalog import get_grant_catalog
            catalog = get_grant_catalog()
            g_obj = catalog.get_by_id(grant_id)
            if not g_obj:
                return error(f"Grant '{grant_id}' not found in catalog.", code=404)
            
            from backend.models.grant import GrantSource, GrantStatus, FundingCurrency
            db_grant = Grant(
                id=uuid.UUID(grant_id) if is_uuid else uuid.uuid4(),
                title=g_obj.name,
                slug=g_obj.id,
                external_id=g_obj.short_name,
                source=GrantSource.DATABASE,
                organization_name=g_obj.administering_body,
                status=GrantStatus.OPEN if g_obj.is_open else GrantStatus.CLOSED,
                country="India",
                currency=FundingCurrency.INR,
                description=g_obj.description,
                is_active=True
            )
            db.session.add(db_grant)
            db.session.commit()

        
        if request.method == "POST":
            
            existing = db.session.query(SavedGrant).filter_by(
                user_id=user_id, startup_id=profile.id, grant_id=db_grant.id
            ).first()
            if existing:
                db.session.delete(existing)
                db.session.commit()
                saved_count = db.session.query(SavedGrant).filter_by(user_id=user_id).count()
                payload = {
                    "success": True,
                    "message": "Bookmark removed successfully.",
                    "is_saved": False,
                    "saved_count": saved_count,
                    "data": {
                        "is_saved": False,
                        "saved_count": saved_count
                    }
                }
                return jsonify(payload), 200

            bookmark = SavedGrant(
                user_id=user_id,
                startup_id=profile.id,
                grant_id=db_grant.id,
                notes=request.get_json(silent=True).get("notes") if request.is_json else None
            )
            db.session.add(bookmark)
            db.session.commit()
            saved_count = db.session.query(SavedGrant).filter_by(user_id=user_id).count()
            payload = {
                "success": True,
                "message": "Grant bookmarked successfully.",
                "is_saved": True,
                "saved_count": saved_count,
                "data": {
                    "is_saved": True,
                    "saved_count": saved_count
                }
            }
            return jsonify(payload), 200

        elif request.method == "DELETE":
            
            bookmark = db.session.query(SavedGrant).filter_by(
                user_id=user_id, startup_id=profile.id, grant_id=db_grant.id
            ).first()
            if not bookmark:
                saved_count = db.session.query(SavedGrant).filter_by(user_id=user_id).count()
                payload = {
                    "success": True,
                    "message": "Bookmark not found.",
                    "is_saved": False,
                    "saved_count": saved_count,
                    "data": {
                        "is_saved": False,
                        "saved_count": saved_count
                    }
                }
                return jsonify(payload), 200
            db.session.delete(bookmark)
            db.session.commit()
            saved_count = db.session.query(SavedGrant).filter_by(user_id=user_id).count()
            payload = {
                "success": True,
                "message": "Bookmark removed successfully.",
                "is_saved": False,
                "saved_count": saved_count,
                "data": {
                    "is_saved": False,
                    "saved_count": saved_count
                }
            }
            return jsonify(payload), 200

    except Exception as exc:
        from backend.app import db as _db
        _db.session.rollback()
        logger.error("save_grant error: %s", exc, exc_info=True)
        return error("Failed to toggle bookmark.", code=500)


@jwt_required()
def list_saved_grants() -> Tuple[Response, int]:
    
    user_id = get_jwt_identity()
    try:
        from backend.app import db
        from backend.models.startup import StartupProfile
        from backend.models.saved_grant import SavedGrant
        from backend.grant_engine.grant_catalog import get_grant_catalog

        
        profile = db.session.query(StartupProfile).filter_by(
            user_id=user_id, is_deleted=False
        ).first()
        if not profile:
            return ok(data=[])

        bookmarks = db.session.query(SavedGrant).filter_by(
            user_id=user_id, startup_id=profile.id
        ).all()

        catalog = get_grant_catalog()
        result = []
        for b in bookmarks:
            db_grant = b.grant
            if not db_grant:
                continue
            
            catalog_grant = catalog.get_by_id(db_grant.slug)
            g_dict = catalog_grant.to_dict() if catalog_grant else {
                "id": db_grant.slug or str(db_grant.id),
                "name": db_grant.title,
                "short_name": db_grant.external_id,
                "administering_body": db_grant.organization_name,
                "description": db_grant.description,
                "is_open": db_grant.status == "open",
                "min_amount_inr": float(db_grant.min_funding_amount) if db_grant.min_funding_amount else None,
                "max_amount_inr": float(db_grant.max_funding_amount) if db_grant.max_funding_amount else None,
                "deadline": db_grant.deadline.isoformat() if db_grant.deadline else None,
            }
            
            result.append({
                "id": str(b.id),
                "grant_id": str(db_grant.id),
                "grant_slug": db_grant.slug,
                "notes": b.notes,
                "label": b.label,
                "grant": g_dict,
            })

        return ok(data=result)

    except Exception as exc:
        logger.error("list_saved_grants error: %s", exc, exc_info=True)
        return error("Failed to load bookmarked grants.", code=500)

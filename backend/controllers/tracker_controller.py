

import logging
from datetime import datetime, timezone
from typing import Tuple

from flask import Response, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from backend.utils.response import (
    ok, created, error, no_content, require_json,
    get_pagination_params, paginated,
)

logger = logging.getLogger("fundforge.controllers.tracker")


@jwt_required()
def create_application() -> Tuple[Response, int]:
    
    if (err := require_json(request)):
        return err

    user_id = get_jwt_identity()
    body = request.get_json(silent=True) or {}

    startup_id = body.get("startup_id")
    grant_id = body.get("grant_id")

    if not startup_id:
        try:
            from backend.app import db
            from backend.models.startup import StartupProfile
            db_profile = db.session.query(StartupProfile).filter_by(
                user_id=user_id, is_deleted=False
            ).first()
            if db_profile:
                startup_id = str(db_profile.id)
            else:
                return error("Startup profile not found. Please create a profile first.", code=422, error_code="PROFILE_NOT_FOUND")
        except Exception as e:
            return error(f"Failed to load startup profile: {e}", code=500)

    if not grant_id:
        return error("grant_id is required.", code=422, error_code="MISSING_FIELD")

    try:
        import uuid
        from backend.app import db
        from backend.models.application import Application, ApplicationStatus, ApplicationPriority
        from backend.models.grant import Grant

        
        try:
            uuid.UUID(str(startup_id))
        except ValueError:
            return error("Invalid startup_id format. Must be a UUID.", code=422)

        
        is_uuid = False
        try:
            uuid.UUID(str(grant_id))
            is_uuid = True
        except ValueError:
            pass

        if is_uuid:
            grant = db.session.query(Grant).filter((Grant.id == grant_id) | (Grant.slug == grant_id) | (Grant.external_id == grant_id)).first()
        else:
            grant = db.session.query(Grant).filter((Grant.slug == grant_id) | (Grant.external_id == grant_id)).first()

        if not grant:
            try:
                from backend.grant_engine.grant_catalog import get_grant_catalog
                g_obj = get_grant_catalog().get_by_id(grant_id)
                g_title = g_obj.name if g_obj else "Sample Grant"
                g_desc = g_obj.description if g_obj else "Grant description"
            except Exception:
                g_title = "Sample Grant"
                g_desc = "Grant description"

            grant = Grant(
                id=uuid.UUID(grant_id) if is_uuid else uuid.uuid4(),
                title=g_title,
                slug=grant_id,
                description=g_desc,
                organization_name="Government of India",
            )
            db.session.add(grant)
            db.session.commit()

        
        grant_id = grant.id

        existing = db.session.query(Application).filter_by(
            startup_id=startup_id, grant_id=grant_id,
        ).first()
        if existing:
            return error(
                "An application already exists for this startup + grant combination.",
                code=409, error_code="APPLICATION_EXISTS",
            )

        priority = ApplicationPriority.MEDIUM
        if body.get("priority"):
            try:
                priority = ApplicationPriority(body["priority"].lower())
            except ValueError:
                return error(f"Invalid priority: '{body['priority']}'.", code=422)

        deadline = None
        if body.get("deadline"):
            try:
                from datetime import date
                deadline = date.fromisoformat(body["deadline"])
            except (ValueError, TypeError):
                return error("Invalid deadline format. Use YYYY-MM-DD.", code=422)

        next_action_date = None
        if body.get("next_action_date"):
            try:
                from datetime import date
                next_action_date = date.fromisoformat(body["next_action_date"])
            except (ValueError, TypeError):
                return error("Invalid next_action_date format. Use YYYY-MM-DD.", code=422)

        application = Application(
            user_id=user_id,
            startup_id=startup_id,
            grant_id=grant_id,
            status=ApplicationStatus.SAVED,
            priority=priority,
            deadline=deadline,
            notes=body.get("notes"),
            next_action=body.get("next_action"),
            next_action_date=next_action_date,
            eligibility_score=body.get("eligibility_score"),
            eligibility_notes=body.get("eligibility_notes"),
        )

        db.session.add(application)
        db.session.commit()

        logger.info(
            "Application created: %s (user=%s, grant=%s)",
            application.id, user_id, grant_id,
        )
        return created(
            data={"application": application.to_dict()},
            message="Application tracking started.",
        )

    except Exception as exc:
        from backend.app import db as _db
        _db.session.rollback()
        logger.error("create_application error: %s", exc, exc_info=True)
        return error("Failed to create application.", code=500)


@jwt_required()
def list_applications() -> Tuple[Response, int]:
    
    user_id = get_jwt_identity()
    page, per_page = get_pagination_params(request)

    try:
        from backend.app import db
        from backend.models.application import Application, ApplicationStatus, ApplicationPriority

        query = db.session.query(Application).filter_by(user_id=user_id)

        status_filter = request.args.get("status")
        if status_filter:
            try:
                query = query.filter(Application.status == ApplicationStatus(status_filter.lower()))
            except ValueError:
                pass

        priority_filter = request.args.get("priority")
        if priority_filter:
            try:
                query = query.filter(Application.priority == ApplicationPriority(priority_filter.lower()))
            except ValueError:
                pass

        startup_filter = request.args.get("startup_id")
        if startup_filter:
            query = query.filter(Application.startup_id == startup_filter)

        query = query.order_by(Application.updated_at.desc())

        total = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()

        return paginated(
            items=[app.to_dict() for app in items],
            total=total, page=page, per_page=per_page,
            message=f"{total} applications found.",
        )

    except Exception as exc:
        logger.error("list_applications error: %s", exc, exc_info=True)
        return error("Failed to list applications.", code=500)


@jwt_required()
def get_application(application_id: str) -> Tuple[Response, int]:
    
    user_id = get_jwt_identity()
    try:
        from backend.app import db
        from backend.models.application import Application

        application = db.session.query(Application).filter_by(
            id=application_id, user_id=user_id,
        ).first()

        if not application:
            return error(f"Application '{application_id}' not found.", code=404)

        return ok(data={"application": application.to_dict()})

    except Exception as exc:
        logger.error("get_application error: %s", exc, exc_info=True)
        return error("Failed to retrieve application.", code=500)


@jwt_required()
def update_application(application_id: str) -> Tuple[Response, int]:
    
    if (err := require_json(request)):
        return err

    user_id = get_jwt_identity()
    body = request.get_json(silent=True) or {}

    if not body:
        return error("Request body is empty.", code=422)

    try:
        from backend.app import db
        from backend.models.application import Application, ApplicationPriority

        application = db.session.query(Application).filter_by(
            id=application_id, user_id=user_id,
        ).first()

        if not application:
            return error(f"Application '{application_id}' not found.", code=404)

        simple_fields = [
            "notes", "next_action", "internal_reference",
            "assigned_officer", "eligibility_notes",
        ]
        for field in simple_fields:
            if field in body:
                setattr(application, field, body[field])

        if "priority" in body and body["priority"]:
            try:
                application.priority = ApplicationPriority(body["priority"].lower())
            except ValueError:
                return error(f"Invalid priority: '{body['priority']}'.", code=422)

        if "deadline" in body:
            if body["deadline"]:
                try:
                    from datetime import date
                    application.deadline = date.fromisoformat(body["deadline"])
                except (ValueError, TypeError):
                    return error("Invalid deadline format.", code=422)
            else:
                application.deadline = None

        if "next_action_date" in body:
            if body["next_action_date"]:
                try:
                    from datetime import date
                    application.next_action_date = date.fromisoformat(body["next_action_date"])
                except (ValueError, TypeError):
                    return error("Invalid next_action_date format.", code=422)
            else:
                application.next_action_date = None

        if "eligibility_score" in body:
            application.eligibility_score = body["eligibility_score"]

        if "award_amount" in body:
            application.award_amount = body["award_amount"]

        if "rejection_reason" in body:
            application.rejection_reason = body["rejection_reason"]

        db.session.commit()
        logger.info("Application updated: %s", application_id)
        return ok(
            data={"application": application.to_dict()},
            message="Application updated successfully.",
        )

    except Exception as exc:
        from backend.app import db as _db
        _db.session.rollback()
        logger.error("update_application error: %s", exc, exc_info=True)
        return error("Failed to update application.", code=500)


@jwt_required()
def transition_status(application_id: str) -> Tuple[Response, int]:
    
    if (err := require_json(request)):
        return err

    user_id = get_jwt_identity()
    body = request.get_json(silent=True) or {}
    new_status_str = (body.get("new_status") or body.get("target_status") or "").strip()

    if not new_status_str:
        return error("new_status is required.", code=422, error_code="MISSING_FIELD")

    try:
        from backend.app import db
        from backend.models.application import Application, ApplicationStatus

        application = db.session.query(Application).filter_by(
            id=application_id, user_id=user_id,
        ).first()

        if not application:
            return error(f"Application '{application_id}' not found.", code=404)

        try:
            new_status = ApplicationStatus(new_status_str.lower())
        except ValueError:
            return error(
                f"Invalid status: '{new_status_str}'. "
                f"Valid statuses: {[s.value for s in ApplicationStatus]}",
                code=422,
            )

        old_status = application.status.value
        application.transition_to(new_status)

        if body.get("notes"):
            existing_notes = application.notes or ""
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            application.notes = (
                f"{existing_notes}\n[{timestamp}] {old_status} → {new_status.value}: {body['notes']}"
            ).strip()

        db.session.commit()

        logger.info(
            "Application %s transitioned: %s → %s",
            application_id, old_status, new_status.value,
        )
        return ok(
            data={"application": application.to_dict()},
            message=f"Status transitioned from '{old_status}' to '{new_status.value}'.",
        )

    except ValueError as ve:
        return error(str(ve), code=422, error_code="INVALID_TRANSITION")
    except Exception as exc:
        from backend.app import db as _db
        _db.session.rollback()
        logger.error("transition_status error: %s", exc, exc_info=True)
        return error("Failed to transition application status.", code=500)


@jwt_required()
def delete_application(application_id: str) -> Tuple[Response, int]:
    
    user_id = get_jwt_identity()
    try:
        from backend.app import db
        from backend.models.application import Application

        application = db.session.query(Application).filter_by(
            id=application_id, user_id=user_id,
        ).first()

        if not application:
            return error(f"Application '{application_id}' not found.", code=404)

        db.session.delete(application)
        db.session.commit()
        logger.info("Application deleted: %s", application_id)
        return no_content()

    except Exception as exc:
        from backend.app import db as _db
        _db.session.rollback()
        logger.error("delete_application error: %s", exc, exc_info=True)
        return error("Failed to delete application.", code=500)


@jwt_required()
def get_application_stats() -> Tuple[Response, int]:
    
    user_id = get_jwt_identity()
    try:
        from backend.app import db
        from backend.models.application import Application, ApplicationStatus
        from backend.models.startup import StartupProfile
        from sqlalchemy import func

        base = db.session.query(Application).filter_by(user_id=user_id)
        total = base.count()

        by_status = {}
        status_counts = (
            db.session.query(Application.status, func.count(Application.id))
            .filter_by(user_id=user_id)
            .group_by(Application.status)
            .all()
        )
        for status, count in status_counts:
            by_status[status.value] = count

        active = sum(
            by_status.get(s.value, 0)
            for s in [
                ApplicationStatus.SAVED,
                ApplicationStatus.RESEARCHING,
                ApplicationStatus.IN_PROGRESS,
                ApplicationStatus.SUBMITTED,
                ApplicationStatus.UNDER_REVIEW,
            ]
        )

        awarded = by_status.get(ApplicationStatus.AWARDED.value, 0)
        rejected = by_status.get(ApplicationStatus.REJECTED.value, 0)

        
        total_funding = db.session.query(func.sum(Application.award_amount)).filter(
            Application.user_id == user_id,
            Application.status == ApplicationStatus.AWARDED
        ).scalar() or 0.0

        
        completed = awarded + rejected
        success_rate = round((awarded / completed) * 100, 1) if completed > 0 else 0.0

        
        funding_by_month = []
        monthly_awards = (
            db.session.query(
                func.strftime("%Y-%m", Application.updated_at),
                func.sum(Application.award_amount)
            )
            .filter(
                Application.user_id == user_id,
                Application.status == ApplicationStatus.AWARDED
            )
            .group_by(func.strftime("%Y-%m", Application.updated_at))
            .order_by(func.strftime("%Y-%m", Application.updated_at).asc())
            .all()
        )
        for month_str, amount in monthly_awards:
            if month_str:
                funding_by_month.append({
                    "month": month_str,
                    "amount": float(amount or 0.0)
                })

        
        if not funding_by_month:
            from datetime import datetime
            curr_month = datetime.now().strftime("%Y-%m")
            funding_by_month.append({"month": curr_month, "amount": float(total_funding)})

        
        sector_stats = (
            db.session.query(
                StartupProfile.sector,
                Application.status,
                func.count(Application.id)
            )
            .join(StartupProfile, Application.startup_id == StartupProfile.id)
            .filter(Application.user_id == user_id)
            .group_by(StartupProfile.sector, Application.status)
            .all()
        )
        sec_map = {}
        for sector, status, count in sector_stats:
            if not sector:
                sector = "other"
            if sector not in sec_map:
                sec_map[sector] = {"awarded": 0, "rejected": 0, "total": 0}
            sec_map[sector]["total"] += count
            if status == ApplicationStatus.AWARDED:
                sec_map[sector]["awarded"] += count
            elif status == ApplicationStatus.REJECTED:
                sec_map[sector]["rejected"] += count

        success_rate_by_sector = []
        for sec, counts in sec_map.items():
            comp = counts["awarded"] + counts["rejected"]
            rate = round((counts["awarded"] / comp) * 100, 1) if comp > 0 else 0.0
            success_rate_by_sector.append({
                "sector": sec,
                "rate": rate,
                "total": counts["total"]
            })

        upcoming_deadlines = (
            base.filter(
                Application.deadline.isnot(None),
                Application.status.in_([
                    ApplicationStatus.SAVED,
                    ApplicationStatus.RESEARCHING,
                    ApplicationStatus.IN_PROGRESS,
                ]),
            )
            .order_by(Application.deadline.asc())
            .limit(5)
            .all()
        )

        return ok(data={
            "total": total,
            "active": active,
            "awarded": awarded,
            "rejected": rejected,
            "success_rate": success_rate,
            "total_funding_secured": float(total_funding),
            "by_status": by_status,
            "funding_by_month": funding_by_month,
            "success_rate_by_sector": success_rate_by_sector,
            "upcoming_deadlines": [
                {
                    "id": str(app.id),
                    "grant_id": str(app.grant_id),
                    "deadline": app.deadline.isoformat() if app.deadline else None,
                    "status": app.status.value,
                    "priority": app.priority.value,
                    "grant": {
                        "id": str(app.grant.id) if app.grant else str(app.grant_id),
                        "title": app.grant.title if app.grant else "Startup India Seed Fund Scheme",
                        "slug": app.grant.slug if app.grant else "sisfs",
                        "organization_name": app.grant.organization_name if app.grant else "DPIIT"
                    } if app.grant else {
                        "id": str(app.grant_id),
                        "title": "Startup India Seed Fund Scheme",
                        "slug": "sisfs",
                        "organization_name": "DPIIT"
                    }
                }
                for app in upcoming_deadlines
            ],
        })

    except Exception as exc:
        logger.error("get_application_stats error: %s", exc, exc_info=True)
        return error("Failed to load application stats.", code=500)

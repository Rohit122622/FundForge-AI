

import logging
from typing import Tuple

from flask import Response, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from backend.utils.response import (
    ok, created, no_content, error, paginated, require_json, get_pagination_params,
)

logger = logging.getLogger("fundforge.controllers.proposal")


def _get_body() -> dict:
    return request.get_json(silent=True) or {}


@jwt_required()
def generate_proposal() -> Tuple[Response, int]:
    
    if (err := require_json(request)):
        return err

    user_id = get_jwt_identity()
    from backend.app import db
    from backend.models.startup import StartupProfile
    db_profile = db.session.query(StartupProfile).filter_by(
        user_id=user_id, is_deleted=False
    ).first()
    if not db_profile:
        return error("Startup profile not found. Please create a profile first before generating a proposal.", code=404, error_code="PROFILE_NOT_FOUND")

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

    body     = _get_body()
    grant_d  = body.get("grant_data")
    grant_id = body.get("grant_id")

    if not profile or not profile.get("company_name"):
        return error("startup_profile is required.", code=422, error_code="MISSING_FIELD")

    
    if not grant_d and grant_id:
        try:
            from backend.grant_engine.grant_catalog import get_grant_catalog
            g_obj = get_grant_catalog().get_by_id(grant_id)
            if g_obj:
                grant_d = g_obj.to_dict()
                grant_d["id"] = grant_id
                grant_d["eligible_stages"] = [s.value for s in g_obj.eligible_stages]
            else:
                from backend.app import db
                from backend.models.grant import Grant
                import uuid
                is_uuid = False
                try:
                    uuid.UUID(str(grant_id))
                    is_uuid = True
                except ValueError:
                    pass
                if is_uuid:
                    db_grant = db.session.query(Grant).filter((Grant.id == grant_id) | (Grant.slug == grant_id) | (Grant.external_id == grant_id)).first()
                else:
                    db_grant = db.session.query(Grant).filter((Grant.slug == grant_id) | (Grant.external_id == grant_id)).first()
                if db_grant:
                    grant_d = {
                        "id": str(db_grant.id),
                        "name": db_grant.title,
                        "title": db_grant.title,
                        "short_name": db_grant.organization_acronym or db_grant.slug or "grant",
                        "description": db_grant.description,
                        "administering_body": db_grant.organization_name,
                        "application_url": db_grant.organization_url,
                        "min_amount_inr": float(db_grant.min_funding_amount) if db_grant.min_funding_amount else None,
                        "max_amount_inr": float(db_grant.max_funding_amount) if db_grant.max_funding_amount else None,
                        "eligible_stages": ["ideation", "proof_of_concept", "early_traction", "growth"],
                    }
        except Exception as exc:
            logger.error("Grant lookup failed: %s", exc)

    if not grant_d:
        return error("grant_data or grant_id is required.", code=422, error_code="MISSING_FIELD")

    try:
        from backend.proposal_generator.proposal_engine import ProposalEngine, ProposalRequest
        from backend.ibm.foundation_models import get_ai_provider
        from backend.rag.rag_engine import get_rag_engine

        ai = get_ai_provider()
        rag = get_rag_engine()
        engine = ProposalEngine(ai_provider=ai, rag_engine=rag)

        req = ProposalRequest(
            startup_profile   = profile,
            grant_data        = grant_d,
            sections          = body.get("sections"),
            tone              = body.get("tone"),
            user_instructions = body.get("user_instructions", ""),
            use_rag           = bool(body.get("use_rag", True)),
            use_ai_review     = bool(body.get("use_ai_review", False)),
            version           = int(body.get("version", 1)),
        )
        result = engine.generate(req)

        from backend.ibm import FallbackManager
        ai_metadata = {}
        if isinstance(ai, FallbackManager):
            ai_metadata = {
                "provider":          ai.last_active_provider,
                "fallback_used":     ai.last_fallback_used,
                "response_time_ms":  ai.last_response_time_ms,
            }

        
        import uuid
        from backend.app import db
        from backend.models.proposal import Proposal, ProposalStatus, ProposalTone
        from backend.models.startup import StartupProfile
        from backend.models.grant import Grant

        
        startup = db.session.query(StartupProfile).filter_by(user_id=user_id, is_deleted=False).first()
        if not startup:
            startup = StartupProfile(
                user_id=user_id,
                company_name=profile.get("company_name", "My Startup"),
                industry="other",
                stage="idea",
                description=profile.get("description", "Description"),
            )
            db.session.add(startup)
            db.session.commit()

        
        g_id = grant_id or grant_d.get("id") or "sisfs"
        is_uuid = False
        try:
            uuid.UUID(str(g_id))
            is_uuid = True
        except ValueError:
            pass

        if is_uuid:
            grant = db.session.query(Grant).filter((Grant.id == g_id) | (Grant.slug == g_id) | (Grant.external_id == g_id)).first()
        else:
            grant = db.session.query(Grant).filter((Grant.slug == g_id) | (Grant.external_id == g_id)).first()

        if not grant:
            grant = Grant(
                id=uuid.UUID(g_id) if is_uuid else uuid.uuid4(),
                title=grant_d.get("title") or grant_d.get("name") or "Sample Grant",
                slug=g_id,
                description=grant_d.get("description") or "Grant description",
                organization_name=grant_d.get("organization_name") or grant_d.get("agency") or grant_d.get("organization") or "Government of India",
            )
            db.session.add(grant)
            db.session.commit()

        
        db.session.query(Proposal).filter_by(
            startup_id=startup.id,
            grant_id=grant.id,
        ).update({"status": ProposalStatus.ARCHIVED})

        
        prop_uuid = uuid.uuid4()
        if result.proposal_id:
            try:
                prop_uuid = uuid.UUID(result.proposal_id)
            except ValueError:
                pass

        sections = result.draft.sections or {}
        proposal = Proposal(
            id=prop_uuid,
            user_id=user_id,
            startup_id=startup.id,
            grant_id=grant.id,
            version=result.version,
            status=ProposalStatus.COMPLETE,
            model_id=ai_metadata.get("provider", "unknown"),
            generation_time_ms=int(result.processing_time_ms or 0),
            tone=ProposalTone(body.get("tone", "professional").lower()),
            user_instructions=body.get("user_instructions", ""),
            quality_score=float(result.quality_score or 0) / 100.0,
            executive_summary=sections.get("executive_summary"),
            problem_statement=sections.get("problem_statement"),
            proposed_solution=sections.get("proposed_solution") or sections.get("solution"),
            impact_statement=sections.get("impact_statement"),
            budget_narrative=sections.get("budget_narrative") or sections.get("budget"),
            timeline=sections.get("timeline"),
            team_qualifications=sections.get("team_qualifications") or sections.get("team"),
            full_text=result.draft.full_text_md,
        )
        db.session.add(proposal)
        db.session.commit()

        
        try:
            pdf_proposal = {**sections}
            pdf_proposal["sections"] = sections
            pdf_payload = {
                "proposal": pdf_proposal,
                "grant": {
                    "title": result.draft.grant_name or g_id,
                    "organization_name": grant.organization_name or "Government of India",
                },
                "startup": {
                    "company_name": startup.company_name,
                    "tagline": startup.description[:100] if startup.description else "",
                }
            }
            import backend.services.document_service as doc_svc
            doc_svc.generate_and_store_pdf(
                pdf_type="proposal",
                user_id=user_id,
                data=pdf_payload,
                startup_id=str(startup.id),
                proposal_id=str(prop_uuid),
            )
        except Exception as pdf_exc:
            logger.error("Failed to auto-store proposal PDF as Document: %s", pdf_exc, exc_info=True)

        return created(
            data={
                "proposal_id":        str(prop_uuid),
                "version":            result.version,
                "status":             result.status,
                "quality_score":      result.quality_score,
                "readiness_band":     result.readiness_band,
                "sections_generated": result.sections_generated,
                "rag_chunks_used":    result.rag_chunks_used,
                "processing_time_ms": result.processing_time_ms,
                "draft":              result.draft.to_dict(),
                "review":             result.review.to_dict(),
                "ai_metadata":        ai_metadata,
            },
            message=f"Proposal generated successfully. Quality: {result.quality_score}/100.",
        )
    except Exception as exc:
        try:
            from backend.app import db as _db
            _db.session.rollback()
        except Exception:
            pass
        from backend.proposal_generator.exceptions import (
            InsufficientDataError, ProposalValidationError,
        )
        if isinstance(exc, InsufficientDataError):
            return error(str(exc), code=422, error_code="INSUFFICIENT_DATA",
                         details={"missing_fields": exc.missing_fields})
        if isinstance(exc, ProposalValidationError):
            return error(str(exc), code=422, error_code="PROPOSAL_VALIDATION_ERROR")
        logger.error("generate_proposal error: %s", exc, exc_info=True)
        return error("Proposal generation failed.", code=500)


@jwt_required()
def generate_section() -> Tuple[Response, int]:
    
    if (err := require_json(request)):
        return err

    body        = _get_body()
    section_key = body.get("section_key", "")
    profile     = body.get("startup_profile")
    grant_d     = body.get("grant_data", {})

    if not section_key:
        return error("section_key is required.", code=422)
    if not profile:
        return error("startup_profile is required.", code=422)

    try:
        from backend.proposal_generator.proposal_engine import ProposalEngine
        from backend.ibm import get_ai_provider
        ai = get_ai_provider()
        engine  = ProposalEngine(ai_provider=ai)
        section = engine.generate_section(
            section_key       = section_key,
            startup_profile   = profile,
            grant_data        = grant_d,
            user_instructions = body.get("user_instructions", ""),
            use_rag           = bool(body.get("use_rag", True)),
        )
        
        from backend.ibm import FallbackManager
        ai_metadata = {}
        if isinstance(ai, FallbackManager):
            ai_metadata = {
                "provider":          ai.last_active_provider,
                "fallback_used":     ai.last_fallback_used,
                "response_time_ms":  ai.last_response_time_ms,
            }

        return ok(
            data={
                "section":     section.to_dict(),
                "ai_metadata": ai_metadata,
            },
            message=f"Section '{section_key}' generated.",
        )
    except Exception as exc:
        logger.error("generate_section error: %s", exc, exc_info=True)
        return error(f"Section generation failed: {exc}", code=500)


@jwt_required()
def list_proposals() -> Tuple[Response, int]:
    
    try:
        from backend.app import db
        from backend.models.proposal import Proposal
        user_id = get_jwt_identity()

        page, per_page = get_pagination_params(request)
        query = db.session.query(Proposal).filter_by(user_id=user_id, is_deleted=False)

        status = request.args.get("status")
        if status:
            query = query.filter_by(status=status)

        grant_id = request.args.get("grant_id")
        if grant_id:
            query = query.filter_by(grant_id=grant_id)

        total = query.count()
        start = (page - 1) * per_page
        proposals = query.order_by(Proposal.created_at.desc()).offset(start).limit(per_page).all()

        items = [p.to_dict() for p in proposals]
        return paginated(items, total, page, per_page, f"{total} proposals found.")
    except Exception as exc:
        logger.error("list_proposals error: %s", exc, exc_info=True)
        return error("Failed to list proposals.", code=500)


@jwt_required()
def get_proposal(proposal_id: str) -> Tuple[Response, int]:
    
    try:
        from backend.app import db
        from backend.models.proposal import Proposal
        proposal = db.session.query(Proposal).filter_by(id=proposal_id, is_deleted=False).first()
        if not proposal:
            return error(f"Proposal '{proposal_id}' not found.", code=404, error_code="NOT_FOUND")
        return ok(data={"proposal": proposal.to_dict()})
    except Exception as exc:
        logger.error("get_proposal error: %s", exc, exc_info=True)
        return error("Failed to retrieve proposal.", code=500)


@jwt_required()
def update_proposal(proposal_id: str) -> Tuple[Response, int]:
    
    if (err := require_json(request)):
        return err
    body = _get_body()
    try:
        from backend.app import db
        from backend.models.proposal import Proposal
        proposal = db.session.query(Proposal).filter_by(id=proposal_id, is_deleted=False).first()
        if not proposal:
            return error(f"Proposal '{proposal_id}' not found.", code=404, error_code="NOT_FOUND")

        updatable_fields = [
            "executive_summary", "problem_statement", "proposed_solution",
            "impact_statement", "budget_narrative", "timeline",
            "team_qualifications", "user_rating", "user_feedback",
        ]
        for f in updatable_fields:
            if f in body:
                setattr(proposal, f, body[f])

        db.session.commit()
        return ok(data={"proposal": proposal.to_dict()}, message="Proposal updated successfully.")
    except Exception as exc:
        try:
            from backend.app import db as _db
            _db.session.rollback()
        except Exception:
            pass
        logger.error("update_proposal error: %s", exc, exc_info=True)
        return error("Failed to update proposal.", code=500)


@jwt_required()
def delete_proposal(proposal_id: str) -> Tuple[Response, int]:
    
    try:
        from backend.app import db
        from backend.models.proposal import Proposal
        proposal = db.session.query(Proposal).filter_by(id=proposal_id, is_deleted=False).first()
        if not proposal:
            return error(f"Proposal '{proposal_id}' not found.", code=404, error_code="NOT_FOUND")
        proposal.is_deleted = True
        db.session.commit()
        return no_content()
    except Exception as exc:
        try:
            from backend.app import db as _db
            _db.session.rollback()
        except Exception:
            pass
        logger.error("delete_proposal error: %s", exc, exc_info=True)
        return error("Failed to delete proposal.", code=500)


@jwt_required()
def export_proposal(proposal_id: str) -> Tuple[Response, int]:
    
    try:
        from backend.app import db
        from backend.models.proposal import Proposal
        from backend.proposal_generator.export_manager import ExportManager
        from backend.proposal_generator.proposal_builder import ProposalDraft

        proposal = db.session.query(Proposal).filter_by(id=proposal_id, is_deleted=False).first()
        if not proposal:
            return error(f"Proposal '{proposal_id}' not found.", code=404, error_code="NOT_FOUND")

        fmt = request.args.get("format", "markdown").lower()

        
        from backend.proposal_generator.proposal_builder import parse_sections_from_markdown
        sections = parse_sections_from_markdown(proposal.full_text)
        
        
        for k in ["executive_summary", "problem_statement", "proposed_solution",
                  "impact_statement", "budget_narrative", "timeline", "team_qualifications"]:
            if k not in sections or not sections[k]:
                sections[k] = getattr(proposal, k) or ""

        
        standard_order = [
            "executive_summary",
            "problem_statement",
            "proposed_solution",
            "innovation_technology",
            "market_opportunity",
            "competitive_advantage",
            "implementation_plan",
            "budget_narrative",
            "financial_plan",
            "kpis",
            "risk_mitigation",
            "impact_statement",
            "timeline",
            "conclusion",
        ]
        
        section_order = []
        for k in standard_order:
            if sections.get(k) and sections[k].strip():
                section_order.append(k)
        for k in sections.keys():
            if k not in standard_order and sections[k].strip():
                section_order.append(k)

        startup = proposal.startup
        industry_val = "Not Specified"
        stage_val = "Not Specified"
        location_val = "India"
        website_val = "Not Specified"
        founding_year_val = "Not Specified"
        team_size_val = "Not Specified"

        if startup:
            industry_val = getattr(startup, "industry", None) or getattr(startup, "sector", None) or "Not Specified"
            stage_val = getattr(startup, "stage", None) or "Not Specified"
            loc_parts = []
            if getattr(startup, "city", None):
                loc_parts.append(startup.city)
            if getattr(startup, "state_province", None) or getattr(startup, "state", None):
                loc_parts.append(getattr(startup, "state_province", None) or getattr(startup, "state", None))
            if getattr(startup, "country", None):
                loc_parts.append(startup.country)
            if loc_parts:
                location_val = ", ".join(loc_parts)
            website_val = getattr(startup, "website", None) or "Not Specified"
            founding_year_val = str(getattr(startup, "founding_year", None) or getattr(startup, "founded_year", None) or "Not Specified")
            team_size_val = str(getattr(startup, "team_size", None) or "Not Specified")

        draft = ProposalDraft(
            proposal_id=str(proposal.id),
            version=proposal.version,
            company_name=proposal.startup.company_name if proposal.startup else "My Startup",
            grant_name=proposal.grant.title if proposal.grant else "My Grant",
            grant_id=proposal.grant.slug if proposal.grant else "sisfs",
            template_id="default",
            tone=proposal.tone.value if proposal.tone else "professional",
            sections=sections,
            section_order=section_order,
            full_text_md=proposal.full_text or "",
            full_text_plain=proposal.full_text or "",
            industry=industry_val,
            stage=stage_val,
            location=location_val,
            website=website_val,
            founding_year=founding_year_val,
            team_size=team_size_val,
        )

        export_mgr = ExportManager()
        result = export_mgr.export(draft, format=fmt)

        return ok(
            data={
                "content":      result.content,
                "format":       result.format,
                "content_type": result.mime_type,
                "filename":     result.filename,
            },
            message=f"Proposal exported to {fmt} format.",
        )
    except Exception as exc:
        logger.error("export_proposal error: %s", exc, exc_info=True)
        return error("Failed to export proposal.", code=500)


@jwt_required()
def review_proposal(proposal_id: str) -> Tuple[Response, int]:
    
    try:
        from backend.app import db
        from backend.models.proposal import Proposal
        from backend.proposal_generator.review_engine import ReviewEngine
        from backend.proposal_generator.proposal_builder import ProposalDraft

        proposal = db.session.query(Proposal).filter_by(id=proposal_id, is_deleted=False).first()
        if not proposal:
            return error(f"Proposal '{proposal_id}' not found.", code=404, error_code="NOT_FOUND")

        draft = ProposalDraft(
            proposal_id=str(proposal.id),
            version=proposal.version,
            company_name=proposal.startup.company_name if proposal.startup else "My Startup",
            grant_name=proposal.grant.title if proposal.grant else "My Grant",
            grant_id=proposal.grant.slug if proposal.grant else "sisfs",
            template_id="default",
            tone=proposal.tone.value if proposal.tone else "professional",
            sections={
                "executive_summary": proposal.executive_summary or "",
                "problem_statement": proposal.problem_statement or "",
                "proposed_solution": proposal.proposed_solution or "",
                "impact_statement": proposal.impact_statement or "",
                "budget_narrative": proposal.budget_narrative or "",
                "timeline": proposal.timeline or "",
                "team_qualifications": proposal.team_qualifications or "",
            }
        )

        from backend.proposal_generator.template_manager import get_template_manager
        tm = get_template_manager()
        grant_slug = proposal.grant.slug if proposal.grant else "sisfs"
        template = tm.resolve_for_grant(grant_slug)

        review_engine = ReviewEngine()
        report = review_engine.review(draft, template=template)

        proposal.quality_score = float(report.quality_score) / 100.0
        db.session.commit()

        return ok(data={"review": report.to_dict()}, message="Proposal reviewed successfully.")
    except Exception as exc:
        try:
            from backend.app import db as _db
            _db.session.rollback()
        except Exception:
            pass
        logger.error("review_proposal error: %s", exc, exc_info=True)
        return error("Failed to run proposal review.", code=500)


def list_templates() -> Tuple[Response, int]:
    
    try:
        from backend.proposal_generator.template_manager import get_template_manager
        tm = get_template_manager()
        return ok(
            data={"templates": tm.list_templates(), "total": tm.count},
            message=f"{tm.count} proposal templates available.",
        )
    except Exception as exc:
        logger.error("list_templates error: %s", exc, exc_info=True)
        return error("Failed to load templates.", code=500)


@jwt_required()
def get_proposal_readiness() -> Tuple[Response, int]:
    
    if (err := require_json(request)):
        return err
    body = _get_body()
    profile = body.get("startup_profile")
    if not profile:
        return error("startup_profile is required.", code=422)
    try:
        from backend.proposal_generator.proposal_engine import ProposalEngine
        from backend.ibm.foundation_models import get_ai_provider
        engine = ProposalEngine(ai_provider=get_ai_provider())
        report = engine.get_readiness_report(profile)
        return ok(data=report, message="Readiness report generated.")
    except Exception as exc:
        logger.error("get_proposal_readiness error: %s", exc, exc_info=True)
        return error("Readiness check failed.", code=500)



import io
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("fundforge.utils.pdf_generator")





try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        HRFlowable,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
    _REPORTLAB_AVAILABLE = True
except ImportError:
    _REPORTLAB_AVAILABLE = False
    logger.warning(
        "ReportLab is not installed. PDF generation will be unavailable. "
        "Install with: pip install reportlab"
    )






def _color(hex_str: str):
    
    hex_str = hex_str.lstrip("#")
    r, g, b = int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)
    return colors.Color(r / 255, g / 255, b / 255)


_NAVY    = "#1B2B5E"
_ACCENT  = "#3B82D4"
_MIDGREY = "#57606A"
_LTGREY  = "#F7F8FA"
_WHITE   = "#FFFFFF"
_BLACK   = "#1F2328"
_GREEN   = "#1A7F4B"
_RED     = "#C0392B"






def _build_styles() -> Dict[str, Any]:
    
    if not _REPORTLAB_AVAILABLE:
        return {}

    base = getSampleStyleSheet()

    def ps(name: str, **kwargs) -> ParagraphStyle:
        return ParagraphStyle(name, parent=base["Normal"], **kwargs)

    return {
        "cover_title": ps(
            "CoverTitle",
            fontName="Helvetica-Bold",
            fontSize=26,
            textColor=_color(_NAVY),
            spaceAfter=8,
            leading=32,
        ),
        "cover_subtitle": ps(
            "CoverSubtitle",
            fontName="Helvetica",
            fontSize=13,
            textColor=_color(_MIDGREY),
            spaceAfter=6,
        ),
        "h1": ps(
            "H1",
            fontName="Helvetica-Bold",
            fontSize=16,
            textColor=_color(_NAVY),
            spaceBefore=18,
            spaceAfter=6,
            leading=20,
        ),
        "h2": ps(
            "H2",
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=_color(_ACCENT),
            spaceBefore=14,
            spaceAfter=4,
            leading=16,
        ),
        "h3": ps(
            "H3",
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=_color(_BLACK),
            spaceBefore=10,
            spaceAfter=3,
        ),
        "body": ps(
            "Body",
            fontName="Helvetica",
            fontSize=10,
            textColor=_color(_BLACK),
            leading=15,
            spaceAfter=6,
            alignment=TA_JUSTIFY,
        ),
        "body_left": ps(
            "BodyLeft",
            fontName="Helvetica",
            fontSize=10,
            textColor=_color(_BLACK),
            leading=15,
            spaceAfter=4,
        ),
        "label": ps(
            "Label",
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=_color(_MIDGREY),
            spaceAfter=1,
        ),
        "value": ps(
            "Value",
            fontName="Helvetica",
            fontSize=10,
            textColor=_color(_BLACK),
            spaceAfter=6,
        ),
        "badge": ps(
            "Badge",
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=_color(_ACCENT),
        ),
        "footer": ps(
            "Footer",
            fontName="Helvetica",
            fontSize=8,
            textColor=_color(_MIDGREY),
            alignment=TA_CENTER,
        ),
        "small": ps(
            "Small",
            fontName="Helvetica",
            fontSize=8,
            textColor=_color(_MIDGREY),
            spaceAfter=2,
        ),
        "amount": ps(
            "Amount",
            fontName="Helvetica-Bold",
            fontSize=14,
            textColor=_color(_GREEN),
            spaceAfter=4,
        ),
    }






class _PageDecorator:
    

    def __init__(self, doc_title: str, company: str = "FundForge AI"):
        self.doc_title = doc_title
        self.company = company
        self._generated = datetime.now(timezone.utc).strftime("%B %d, %Y")

    def __call__(self, canvas, doc):
        if not _REPORTLAB_AVAILABLE:
            return
        canvas.saveState()
        w, h = doc.pagesize

        
        canvas.setFillColor(_color(_NAVY))
        canvas.rect(0, h - 28 * mm, w, 28 * mm, fill=1, stroke=0)

        
        canvas.setFillColor(_color(_WHITE))
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawString(20 * mm, h - 16 * mm, self.company)

        
        canvas.setFont("Helvetica", 9)
        canvas.drawCentredString(w / 2, h - 16 * mm, self.doc_title)

        
        canvas.drawRightString(w - 20 * mm, h - 16 * mm, self._generated)

        
        canvas.setFillColor(_color(_LTGREY))
        canvas.rect(0, 0, w, 14 * mm, fill=1, stroke=0)

        
        canvas.setFillColor(_color(_MIDGREY))
        canvas.setFont("Helvetica", 8)
        canvas.drawCentredString(
            w / 2, 5 * mm,
            f"Page {doc.page}  ·  Confidential  ·  Generated by {self.company}",
        )

        canvas.restoreState()






def _divider(styles: dict):
    return HRFlowable(
        width="100%",
        thickness=0.5,
        color=_color(_ACCENT),
        spaceAfter=6,
        spaceBefore=4,
    )


def _kv_row(label: str, value: str, styles: dict) -> List:
    
    return [
        Paragraph(label.upper(), styles["label"]),
        Paragraph(str(value) if value else "—", styles["value"]),
    ]


def _kv_table(rows: List[tuple], styles: dict) -> Table:
    
    data = []
    for label, value in rows:
        data.append([
            Paragraph(label.upper(), styles["label"]),
            Paragraph(str(value) if value else "—", styles["value"]),
        ])

    t = Table(data, colWidths=["35%", "65%"])
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0),    _color(_LTGREY)),
        ("BACKGROUND",  (0, 0), (0, -1),    _color(_LTGREY)),
        ("TEXTCOLOR",   (0, 0), (-1, -1),   _color(_BLACK)),
        ("FONTNAME",    (0, 0), (-1, -1),   "Helvetica"),
        ("FONTSIZE",    (0, 0), (-1, -1),   9),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [_color(_WHITE), _color(_LTGREY)]),
        ("GRID",        (0, 0), (-1, -1),   0.25, _color("#E5E7EB")),
        ("TOPPADDING",  (0, 0), (-1, -1),   5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1),   8),
    ]))
    return t


def _section_header(title: str, styles: dict) -> List:
    return [
        Spacer(1, 4 * mm),
        Paragraph(title, styles["h1"]),
        _divider(styles),
    ]


def _subsection(title: str, body: str, styles: dict) -> List:
    elements = [Paragraph(title, styles["h2"])]
    if body:
        for para in body.split("\n\n"):
            para = para.strip()
            if para:
                elements.append(Paragraph(para, styles["body"]))
    return elements


def _check_reportlab() -> None:
    if not _REPORTLAB_AVAILABLE:
        raise RuntimeError(
            "ReportLab is required for PDF generation. "
            "Install with: pip install reportlab"
        )


def _fmt_currency(amount, currency: str = "USD") -> str:
    
    if amount is None:
        return "—"
    try:
        return f"{currency} {float(amount):,.0f}"
    except (ValueError, TypeError):
        return str(amount)


def _fmt_date(d) -> str:
    
    if d is None:
        return "—"
    if hasattr(d, "strftime"):
        return d.strftime("%B %d, %Y")
    return str(d)






def generate_proposal_pdf(
    proposal: Dict[str, Any],
    grant: Dict[str, Any],
    startup: Dict[str, Any],
) -> bytes:
    
    _check_reportlab()
    styles = _build_styles()
    buf = io.BytesIO()

    title = f"Grant Proposal — {grant.get('title', 'Grant Application')[:60]}"
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=35 * mm,
        bottomMargin=20 * mm,
        title=title,
        author=startup.get("company_name", "FundForge AI"),
    )

    decorator = _PageDecorator(doc_title=title, company="FundForge AI")
    story = []

    
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph(startup.get("company_name", "Company Name"), styles["cover_title"]))
    story.append(Paragraph(startup.get("tagline", ""), styles["cover_subtitle"]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(f"Grant Application: {grant.get('title', '')}", styles["h2"]))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        f"Organisation: {grant.get('organization_name', '—')}",
        styles["body_left"],
    ))
    if grant.get("deadline"):
        story.append(Paragraph(f"Deadline: {_fmt_date(grant['deadline'])}", styles["body_left"]))
    if grant.get("max_funding_amount"):
        story.append(Paragraph(
            f"Maximum Award: {_fmt_currency(grant.get('max_funding_amount'), grant.get('currency', 'USD'))}",
            styles["amount"],
        ))
    story.append(Spacer(1, 6 * mm))
    story.append(_divider(styles))

    
    story += _section_header("Application Details", styles)
    meta_rows = [
        ("Applicant",     startup.get("company_name", "—")),
        ("Industry",      startup.get("industry", "—").replace("_", " ").title()),
        ("Stage",         startup.get("stage", "—").replace("_", " ").title()),
        ("Location",      f"{startup.get('city', '')} {startup.get('state_province', '')} {startup.get('country', '')}".strip()),
        ("Team Size",     str(startup.get("team_size", "—"))),
        ("Founding Year", str(startup.get("founding_year", "—"))),
        ("Website",       startup.get("website", "—")),
        ("Grant",         grant.get("title", "—")),
        ("Grantor",       grant.get("organization_name", "—")),
        ("Proposal Ver.", f"v{proposal.get('version', 1)}"),
        ("Generated",     _fmt_date(datetime.now(timezone.utc))),
    ]
    story.append(_kv_table(meta_rows, styles))

    
    standard_order = [
        ("executive_summary", "Executive Summary"),
        ("problem_statement", "Problem Statement"),
        ("proposed_solution", "Proposed Solution"),
        ("innovation_technology", "Innovation & Technology"),
        ("market_opportunity", "Market Opportunity"),
        ("competitive_advantage", "Competitive Advantage"),
        ("implementation_plan", "Implementation Plan"),
        ("budget_narrative", "Budget Utilisation"),
        ("financial_plan", "Financial Projections"),
        ("kpis", "Key Performance Indicators"),
        ("risk_mitigation", "Risk Analysis & Mitigation"),
        ("impact_statement", "Expected Impact"),
        ("timeline", "Implementation Timeline"),
        ("conclusion", "Conclusion"),
    ]

    sections = []
    prop_sections = proposal.get("sections") or {}
    for key, display_name in standard_order:
        val = prop_sections.get(key) or proposal.get(key)
        if val and val.strip():
            sections.append((display_name, val))
            
    for key, val in prop_sections.items():
        if key not in [item[0] for item in standard_order] and val and val.strip():
            sections.append((key.replace("_", " ").title(), val))

    for sec_title, sec_body in sections:
        if sec_body and sec_body.strip():
            story += _section_header(sec_title, styles)
            for para in sec_body.strip().split("\n\n"):
                para = para.strip()
                if para:
                    story.append(Paragraph(para, styles["body"]))

    
    if grant.get("ai_eligibility_notes"):
        story += _section_header("AI Eligibility Assessment", styles)
        story.append(Paragraph(grant["ai_eligibility_notes"], styles["body"]))

    
    story.append(PageBreak())
    story.append(Spacer(1, 20 * mm))
    story.append(Paragraph("Disclaimer", styles["h2"]))
    story.append(Paragraph(
        "This proposal was generated with the assistance of IBM Granite AI via the "
        "FundForge AI platform. The applicant is responsible for reviewing, editing, "
        "and verifying all content before submission. FundForge AI does not guarantee "
        "grant award outcomes.",
        styles["small"],
    ))

    doc.build(story, onFirstPage=decorator, onLaterPages=decorator)
    logger.info(
        "Proposal PDF generated: company=%s grant=%s size=%d bytes",
        startup.get("company_name"),
        grant.get("title", "")[:40],
        buf.tell(),
    )
    return buf.getvalue()






def generate_grant_report_pdf(
    grant: Dict[str, Any],
    match_score: Optional[int] = None,
    startup: Optional[Dict[str, Any]] = None,
) -> bytes:
    
    _check_reportlab()
    styles = _build_styles()
    buf = io.BytesIO()

    title = f"Grant Report — {grant.get('title', 'Grant')[:60]}"
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=35 * mm,
        bottomMargin=20 * mm,
        title=title,
    )

    decorator = _PageDecorator(doc_title=title)
    story = []

    
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(grant.get("title", "Grant Opportunity"), styles["cover_title"]))
    story.append(Paragraph(grant.get("organization_name", ""), styles["cover_subtitle"]))
    story.append(Spacer(1, 4 * mm))

    
    if match_score is not None:
        color = _GREEN if match_score >= 70 else (_ACCENT if match_score >= 40 else _RED)
        story.append(Paragraph(
            f'<font color="{color}"><b>AI Match Score: {match_score}/100</b></font>',
            styles["h2"],
        ))

    story.append(_divider(styles))

    
    story += _section_header("Grant Details", styles)
    detail_rows = [
        ("Organisation",    grant.get("organization_name", "—")),
        ("Acronym",         grant.get("organization_acronym", "—")),
        ("Type",            grant.get("grant_type", "—").replace("_", " ").title()),
        ("Sector",          grant.get("sector", "—").replace("_", " ").title()),
        ("Status",          grant.get("status", "—").upper()),
        ("Country",         grant.get("country", "—")),
        ("Min Award",       _fmt_currency(grant.get("min_funding_amount"), grant.get("currency", "USD"))),
        ("Max Award",       _fmt_currency(grant.get("max_funding_amount"), grant.get("currency", "USD"))),
        ("Typical Award",   _fmt_currency(grant.get("typical_award_amount"), grant.get("currency", "USD"))),
        ("Total Budget",    _fmt_currency(grant.get("total_program_budget"), grant.get("currency", "USD"))),
        ("Deadline",        _fmt_date(grant.get("deadline"))),
        ("Open Date",       _fmt_date(grant.get("open_date"))),
        ("Apply URL",       grant.get("application_url", "—")),
        ("Guidelines URL",  grant.get("guidelines_url", "—")),
    ]
    story.append(_kv_table(detail_rows, styles))

    
    if grant.get("description"):
        story += _section_header("Programme Description", styles)
        story.append(Paragraph(grant["description"], styles["body"]))

    
    if grant.get("eligibility_criteria"):
        story += _section_header("Eligibility Criteria", styles)
        story.append(Paragraph(grant["eligibility_criteria"], styles["body"]))

    
    if grant.get("application_requirements"):
        story += _section_header("Application Requirements", styles)
        story.append(Paragraph(grant["application_requirements"], styles["body"]))

    
    if grant.get("ai_summary"):
        story += _section_header("AI Summary", styles)
        story.append(Paragraph(grant["ai_summary"], styles["body"]))

    
    if startup:
        story += _section_header("Applicant Context", styles)
        ctx_rows = [
            ("Company",   startup.get("company_name", "—")),
            ("Industry",  startup.get("industry", "—").replace("_", " ").title()),
            ("Stage",     startup.get("stage", "—").replace("_", " ").title()),
            ("Funding Needed", startup.get("funding_needed", "—")),
        ]
        story.append(_kv_table(ctx_rows, styles))

    doc.build(story, onFirstPage=decorator, onLaterPages=decorator)
    logger.info("Grant report PDF generated: grant=%s", grant.get("title", "")[:40])
    return buf.getvalue()






def generate_application_pdf(
    application: Dict[str, Any],
    grant: Dict[str, Any],
    startup: Dict[str, Any],
) -> bytes:
    
    _check_reportlab()
    styles = _build_styles()
    buf = io.BytesIO()

    title = f"Application Summary — {startup.get('company_name', 'Applicant')}"
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=35 * mm,
        bottomMargin=20 * mm,
        title=title,
    )

    decorator = _PageDecorator(doc_title=title)
    story = []

    
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("Application Tracker Summary", styles["cover_title"]))
    story.append(Paragraph(startup.get("company_name", ""), styles["cover_subtitle"]))
    story.append(Spacer(1, 4 * mm))

    status = application.get("status", "unknown").upper().replace("_", " ")
    score  = application.get("eligibility_score")
    story.append(Paragraph(f"Status: {status}", styles["h2"]))
    if score is not None:
        story.append(Paragraph(f"Eligibility Score: {score}/100", styles["h3"]))

    story.append(_divider(styles))

    
    story += _section_header("Application Details", styles)
    app_rows = [
        ("Grant",             grant.get("title", "—")),
        ("Grantor",           grant.get("organization_name", "—")),
        ("Status",            status),
        ("Priority",          application.get("priority", "—").upper()),
        ("Deadline",          _fmt_date(application.get("deadline"))),
        ("Submitted",         _fmt_date(application.get("submitted_at"))),
        ("Award Date",        _fmt_date(application.get("awarded_at"))),
        ("Award Amount",      _fmt_currency(application.get("award_amount"))),
        ("Eligibility Score", f"{score}/100" if score is not None else "—"),
        ("Reference",         application.get("internal_reference", "—")),
        ("Programme Officer", application.get("assigned_officer", "—")),
        ("Next Action",       application.get("next_action", "—")),
        ("Next Action Date",  _fmt_date(application.get("next_action_date"))),
    ]
    story.append(_kv_table(app_rows, styles))

    
    if application.get("notes"):
        story += _section_header("Notes & Journal", styles)
        story.append(Paragraph(application["notes"], styles["body"]))

    
    if application.get("eligibility_notes"):
        story += _section_header("AI Eligibility Notes", styles)
        story.append(Paragraph(application["eligibility_notes"], styles["body"]))

    
    if application.get("rejection_reason"):
        story += _section_header("Rejection Feedback", styles)
        story.append(Paragraph(application["rejection_reason"], styles["body"]))

    
    story += _section_header("Grant Summary", styles)
    grant_rows = [
        ("Sector",      grant.get("sector", "—").replace("_", " ").title()),
        ("Type",        grant.get("grant_type", "—").replace("_", " ").title()),
        ("Max Award",   _fmt_currency(grant.get("max_funding_amount"), grant.get("currency", "USD"))),
        ("Deadline",    _fmt_date(grant.get("deadline"))),
        ("Apply URL",   grant.get("application_url", "—")),
    ]
    story.append(_kv_table(grant_rows, styles))

    doc.build(story, onFirstPage=decorator, onLaterPages=decorator)
    logger.info(
        "Application PDF generated: company=%s grant=%s",
        startup.get("company_name"),
        grant.get("title", "")[:40],
    )
    return buf.getvalue()






def generate_startup_profile_pdf(startup: Dict[str, Any]) -> bytes:
    
    _check_reportlab()
    styles = _build_styles()
    buf = io.BytesIO()

    company = startup.get("company_name", "Startup Profile")
    title = f"Company Profile — {company}"
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=35 * mm,
        bottomMargin=20 * mm,
        title=title,
    )

    decorator = _PageDecorator(doc_title=title)
    story = []

    
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph(company, styles["cover_title"]))
    if startup.get("tagline"):
        story.append(Paragraph(startup["tagline"], styles["cover_subtitle"]))
    story.append(Spacer(1, 6 * mm))

    profile_score = startup.get("profile_score", 0)
    story.append(Paragraph(
        f"Profile Completeness: {profile_score}%",
        styles["h3"],
    ))
    story.append(_divider(styles))

    
    story += _section_header("Company Overview", styles)
    overview_rows = [
        ("Company Name",     startup.get("company_name", "—")),
        ("Industry",         startup.get("industry", "—").replace("_", " ").title()),
        ("Stage",            startup.get("stage", "—").replace("_", " ").title()),
        ("Entity Type",      (startup.get("entity_type") or "—").replace("_", " ").title()),
        ("Founded",          str(startup.get("founding_year", "—"))),
        ("Team Size",        str(startup.get("team_size", "—"))),
        ("Country",          startup.get("country", "—")),
        ("State/Province",   startup.get("state_province", "—")),
        ("City",             startup.get("city", "—")),
        ("Website",          startup.get("website", "—")),
        ("Annual Revenue",   startup.get("annual_revenue", "—")),
        ("Total Raised",     startup.get("total_funding_raised", "—")),
        ("Funding Needed",   startup.get("funding_needed", "—")),
    ]
    story.append(_kv_table(overview_rows, styles))

    
    narrative_sections = [
        ("Company Description",  startup.get("description")),
        ("Problem Statement",    startup.get("problem_statement")),
        ("Solution",             startup.get("solution_statement")),
        ("Impact",               startup.get("impact_statement")),
        ("Target Market",        startup.get("target_market")),
        ("Technology Stack",     startup.get("technology_stack")),
    ]

    for sec_title, sec_body in narrative_sections:
        if sec_body and sec_body.strip():
            story += _section_header(sec_title, styles)
            story.append(Paragraph(sec_body.strip(), styles["body"]))

    doc.build(story, onFirstPage=decorator, onLaterPages=decorator)
    logger.info(
        "Startup profile PDF generated: company=%s score=%d%%",
        company,
        profile_score,
    )
    return buf.getvalue()

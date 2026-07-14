

import logging
from datetime import date, datetime, timezone, timedelta
from typing import List

logger = logging.getLogger("fundforge.database.seed")


def seed_all(app=None) -> None:
    
    def _run():
        logger.info("Starting database seed...")
        users = seed_users()
        startups = seed_startup_profiles(users)
        grants = seed_grants()
        seed_applications(users, startups, grants)
        seed_saved_grants(users, startups, grants)
        logger.info("Database seed complete.")

    if app is not None:
        with app.app_context():
            _run()
    else:
        _run()






def seed_users() -> List:
    
    from backend.app import db
    from backend.models import User, UserRole, UserStatus

    existing = db.session.query(User).count()
    if existing:
        logger.info("Users already seeded (%d found). Skipping.", existing)
        return db.session.query(User).all()

    users_data = [
        {
            "first_name": "Alice",
            "last_name": "Chen",
            "email": "alice@fundforge.dev",
            "role": UserRole.FOUNDER,
            "status": UserStatus.ACTIVE,
            "email_verified": True,
            "password": "DevPassword1!",
        },
        {
            "first_name": "Bob",
            "last_name": "Okafor",
            "email": "bob@fundforge.dev",
            "role": UserRole.FOUNDER,
            "status": UserStatus.ACTIVE,
            "email_verified": True,
            "password": "DevPassword1!",
        },
        {
            "first_name": "Admin",
            "last_name": "User",
            "email": "admin@fundforge.dev",
            "role": UserRole.ADMIN,
            "status": UserStatus.ACTIVE,
            "email_verified": True,
            "password": "AdminPass1!",
        },
    ]

    users = []
    for data in users_data:
        user = User(
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data["email"],
            role=data["role"],
            status=data["status"],
            email_verified=data["email_verified"],
            password_hash="placeholder",  
        )
        user.set_password(data["password"])
        db.session.add(user)
        users.append(user)

    db.session.commit()
    logger.info("Seeded %d users.", len(users))
    return users


def seed_startup_profiles(users: List) -> List:
    
    from backend.app import db
    from backend.models import StartupProfile, StartupStage, IndustryVertical, UserRole

    founder_users = [u for u in users if u.role == UserRole.FOUNDER]
    existing = db.session.query(StartupProfile).count()
    if existing:
        logger.info("Startup profiles already seeded (%d found). Skipping.", existing)
        return db.session.query(StartupProfile).all()

    profiles_data = [
        {
            "user": founder_users[0],
            "company_name": "GreenPath AI",
            "tagline": "Climate intelligence for sustainable supply chains",
            "industry": IndustryVertical.CLIMATE_TECH,
            "stage": StartupStage.SEED,
            "country": "United States",
            "state_province": "California",
            "city": "San Francisco",
            "team_size": 8,
            "founding_year": 2022,
            "description": (
                "GreenPath AI builds AI-powered supply chain analytics that help "
                "Fortune 500 companies measure, reduce, and report their Scope 3 "
                "carbon emissions. Our platform integrates with existing ERP systems "
                "and provides real-time emissions dashboards and reduction roadmaps."
            ),
            "problem_statement": (
                "Over 70% of corporate emissions come from supply chains, yet most "
                "companies lack the data infrastructure to measure them accurately."
            ),
            "solution_statement": (
                "We provide automated Scope 3 data collection, AI-powered emissions "
                "modelling, and actionable reduction recommendations."
            ),
            "impact_statement": (
                "Each customer on our platform reduces supply chain emissions by an "
                "average of 18% within 12 months."
            ),
            "funding_needed": "$2M–$5M",
            "annual_revenue": "$100k–$500k",
            "website": "https://greenpathAI.example.com",
        },
        {
            "user": founder_users[1],
            "company_name": "HealthBridge",
            "tagline": "Connecting rural communities to specialist care",
            "industry": IndustryVertical.HEALTH_TECH,
            "stage": StartupStage.PRE_SEED,
            "country": "United States",
            "state_province": "Texas",
            "city": "Austin",
            "team_size": 3,
            "founding_year": 2023,
            "description": (
                "HealthBridge is a telehealth platform purpose-built for rural "
                "communities. We connect patients in underserved areas with "
                "specialist physicians via asynchronous video consultations, "
                "reducing wait times from months to days."
            ),
            "problem_statement": (
                "30 million Americans in rural areas have no access to specialist "
                "healthcare within 50 miles of their home."
            ),
            "solution_statement": (
                "Async video consultations with AI-assisted triage that pre-screens "
                "patients and routes them to the right specialist automatically."
            ),
            "impact_statement": (
                "Pilot programme reduced specialist wait times by 73% across 4 rural "
                "counties in West Texas."
            ),
            "funding_needed": "$500k–$1M",
            "annual_revenue": "$0–$100k",
            "website": "https://healthbridge.example.com",
        },
    ]

    profiles = []
    for data in profiles_data:
        user = data.pop("user")
        profile = StartupProfile(user_id=user.id, **data)
        profile.compute_profile_score()
        db.session.add(profile)
        profiles.append(profile)

    db.session.commit()
    logger.info("Seeded %d startup profiles.", len(profiles))
    return profiles


def seed_grants() -> List:
    
    from backend.app import db
    from backend.models import Grant, GrantSource, GrantType, GrantSector, GrantStatus, FundingCurrency
    from backend.grant_engine.grant_catalog import get_grant_catalog
    from backend.grant_engine.startup_profiler import IndianSector
    from decimal import Decimal

    existing = db.session.query(Grant).count()
    if existing:
        logger.info("Grants already seeded (%d found). Skipping.", existing)
        return db.session.query(Grant).all()

    catalog = get_grant_catalog()
    all_catalog_grants = catalog.all()

    def map_instrument(inst) -> GrantType:
        from backend.grant_engine.grant_catalog import GrantInstrument
        
        mapping = {
            GrantInstrument.GRANT: GrantType.GRANT,
            GrantInstrument.EQUITY_FUND: GrantType.EQUITY,
            GrantInstrument.SOFT_LOAN: GrantType.LOAN,
            GrantInstrument.CREDIT_GUARANTEE: GrantType.OTHER,
            GrantInstrument.INCUBATION: GrantType.ACCELERATOR,
            GrantInstrument.FELLOWSHIP: GrantType.FELLOWSHIP,
            GrantInstrument.PRIZE: GrantType.PRIZE,
            GrantInstrument.SUBSIDY: GrantType.OTHER
        }
        return mapping.get(inst, GrantType.GRANT)

    def map_sector(sec) -> GrantSector:
        mapping = {
            IndianSector.AGRITECH: GrantSector.AGRICULTURE,
            IndianSector.BIOTECH: GrantSector.SCIENCE_RESEARCH,
            IndianSector.CLEAN_ENERGY: GrantSector.CLIMATE_ENVIRONMENT,
            IndianSector.DEEPTECH: GrantSector.TECH_STARTUP,
            IndianSector.DEFENCE: GrantSector.DEFENSE,
            IndianSector.EDTECH: GrantSector.EDUCATION,
            IndianSector.FINTECH: GrantSector.TECH_STARTUP,
            IndianSector.FOODTECH: GrantSector.AGRICULTURE,
            IndianSector.HEALTHTECH: GrantSector.HEALTH,
            IndianSector.ICT: GrantSector.TECH_STARTUP,
            IndianSector.MANUFACTURING: GrantSector.MANUFACTURING,
            IndianSector.MEDTECH: GrantSector.HEALTH,
            IndianSector.MOBILITY: GrantSector.TECH_STARTUP,
            IndianSector.RURAL_TECH: GrantSector.RURAL_DEVELOPMENT,
            IndianSector.SOCIAL_IMPACT: GrantSector.SOCIAL_ENTERPRISE,
            IndianSector.SPACE_TECH: GrantSector.TECH_STARTUP,
            IndianSector.WATER_SANITATION: GrantSector.RURAL_DEVELOPMENT,
            IndianSector.WOMEN_LED: GrantSector.WOMEN_OWNED,
            IndianSector.OTHER: GrantSector.OTHER
        }
        return mapping.get(sec, GrantSector.OTHER)

    grants = []
    for g in all_catalog_grants:
        primary_sec = list(g.target_sectors)[0] if g.target_sectors else IndianSector.OTHER
        grant_record = Grant(
            title=g.name,
            slug=g.id,
            external_id=g.short_name,
            source=GrantSource.DATABASE,
            organization_name=g.administering_body,
            organization_acronym=g.short_name,
            organization_url=g.application_url,
            grant_type=map_instrument(g.instrument),
            sector=map_sector(primary_sec),
            status=GrantStatus.OPEN if g.is_open else GrantStatus.CLOSED,
            country="India",
            currency=FundingCurrency.INR,
            min_funding_amount=Decimal(str(g.min_amount_inr)) if g.min_amount_inr else None,
            max_funding_amount=Decimal(str(g.max_amount_inr)) if g.max_amount_inr else None,
            typical_award_amount=Decimal(str(g.typical_amount_inr)) if g.typical_amount_inr else None,
            deadline=g.deadline,
            description=g.description,
            eligibility_criteria="\n".join(g.eligibility_summary),
            tags=",".join(g.tags),
            is_active=True,
            is_verified=True,
            is_featured=True if g.id in ["sisfs", "birac_big", "nidhi_prayas", "digital_india_genesis"] else False,
        )
        db.session.add(grant_record)
        grants.append(grant_record)

    db.session.commit()
    logger.info("Seeded %d grants.", len(grants))
    return grants


def seed_applications(users: List, startups: List, grants: List) -> None:
    
    from backend.app import db
    from backend.models import Application, ApplicationStatus, ApplicationPriority

    existing = db.session.query(Application).count()
    if existing:
        logger.info("Applications already seeded (%d found). Skipping.", existing)
        return

    if not startups or not grants:
        logger.warning("No startups or grants to seed applications against. Skipping.")
        return

    apps_data = [
        {
            "user_id": startups[0].user_id,
            "startup_id": startups[0].id,
            "grant_id": grants[0].id,
            "status": ApplicationStatus.IN_PROGRESS,
            "priority": ApplicationPriority.HIGH,
            "deadline": grants[0].deadline,
            "eligibility_score": 82,
            "notes": "Strong match. PI requirement needs verification with legal.",
            "next_action": "Complete technical narrative section",
            "next_action_date": date.today() + timedelta(days=7),
        },
        {
            "user_id": startups[0].user_id,
            "startup_id": startups[0].id,
            "grant_id": grants[3].id,
            "status": ApplicationStatus.RESEARCHING,
            "priority": ApplicationPriority.MEDIUM,
            "deadline": grants[3].deadline,
            "eligibility_score": 74,
            "notes": "High risk / high reward. Need to assess R&D budget alignment.",
        },
        {
            "user_id": startups[1].user_id,
            "startup_id": startups[1].id,
            "grant_id": grants[2].id,
            "status": ApplicationStatus.SUBMITTED,
            "priority": ApplicationPriority.HIGH,
            "deadline": grants[2].deadline,
            "eligibility_score": 91,
            "notes": "Excellent fit with rural telehealth focus.",
        },
    ]

    for data in apps_data:
        app_record = Application(**data)
        if data["status"] == ApplicationStatus.SUBMITTED:
            app_record.submitted_at = datetime.now(timezone.utc)
        db.session.add(app_record)

    db.session.commit()
    logger.info("Seeded %d applications.", len(apps_data))


def seed_saved_grants(users: List, startups: List, grants: List) -> None:
    
    from backend.app import db
    from backend.models import SavedGrant

    existing = db.session.query(SavedGrant).count()
    if existing:
        logger.info("SavedGrants already seeded (%d found). Skipping.", existing)
        return

    if not startups or not grants:
        logger.warning("No startups or grants to seed saved grants against. Skipping.")
        return

    saved_data = [
        {
            "user_id": startups[0].user_id,
            "startup_id": startups[0].id,
            "grant_id": grants[1].id,
            "notes": "Bookmarked for Q3 review — REAP rolling deadline.",
            "label": "Q3 Pipeline",
            "reminder_date": date.today() + timedelta(days=30),
        },
        {
            "user_id": startups[0].user_id,
            "startup_id": startups[0].id,
            "grant_id": grants[4].id,
            "notes": "Good fallback option if ARPA-E is too competitive.",
            "label": "Backup",
        },
        {
            "user_id": startups[1].user_id,
            "startup_id": startups[1].id,
            "grant_id": grants[0].id,
            "notes": "NSF SBIR for Phase 2 planning.",
            "label": "Future",
            "reminder_date": date.today() + timedelta(days=60),
        },
    ]

    for data in saved_data:
        saved = SavedGrant(**data)
        db.session.add(saved)

    db.session.commit()
    logger.info("Seeded %d saved grants.", len(saved_data))






if __name__ == "__main__":
    import os
    import sys

    
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

    from backend.app import create_app
    from backend.database.database import init_db

    flask_app = create_app(config_name="development")

    with flask_app.app_context():
        init_db()
        seed_all()

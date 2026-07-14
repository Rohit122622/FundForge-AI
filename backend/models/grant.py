

import logging
from datetime import date
from decimal import Decimal
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    Enum,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, validates

from backend.database.base import Base
from backend.models.base_model import BaseModel

if TYPE_CHECKING:
    from backend.models.application import Application
    from backend.models.saved_grant import SavedGrant
    from backend.models.proposal import Proposal

logger = logging.getLogger("fundforge.models.grant")






class GrantSource(str, PyEnum):
    
    DATABASE = "database"   
    GOOGLE   = "google"     
    MANUAL   = "manual"     


class GrantType(str, PyEnum):
    
    GRANT              = "grant"
    LOAN               = "loan"
    EQUITY             = "equity"
    PRIZE              = "prize"
    FELLOWSHIP         = "fellowship"
    ACCELERATOR        = "accelerator"
    CONTRACT           = "contract"
    TAX_CREDIT         = "tax_credit"
    IN_KIND_SUPPORT    = "in_kind_support"
    OTHER              = "other"


class GrantSector(str, PyEnum):
    
    AGRICULTURE         = "agriculture"
    ARTS_CULTURE        = "arts_culture"
    CLIMATE_ENVIRONMENT = "climate_environment"
    DEFENSE             = "defense"
    EDUCATION           = "education"
    ENERGY              = "energy"
    ENTREPRENEURSHIP    = "entrepreneurship"
    EXPORT_TRADE        = "export_trade"
    HEALTH              = "health"
    HOUSING             = "housing"
    INNOVATION          = "innovation"
    MANUFACTURING       = "manufacturing"
    MINORITY_OWNED      = "minority_owned"
    RURAL_DEVELOPMENT   = "rural_development"
    SCIENCE_RESEARCH    = "science_research"
    SOCIAL_ENTERPRISE   = "social_enterprise"
    STEM                = "stem"
    TECH_STARTUP        = "tech_startup"
    VETERANS            = "veterans"
    WOMEN_OWNED         = "women_owned"
    OTHER               = "other"


class GrantStatus(str, PyEnum):
    
    OPEN        = "open"
    ROLLING     = "rolling"   
    CLOSED      = "closed"
    UPCOMING    = "upcoming"
    EXPIRED     = "expired"
    UNKNOWN     = "unknown"


class FundingCurrency(str, PyEnum):
    
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    CAD = "CAD"
    AUD = "AUD"
    INR = "INR"
    OTHER = "OTHER"






class Grant(BaseModel, Base):
    

    __tablename__ = "grants"

    __table_args__ = (
        UniqueConstraint("external_id", "source", name="uq_grants_external_id_source"),
        Index("ix_grants_status", "status"),
        Index("ix_grants_sector", "sector"),
        Index("ix_grants_grant_type", "grant_type"),
        Index("ix_grants_deadline", "deadline"),
        Index("ix_grants_country", "country"),
        Index("ix_grants_is_active", "is_active"),
        Index("ix_grants_source", "source"),
        CheckConstraint(
            "min_funding_amount IS NULL OR max_funding_amount IS NULL OR "
            "min_funding_amount <= max_funding_amount",
            name="ck_grants_funding_range",
        ),
        CheckConstraint(
            "ai_match_score IS NULL OR (ai_match_score >= 0 AND ai_match_score <= 100)",
            name="ck_grants_match_score_range",
        ),
        {"comment": "Funding opportunity records from all sources"},
    )

    
    title: str = Column(
        String(500),
        nullable=False,
        comment="Grant programme or award title",
    )

    slug: Optional[str] = Column(
        String(600),
        nullable=True,
        index=True,
        comment="URL-safe unique identifier (auto-generated from title + id)",
    )

    external_id: Optional[str] = Column(
        String(255),
        nullable=True,
        comment="ID assigned by the source system (e.g. grants.gov opportunity number)",
    )

    source: GrantSource = Column(
        Enum(GrantSource, name="grant_source", create_constraint=True),
        nullable=False,
        default=GrantSource.DATABASE,
        comment="How this record was discovered / entered",
    )

    
    organization_name: str = Column(
        String(500),
        nullable=False,
        comment="Name of the granting organisation or agency",
    )

    organization_acronym: Optional[str] = Column(
        String(50),
        nullable=True,
        comment="Acronym (e.g. NSF, SBA, USDA)",
    )

    organization_url: Optional[str] = Column(
        String(500),
        nullable=True,
        comment="Granting organisation website",
    )

    
    grant_type: GrantType = Column(
        Enum(GrantType, name="grant_type", create_constraint=True),
        nullable=False,
        default=GrantType.GRANT,
        comment="Funding instrument type",
    )

    sector: GrantSector = Column(
        Enum(GrantSector, name="grant_sector", create_constraint=True),
        nullable=False,
        default=GrantSector.OTHER,
        comment="Primary programme sector",
    )

    secondary_sector: Optional[GrantSector] = Column(
        Enum(GrantSector, name="grant_sector_secondary", create_constraint=True),
        nullable=True,
        comment="Optional secondary sector",
    )

    status: GrantStatus = Column(
        Enum(GrantStatus, name="grant_status", create_constraint=True),
        nullable=False,
        default=GrantStatus.OPEN,
        comment="Current lifecycle status",
    )

    
    country: str = Column(
        String(100),
        nullable=False,
        default="United States",
        comment="Country where applicants must be located / operate",
    )

    state_province: Optional[str] = Column(
        String(200),
        nullable=True,
        comment="State / province restriction (NULL = no restriction)",
    )

    is_international: bool = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="True when the grant accepts international applicants",
    )

    
    currency: FundingCurrency = Column(
        Enum(FundingCurrency, name="funding_currency", create_constraint=True),
        nullable=False,
        default=FundingCurrency.USD,
        comment="Currency for funding amounts",
    )

    min_funding_amount: Optional[Decimal] = Column(
        Numeric(precision=15, scale=2),
        nullable=True,
        comment="Minimum award amount",
    )

    max_funding_amount: Optional[Decimal] = Column(
        Numeric(precision=15, scale=2),
        nullable=True,
        comment="Maximum award amount (NULL = uncapped)",
    )

    typical_award_amount: Optional[Decimal] = Column(
        Numeric(precision=15, scale=2),
        nullable=True,
        comment="Representative / average award size for display",
    )

    total_program_budget: Optional[Decimal] = Column(
        Numeric(precision=18, scale=2),
        nullable=True,
        comment="Total programme budget across all awards",
    )

    expected_awards_count: Optional[int] = Column(
        Integer,
        nullable=True,
        comment="Approximate number of awards expected this cycle",
    )

    
    deadline: Optional[date] = Column(
        Date,
        nullable=True,
        comment="Application deadline (NULL = rolling or unknown)",
    )

    open_date: Optional[date] = Column(
        Date,
        nullable=True,
        comment="Date applications open",
    )

    award_date: Optional[date] = Column(
        Date,
        nullable=True,
        comment="Expected announcement / award date",
    )

    
    description: str = Column(
        Text,
        nullable=False,
        comment="Full programme description — used by RAG pipeline and AI matching",
    )

    eligibility_criteria: Optional[str] = Column(
        Text,
        nullable=True,
        comment="Structured eligibility requirements",
    )

    application_requirements: Optional[str] = Column(
        Text,
        nullable=True,
        comment="What applicants must submit",
    )

    evaluation_criteria: Optional[str] = Column(
        Text,
        nullable=True,
        comment="How applications will be scored / evaluated",
    )

    
    application_url: Optional[str] = Column(
        String(500),
        nullable=True,
        comment="Direct link to the grant application portal",
    )

    guidelines_url: Optional[str] = Column(
        String(500),
        nullable=True,
        comment="Link to the full programme guidelines / NOFO",
    )

    
    ai_match_score: Optional[int] = Column(
        Integer,
        nullable=True,
        comment="IBM Granite relevance score 0–100 for the last matched startup",
    )

    ai_summary: Optional[str] = Column(
        Text,
        nullable=True,
        comment="AI-generated one-paragraph summary of the grant",
    )

    ai_eligibility_notes: Optional[str] = Column(
        Text,
        nullable=True,
        comment="AI-generated eligibility assessment notes",
    )

    tags: Optional[str] = Column(
        Text,
        nullable=True,
        comment="Comma-separated keyword tags for filtering and search",
    )

    
    is_active: bool = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="False when the grant is archived or deactivated",
    )

    is_featured: bool = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="True when manually featured on the discover page",
    )

    is_verified: bool = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="True when an admin has manually verified the grant details",
    )

    view_count: int = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of times this grant has been viewed on the platform",
    )

    application_count: int = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Denormalised count of applications submitted via FundForge",
    )

    
    applications: List["Application"] = relationship(
        "Application",
        back_populates="grant",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    saved_by: List["SavedGrant"] = relationship(
        "SavedGrant",
        back_populates="grant",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    proposals: List["Proposal"] = relationship(
        "Proposal",
        back_populates="grant",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    
    @validates("title")
    def validate_title(self, _key: str, value: str) -> str:
        value = (value or "").strip()
        if not value:
            raise ValueError("Grant title must not be blank.")
        return value

    @validates("min_funding_amount", "max_funding_amount", "typical_award_amount")
    def validate_amount(self, key: str, value) -> Optional[Decimal]:
        if value is None:
            return None
        dec = Decimal(str(value))
        if dec < 0:
            raise ValueError(f"{key} must be non-negative.")
        return dec

    
    @property
    def is_open(self) -> bool:
        
        return self.status in (GrantStatus.OPEN, GrantStatus.ROLLING) and self.is_active

    @property
    def days_until_deadline(self) -> Optional[int]:
        
        if self.deadline is None:
            return None
        delta = self.deadline - date.today()
        return delta.days

    @property
    def tag_list(self) -> List[str]:
        
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(",") if t.strip()]

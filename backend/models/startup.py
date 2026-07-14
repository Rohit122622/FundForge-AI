

import logging
import uuid
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, validates

from backend.database.base import Base
from backend.models.base_model import BaseModel, GUID

if TYPE_CHECKING:
    from backend.models.user import User
    from backend.models.application import Application
    from backend.models.proposal import Proposal
    from backend.models.saved_grant import SavedGrant

logger = logging.getLogger("fundforge.models.startup")






class StartupStage(str, PyEnum):
    
    IDEA          = "idea"
    PRE_SEED      = "pre_seed"
    SEED          = "seed"
    SERIES_A      = "series_a"
    SERIES_B      = "series_b"
    SERIES_C_PLUS = "series_c_plus"
    BOOTSTRAPPED  = "bootstrapped"
    PROFITABLE    = "profitable"


class IndustryVertical(str, PyEnum):
    
    AGRICULTURE         = "agriculture"
    CLIMATE_TECH        = "climate_tech"
    DEEP_TECH           = "deep_tech"
    EDUCATION           = "education"
    ENERGY              = "energy"
    FINTECH             = "fintech"
    GOVTECH             = "govtech"
    HEALTH_TECH         = "health_tech"
    LOGISTICS           = "logistics"
    MANUFACTURING       = "manufacturing"
    MEDIA_ENTERTAINMENT = "media_entertainment"
    REAL_ESTATE         = "real_estate"
    RETAIL              = "retail"
    SAAS                = "saas"
    SOCIAL_IMPACT       = "social_impact"
    OTHER               = "other"


class EntityType(str, PyEnum):
    
    SOLE_PROPRIETORSHIP = "sole_proprietorship"
    LLC                 = "llc"
    C_CORP              = "c_corp"
    S_CORP              = "s_corp"
    NONPROFIT           = "nonprofit"
    COOPERATIVE         = "cooperative"
    OTHER               = "other"






class StartupProfile(BaseModel, Base):
    

    __tablename__ = "startup_profiles"

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_startup_profiles_user_id"),
        Index("ix_startup_profiles_stage", "stage"),
        Index("ix_startup_profiles_industry", "industry"),
        Index("ix_startup_profiles_country", "country"),
        Index("ix_startup_profiles_user_id", "user_id"),
        CheckConstraint("team_size >= 1", name="ck_startup_profiles_team_size_positive"),
        CheckConstraint(
            "founding_year >= 1900 AND founding_year <= 2100",
            name="ck_startup_profiles_founding_year_range",
        ),
        {"comment": "Startup company profiles linked to user accounts"},
    )

    
    user_id: uuid.UUID = Column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Owning user account",
    )

    
    company_name: str = Column(
        String(255),
        nullable=False,
        comment="Legal or trading name of the startup",
    )

    tagline: Optional[str] = Column(
        String(300),
        nullable=True,
        comment="One-line value proposition",
    )

    website: Optional[str] = Column(
        String(500),
        nullable=True,
        comment="Company website URL",
    )

    logo_url: Optional[str] = Column(
        String(500),
        nullable=True,
        comment="URL to the company logo",
    )

    
    industry: IndustryVertical = Column(
        Enum(IndustryVertical, name="industry_vertical", create_constraint=True),
        nullable=False,
        comment="Primary industry sector",
    )

    secondary_industry: Optional[IndustryVertical] = Column(
        Enum(IndustryVertical, name="industry_vertical_secondary", create_constraint=True),
        nullable=True,
        comment="Secondary industry sector (optional cross-sector startups)",
    )

    stage: StartupStage = Column(
        Enum(StartupStage, name="startup_stage", create_constraint=True),
        nullable=False,
        comment="Current funding/development stage",
    )

    entity_type: Optional[EntityType] = Column(
        Enum(EntityType, name="entity_type", create_constraint=True),
        nullable=True,
        comment="Legal entity structure",
    )

    
    country: str = Column(
        String(100),
        nullable=False,
        default="India",
        comment="Country of incorporation / primary operations",
    )

    state_province: Optional[str] = Column(
        String(100),
        nullable=True,
        comment="State or province",
    )

    city: Optional[str] = Column(
        String(100),
        nullable=True,
        comment="City of primary operations",
    )

    
    team_size: int = Column(
        Integer,
        nullable=False,
        default=1,
        comment="Current full-time equivalent headcount",
    )

    founding_year: Optional[int] = Column(
        Integer,
        nullable=True,
        comment="Year the company was founded",
    )

    
    annual_revenue: Optional[str] = Column(
        String(50),
        nullable=True,
        comment="Annual revenue bracket (e.g. '$0–$100k', '$100k–$1M')",
    )

    total_funding_raised: Optional[str] = Column(
        String(50),
        nullable=True,
        comment="Total external funding raised to date (bracket or exact figure)",
    )

    funding_needed: Optional[str] = Column(
        String(50),
        nullable=True,
        comment="Approximate funding being sought in this round",
    )

    
    description: str = Column(
        Text,
        nullable=False,
        comment="Company description — primary input for AI grant matching",
    )

    problem_statement: Optional[str] = Column(
        Text,
        nullable=True,
        comment="Problem the startup solves",
    )

    solution_statement: Optional[str] = Column(
        Text,
        nullable=True,
        comment="How the product/service addresses the problem",
    )

    impact_statement: Optional[str] = Column(
        Text,
        nullable=True,
        comment="Social, environmental, or economic impact",
    )

    technology_stack: Optional[str] = Column(
        Text,
        nullable=True,
        comment="Key technologies used (free-form text or comma-separated list)",
    )

    target_market: Optional[str] = Column(
        Text,
        nullable=True,
        comment="Description of target customers / market",
    )

    dpiit_number: Optional[str] = Column(
        String(100),
        nullable=True,
        comment="DPIIT recognition number",
    )

    is_dpiit_recognised: bool = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Is startup DPIIT recognised",
    )

    pan_number: Optional[str] = Column(
        String(100),
        nullable=True,
        comment="PAN card number",
    )

    gstin: Optional[str] = Column(
        String(100),
        nullable=True,
        comment="GSTIN number",
    )

    sector: Optional[str] = Column(
        String(100),
        nullable=True,
        comment="Freeform sector name",
    )

    
    profile_score: int = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Computed completeness score 0–100 used to surface profile gaps",
    )

    
    user: "User" = relationship(
        "User",
        back_populates="startup_profile",
        lazy="select",
    )

    applications: List["Application"] = relationship(
        "Application",
        back_populates="startup",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    proposals: List["Proposal"] = relationship(
        "Proposal",
        back_populates="startup",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    saved_grants: List["SavedGrant"] = relationship(
        "SavedGrant",
        back_populates="startup",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    
    @validates("company_name")
    def validate_company_name(self, _key: str, value: str) -> str:
        value = (value or "").strip()
        if not value:
            raise ValueError("company_name must not be blank.")
        return value

    @validates("team_size")
    def validate_team_size(self, _key: str, value: object) -> int:
        if value is None:
            return 1
        try:
            val_int = int(value)
            if val_int < 1:
                raise ValueError("team_size must be at least 1.")
            return val_int
        except (TypeError, ValueError) as exc:
            raise ValueError(f"team_size must be a valid integer: {exc}")

    @validates("website")
    def validate_website(self, _key: str, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if value and not value.startswith(("http://", "https://")):
            return f"https://{value}"
        return value

    
    def compute_profile_score(self) -> int:
        
        weights = {
            "company_name":        10,
            "description":         15,
            "industry":            10,
            "stage":               10,
            "country":             5,
            "team_size":           5,
            "founding_year":       5,
            "problem_statement":   10,
            "solution_statement":  10,
            "impact_statement":    5,
            "website":             5,
            "funding_needed":      5,
            "target_market":       5,
        }
        total_weight = sum(weights.values())
        earned = sum(
            w for field, w in weights.items() if bool(getattr(self, field, None))
        )
        score = min(100, round((earned / total_weight) * 100))
        self.profile_score = score
        return score

    def to_dict(
        self,
        exclude: Optional[set] = None,
        include_deleted: bool = False,
    ) -> dict:
        res = super().to_dict(exclude=exclude, include_deleted=include_deleted)
        res["state"] = self.state_province
        res["funding_raised"] = self.total_funding_raised
        res["founded_year"] = self.founding_year
        res["sector"] = self.sector or (self.industry.value if self.industry else "other")
        res["industry_name"] = self.industry.value if self.industry else "other"
        res["is_dpiit_recognised"] = self.is_dpiit_recognised
        res["PAN"] = self.pan_number
        res["GST"] = self.gstin
        res["revenue"] = self.annual_revenue
        return res

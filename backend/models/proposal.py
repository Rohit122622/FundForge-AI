

import logging
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship, validates

from backend.database.base import Base
from backend.models.base_model import BaseModel, GUID

if TYPE_CHECKING:
    from backend.models.user import User
    from backend.models.startup import StartupProfile
    from backend.models.grant import Grant
    from backend.models.application import Application

logger = logging.getLogger("fundforge.models.proposal")






class ProposalStatus(str, PyEnum):
    
    GENERATING = "generating"
    COMPLETE   = "complete"
    FAILED     = "failed"
    EDITING    = "editing"
    FINALISED  = "finalised"
    ARCHIVED   = "archived"


class ProposalTone(str, PyEnum):
    
    PROFESSIONAL = "professional"
    PERSUASIVE   = "persuasive"
    TECHNICAL    = "technical"
    NARRATIVE    = "narrative"
    CONCISE      = "concise"






class Proposal(BaseModel, Base):
    

    __tablename__ = "proposals"

    __table_args__ = (
        Index("ix_proposals_user_id", "user_id"),
        Index("ix_proposals_startup_id", "startup_id"),
        Index("ix_proposals_grant_id", "grant_id"),
        Index("ix_proposals_status", "status"),
        Index("ix_proposals_version", "startup_id", "grant_id", "version"),
        CheckConstraint(
            "version >= 1",
            name="ck_proposals_version_positive",
        ),
        CheckConstraint(
            "quality_score IS NULL OR (quality_score >= 0.0 AND quality_score <= 1.0)",
            name="ck_proposals_quality_score_range",
        ),
        {"comment": "AI-generated grant proposals with version history"},
    )

    
    user_id: uuid.UUID = Column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="User who triggered the generation",
    )

    startup_id: uuid.UUID = Column(
        GUID,
        ForeignKey("startup_profiles.id", ondelete="CASCADE"),
        nullable=False,
        comment="Startup profile used as the proposal context",
    )

    grant_id: uuid.UUID = Column(
        GUID,
        ForeignKey("grants.id", ondelete="CASCADE"),
        nullable=False,
        comment="Grant opportunity this proposal targets",
    )

    application_id: Optional[uuid.UUID] = Column(
        GUID,
        ForeignKey("applications.id", ondelete="SET NULL"),
        nullable=True,
        comment="Optional link to the parent application record",
    )

    
    version: int = Column(
        Integer,
        nullable=False,
        default=1,
        comment="Monotonically increasing version number per (startup, grant) pair",
    )

    status: ProposalStatus = Column(
        Enum(ProposalStatus, name="proposal_status", create_constraint=True),
        nullable=False,
        default=ProposalStatus.GENERATING,
        comment="Current lifecycle status",
    )

    
    model_id: Optional[str] = Column(
        String(200),
        nullable=True,
        comment="IBM Granite model identifier used for generation",
    )

    prompt_tokens: Optional[int] = Column(
        Integer,
        nullable=True,
        comment="Number of tokens in the input prompt",
    )

    completion_tokens: Optional[int] = Column(
        Integer,
        nullable=True,
        comment="Number of tokens in the generated output",
    )

    generation_time_ms: Optional[int] = Column(
        Integer,
        nullable=True,
        comment="Wall-clock time in milliseconds for the generation call",
    )

    tone: ProposalTone = Column(
        Enum(ProposalTone, name="proposal_tone", create_constraint=True),
        nullable=False,
        default=ProposalTone.PROFESSIONAL,
        comment="Tone directive used during generation",
    )

    user_instructions: Optional[str] = Column(
        Text,
        nullable=True,
        comment="Custom instructions supplied by the user before generation",
    )

    
    executive_summary: Optional[str] = Column(
        Text,
        nullable=True,
        comment="Executive summary section",
    )

    problem_statement: Optional[str] = Column(
        Text,
        nullable=True,
        comment="Problem statement section",
    )

    proposed_solution: Optional[str] = Column(
        Text,
        nullable=True,
        comment="Proposed solution section",
    )

    impact_statement: Optional[str] = Column(
        Text,
        nullable=True,
        comment="Impact / outcomes section",
    )

    budget_narrative: Optional[str] = Column(
        Text,
        nullable=True,
        comment="Budget justification and narrative",
    )

    timeline: Optional[str] = Column(
        Text,
        nullable=True,
        comment="Project timeline and milestones",
    )

    team_qualifications: Optional[str] = Column(
        Text,
        nullable=True,
        comment="Team background and qualifications section",
    )

    full_text: Optional[str] = Column(
        Text,
        nullable=True,
        comment="Complete raw proposal text as returned by IBM Granite",
    )

    
    quality_score: Optional[float] = Column(
        Float,
        nullable=True,
        comment="AI self-assessed quality score 0.0–1.0",
    )

    user_rating: Optional[int] = Column(
        Integer,
        nullable=True,
        comment="User's 1–5 star rating of the generated proposal",
    )

    user_feedback: Optional[str] = Column(
        Text,
        nullable=True,
        comment="Free-form user feedback on the proposal quality",
    )

    
    is_exported: bool = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="True once the proposal has been exported to PDF / DOCX",
    )

    exported_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="UTC timestamp of most recent export",
    )

    
    user: "User" = relationship(
        "User",
        back_populates="proposals",
        lazy="select",
    )

    startup: "StartupProfile" = relationship(
        "StartupProfile",
        back_populates="proposals",
        lazy="select",
    )

    grant: "Grant" = relationship(
        "Grant",
        back_populates="proposals",
        lazy="select",
    )

    application: Optional["Application"] = relationship(
        "Application",
        back_populates="proposals",
        lazy="select",
    )

    
    @validates("version")
    def validate_version(self, _key: str, value: int) -> int:
        if int(value) < 1:
            raise ValueError("version must be >= 1.")
        return int(value)

    @validates("user_rating")
    def validate_user_rating(self, _key: str, value: Optional[int]) -> Optional[int]:
        if value is None:
            return None
        if not (1 <= int(value) <= 5):
            raise ValueError("user_rating must be between 1 and 5.")
        return int(value)

    @validates("quality_score")
    def validate_quality_score(self, _key: str, value: Optional[float]) -> Optional[float]:
        if value is None:
            return None
        if not (0.0 <= float(value) <= 1.0):
            raise ValueError("quality_score must be between 0.0 and 1.0.")
        return float(value)

    
    def to_dict(self) -> dict:
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        if self.status:
            data["status"] = self.status.value
        if self.tone:
            data["tone"] = self.tone.value
        if self.user_id:
            data["user_id"] = str(self.user_id)
        if self.startup_id:
            data["startup_id"] = str(self.startup_id)
        if self.grant_id:
            data["grant_id"] = str(self.grant_id)
        if self.id:
            data["id"] = str(self.id)
        if self.created_at:
            data["created_at"] = self.created_at.isoformat()
        if self.updated_at:
            data["updated_at"] = self.updated_at.isoformat()

        
        from backend.proposal_generator.proposal_builder import parse_sections_from_markdown
        sections = parse_sections_from_markdown(self.full_text)
        
        
        for k in ["executive_summary", "problem_statement", "proposed_solution", 
                  "impact_statement", "budget_narrative", "timeline", "team_qualifications"]:
            if k not in sections or not sections[k]:
                sections[k] = getattr(self, k) or ""
                
        data["sections"] = sections
        return data

    @property
    def word_count(self) -> int:
        
        if not self.full_text:
            return 0
        return len(self.full_text.split())

    @property
    def is_editable(self) -> bool:
        
        return self.status in (ProposalStatus.COMPLETE, ProposalStatus.EDITING)

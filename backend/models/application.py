

import logging
import uuid
from datetime import date, datetime, timezone
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Dict, List, Optional, Set

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, validates

from backend.database.base import Base
from backend.models.base_model import BaseModel, GUID

if TYPE_CHECKING:
    from backend.models.user import User
    from backend.models.startup import StartupProfile
    from backend.models.grant import Grant
    from backend.models.proposal import Proposal

logger = logging.getLogger("fundforge.models.application")






class ApplicationStatus(str, PyEnum):
    
    SAVED        = "saved"         
    RESEARCHING  = "researching"   
    IN_PROGRESS  = "in_progress"   
    SUBMITTED    = "submitted"     
    UNDER_REVIEW = "under_review"  
    AWARDED      = "awarded"       
    REJECTED     = "rejected"      
    WITHDRAWN    = "withdrawn"     
    ABANDONED    = "abandoned"     


class ApplicationPriority(str, PyEnum):
    
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"
    URGENT = "urgent"






_ALLOWED_TRANSITIONS: Dict[ApplicationStatus, Set[ApplicationStatus]] = {
    ApplicationStatus.SAVED:        {ApplicationStatus.RESEARCHING, ApplicationStatus.IN_PROGRESS, ApplicationStatus.ABANDONED},
    ApplicationStatus.RESEARCHING:  {ApplicationStatus.IN_PROGRESS, ApplicationStatus.ABANDONED, ApplicationStatus.WITHDRAWN},
    ApplicationStatus.IN_PROGRESS:  {ApplicationStatus.SUBMITTED, ApplicationStatus.ABANDONED, ApplicationStatus.WITHDRAWN},
    ApplicationStatus.SUBMITTED:    {ApplicationStatus.UNDER_REVIEW, ApplicationStatus.WITHDRAWN, ApplicationStatus.ABANDONED},
    ApplicationStatus.UNDER_REVIEW: {ApplicationStatus.AWARDED, ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN},
    ApplicationStatus.AWARDED:      set(),  
    ApplicationStatus.REJECTED:     set(),  
    ApplicationStatus.WITHDRAWN:    set(),  
    ApplicationStatus.ABANDONED:    set(),  
}






class Application(BaseModel, Base):
    

    __tablename__ = "applications"

    __table_args__ = (
        UniqueConstraint(
            "startup_id", "grant_id",
            name="uq_applications_startup_grant",
        ),
        Index("ix_applications_status", "status"),
        Index("ix_applications_user_id", "user_id"),
        Index("ix_applications_startup_id", "startup_id"),
        Index("ix_applications_grant_id", "grant_id"),
        Index("ix_applications_deadline", "deadline"),
        Index("ix_applications_submitted_at", "submitted_at"),
        CheckConstraint(
            "eligibility_score IS NULL OR (eligibility_score >= 0 AND eligibility_score <= 100)",
            name="ck_applications_eligibility_score_range",
        ),
        {"comment": "Grant application tracking records"},
    )

    
    user_id: uuid.UUID = Column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="User who owns this application record",
    )

    startup_id: uuid.UUID = Column(
        GUID,
        ForeignKey("startup_profiles.id", ondelete="CASCADE"),
        nullable=False,
        comment="Startup profile the application is submitted on behalf of",
    )

    grant_id: uuid.UUID = Column(
        GUID,
        ForeignKey("grants.id", ondelete="CASCADE"),
        nullable=False,
        comment="Grant opportunity being pursued",
    )

    
    status: ApplicationStatus = Column(
        Enum(ApplicationStatus, name="application_status", create_constraint=True),
        nullable=False,
        default=ApplicationStatus.SAVED,
        comment="Current FSM state of the application",
    )

    priority: ApplicationPriority = Column(
        Enum(ApplicationPriority, name="application_priority", create_constraint=True),
        nullable=False,
        default=ApplicationPriority.MEDIUM,
        comment="User-assigned priority",
    )

    
    deadline: Optional[date] = Column(
        Date,
        nullable=True,
        comment="Local copy of the grant deadline for calendar / reminder use",
    )

    submitted_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="UTC timestamp when the application was submitted to the grantor",
    )

    awarded_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="UTC timestamp when the award notification was received",
    )

    rejected_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="UTC timestamp when the rejection was received",
    )

    
    award_amount: Optional[Numeric] = Column(
        Numeric(precision=15, scale=2),
        nullable=True,
        comment="Actual amount awarded (filled after AWARDED transition)",
    )

    rejection_reason: Optional[str] = Column(
        Text,
        nullable=True,
        comment="Rejection reason or feedback received from the grantor",
    )

    
    eligibility_score: Optional[int] = Column(
        Integer,
        nullable=True,
        comment="IBM Granite eligibility match score 0–100",
    )

    eligibility_notes: Optional[str] = Column(
        Text,
        nullable=True,
        comment="AI-generated eligibility assessment",
    )

    
    internal_reference: Optional[str] = Column(
        String(200),
        nullable=True,
        comment="Grantor-assigned reference number after submission",
    )

    assigned_officer: Optional[str] = Column(
        String(255),
        nullable=True,
        comment="Name or email of the programme officer handling the application",
    )

    next_action: Optional[str] = Column(
        String(500),
        nullable=True,
        comment="User-defined next action item",
    )

    next_action_date: Optional[date] = Column(
        Date,
        nullable=True,
        comment="Due date for the next action",
    )

    notes: Optional[str] = Column(
        Text,
        nullable=True,
        comment="Free-form notes and journal entries",
    )

    
    user: "User" = relationship(
        "User",
        back_populates="applications",
        lazy="select",
    )

    startup: "StartupProfile" = relationship(
        "StartupProfile",
        back_populates="applications",
        lazy="select",
    )

    grant: "Grant" = relationship(
        "Grant",
        back_populates="applications",
        lazy="select",
    )

    proposals: List["Proposal"] = relationship(
        "Proposal",
        back_populates="application",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    
    def transition_to(self, new_status: ApplicationStatus) -> None:
        
        allowed = _ALLOWED_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise ValueError(
                f"Cannot transition Application from '{self.status}' to '{new_status}'. "
                f"Allowed: {[s.value for s in allowed] or 'none (terminal state)'}."
            )

        now = datetime.now(timezone.utc)
        old_status = self.status
        self.status = new_status

        
        if new_status == ApplicationStatus.SUBMITTED:
            self.submitted_at = now
        elif new_status == ApplicationStatus.AWARDED:
            self.awarded_at = now
        elif new_status == ApplicationStatus.REJECTED:
            self.rejected_at = now

        logger.info(
            "Application %s: %s → %s",
            getattr(self, "id", "?"),
            old_status,
            new_status,
        )

    
    def to_dict(self) -> dict:
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        if self.status:
            data["status"] = self.status.value
        if self.priority:
            data["priority"] = self.priority.value
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
        if self.submitted_at:
            data["submitted_at"] = self.submitted_at.isoformat()
        if self.awarded_at:
            data["awarded_at"] = self.awarded_at.isoformat()
        if self.rejected_at:
            data["rejected_at"] = self.rejected_at.isoformat()
        if self.next_action_date:
            data["next_action_date"] = self.next_action_date.isoformat()
        if self.deadline:
            data["deadline"] = self.deadline.isoformat()

        
        if self.grant:
            data["grant"] = {
                "id": str(self.grant.id),
                "title": self.grant.title,
                "slug": self.grant.slug,
                "organization_name": self.grant.organization_name
            }
        else:
            data["grant"] = {
                "id": str(self.grant_id),
                "title": "Startup India Seed Fund Scheme",
                "slug": "sisfs",
                "organization_name": "DPIIT"
            }
            
        return data

    @property
    def is_terminal(self) -> bool:
        
        return not _ALLOWED_TRANSITIONS.get(self.status, {True})

    @property
    def is_active_pursuit(self) -> bool:
        
        return self.status in (
            ApplicationStatus.SAVED,
            ApplicationStatus.RESEARCHING,
            ApplicationStatus.IN_PROGRESS,
            ApplicationStatus.SUBMITTED,
            ApplicationStatus.UNDER_REVIEW,
        )

    @validates("eligibility_score")
    def validate_eligibility_score(self, _key: str, value: Optional[int]) -> Optional[int]:
        if value is None:
            return None
        if not (0 <= int(value) <= 100):
            raise ValueError("eligibility_score must be between 0 and 100.")
        return int(value)

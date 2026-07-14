

import logging
import uuid
from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    ForeignKey,
    Index,
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

logger = logging.getLogger("fundforge.models.saved_grant")


class SavedGrant(BaseModel, Base):
    

    __tablename__ = "saved_grants"

    __table_args__ = (
        UniqueConstraint(
            "user_id", "startup_id", "grant_id",
            name="uq_saved_grants_user_startup_grant",
        ),
        Index("ix_saved_grants_user_id", "user_id"),
        Index("ix_saved_grants_startup_id", "startup_id"),
        Index("ix_saved_grants_grant_id", "grant_id"),
        Index("ix_saved_grants_reminder_date", "reminder_date"),
        {"comment": "Bookmark records linking startups to saved grant opportunities"},
    )

    
    user_id: uuid.UUID = Column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="User who saved this grant",
    )

    startup_id: uuid.UUID = Column(
        GUID,
        ForeignKey("startup_profiles.id", ondelete="CASCADE"),
        nullable=False,
        comment="Startup profile this bookmark belongs to",
    )

    grant_id: uuid.UUID = Column(
        GUID,
        ForeignKey("grants.id", ondelete="CASCADE"),
        nullable=False,
        comment="The bookmarked grant",
    )

    
    notes: Optional[str] = Column(
        Text,
        nullable=True,
        comment="User notes about why they saved this grant",
    )

    label: Optional[str] = Column(
        String(100),
        nullable=True,
        comment="User-assigned colour label or category tag (e.g. 'high priority', 'Q3')",
    )

    reminder_date: Optional[date] = Column(
        Date,
        nullable=True,
        comment="Date to send a reminder notification about this grant deadline",
    )

    is_notified: bool = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="True once a deadline reminder notification has been sent",
    )

    
    user: "User" = relationship(
        "User",
        back_populates="saved_grants",
        lazy="select",
    )

    startup: "StartupProfile" = relationship(
        "StartupProfile",
        back_populates="saved_grants",
        lazy="select",
    )

    grant: "Grant" = relationship(
        "Grant",
        back_populates="saved_by",
        lazy="select",
    )

    
    @validates("label")
    def validate_label(self, _key: str, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value if value else None

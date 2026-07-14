

import logging
from datetime import datetime, timezone, timedelta
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, List, Optional

import bcrypt
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, validates

from backend.database.base import Base
from backend.models.base_model import BaseModel

if TYPE_CHECKING:
    from backend.models.startup import StartupProfile
    from backend.models.application import Application
    from backend.models.proposal import Proposal
    from backend.models.saved_grant import SavedGrant

logger = logging.getLogger("fundforge.models.user")





class UserRole(str, PyEnum):
    
    FOUNDER  = "founder"
    ADMIN    = "admin"
    REVIEWER = "reviewer"


class UserStatus(str, PyEnum):
    
    PENDING     = "pending"
    ACTIVE      = "active"
    SUSPENDED   = "suspended"
    DEACTIVATED = "deactivated"






class User(BaseModel, Base):
    

    __tablename__ = "users"
    __allow_unmapped__ = True

    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        Index("ix_users_email_active", "email", "is_deleted"),
        Index("ix_users_role", "role"),
        Index("ix_users_status", "status"),
        {"comment": "Platform user accounts"},
    )

    
    email: str = Column(
        String(320),
        nullable=False,
        comment="User's email address — login identifier",
    )

    first_name: str = Column(
        String(100),
        nullable=False,
        comment="User's given name",
    )

    last_name: str = Column(
        String(100),
        nullable=False,
        comment="User's family name",
    )

    display_name: Optional[str] = Column(
        String(200),
        nullable=True,
        comment="Optional display / brand name",
    )

    avatar_url: Optional[str] = Column(
        String(500),
        nullable=True,
        comment="URL to profile avatar image",
    )

    
    password_hash: str = Column(
        String(255),
        nullable=False,
        comment="bcrypt hash of the user's password",
    )

    role: UserRole = Column(
        Enum(UserRole, name="user_role", create_constraint=True),
        nullable=False,
        default=UserRole.FOUNDER,
        comment="Access-control role",
    )

    status: UserStatus = Column(
        Enum(UserStatus, name="user_status", create_constraint=True),
        nullable=False,
        default=UserStatus.PENDING,
        comment="Account lifecycle status",
    )

    
    email_verified: bool = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="True once the user has clicked the verification link",
    )

    email_verify_token_hash: Optional[str] = Column(
        String(255),
        nullable=True,
        comment="bcrypt hash of the pending email-verification token",
    )

    email_verify_sent_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the verification email was last sent (UTC)",
    )

    
    reset_token_hash: Optional[str] = Column(
        String(255),
        nullable=True,
        comment="bcrypt hash of the active password-reset token",
    )

    reset_token_expires_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="UTC expiry of the password-reset token",
    )

    
    last_login_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="UTC timestamp of the most recent successful login",
    )

    last_login_ip: Optional[str] = Column(
        String(45),
        nullable=True,
        comment="IPv4 or IPv6 address of the most recent login",
    )

    failed_login_attempts: int = Column(
        String(5),   
        nullable=False,
        default="0",
        comment="Consecutive failed login attempts (reset on success)",
    )

    locked_until: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Account is locked from login until this UTC timestamp",
    )

    
    startup_profile: Optional["StartupProfile"] = relationship(
        "StartupProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="select",
    )

    applications: List["Application"] = relationship(
        "Application",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    proposals: List["Proposal"] = relationship(
        "Proposal",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    saved_grants: List["SavedGrant"] = relationship(
        "SavedGrant",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    
    @validates("email")
    def validate_email(self, _key: str, value: str) -> str:
        
        if not value or "@" not in value:
            raise ValueError(f"Invalid email address: {value!r}")
        return value.strip().lower()

    @validates("first_name", "last_name")
    def validate_name(self, key: str, value: str) -> str:
        
        value = (value or "").strip()
        if not value:
            raise ValueError(f"{key} must not be blank.")
        return value

    
    def set_password(self, plaintext: str) -> None:
        
        if len(plaintext) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        salt = bcrypt.gensalt(rounds=12)
        self.password_hash = bcrypt.hashpw(
            plaintext.encode("utf-8"), salt
        ).decode("utf-8")

    def check_password(self, plaintext: str) -> bool:
        
        if not self.password_hash:
            return False
        return bcrypt.checkpw(
            plaintext.encode("utf-8"),
            self.password_hash.encode("utf-8"),
        )

    
    def set_reset_token(self, token: str, expires_minutes: int = 60) -> None:
        
        salt = bcrypt.gensalt(rounds=10)
        self.reset_token_hash = bcrypt.hashpw(
            token.encode("utf-8"), salt
        ).decode("utf-8")
        self.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=expires_minutes
        )

    def verify_reset_token(self, token: str) -> bool:
        
        if not self.reset_token_hash or not self.reset_token_expires_at:
            return False
        if datetime.now(timezone.utc) > self.reset_token_expires_at:
            return False
        return bcrypt.checkpw(
            token.encode("utf-8"),
            self.reset_token_hash.encode("utf-8"),
        )

    def clear_reset_token(self) -> None:
        
        self.reset_token_hash = None
        self.reset_token_expires_at = None

    def set_verify_token(self, token: str) -> None:
        
        salt = bcrypt.gensalt(rounds=10)
        self.email_verify_token_hash = bcrypt.hashpw(
            token.encode("utf-8"), salt
        ).decode("utf-8")
        self.email_verify_sent_at = datetime.now(timezone.utc)

    def verify_email_token(self, token: str) -> bool:
        
        if not self.email_verify_token_hash:
            return False
        return bcrypt.checkpw(
            token.encode("utf-8"),
            self.email_verify_token_hash.encode("utf-8"),
        )

    
    def is_locked(self) -> bool:
        
        if self.locked_until is None:
            return False
        return datetime.now(timezone.utc) < self.locked_until

    def record_login_attempt(self, success: bool, ip: Optional[str] = None) -> None:
        
        attempts = int(self.failed_login_attempts or 0)
        if success:
            self.failed_login_attempts = "0"
            self.locked_until = None
            self.last_login_at = datetime.now(timezone.utc)
            self.last_login_ip = ip
        else:
            attempts += 1
            self.failed_login_attempts = str(attempts)
            if attempts >= 10:
                self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=60)
            elif attempts >= 5:
                self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)

    
    @property
    def full_name(self) -> str:
        
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_active(self) -> bool:
        
        return self.status == UserStatus.ACTIVE

    @property
    def is_admin(self) -> bool:
        
        return self.role == UserRole.ADMIN

    
    _SENSITIVE_FIELDS = {
        "password_hash",
        "reset_token_hash",
        "email_verify_token_hash",
    }

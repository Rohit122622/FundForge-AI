

import logging
import uuid
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional

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
)
from sqlalchemy.orm import relationship, validates

from backend.database.base import Base
from backend.models.base_model import BaseModel, GUID

if TYPE_CHECKING:
    from backend.models.user import User

logger = logging.getLogger("fundforge.models.document")






class DocumentType(str, PyEnum):
    
    PROPOSAL          = "proposal"
    GRANT_REPORT      = "grant_report"
    APPLICATION_SUMMARY = "application_summary"
    STARTUP_PROFILE   = "startup_profile"
    SUPPORTING_DOC    = "supporting_doc"   
    FINANCIAL_REPORT  = "financial_report"
    PITCH_DECK        = "pitch_deck"
    OTHER             = "other"


class DocumentStatus(str, PyEnum):
    
    UPLOADING  = "uploading"   
    SCANNING   = "scanning"    
    READY      = "ready"       
    INFECTED   = "infected"    
    PROCESSING = "processing"  
    FAILED     = "failed"      
    ARCHIVED   = "archived"    






class Document(BaseModel, Base):
    

    __tablename__ = "documents"

    __table_args__ = (
        Index("ix_documents_user_id",        "user_id"),
        Index("ix_documents_startup_id",     "startup_id"),
        Index("ix_documents_proposal_id",    "proposal_id"),
        Index("ix_documents_application_id", "application_id"),
        Index("ix_documents_document_type",  "document_type"),
        Index("ix_documents_status",         "status"),
        CheckConstraint(
            "file_size_bytes > 0",
            name="ck_documents_positive_size",
        ),
        {"comment": "File metadata for uploaded and generated documents"},
    )

    
    user_id: uuid.UUID = Column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="User who owns this document",
    )

    startup_id: Optional[uuid.UUID] = Column(
        GUID,
        ForeignKey("startup_profiles.id", ondelete="SET NULL"),
        nullable=True,
        comment="Startup profile this document is associated with",
    )

    proposal_id: Optional[uuid.UUID] = Column(
        GUID,
        ForeignKey("proposals.id", ondelete="SET NULL"),
        nullable=True,
        comment="Proposal this document was generated from (if applicable)",
    )

    application_id: Optional[uuid.UUID] = Column(
        GUID,
        ForeignKey("applications.id", ondelete="SET NULL"),
        nullable=True,
        comment="Application this document belongs to (if applicable)",
    )

    
    original_filename: str = Column(
        String(500),
        nullable=False,
        comment="Original filename as provided by the client",
    )

    storage_filename: str = Column(
        String(500),
        nullable=False,
        comment="UUID-based sanitised filename on the storage backend",
    )

    storage_path: str = Column(
        String(1000),
        nullable=False,
        unique=True,
        comment="Full path / key in the storage backend",
    )

    file_extension: str = Column(
        String(20),
        nullable=False,
        comment="Lowercase extension without leading dot (e.g. 'pdf', 'docx')",
    )

    mime_type: str = Column(
        String(200),
        nullable=False,
        default="application/octet-stream",
        comment="MIME type detected at upload time",
    )

    file_size_bytes: int = Column(
        Integer,
        nullable=False,
        comment="File size in bytes",
    )

    
    document_type: DocumentType = Column(
        Enum(DocumentType, name="document_type", create_constraint=True),
        nullable=False,
        default=DocumentType.SUPPORTING_DOC,
        comment="Purpose category of this document",
    )

    status: DocumentStatus = Column(
        Enum(DocumentStatus, name="document_status", create_constraint=True),
        nullable=False,
        default=DocumentStatus.UPLOADING,
        comment="Processing lifecycle status",
    )

    
    display_name: Optional[str] = Column(
        String(500),
        nullable=True,
        comment="Optional user-facing display name (falls back to original_filename)",
    )

    description: Optional[str] = Column(
        Text,
        nullable=True,
        comment="Optional description of the document's purpose",
    )

    
    is_public: bool = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="True when the document is accessible without authentication",
    )

    virus_scan_passed: Optional[bool] = Column(
        Boolean,
        nullable=True,
        comment="Result of the virus scan (None = not yet scanned)",
    )

    
    download_count: int = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Total number of times this document has been downloaded",
    )

    
    user: "User" = relationship(
        "User",
        lazy="select",
        foreign_keys=[user_id],
    )

    
    @validates("original_filename")
    def validate_original_filename(self, _key: str, value: str) -> str:
        value = (value or "").strip()
        if not value:
            raise ValueError("original_filename must not be blank.")
        return value[:500]

    @validates("file_size_bytes")
    def validate_size(self, _key: str, value: int) -> int:
        if int(value) <= 0:
            raise ValueError("file_size_bytes must be positive.")
        return int(value)

    
    @property
    def label(self) -> str:
        
        return self.display_name or self.original_filename

    @property
    def size_human(self) -> str:
        
        n = self.file_size_bytes
        kb = 1024
        mb = kb * 1024
        if n >= mb:
            return f"{n / mb:.1f} MB"
        if n >= kb:
            return f"{n / kb:.1f} KB"
        return f"{n} B"

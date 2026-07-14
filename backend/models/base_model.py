

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, TypeVar

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import declarative_mixin
from sqlalchemy.types import TypeDecorator, CHAR

logger = logging.getLogger("fundforge.models.base")

T = TypeVar("T", bound="BaseModel")






class GUID(TypeDecorator):
    

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return str(value) if not isinstance(value, uuid.UUID) else value
        return str(value) if isinstance(value, uuid.UUID) else str(uuid.UUID(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            return uuid.UUID(value)
        return value






@declarative_mixin
class TimestampMixin:
    __allow_unmapped__ = True
    """
    Adds ``created_at`` and ``updated_at`` UTC timestamp columns.

    ``updated_at`` is refreshed automatically on every UPDATE via a
    SQLAlchemy ``before_update`` event listener registered at class creation.
    """

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="UTC timestamp when the record was created",
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="UTC timestamp of the last modification",
    )






@declarative_mixin
class SoftDeleteMixin:
    __allow_unmapped__ = True
    """
    Timeouts
    """

    is_deleted = Column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="True when the record has been soft-deleted",
    )

    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="UTC timestamp when the record was soft-deleted; NULL if active",
    )

    def soft_delete(self) -> None:
        
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
        logger.debug(
            "Soft-deleted %s id=%s", self.__class__.__name__, getattr(self, "id", "?")
        )

    def restore(self) -> None:
        
        self.is_deleted = False
        self.deleted_at = None
        logger.debug(
            "Restored %s id=%s", self.__class__.__name__, getattr(self, "id", "?")
        )






@declarative_mixin
class AuditMixin:
    __allow_unmapped__ = True
    """
    Tracks which user created and last modified a record.

    Values are plain strings (user UUIDs) so models do not need a foreign-key
    dependency on the User table — keeping this mixin portable.
    """

    created_by = Column(
        String(36),
        nullable=True,
        comment="UUID of the user who created this record",
    )

    updated_by = Column(
        String(36),
        nullable=True,
        comment="UUID of the user who last modified this record",
    )






@declarative_mixin
class BaseModel(TimestampMixin, SoftDeleteMixin, AuditMixin):
    

    __abstract__ = True
    __allow_unmapped__ = True

    id = Column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
        comment="Universally unique identifier for this record",
    )

    
    _HIDDEN_FIELDS: Set[str] = {"_sa_instance_state"}

    
    _SENSITIVE_FIELDS: Set[str] = {"password_hash", "reset_token", "verify_token"}

    def to_dict(
        self,
        exclude: Optional[Set[str]] = None,
        include_deleted: bool = False,
    ) -> Dict[str, Any]:
        
        excluded = self._HIDDEN_FIELDS | (exclude or set())
        result: Dict[str, Any] = {}

        for column in self.__table__.columns:  
            if column.name in excluded:
                continue
            value = getattr(self, column.name)
            if isinstance(value, uuid.UUID):
                value = str(value)
            elif isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value

        return result

    def to_safe_dict(self, exclude: Optional[Set[str]] = None) -> Dict[str, Any]:
        
        sensitive = self._SENSITIVE_FIELDS | (exclude or set())
        return self.to_dict(exclude=sensitive)

    @classmethod
    def get_columns(cls) -> List[str]:
        
        return [col.name for col in cls.__table__.columns]  

    def update_from_dict(self, data: Dict[str, Any], allowed: Optional[Set[str]] = None) -> None:
        
        columns = {col.name for col in self.__table__.columns}  
        for key, value in data.items():
            if allowed is not None and key not in allowed:
                continue
            if key in columns and key not in {"id", "created_at", "created_by"}:
                setattr(self, key, value)

    def __repr__(self) -> str:
        pk = getattr(self, "id", None)
        return f"<{self.__class__.__name__} id={pk}>"

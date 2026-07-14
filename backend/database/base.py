

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    __allow_unmapped__ = True
    """
    Central SQLAlchemy declarative base.

    All ORM models inherit from both :class:`~backend.models.base_model.BaseModel`
    and this class.  Using SQLAlchemy 2.x ``DeclarativeBase`` subclass style
    gives us typed column declarations and first-class ``Mapped[]`` support
    when models are upgraded in future iterations.
    """

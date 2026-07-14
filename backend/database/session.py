

import logging
from contextlib import contextmanager
from functools import wraps
from typing import Callable, Generator, TypeVar

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

logger = logging.getLogger("fundforge.database.session")

F = TypeVar("F", bound=Callable)


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    
    from backend.app import db  

    session: Session = db.session

    try:
        yield session
        session.commit()
        logger.debug("Transaction committed successfully.")
    except SQLAlchemyError as exc:
        session.rollback()
        logger.error(
            "SQLAlchemy error — transaction rolled back: %s",
            exc,
            exc_info=True,
        )
        raise
    except Exception as exc:
        session.rollback()
        logger.error(
            "Unexpected error — transaction rolled back: %s",
            exc,
            exc_info=True,
        )
        raise
    finally:
        session.close()


def get_session() -> Session:
    
    from backend.app import db
    return db.session


def transactional(func: F) -> F:
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        
        
        if kwargs.get("session") is not None:
            return func(*args, **kwargs)

        with session_scope() as session:
            kwargs["session"] = session
            return func(*args, **kwargs)

    return wrapper  


def paginate_query(query, page: int = 1, per_page: int = 20) -> dict:
    
    if page < 1:
        page = 1
    if per_page < 1:
        per_page = 20

    total: int = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    pages = max(1, -(-total // per_page))  

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
        "has_next": page < pages,
        "has_prev": page > 1,
    }

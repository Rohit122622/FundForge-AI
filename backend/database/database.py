

import logging

from sqlalchemy import text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from backend.database.base import Base

logger = logging.getLogger("fundforge.database")


def _import_all_models() -> None:
    
    
    pass  


def init_db(app=None) -> None:
    
    from backend.app import db  

    _import_all_models()

    def _create():
        try:
            db.create_all()
            logger.info(
                "Database tables created/verified: %s",
                list(Base.metadata.tables.keys()),
            )
        except SQLAlchemyError as exc:
            logger.error("Failed to create database tables: %s", exc, exc_info=True)
            raise

    if app is not None:
        with app.app_context():
            _create()
    else:
        _create()


def drop_db(app=None) -> None:
    
    from backend.app import db

    _import_all_models()

    def _drop():
        try:
            db.drop_all()
            logger.warning("All database tables dropped.")
        except SQLAlchemyError as exc:
            logger.error("Failed to drop database tables: %s", exc, exc_info=True)
            raise

    if app is not None:
        with app.app_context():
            _drop()
    else:
        _drop()


def check_db_connection(app=None) -> bool:
    
    from backend.app import db

    def _probe() -> bool:
        try:
            db.session.execute(text("SELECT 1"))
            logger.debug("Database connectivity check: OK")
            return True
        except OperationalError as exc:
            logger.error("Database connectivity check failed: %s", exc)
            return False

    if app is not None:
        with app.app_context():
            return _probe()
    return _probe()


def get_table_names(app=None) -> list:
    
    _import_all_models()

    def _names() -> list:
        from backend.app import db
        inspector = db.inspect(db.engine)
        return sorted(inspector.get_table_names())

    if app is not None:
        with app.app_context():
            return _names()
    return _names()

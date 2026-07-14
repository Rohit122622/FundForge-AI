

import logging
from typing import List

logger = logging.getLogger("fundforge.database.migrations")


def run_migrations(revision: str = "head", app=None) -> None:
    
    from flask_migrate import upgrade as flask_migrate_upgrade

    def _upgrade():
        try:
            flask_migrate_upgrade(revision=revision)
            logger.info("Migrations applied successfully to revision: %s", revision)
        except Exception as exc:
            logger.error("Migration failed: %s", exc, exc_info=True)
            raise RuntimeError(f"Database migration failed: {exc}") from exc

    if app is not None:
        with app.app_context():
            _upgrade()
    else:
        _upgrade()


def create_migration(message: str, app=None) -> None:
    
    from flask_migrate import migrate as flask_migrate_migrate

    def _migrate():
        try:
            flask_migrate_migrate(message=message)
            logger.info("Migration created: %s", message)
        except Exception as exc:
            logger.error("Migration generation failed: %s", exc, exc_info=True)
            raise RuntimeError(f"Migration generation failed: {exc}") from exc

    if app is not None:
        with app.app_context():
            _migrate()
    else:
        _migrate()


def downgrade_migration(revision: str = "-1", app=None) -> None:
    
    from flask_migrate import downgrade as flask_migrate_downgrade

    def _downgrade():
        try:
            flask_migrate_downgrade(revision=revision)
            logger.info("Rolled back to revision: %s", revision)
        except Exception as exc:
            logger.error("Downgrade failed: %s", exc, exc_info=True)
            raise RuntimeError(f"Downgrade failed: {exc}") from exc

    if app is not None:
        with app.app_context():
            _downgrade()
    else:
        _downgrade()


def get_migration_status(app=None) -> List[dict]:
    
    from flask_migrate import current as flask_migrate_current

    def _status() -> List[dict]:
        try:
            flask_migrate_current()
            
            return [{"status": "OK", "message": "Migration status logged to stdout."}]
        except Exception as exc:
            logger.warning("Could not retrieve migration status: %s", exc)
            return [{"status": "ERROR", "message": str(exc)}]

    if app is not None:
        with app.app_context():
            return _status()
    return _status()


def stamp_revision(revision: str = "head", app=None) -> None:
    
    from flask_migrate import stamp as flask_migrate_stamp

    def _stamp():
        try:
            flask_migrate_stamp(revision=revision)
            logger.info("Database stamped at revision: %s", revision)
        except Exception as exc:
            logger.error("Stamp failed: %s", exc, exc_info=True)
            raise RuntimeError(f"Stamp failed: {exc}") from exc

    if app is not None:
        with app.app_context():
            _stamp()
    else:
        _stamp()

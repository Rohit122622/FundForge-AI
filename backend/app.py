

import logging
import os
import time
import uuid
from http import HTTPStatus
from typing import Optional, Tuple

from flask import Flask, Response, g, jsonify, request
from flask_cors import CORS

from backend.config import configure_logging, get_config, log_exception

logger = logging.getLogger("fundforge.app")








from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db: SQLAlchemy = SQLAlchemy()
migrate: Migrate = Migrate()






def create_app(config_name: Optional[str] = None) -> Flask:
    
    
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development").lower()

    config_class = get_config() if config_name != "testing" else _get_testing_config()

    
    
    configure_logging(
        log_level=config_class.LOG_LEVEL,
        log_format=config_class.LOG_FORMAT,
        app_name="fundforge",
    )

    logger.info("Creating FundForge AI application [env=%s]", config_name)

    
    try:
        config_class.validate()
    except EnvironmentError as exc:
        logger.error("Environment validation failed: %s", exc)
        raise

    
    
    root_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    instance_path = os.path.join(root_dir, "instance")
    os.makedirs(instance_path, exist_ok=True)

    app = Flask(
        __name__,
        instance_path=instance_path,
        instance_relative_config=False,
    )
    app.url_map.strict_slashes = False
    app.config.from_object(config_class)

    
    _ensure_upload_folder(app)

    
    _init_extensions(app)

    
    with app.app_context():
        if config_name != "production":
            try:
                from backend.database.base import Base
                Base.metadata.create_all(bind=db.engine)
                logger.info("Database tables created/verified successfully.")
                
                from backend.database.seed import seed_all
                seed_all()
                logger.info("Database seeded successfully.")
            except Exception as e:
                logger.error("Failed to auto-create and seed database: %s", e)

    
    _init_jwt(app)

    
    _init_cors(app)

    
    _register_request_hooks(app)

    
    _register_blueprints(app)

    
    _register_error_handlers(app)

    
    _register_system_endpoints(app)

    logger.info(
        "FundForge AI started — version=%s env=%s port=%s",
        config_class.APP_VERSION,
        config_name,
        config_class.PORT,
    )

    return app






def _get_testing_config():
    
    from backend.config.settings import TestingConfig
    return TestingConfig


def _ensure_upload_folder(app: Flask) -> None:
    
    folder = app.config.get("UPLOAD_FOLDER", "uploads")
    os.makedirs(folder, exist_ok=True)
    logger.debug("Upload folder ready: %s", folder)


def _init_extensions(app: Flask) -> None:
    
    db.init_app(app)
    migrate.init_app(app, db)
    logger.debug("SQLAlchemy and Flask-Migrate initialised")


def _init_jwt(app: Flask) -> None:
    
    from backend.utils.jwt_manager import init_jwt
    init_jwt(app)


def _init_cors(app: Flask) -> None:
    
    CORS(
        app,
        origins=app.config["CORS_ORIGINS"],
        methods=app.config["CORS_METHODS"],
        allow_headers=app.config["CORS_ALLOW_HEADERS"],
        expose_headers=app.config["CORS_EXPOSE_HEADERS"],
        max_age=app.config["CORS_MAX_AGE"],
        supports_credentials=True,
    )
    logger.debug("CORS configured for origins: %s", app.config["CORS_ORIGINS"])


def _register_request_hooks(app: Flask) -> None:
    

    @app.before_request
    def before_request() -> None:
        
        g.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        g.start_time = time.monotonic()
        logger.debug(
            "→ %s %s [request_id=%s]",
            request.method,
            request.path,
            g.request_id,
        )

    @app.after_request
    def after_request(response: Response) -> Response:
        
        request_id: str = getattr(g, "request_id", "unknown")
        response.headers["X-Request-ID"] = request_id

        duration_ms = (
            (time.monotonic() - g.start_time) * 1000
            if hasattr(g, "start_time")
            else -1
        )

        logger.info(
            "← %s %s %d  %.2fms [request_id=%s]",
            request.method,
            request.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        return response


def _register_blueprints(app: Flask) -> None:
    
    from backend.routes.auth_routes import auth_bp
    from backend.routes.grant_routes import grants_bp
    from backend.routes.proposal_routes import proposals_bp
    from backend.routes.profile_routes import profile_bp
    from backend.routes.tracker_routes import tracker_bp
    from backend.routes.search_routes import search_bp
    from backend.routes.document_routes import documents_bp
    from backend.routes.rag_routes import rag_bp
    from backend.routes.eligibility_routes import eligibility_bp
    from backend.routes.dashboard_routes import dashboard_bp
    from backend.routes.system_routes import system_bp

    blueprints = [
        (auth_bp,          "/api/v1/auth"),
        (grants_bp,        "/api/v1/grants"),
        (proposals_bp,     "/api/v1/proposals"),
        (profile_bp,       "/api/v1/profile"),
        (tracker_bp,       "/api/v1/tracker"),
        (search_bp,        "/api/v1/search"),
        (documents_bp,     "/api/v1/documents"),
        (rag_bp,           "/api/v1/rag"),
        (eligibility_bp,   "/api/v1/eligibility"),
        (dashboard_bp,     "/api/v1/dashboard"),
        (system_bp,        "/api/v1/system"),
    ]

    for blueprint, url_prefix in blueprints:
        app.register_blueprint(blueprint, url_prefix=url_prefix)
        logger.debug("Blueprint registered: %s → %s", blueprint.name, url_prefix)


def _register_error_handlers(app: Flask) -> None:
    

    def _error_response(
        status: HTTPStatus,
        message: Optional[str] = None,
    ) -> Tuple[Response, int]:
        payload = {
            "success": False,
            "error": {
                "code": status.value,
                "status": status.phrase,
                "message": message or status.description,
            },
            "request_id": getattr(g, "request_id", None),
        }
        return jsonify(payload), status.value

    @app.errorhandler(400)
    def bad_request(exc: Exception) -> Tuple[Response, int]:
        log_exception(logger, exc, context="400 Bad Request")
        return _error_response(HTTPStatus.BAD_REQUEST, str(exc) or None)

    @app.errorhandler(401)
    def unauthorized(exc: Exception) -> Tuple[Response, int]:
        return _error_response(HTTPStatus.UNAUTHORIZED)

    @app.errorhandler(403)
    def forbidden(exc: Exception) -> Tuple[Response, int]:
        return _error_response(HTTPStatus.FORBIDDEN)

    @app.errorhandler(404)
    def not_found(exc: Exception) -> Tuple[Response, int]:
        return _error_response(
            HTTPStatus.NOT_FOUND,
            f"The requested resource '{request.path}' was not found.",
        )

    @app.errorhandler(405)
    def method_not_allowed(exc: Exception) -> Tuple[Response, int]:
        return _error_response(
            HTTPStatus.METHOD_NOT_ALLOWED,
            f"Method '{request.method}' is not allowed on '{request.path}'.",
        )

    @app.errorhandler(413)
    def request_entity_too_large(exc: Exception) -> Tuple[Response, int]:
        max_mb = app.config.get("MAX_CONTENT_LENGTH", 0) // (1024 * 1024)
        return _error_response(
            HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            f"File exceeds the maximum allowed size of {max_mb} MB.",
        )

    @app.errorhandler(422)
    def unprocessable_entity(exc: Exception) -> Tuple[Response, int]:
        log_exception(logger, exc, context="422 Unprocessable Entity")
        return _error_response(HTTPStatus.UNPROCESSABLE_ENTITY, str(exc) or None)

    @app.errorhandler(429)
    def too_many_requests(exc: Exception) -> Tuple[Response, int]:
        return _error_response(
            HTTPStatus.TOO_MANY_REQUESTS,
            "Rate limit exceeded. Please slow down your requests.",
        )

    @app.errorhandler(500)
    def internal_server_error(exc: Exception) -> Tuple[Response, int]:
        log_exception(logger, exc, context="500 Internal Server Error")
        return _error_response(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            "An unexpected error occurred. Our team has been notified.",
        )

    @app.errorhandler(503)
    def service_unavailable(exc: Exception) -> Tuple[Response, int]:
        return _error_response(
            HTTPStatus.SERVICE_UNAVAILABLE,
            "The service is temporarily unavailable. Please try again shortly.",
        )

    logger.debug("Global error handlers registered")


def _register_system_endpoints(app: Flask) -> None:
    

    @app.get("/")
    def root() -> Tuple[Response, int]:
      
      return jsonify({
          "message": f"Welcome to {app.config['APP_NAME']} API",
          "docs": "/api/v1/docs",
          "health": "/health",
          "version": "/version",
      }), HTTPStatus.OK.value

    @app.get("/api/v1/swagger.json")
    def swagger_json() -> Tuple[Response, int]:
      
      import json
      try:
          with open(os.path.join(app.root_path, "swagger.json"), "r") as f:
              data = json.load(f)
          return jsonify(data), HTTPStatus.OK.value
      except Exception as e:
          return jsonify({"error": f"Failed to load api specifications: {e}"}), HTTPStatus.INTERNAL_SERVER_ERROR.value

    @app.get("/api/v1/docs")
    def swagger_ui() -> str:
      
      return """
      <!DOCTYPE html>
      <html>
      <head>
        <title>FundForge API Reference</title>
        <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
      </head>
      <body style="margin:0;padding:0;background:#fafafa;">
        <div id="swagger-ui"></div>
        <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
        <script>
          window.onload = () => {
            window.ui = SwaggerUIBundle({
              url: '/api/v1/swagger.json',
              dom_id: '#swagger-ui',
              deepLinking: true,
              presets: [
                SwaggerUIBundle.presets.apis,
                SwaggerUIBundle.SwaggerUIStandalonePreset
              ],
              layout: "BaseLayout"
            });
          };
        </script>
      </body>
      </html>
      """

    @app.get("/health")
    def health() -> Tuple[Response, int]:
        
        checks: dict = {
            "app": "ok",
            "database": "unknown",
        }
        overall_status = HTTPStatus.OK

        
        try:
            with app.app_context():
                db.session.execute(db.text("SELECT 1"))
            checks["database"] = "ok"
        except Exception as exc:
            log_exception(logger, exc, context="Health check — database probe")
            checks["database"] = "unreachable"
            overall_status = HTTPStatus.SERVICE_UNAVAILABLE

        payload = {
            "status": "healthy" if overall_status == HTTPStatus.OK else "degraded",
            "version": app.config["APP_VERSION"],
            "environment": os.getenv("FLASK_ENV", "development"),
            "checks": checks,
            "request_id": getattr(g, "request_id", None),
        }
        return jsonify(payload), overall_status.value

    @app.get("/version")
    def version() -> Tuple[Response, int]:
        
        return jsonify({
            "app_name": app.config["APP_NAME"],
            "version": app.config["APP_VERSION"],
            "description": app.config.get("APP_DESCRIPTION", ""),
            "environment": os.getenv("FLASK_ENV", "development"),
            "python_version": _get_python_version(),
            "flask_version": _get_flask_version(),
        }), HTTPStatus.OK.value

    logger.debug("System endpoints registered: /, /health, /version")






def _get_python_version() -> str:
    
    import sys
    return sys.version.split(" ")[0]


def _get_flask_version() -> str:
    
    try:
        import flask
        return flask.__version__
    except AttributeError:
        return "unknown"

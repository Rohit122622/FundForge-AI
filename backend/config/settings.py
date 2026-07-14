

import os
import logging
from typing import List, Set
from dotenv import load_dotenv


load_dotenv()

logger = logging.getLogger(__name__)


def _require_env(key: str) -> str:
    
    value = os.getenv(key, "").strip()
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{key}' is not set. "
            "Check your .env file or deployment environment."
        )
    return value


def _parse_allowed_extensions(raw: str) -> Set[str]:
    
    return {
        ext.strip().lstrip(".").lower()
        for ext in raw.split(",")
        if ext.strip()
    }


def _parse_origins(raw: str) -> List[str]:
    
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


class BaseConfig:
    

    
    APP_NAME: str = os.getenv("APP_NAME", "FundForge AI")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    APP_DESCRIPTION: str = "AI-Powered Grant & Funding Finder for Startups"

    
    SECRET_KEY: str = os.getenv("FLASK_SECRET_KEY", "")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    TESTING: bool = False
    PORT: int = int(os.getenv("PORT", "5000"))
    JSON_SORT_KEYS: bool = False
    PROPAGATE_EXCEPTIONS: bool = True

    
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET", "")
    JWT_ACCESS_TOKEN_EXPIRES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", "3600"))   
    JWT_REFRESH_TOKEN_EXPIRES: int = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES", "604800"))  

    
    
    _db_url = os.getenv("DATABASE_URL", "sqlite:///instance/fundforge.db")
    if _db_url.startswith("sqlite:///"):
        _rel_path = _db_url[10:]
        if not os.path.isabs(_rel_path):
            _config_dir = os.path.dirname(os.path.abspath(__file__))
            _project_root = os.path.dirname(os.path.dirname(_config_dir))
            _abs_path = os.path.abspath(os.path.join(_project_root, _rel_path))
        else:
            _abs_path = _rel_path
        
        os.makedirs(os.path.dirname(_abs_path), exist_ok=True)
        if os.name == 'nt':
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{_abs_path}"
        else:
            SQLALCHEMY_DATABASE_URI = f"sqlite:////{_abs_path}"
    else:
        SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ENGINE_OPTIONS: dict = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 10,
        "max_overflow": 20,
    }

    
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    
    CORS_ORIGINS: List[str] = _parse_origins(
        os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000")
    )
    CORS_METHODS: List[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    CORS_ALLOW_HEADERS: List[str] = ["Content-Type", "Authorization", "X-Request-ID"]
    CORS_EXPOSE_HEADERS: List[str] = ["X-Total-Count", "X-Page", "X-Per-Page"]
    CORS_MAX_AGE: int = 600  

    
    UPLOAD_FOLDER: str = os.getenv("UPLOAD_FOLDER", "uploads")
    MAX_CONTENT_LENGTH: int = int(os.getenv("MAX_UPLOAD_SIZE", str(16 * 1024 * 1024)))  
    ALLOWED_EXTENSIONS: Set[str] = _parse_allowed_extensions(
        os.getenv("ALLOWED_EXTENSIONS", "pdf,docx,doc,txt,md")
    )

    
    IBM_API_KEY: str = os.getenv("IBM_API_KEY", "")
    IBM_PROJECT_ID: str = os.getenv("IBM_PROJECT_ID", "")
    IBM_URL: str = os.getenv("IBM_URL", "https://us-south.ml.cloud.ibm.com")
    IBM_GRANITE_MODEL_ID: str = os.getenv(
        "IBM_GRANITE_MODEL_ID", "ibm/granite-13b-instruct-v2"
    )
    IBM_EMBEDDING_MODEL_ID: str = os.getenv(
        "IBM_EMBEDDING_MODEL_ID", "ibm/slate-125m-english-rtrvr"
    )
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    
    VECTOR_INDEX_ID: str = os.getenv("VECTOR_INDEX_ID", "")
    VECTOR_INDEX_INSTANCE_ID: str = os.getenv("VECTOR_INDEX_INSTANCE_ID", "")
    RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "5"))
    RAG_SIMILARITY_THRESHOLD: float = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.65"))

    
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GOOGLE_CSE_ID: str = os.getenv("GOOGLE_CSE_ID", "")
    GOOGLE_SEARCH_NUM_RESULTS: int = int(os.getenv("GOOGLE_SEARCH_NUM_RESULTS", "10"))

    
    RATELIMIT_DEFAULT: str = os.getenv("RATELIMIT_DEFAULT", "200/hour")
    RATELIMIT_STORAGE_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    
    DEFAULT_PAGE_SIZE: int = int(os.getenv("DEFAULT_PAGE_SIZE", "20"))
    MAX_PAGE_SIZE: int = int(os.getenv("MAX_PAGE_SIZE", "100"))

    
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")  

    @classmethod
    def validate(cls) -> None:
        
        required: List[tuple] = [
            ("FLASK_SECRET_KEY", cls.SECRET_KEY),
            ("JWT_SECRET", cls.JWT_SECRET_KEY),
        ]

        
        
        advisory: List[tuple] = [
            ("IBM_API_KEY", cls.IBM_API_KEY),
            ("IBM_PROJECT_ID", cls.IBM_PROJECT_ID),
            ("IBM_URL", cls.IBM_URL),
            ("GOOGLE_API_KEY", cls.GOOGLE_API_KEY),
            ("GOOGLE_CSE_ID", cls.GOOGLE_CSE_ID),
        ]

        missing_required = [name for name, val in required if not val]
        if missing_required:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing_required)}. "
                "Set them in your .env file or deployment environment."
            )

        missing_advisory = [name for name, val in advisory if not val]
        if missing_advisory:
            logger.warning(
                "Advisory environment variables not set — some features will be disabled: %s",
                ", ".join(missing_advisory),
            )

    @classmethod
    def as_dict(cls) -> dict:
        
        sensitive = {"SECRET_KEY", "JWT_SECRET_KEY", "IBM_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY"}
        return {
            key: ("***" if key in sensitive else val)
            for key, val in cls.__dict__.items()
            if not key.startswith("_") and not callable(val)
        }


class DevelopmentConfig(BaseConfig):
    

    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    LOG_FORMAT: str = "text"
    SQLALCHEMY_ECHO: bool = True  


class TestingConfig(BaseConfig):
    

    TESTING: bool = True
    DEBUG: bool = True
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///test_fundforge.db"
    SQLALCHEMY_ENGINE_OPTIONS: dict = {}
    SQLALCHEMY_ECHO: bool = False
    WTF_CSRF_ENABLED: bool = False
    LOG_LEVEL: str = "WARNING"


class ProductionConfig(BaseConfig):
    

    DEBUG: bool = False
    TESTING: bool = False
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "WARNING")
    LOG_FORMAT: str = "json"
    SQLALCHEMY_ECHO: bool = False

    @classmethod
    def validate(cls) -> None:
        
        super().validate()

        strict_required: List[tuple] = [
            ("IBM_API_KEY", cls.IBM_API_KEY),
            ("IBM_PROJECT_ID", cls.IBM_PROJECT_ID),
            ("IBM_URL", cls.IBM_URL),
            ("GOOGLE_API_KEY", cls.GOOGLE_API_KEY),
            ("GOOGLE_CSE_ID", cls.GOOGLE_CSE_ID),
            ("DATABASE_URL", cls.SQLALCHEMY_DATABASE_URI),
        ]
        missing = [name for name, val in strict_required if not val]
        if missing:
            raise EnvironmentError(
                f"Production startup failed. Missing variables: {', '.join(missing)}"
            )






_CONFIG_MAP: dict = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config() -> type:
    
    env = os.getenv("FLASK_ENV", "development").lower().strip()
    config_class = _CONFIG_MAP.get(env, DevelopmentConfig)
    logger.debug("Loading configuration for environment: '%s' → %s", env, config_class.__name__)
    return config_class

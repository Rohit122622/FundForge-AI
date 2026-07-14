

import logging
import logging.config
import sys
import json
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional






class JSONFormatter(logging.Formatter):
    

    
    
    _SKIP_ATTRS = frozenset({
        "args", "created", "exc_info", "exc_text", "filename",
        "funcName", "id", "levelname", "levelno", "lineno",
        "message", "module", "msecs", "msg", "name", "pathname",
        "process", "processName", "relativeCreated", "stack_info",
        "taskName", "thread", "threadName",
    })

    def format(self, record: logging.LogRecord) -> str:  
        
        record.message = record.getMessage()

        payload: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.message,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack_info"] = self.formatStack(record.stack_info)

        
        extra = {
            key: value
            for key, value in record.__dict__.items()
            if key not in self._SKIP_ATTRS
        }
        if extra:
            payload["extra"] = extra

        try:
            return json.dumps(payload, default=str, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            payload["serialization_error"] = str(exc)
            return json.dumps(payload, default=str)






_LEVEL_COLORS = {
    "DEBUG":    "\033[36m",   
    "INFO":     "\033[32m",   
    "WARNING":  "\033[33m",   
    "ERROR":    "\033[31m",   
    "CRITICAL": "\033[35m",   
}
_RESET = "\033[0m"


class ColourTextFormatter(logging.Formatter):
    

    def format(self, record: logging.LogRecord) -> str:  
        color = _LEVEL_COLORS.get(record.levelname, "")
        level_str = f"{color}{record.levelname:<8}{_RESET}"
        base = (
            f"{self.formatTime(record, '%Y-%m-%d %H:%M:%S,%f'[:-3])} "
            f"[{level_str}] "
            f"{record.name:<25} — "
            f"{record.getMessage()}"
        )
        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)
        return base






def configure_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    app_name: Optional[str] = "fundforge",
) -> None:
    
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    
    if log_format.lower() == "json":
        formatter: logging.Formatter = JSONFormatter()
    else:
        formatter = ColourTextFormatter()

    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)

    
    
    
    config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "selected": {
                "()": JSONFormatter if log_format.lower() == "json" else ColourTextFormatter,
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "selected",
                "level": log_level.upper(),
            }
        },
        "loggers": {
            
            app_name: {
                "handlers": ["console"],
                "level": log_level.upper(),
                "propagate": False,
            },
            
            "werkzeug": {
                "handlers": ["console"],
                "level": "WARNING" if log_format == "json" else "INFO",
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "handlers": ["console"],
                "level": "WARNING",
                "propagate": False,
            },
            "urllib3": {
                "handlers": ["console"],
                "level": "WARNING",
                "propagate": False,
            },
            "ibm_watson_machine_learning": {
                "handlers": ["console"],
                "level": "WARNING",
                "propagate": False,
            },
        },
        
        "root": {
            "handlers": ["console"],
            "level": log_level.upper(),
        },
    }

    logging.config.dictConfig(config)

    
    startup_logger = logging.getLogger(app_name)
    startup_logger.info(
        "Logging initialised — level=%s format=%s",
        log_level.upper(),
        log_format,
    )


def get_request_logger(name: str = "fundforge.request") -> logging.Logger:
    
    return logging.getLogger(name)


def log_exception(logger: logging.Logger, exc: Exception, context: Optional[str] = None) -> None:
    
    message = f"{context}: {exc}" if context else str(exc)
    logger.error(
        message,
        exc_info=True,
        extra={"traceback": traceback.format_exc()},
    )

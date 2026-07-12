import contextvars
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict

# Context variables to trace Request/Correlation IDs across async execution threads
correlation_id_ctx = contextvars.ContextVar("correlation_id", default="system")
request_id_ctx = contextvars.ContextVar("request_id", default="system")


class JSONFormatter(logging.Formatter):
    """
    Custom Formatter that outputs logs in JSON format.
    Ensures that Correlation and Request IDs are present if set in context.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_record: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "correlation_id": correlation_id_ctx.get(),
            "request_id": request_id_ctx.get(),
        }

        # Include details if passed extra context
        if hasattr(record, "extra_data") and record.extra_data:
            log_record["extra"] = record.extra_data

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record)


def setup_logging():
    """Initialise logging configuration."""
    root_logger = logging.getLogger()
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Standard out handler using JSON formatting
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(JSONFormatter())
    
    root_logger.addHandler(stdout_handler)
    root_logger.setLevel(logging.INFO)

    # Suppress verbose third-party loggers if necessary
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


# Helper functions to obtain specific logs categorized for Enterprise Audits
def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


# Categories ready for Phase 2+ integrations
auth_logger = logging.getLogger("auth_events")
security_logger = logging.getLogger("security_events")
business_logger = logging.getLogger("business_events")
performance_logger = logging.getLogger("performance_events")

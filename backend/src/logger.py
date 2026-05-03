import contextvars
import json
import logging
import logging.config
from dataclasses import dataclass
from typing import override

from src.env import LOG_LEVEL

request_id_ctx_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")

_APP_FMT = (
    "time=%(asctime)s "
    "level=%(levelname)s "
    "name=%(name)s "
    "pid=%(process)d "
    "caller=%(module)s:%(lineno)d "
    "request_id=%(request_id)s "
    "trace_id=%(otelTraceID)s "
    "span_id=%(otelSpanID)s "
    "msg=%(message)s"
)
_SYSTEM_FMT = (
    "time=%(asctime)s "
    "level=%(levelname)s "
    "name=%(name)s "
    "pid=%(process)d "
    "caller=%(module)s:%(lineno)d "
    "msg=%(message)s"
)
_DATE_FMT = "%Y-%m-%dT%H:%M:%S"


class LogFormatter(logging.Formatter):
    """JSON-escapes the msg field to keep each log record on a single line."""

    @override
    def formatMessage(self, record: logging.LogRecord) -> str:
        record.message = json.dumps(record.message, ensure_ascii=False)
        return super().formatMessage(record)


class RequestIdFilter(logging.Filter):
    """Injects request_id into every log record."""

    @override
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx_var.get("")
        return True


# Passed to gunicorn via logconfig_dict — applied at Logger init, before first log line.
# Also used directly via configure_logging() when running with plain uvicorn.
LOGGING_CONFIG: dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {"()": RequestIdFilter},
    },
    "formatters": {
        # app logs — include request/trace context
        "app": {"()": LogFormatter, "format": _APP_FMT, "datefmt": _DATE_FMT},
        # system logs (gunicorn/uvicorn internals) — no request context
        "system": {"()": LogFormatter, "format": _SYSTEM_FMT, "datefmt": _DATE_FMT},
    },
    "handlers": {
        # app logs — request/trace context fields
        "stdout_app": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "app",
            "filters": ["request_id"],
        },
        # everything else (root, third-party libs) — no context fields
        "stdout_system": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "system",
        },
        # gunicorn.error / uvicorn.error → stderr
        "stderr": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
            "formatter": "system",
        },
    },
    "root": {
        "level": LOG_LEVEL,
        "handlers": ["stdout_system"],
    },
    "loggers": {
        # app has its own handler — doesn't propagate to avoid double logging
        "app": {"level": LOG_LEVEL, "handlers": ["stdout_app"], "propagate": False},
        "system": {"level": LOG_LEVEL, "handlers": ["stdout_system"], "propagate": False},
        # uvicorn internals → propagate to root (system fmt) except .error → stderr
        "uvicorn": {"handlers": [], "propagate": True},
        "uvicorn.error": {"handlers": ["stderr"], "propagate": False},
        "uvicorn.access": {"handlers": [], "propagate": False},
        # gunicorn internals → same pattern
        "gunicorn": {"handlers": [], "propagate": True},
        "gunicorn.error": {"handlers": ["stderr"], "propagate": False},
        "gunicorn.access": {"handlers": [], "propagate": False},
    },
}


def configure_logging() -> None:
    """Apply logging config (used when running with plain uvicorn)."""
    logging.config.dictConfig(LOGGING_CONFIG)


@dataclass(frozen=True, slots=True)
class Logger:
    app = logging.getLogger("app")
    system = logging.getLogger("system")

log = Logger()

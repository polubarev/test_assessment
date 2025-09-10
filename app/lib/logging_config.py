import logging
import os
import json
from typing import Optional


def setup_logging(level: Optional[str] = None) -> None:
    """
    Configure root logging. Idempotent: safe to call multiple times.

    Level can be provided via argument, or env var LOG_LEVEL (defaults to INFO).
    """
    if getattr(setup_logging, "_configured", False):
        return

    level_name = (level or os.getenv("LOG_LEVEL") or "INFO").upper()
    try:
        log_level = getattr(logging, level_name)
    except AttributeError:
        log_level = logging.INFO

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    # Enrich logs to display "extra" fields as JSON in a trailing context column
    root_logger = logging.getLogger()

    # Standard LogRecord attributes to exclude from extras
    standard_attrs = {
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
        "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
        "created", "msecs", "relativeCreated", "thread", "threadName",
        "processName", "process", "asctime", "message"
    }

    class _ExtraContextFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
            extras = {k: v for k, v in record.__dict__.items() if k not in standard_attrs}
            # Avoid extremely long outputs; cap to ~2KB
            try:
                context = json.dumps(extras, ensure_ascii=False, default=str)
            except Exception:
                context = str(extras)
            if len(context) > 2048:
                context = context[:2048] + "…"
            setattr(record, "context", context if extras else "")
            return True

    context_filter = _ExtraContextFilter()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s %(context)s")

    for handler in root_logger.handlers:
        handler.addFilter(context_filter)
        handler.setFormatter(formatter)

    # Avoid duplicate logs when uvicorn/gunicorn also configures logging
    logging.getLogger("uvicorn").propagate = True
    logging.getLogger("uvicorn.error").propagate = True
    logging.getLogger("uvicorn.access").propagate = False

    setup_logging._configured = True  # type: ignore[attr-defined]


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a module logger after ensuring logging is configured."""
    setup_logging()
    return logging.getLogger(name if name else __name__)



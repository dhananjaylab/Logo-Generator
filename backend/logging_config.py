"""
Structured logging configuration for Logo Generator.
Replaces print() statements with proper logging levels and formats.
Integrates with Sentry for error tracking.

P1.5: SQL echo is disabled at the database.py level (_echo_sql = False always).
      This module provides controlled debug logging via the event listener in
      database.py instead — it logs SQL *shapes* (never parameter values) and
      only when LOG_LEVEL=DEBUG is explicitly set in the environment.
"""

import logging
import logging.handlers
import os
import sys
from pythonjsonlogger import jsonlogger
from observability import request_id_ctx

# Try to import Sentry, graceful fallback if not installed
try:
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False

# ─────────────────────────────────────────────────────────────────────────────
# Sentry Configuration (Optional: requires sentry-sdk)
# ─────────────────────────────────────────────────────────────────────────────

if SENTRY_AVAILABLE:
    sentry_dsn = os.getenv("SENTRY_DSN")
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            traces_sample_rate=0.1 if os.getenv("ENV") != "production" else 0.05,
            profiles_sample_rate=0.1 if os.getenv("ENV") != "production" else 0.01,
            integrations=[
                LoggingIntegration(level=logging.INFO, event_level=logging.ERROR)
            ]
        )


# ─────────────────────────────────────────────────────────────────────────────
# Logging Formatters
# ─────────────────────────────────────────────────────────────────────────────

class RequestIDFilter(logging.Filter):
    """
    Add request_id to every log record.

    Reads from observability.request_id_ctx, which is set by metrics_middleware
    (observability.py) at the start of each HTTP request and cleared on
    completion. This means every log line produced during a request — including
    those from background coroutines that inherit the context — will carry the
    same request_id, making log correlation trivial.
    """
    def filter(self, record):
        record.request_id = request_id_ctx.get()
        return True


def setup_logging():
    """Initialize structured logging with JSON format for production."""

    root_logger = logging.getLogger()
    root_logger.setLevel(
        logging.DEBUG if os.getenv("LOG_LEVEL", "").upper() == "DEBUG"
        else logging.DEBUG if os.getenv("ENV") != "production"
        else logging.INFO
    )

    # Remove any handlers already attached (prevents duplicate output when
    # setup_logging() is called more than once, e.g. in tests).
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # ── Console Handler (always active) ──────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)

    if os.getenv("ENV") == "production":
        # JSON format for production — machine-readable, ingestible by
        # Datadog / CloudWatch / Loki without a parser plugin.
        formatter = jsonlogger.JsonFormatter(
            fmt="%(timestamp)s %(level)s %(name)s %(message)s %(request_id)s",
            timestamp=True,
        )
    else:
        # Human-readable format for local development.
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)-8s [%(name)s:%(lineno)d] "
            "[req=%(request_id)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler.setFormatter(formatter)
    console_handler.addFilter(RequestIDFilter())
    root_logger.addHandler(console_handler)

    # ── File Handler (optional — set LOG_FILE env var to enable) ─────────────
    log_file = os.getenv("LOG_FILE")
    if log_file:
        try:
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,   # 10 MB
                backupCount=5,
            )
            file_handler.setFormatter(formatter)
            file_handler.addFilter(RequestIDFilter())
            root_logger.addHandler(file_handler)
        except Exception as exc:
            root_logger.warning(f"Failed to set up file logging at '{log_file}': {exc}")

    # ── Per-library noise reduction ───────────────────────────────────────────
    # These libraries log at DEBUG/INFO levels that are rarely actionable and
    # obscure application-level logs during local development.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("arq").setLevel(logging.INFO)
    logging.getLogger("google.genai").setLevel(logging.INFO)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


# Initialize on module import so that the first `import logging_config` in
# app.py / worker startup calls setup_logging() before any other module logs.
setup_logging()


def get_logger(name: str) -> logging.Logger:
    """Return a named logger. Preferred over logging.getLogger() at call sites."""
    return logging.getLogger(name)

"""
Structured logging configuration for Logo Generator.
Replaces print() statements with proper logging levels and formats.
Integrates with Sentry for error tracking.
"""

import logging
import logging.handlers
import os
import sys
from pythonjsonlogger import jsonlogger

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
    """Add request_id to logging context if available"""
    def __init__(self, request_id_var: str = "request_id"):
        self.request_id_var = request_id_var
        
    def filter(self, record):
        # Try to get request_id from context (should be set by middleware)
        record.request_id = getattr(record, "request_id", "N/A")
        return True


def setup_logging():
    """Initialize structured logging with JSON format for production"""
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if os.getenv("ENV") != "production" else logging.INFO)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # ── Console Handler (always) ────────────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    
    if os.getenv("ENV") == "production":
        # JSON format for production (machine-readable)
        formatter = jsonlogger.JsonFormatter(
            fmt='%(timestamp)s %(level)s %(name)s %(message)s %(request_id)s',
            timestamp=True
        )
    else:
        # Human-readable format for development
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)-8s [%(name)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(formatter)
    console_handler.addFilter(RequestIDFilter())
    root_logger.addHandler(console_handler)
    
    # ── File Handler (optional, if LOG_FILE env set) ────────────────────────
    log_file = os.getenv("LOG_FILE")
    if log_file:
        try:
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10485760,  # 10MB
                backupCount=5
            )
            file_handler.setFormatter(formatter)
            file_handler.addFilter(RequestIDFilter())
            root_logger.addHandler(file_handler)
        except Exception as e:
            root_logger.warning(f"Failed to setup file logging: {e}")
    
    # ── Per-module loggers ──────────────────────────────────────────────────
    # Reduce noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("arq").setLevel(logging.INFO)
    logging.getLogger("google.genai").setLevel(logging.INFO)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)


# Initialize logging on module load
setup_logging()

# Export logger factory
def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name"""
    return logging.getLogger(name)

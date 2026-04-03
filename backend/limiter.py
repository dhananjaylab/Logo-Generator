import os
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

# Use REDIS_URL for rate limit state (persisted & shared across workers)
redis_url = os.getenv("REDIS_URL")

if not redis_url:
    logger.error(
        "REDIS_URL not configured. Rate limits will not persist across restarts. "
        "Set REDIS_URL env var for production."
    )
    # Warn but allow in dev; fail hard in production
    if os.getenv("ENV") == "production":
        raise ValueError("REDIS_URL required in production for rate limiting")
    redis_url = "memory://"

limiter = Limiter(
    key_func=get_remote_address, 
    storage_uri=redis_url,
    default_limits=["200 per day", "50 per hour"],  # Sensible defaults
)

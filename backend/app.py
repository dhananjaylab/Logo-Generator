import os
from pathlib import Path
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

load_dotenv()

# Initialize structured logging FIRST (before any other imports)
from logging_config import setup_logging, get_logger
setup_logging()
logger = get_logger(__name__)

from routers import router as logo_router
from database import init_db
from limiter import limiter
from arq import create_pool
from config import REDIS_SETTINGS
from observability import metrics_middleware

# (Limiter initialized in limiter.py)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events for the FastAPI application."""
    # Startup: Initialize database and create redis pool
    await init_db()
    logger.info("[OK] Database initialized")
    
    # Create and store redis connection pool at startup (avoid per-request creation)
    app.state.redis = await create_pool(REDIS_SETTINGS)
    logger.info("[OK] Redis pool created at startup")
    
    yield
    
    # Shutdown: Close redis pool
    if hasattr(app.state, 'redis'):
        await app.state.redis.close()
        logger.info("[OK] Redis pool closed at shutdown")

app = FastAPI(
    title="Logo Generator API",
    description="Generate logos using Gemini or DALL-E 3",
    version="2.1.0",
    lifespan=lifespan,
)

# ── Middleware & Security ───────────────────────────────────────────────────

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS Configuration ─────────────────────────────────────────────────────
# Production: use specific origins, never wildcard with credentials

# Parse allowed origins from env (comma-separated for production)
allowed_origins_str = os.getenv(
    "ALLOWED_ORIGINS", 
    "http://localhost:3000" if os.getenv("ENV") != "production" else ""
)

allowed_origins = [
    origin.strip() 
    for origin in allowed_origins_str.split(",") 
    if origin.strip()
]

if not allowed_origins and os.getenv("ENV") == "production":
    raise ValueError(
        "CORS: ALLOWED_ORIGINS must be set in production. "
        "Set ALLOWED_ORIGINS env var (comma-separated)."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins or ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=3600,
)

# ── Observability & Metrics Collection ──────────────────────────────────────
app.middleware("http")(metrics_middleware)

# ── Endpoints ───────────────────────────────────────────────────────────────

app.include_router(logo_router)


@app.get("/")
async def root():
    return {
        "message": "Logo Generator API v2.1",
        "docs":    "/docs",
        "health":  "/api/health",
        "generate":"/api/generate",
        "static":  "/static/generated_logos/<gemini|dalle>/<filename>",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
import os
from pathlib import Path
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
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
    description="Generate logos using Gemini or GPT image",
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


@app.api_route("/api", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"])
async def legacy_api_root(request: Request):
    target = "/api/v1"
    if request.url.query:
        target = f"{target}?{request.url.query}"
    return RedirectResponse(url=target, status_code=307)


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"])
async def legacy_api_redirect(path: str, request: Request):
    if path == "v1" or path.startswith("v1/"):
        return JSONResponse(content={"detail": "Not Found"}, status_code=404)
    target = f"/api/v1/{path}"
    if request.url.query:
        target = f"{target}?{request.url.query}"
    return RedirectResponse(url=target, status_code=307)


@app.get("/metrics", include_in_schema=False)
async def metrics_endpoint():
    """Prometheus scrape endpoint."""
    try:
        from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest, multiprocess

        registry = CollectorRegistry()
        if os.getenv("PROMETHEUS_MULTIPROC_DIR"):
            multiprocess.MultiProcessCollector(registry)
            content = generate_latest(registry)
        else:
            from prometheus_client import REGISTRY

            content = generate_latest(REGISTRY)
        return Response(content=content, media_type=CONTENT_TYPE_LATEST)
    except Exception as exc:
        logger.warning(f"[Metrics] Prometheus endpoint unavailable: {exc}")
        return Response(content="prometheus metrics unavailable\n", status_code=503, media_type="text/plain")


@app.get("/")
async def root():
    return {
        "message": "Logo Generator API v2.1",
        "docs":    "/docs",
        "health":  "/api/v1/health",
        "generate":"/api/v1/generate",
        "static":  "/static/generated_logos/<gemini|openai>/<filename>",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)

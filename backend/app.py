import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

load_dotenv()

from logging_config import setup_logging, get_logger
setup_logging()
logger = get_logger(__name__)

from routers import router as logo_router
from database import init_db
from limiter import limiter
from arq import create_pool
from config import REDIS_SETTINGS
from dependencies import Clients
from prom_metrics import component_ready
from observability import metrics_middleware
from circuit_breaker import close_all as close_circuit_breakers  # P2 — cleanup


# ─────────────────────────────────────────────────────────────────────────────
# Redis pool creation with retry  (HIGH-01 FIX)
# ─────────────────────────────────────────────────────────────────────────────

async def _create_redis_pool_with_retry(max_attempts: int = 5):
    """
    Create the ARQ Redis pool with exponential-backoff retry.

    Previously, a single failed create_pool() call during startup would crash
    the entire application with an unhandled exception. This is especially
    problematic in containerised environments where Redis may not be immediately
    available when the API container starts.

    Backoff schedule (seconds): 2, 4, 8, 10, 10 (capped at 10)
    """
    last_exc: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            pool = await create_pool(REDIS_SETTINGS)
            # Verify the connection is actually usable before declaring success
            await pool.ping()
            logger.info(f"[Redis] Connected successfully on attempt {attempt}/{max_attempts}")
            return pool

        except Exception as exc:
            last_exc = exc
            if attempt >= max_attempts:
                break

            delay = min(2 ** attempt, 10)   # 2, 4, 8, 10, 10 …
            logger.warning(
                f"[Redis] Attempt {attempt}/{max_attempts} failed: {exc}. "
                f"Retrying in {delay}s…"
            )
            await asyncio.sleep(delay)

    # All attempts exhausted
    logger.error(
        f"[Redis] All {max_attempts} connection attempts failed. "
        "The API will start in a degraded state — generation and history "
        "endpoints will return 503 until Redis becomes available. "
        f"Last error: {last_exc}"
    )
    # Return None so the app starts in degraded mode rather than refusing to
    # start at all. The get_redis() dependency in routers.py returns 503 when
    # app.state.redis is None.
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Application Lifespan
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    await init_db()
    logger.info("[OK] Database initialised")
    component_ready.labels(component="db").set(1)

    # Create Redis pool with retry — degraded start is allowed if Redis is down
    app.state.redis = await _create_redis_pool_with_retry(max_attempts=5)
    if app.state.redis:
        logger.info("[OK] Redis pool created")
        component_ready.labels(component="redis").set(1)
    else:
        logger.warning("[DEGRADED] Redis unavailable at startup — running without queue")
        component_ready.labels(component="redis").set(0)

    component_ready.labels(component="api").set(1)
    component_ready.labels(component="openai").set(1 if Clients.is_openai_ready() else 0)
    component_ready.labels(component="gemini").set(1 if Clients.is_gemini_ready() else 0)

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────────
    if app.state.redis:
        try:
            await app.state.redis.close()
            logger.info("[OK] Redis pool closed")
        except Exception as exc:
            logger.warning(f"[Redis] Error closing pool: {exc}")

    # Close the dedicated Redis connections held by circuit breakers
    await close_circuit_breakers()
    logger.info("[OK] Circuit breaker connections closed")


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI App
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Logo Generator API",
    description="Generate logos using Gemini or GPT image",
    version="2.2.0",
    lifespan=lifespan,
)

# ── Rate limiting ────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ─────────────────────────────────────────────────────────────────────
allowed_origins_str = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000" if os.getenv("ENV") != "production" else "",
)
allowed_origins = [o.strip() for o in allowed_origins_str.split(",") if o.strip()]

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

# ── Observability ────────────────────────────────────────────────────────────
app.middleware("http")(metrics_middleware)

# ── Routes ───────────────────────────────────────────────────────────────────
app.include_router(logo_router)


@app.api_route(
    "/api",
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
)
async def legacy_api_root(request: Request):
    target = "/api/v1"
    if request.url.query:
        target = f"{target}?{request.url.query}"
    return RedirectResponse(url=target, status_code=307)


@app.api_route(
    "/api/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
)
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
        from prometheus_client import (
            CONTENT_TYPE_LATEST,
            CollectorRegistry,
            generate_latest,
            multiprocess,
            REGISTRY,
        )
        if os.getenv("PROMETHEUS_MULTIPROC_DIR"):
            registry = CollectorRegistry()
            multiprocess.MultiProcessCollector(registry)
            content = generate_latest(registry)
        else:
            content = generate_latest(REGISTRY)
        return Response(content=content, media_type=CONTENT_TYPE_LATEST)
    except Exception as exc:
        logger.warning(f"[Metrics] Prometheus endpoint unavailable: {exc}")
        return Response(
            content="prometheus metrics unavailable\n",
            status_code=503,
            media_type="text/plain",
        )


@app.get("/")
async def root():
    return {
        "message": "Logo Generator API v2.2",
        "docs":    "/docs",
        "health":  "/api/v1/health",
        "generate": "/api/v1/generate",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)

import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

load_dotenv()

from routers import router as logo_router
from database import init_db
from limiter import limiter
from arq import create_pool
from config import REDIS_SETTINGS

# (Limiter initialized in limiter.py)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events for the FastAPI application."""
    # Startup: Initialize database and create redis pool
    await init_db()
    
    # Create and store redis connection pool at startup (avoid per-request creation)
    app.state.redis = await create_pool(REDIS_SETTINGS)
    print("[ARQ] ✓ Redis pool created at startup")
    
    yield
    
    # Shutdown: Close redis pool
    if hasattr(app.state, 'redis'):
        await app.state.redis.close()
        print("[ARQ] ✓ Redis pool closed at shutdown")

app = FastAPI(
    title="Logo Generator API",
    description="Generate logos using Gemini or DALL-E 3",
    version="2.1.0",
    lifespan=lifespan,
)

# ── Middleware & Security ───────────────────────────────────────────────────

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        os.getenv("FRONTEND_URL", ""),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
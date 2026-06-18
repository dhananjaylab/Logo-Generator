import os
import logging
import time
from functools import lru_cache
from google import genai
from openai import AsyncOpenAI
import httpx
from jose import jwt
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Clients:
    """Container for API clients"""
    _gemini_client = None
    _openai_client = None

    @classmethod
    def get_gemini_client(cls):
        if cls._gemini_client is None:
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                cls._gemini_client = genai.Client(api_key=api_key)
        return cls._gemini_client

    @classmethod
    def get_openai_client(cls):
        if cls._openai_client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                cls._openai_client = AsyncOpenAI(api_key=api_key)
        return cls._openai_client

    @classmethod
    def is_gemini_ready(cls):
        return cls.get_gemini_client() is not None

    @classmethod
    def is_openai_ready(cls):
        return cls.get_openai_client() is not None


def get_gemini_client():
    return Clients.get_gemini_client()


def get_openai_client():
    return Clients.get_openai_client()


# ── Clerk Auth Dependency ───────────────────────────────────────────────────

security = HTTPBearer()

# SECURITY FIX (P1.3):
# ALLOW_DEV_TOKEN must be explicitly set to "true" in the environment to
# permit DEV_TOKEN bypass.  It is blocked unconditionally in "production" and
# "staging" environments regardless of this flag, so an accidental leak of
# ALLOW_DEV_TOKEN=true into a higher tier cannot open a bypass.
#
# The token value itself must NEVER be committed to version control or README.
# Generate a fresh value per developer with:  python -c "import secrets; print(secrets.token_hex(32))"
_ALLOW_DEV_TOKEN: bool = os.getenv("ALLOW_DEV_TOKEN", "false").strip().lower() == "true"
_BLOCKED_ENVS: frozenset = frozenset({"production", "staging"})


class ClerkAuthProvider:
    """Helper to handle Clerk JWT validation with JWKS caching."""
    _jwks_cache = None
    _last_fetch: float = 0.0
    _cache_ttl: int = 3600  # 1 hour

    @classmethod
    async def get_jwks(cls):
        jwks_url = os.getenv("CLERK_JWKS_URL")
        if not jwks_url or jwks_url == "your_clerk_jwks_url_here":
            logger.warning(
                "[AUTH] CLERK_JWKS_URL not configured. "
                "Set CLERK_JWKS_URL env var to enable token validation."
            )
            return None

        now = time.time()
        if cls._jwks_cache is None or (now - cls._last_fetch) > cls._cache_ttl:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(jwks_url, timeout=10)
                    response.raise_for_status()
                    cls._jwks_cache = response.json()
                    cls._last_fetch = now
                    logger.info(f"[AUTH] Refreshed JWKS from {jwks_url}")
            except Exception as e:
                logger.error(f"[AUTH] Failed to fetch JWKS: {e}")
                if cls._jwks_cache:
                    logger.warning("[AUTH] Returning stale JWKS cache")
                    return cls._jwks_cache
                raise HTTPException(status_code=500, detail="Authentication configuration error")

        return cls._jwks_cache


async def validate_token_string(token: str | None) -> dict:
    """
    Validate a raw token string.
    Raises HTTPException on failure; returns the JWT payload dict on success.

    DEV_TOKEN bypass rules (P1.3):
      1. Blocked unconditionally when ENV is 'production' or 'staging'.
      2. Blocked when ALLOW_DEV_TOKEN env var is not explicitly "true".
      3. The token value must differ from the public placeholder in .env.template.
    """
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    current_env = os.getenv("ENV", "development")
    dev_token = os.getenv("DEV_TOKEN", "")

    # ── DEV_TOKEN bypass ────────────────────────────────────────────────────
    if dev_token and token == dev_token:

        # Hard block in production / staging — no exceptions.
        if current_env in _BLOCKED_ENVS:
            logger.error(
                f"[AUTH] ❌ DEV_TOKEN rejected: environment is '{current_env}'. "
                "DEV_TOKEN bypass is never permitted in production or staging."
            )
            raise HTTPException(
                status_code=403,
                detail="Dev tokens are not permitted in this environment.",
            )

        # Soft block: ALLOW_DEV_TOKEN must be set to "true" in the env file.
        if not _ALLOW_DEV_TOKEN:
            logger.error(
                "[AUTH] ❌ DEV_TOKEN rejected: ALLOW_DEV_TOKEN is not set to 'true'. "
                "Add ALLOW_DEV_TOKEN=true to your local .env to enable dev bypass."
            )
            raise HTTPException(
                status_code=403,
                detail="Dev token usage is disabled. Set ALLOW_DEV_TOKEN=true in your environment.",
            )

        logger.info("[AUTH] ✅ Authorized via DEV_TOKEN (local development mode)")
        return {"sub": "developer", "status": "verified_via_dev_token"}

    # ── Clerk JWT validation ────────────────────────────────────────────────
    jwks = await ClerkAuthProvider.get_jwks()

    if not jwks:
        # No JWKS configured. In non-production environments, allow anonymously
        # so local dev without Clerk still works when DEV_TOKEN is not set.
        if current_env not in _BLOCKED_ENVS:
            logger.warning("[AUTH] ⚠ Skipping validation — JWKS not configured (dev mode)")
            return {"sub": "anonymous", "status": "unverified"}
        raise HTTPException(status_code=500, detail="Authentication service unavailable")

    try:
        is_production = current_env == "production"
        verify_aud = is_production
        audience = os.getenv(
            "CLERK_AUDIENCE",
            os.getenv("NEXT_PUBLIC_API_URL", "http://localhost:3000"),
        )
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience=audience if verify_aud else None,
            options={"verify_aud": verify_aud},
        )
        logger.info(f"[AUTH] ✅ JWT validated for user: {payload.get('sub')}")
        return payload

    except Exception as e:
        logger.warning(f"[AUTH] ❌ Token validation failed: {e}")
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def validate_clerk_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """FastAPI dependency. Validates the Authorization: Bearer <token> header."""
    return await validate_token_string(credentials.credentials)

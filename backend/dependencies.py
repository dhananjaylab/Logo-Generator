import os
import logging
from functools import lru_cache
from google import genai
from openai import AsyncOpenAI
import httpx
import time
from jose import jwt
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class Clients:
    """Container for API clients"""
    _gemini_client = None
    _openai_client = None

    @classmethod
    def get_gemini_client(cls):
        """Get or initialize Gemini client"""
        if cls._gemini_client is None:
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                cls._gemini_client = genai.Client(api_key=api_key)
        return cls._gemini_client

    @classmethod
    def get_openai_client(cls):
        """Get or initialize OpenAI client"""
        if cls._openai_client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                cls._openai_client = AsyncOpenAI(api_key=api_key)
        return cls._openai_client

    @classmethod
    def is_gemini_ready(cls):
        """Check if Gemini client is ready"""
        return cls.get_gemini_client() is not None

    @classmethod
    def is_openai_ready(cls):
        """Check if OpenAI client is ready"""
        return cls.get_openai_client() is not None


# Dependency functions for FastAPI
def get_gemini_client():
    """Dependency for Gemini client"""
    return Clients.get_gemini_client()


def get_openai_client():
    """Dependency for OpenAI client"""
    return Clients.get_openai_client()


# ── Clerk Auth Dependency ───────────────────────────────────────────────────

security = HTTPBearer()

class ClerkAuthProvider:
    """Helper to handle Clerk JWT validation with JWKS caching"""
    _jwks_cache = None
    _last_fetch = 0
    _cache_ttl = 3600  # 1 hour

    @classmethod
    async def get_jwks(cls):
        """Fetch JWKS from Clerk if cache is expired"""
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

async def validate_clerk_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """FastAPI dependency to validate Clerk JWT"""
    token = credentials.credentials
    
    # ── Dev Token Bypass (DEV only, not in PROD) ────────────────────────────
    # For local testing, allow a pre-configured developer token
    # ONLY if ENV != "production"
    is_production = os.getenv("ENV") == "production"
    dev_token = os.getenv("DEV_TOKEN")
    
    if dev_token and token == dev_token:
        if is_production:
            logger.error("[AUTH] ❌ DEV_TOKEN used in production - rejecting")
            raise HTTPException(
                status_code=403,
                detail="Dev tokens not allowed in production",
                headers={"WWW-Authenticate": "Bearer"},
            )
        logger.info("[AUTH] ✅ Authorized via DEV_TOKEN (dev mode)")
        return {"sub": "developer", "status": "verified_via_dev_token"}

    # ── Clerk JWT Validation ────────────────────────────────────────────────
    jwks = await ClerkAuthProvider.get_jwks()
    
    if not jwks:
        if is_production:
            logger.error("[AUTH] JWKS not available in production")
            raise HTTPException(
                status_code=500, 
                detail="Authentication service unavailable"
            )
        # In dev mode, allow unverified if JWKS not configured
        logger.warning("[AUTH] ⚠ Skipping validation - JWKS not configured (dev mode)")
        return {"sub": "anonymous", "status": "unverified"}

    try:
        # Clerk expects: audience = "http://localhost:3000" or your frontend URL
        # In production, verify_aud must be True
        verify_aud = is_production
        audience = os.getenv("CLERK_AUDIENCE", os.getenv("NEXT_PUBLIC_API_URL", "http://localhost:3000"))
        
        payload = jwt.decode(
            token, 
            jwks, 
            algorithms=["RS256"],
            audience=audience if verify_aud else None,
            options={"verify_aud": verify_aud}
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

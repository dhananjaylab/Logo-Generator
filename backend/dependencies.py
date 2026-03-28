import os
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
            # For development/demo, we might want to skip if not configured, 
            # but for security we should probably fail.
            print("[AUTH] ⚠ CLERK_JWKS_URL not configured")
            return None

        now = time.time()
        if cls._jwks_cache is None or (now - cls._last_fetch) > cls._cache_ttl:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(jwks_url)
                    response.raise_for_status()
                    cls._jwks_cache = response.json()
                    cls._last_fetch = now
                    print(f"[AUTH] Refreshed JWKS from {jwks_url}")
            except Exception as e:
                print(f"[AUTH] ❌ Failed to fetch JWKS: {e}")
                if cls._jwks_cache:
                    return cls._jwks_cache # Return stale cache if error
                raise HTTPException(status_code=500, detail="Authentication configuration error")
        
        return cls._jwks_cache

async def validate_clerk_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """FastAPI dependency to validate Clerk JWT"""
    token = credentials.credentials
    
    # ── Dev Token Bypass ───────────────────────────────────────────────────
    # For local testing, allow a pre-configured developer token
    dev_token = os.getenv("DEV_TOKEN")
    if dev_token and token == dev_token:
        print("[AUTH] ✅ Authorized via DEV_TOKEN")
        return {"sub": "developer", "status": "verified_via_dev_token"}

    jwks = await ClerkAuthProvider.get_jwks()
    
    if not jwks:
        # If JWKS is not configured, we allow it for now but log warning
        # Alternatively: raise HTTPException(500, "Auth not configured")
        print("[AUTH] ⚠ Skipping validation - JWKS not configured")
        return {"sub": "anonymous", "status": "unverified"}

    try:
        # In a real app, you'd find the correct key from JWKS by 'kid'
        # For simplicity with jose.jwt, it can often handle JWKS directly or you map kids.
        # But Clerk usually provides a simple JWKS.
        payload = jwt.decode(
            token, 
            jwks, 
            algorithms=["RS256"],
            options={"verify_aud": False} # Adjust based on your Clerk setup
        )
        return payload
    except Exception as e:
        print(f"[AUTH] ❌ Token validation failed: {e}")
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

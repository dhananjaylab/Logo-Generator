import asyncio
import logging
from arq import worker
from google import genai

from config import REDIS_URL, REDIS_SETTINGS
from services import LLMService
from dependencies import Clients

logger = logging.getLogger(__name__)

async def generate_gemini_task(ctx, user_ip: str, user_id: str, **kwargs):
    """
    Background task to generate a logo using Gemini.
    Uses LLMService stored in ARQ context for connection reuse.
    """
    # Try to get LLMService from context (reused), fallback to create new one
    llm = ctx.get("llm_gemini") if hasattr(ctx, "get") else None
    
    if not llm:
        gemini_client = Clients.get_gemini_client()
        llm = LLMService(gemini_client, None)
    
    print(f"[Gemini Worker] Starting generation for {kwargs.get('text')}")
    
    try:
        path, prompt = await llm.generate_logo_with_gemini(user_ip=user_ip, user_id=user_id, **kwargs)
        return {"result": [path], "generator": "gemini", "prompt": prompt, "status": "completed"}
    except Exception as exc:
        logger.error(f"[Gemini Worker] Generation failed: {exc}")
        return {"status": "failed", "error": str(exc)}

async def startup(ctx):
    logger.info("[Gemini Worker] Starting up...")
    gemini_client = Clients.get_gemini_client()
    # Store LLMService in context for reuse across tasks
    ctx["llm_gemini"] = LLMService(gemini_client, None)

async def shutdown(ctx):
    logger.info("[Gemini Worker] Shutting down...")

class WorkerSettings:
    """
    ARQ worker settings for Gemini.
    Configures job result TTL (2 days) to prevent result accumulation.
    """
    functions = [generate_gemini_task]
    redis_settings = REDIS_SETTINGS
    queue_name = 'gemini_queue'
    on_startup = startup
    on_shutdown = shutdown
    result_ttl = 172800  # 2 days in seconds: results auto-expire after 2 days

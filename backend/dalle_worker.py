import asyncio
import logging
from arq import worker
from google import genai
from openai import AsyncOpenAI

from config import REDIS_URL, REDIS_SETTINGS
from services import LLMService
from dependencies import Clients

logger = logging.getLogger(__name__)

async def generate_dalle_task(ctx, user_ip: str, user_id: str, **kwargs):
    """
    Background task to generate a logo using DALL-E 3.
    Uses LLMService stored in ARQ context for connection reuse.
    """
    # Try to get LLMService from context (reused), fallback to create new one
    llm = ctx.get("llm_dalle") if hasattr(ctx, "get") else None
    
    if not llm:
        openai_client = Clients.get_openai_client()
        llm = LLMService(None, openai_client)
    
    print(f"[DALL-E Worker] Starting generation for {kwargs.get('text')}")
    
    try:
        path, prompt = await llm.generate_logo_with_dalle(user_ip=user_ip, user_id=user_id, **kwargs)
        return {"result": [path], "generator": "dalle-3", "prompt": prompt, "status": "completed"}
    except Exception as exc:
        logger.error(f"[DALL-E Worker] Generation failed: {exc}")
        return {"status": "failed", "error": str(exc)}

async def startup(ctx):
    logger.info("[DALL-E Worker] Starting up...")
    openai_client = Clients.get_openai_client()
    # Store LLMService in context for reuse across tasks
    ctx["llm_dalle"] = LLMService(None, openai_client)

async def shutdown(ctx):
    logger.info("[DALL-E Worker] Shutting down...")

class WorkerSettings:
    """
    ARQ worker settings for DALL-E.
    Configures job result TTL (2 days) to prevent result accumulation.
    """
    functions = [generate_dalle_task]
    redis_settings = REDIS_SETTINGS
    queue_name = 'dalle_queue'
    on_startup = startup
    on_shutdown = shutdown
    result_ttl = 172800  # 2 days in seconds: results auto-expire after 2 days

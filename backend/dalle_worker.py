import asyncio
import json
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
    Publishes completion event to Redis for WebSocket subscribers.
    """
    # Try to get LLMService from context (reused), fallback to create new one
    llm = ctx.get("llm_dalle") if hasattr(ctx, "get") else None
    
    if not llm:
        openai_client = Clients.get_openai_client()
        llm = LLMService(None, openai_client)
    
    job_id = ctx.get("job_id")
    redis = ctx.get("redis")

    logger.info(f"[DALL-E Worker] Starting generation for '{kwargs.get('text')}' (job={job_id})")
    
    try:
        path, prompt = await llm.generate_logo_with_dalle(user_ip=user_ip, user_id=user_id, **kwargs)
        result = {"result": [path], "generator": "dalle-3", "prompt": prompt, "status": "completed"}

        # Notify WebSocket subscribers — replaces server-side polling
        if job_id and redis:
            event = json.dumps({
                "status": "completed",
                "user_id": user_id,  # for ownership validation in WS handler
                "result": {
                    "result": result["result"],
                    "generator": result["generator"],
                    "prompt": result["prompt"],
                    "brand": kwargs.get("text", ""),
                    "style": kwargs.get("style", ""),
                    "palette": kwargs.get("palette", ""),
                }
            })
            await redis.publish(f"job:complete:{job_id}", event)

        return result

    except Exception as exc:
        logger.error(f"[DALL-E Worker] Generation failed: {exc}")
        error_event = json.dumps({"status": "failed", "error": str(exc), "user_id": user_id})
        if job_id and redis:
            await redis.publish(f"job:complete:{job_id}", error_event)
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

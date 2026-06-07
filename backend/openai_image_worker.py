import json
import logging

from config import REDIS_SETTINGS
from services import LLMService
from dependencies import Clients

logger = logging.getLogger(__name__)


async def generate_openai_image_task(ctx, user_ip: str, user_id: str, **kwargs):
    """
    Background task to generate a logo using the GPT image model.
    Uses LLMService stored in ARQ context for connection reuse.
    Publishes completion event to Redis for WebSocket subscribers.
    """
    llm = ctx.get("llm_openai_image") if hasattr(ctx, "get") else None

    if not llm:
        openai_client = Clients.get_openai_client()
        llm = LLMService(None, openai_client)

    job_id = ctx.get("job_id")
    redis = ctx.get("redis")

    logger.info(f"[OpenAI Image Worker] Starting generation for '{kwargs.get('text')}' (job={job_id})")

    try:
        path, prompt = await llm.generate_logo_with_openai_image(user_ip=user_ip, user_id=user_id, **kwargs)
        result = {"result": [path], "generator": "gpt-image-2-2026-04-21", "prompt": prompt, "status": "completed"}

        if job_id and redis:
            event = json.dumps({
                "status": "completed",
                "user_id": user_id,
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
        logger.error(f"[OpenAI Image Worker] Generation failed: {exc}")
        error_event = json.dumps({"status": "failed", "error": str(exc), "user_id": user_id})
        if job_id and redis:
            await redis.publish(f"job:complete:{job_id}", error_event)
        return {"status": "failed", "error": str(exc)}


async def startup(ctx):
    logger.info("[OpenAI Image Worker] Starting up...")
    openai_client = Clients.get_openai_client()
    ctx["llm_openai_image"] = LLMService(None, openai_client)


async def shutdown(ctx):
    logger.info("[OpenAI Image Worker] Shutting down...")


class WorkerSettings:
    """
    ARQ worker settings for OpenAI image generation.
    Configures job result TTL (2 days) to prevent result accumulation.
    """
    functions = [generate_openai_image_task]
    redis_settings = REDIS_SETTINGS
    queue_name = 'openai_image_queue'
    on_startup = startup
    on_shutdown = shutdown
    result_ttl = 172800  # 2 days in seconds: results auto-expire after 2 days

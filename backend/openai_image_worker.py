import os
import json
import logging
import time
from datetime import datetime, timezone

from config import REDIS_SETTINGS
from database import AsyncSessionLocal
from prom_metrics import generation_requests, generation_latency, errors_total, job_retries_total, dlq_jobs_total, worker_max_jobs
from repository import LogoRepository
from services import LLMService
from dependencies import Clients

logger = logging.getLogger(__name__)


def _retry_count(ctx) -> int:
    value = ctx.get("retry", ctx.get("job_try", ctx.get("job_try_count", 0))) if hasattr(ctx, "get") else 0
    try:
        return int(value or 0)
    except Exception:
        return 0


async def _handle_permanent_failure(ctx, user_id: str, error: Exception, queue_name: str, brand: str):
    redis = ctx.get("redis") if hasattr(ctx, "get") else None
    job_id = ctx.get("job_id") if hasattr(ctx, "get") else None
    retry_count = _retry_count(ctx)
    max_tries = WorkerSettings.max_tries

    if retry_count + 1 >= max_tries and redis and job_id:
        entry = json.dumps(
            {
                "job_id": job_id,
                "brand": brand,
                "user_id": user_id,
                "error": str(error),
                "tries": retry_count + 1,
                "failed_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        await redis.lpush(queue_name, entry)
        await redis.ltrim(queue_name, 0, 999)
        dlq_jobs_total.labels(queue=queue_name, generator="gpt-image-2-2026-04-21").inc()
        logger.error(
            f"[OpenAI Image Worker] Job {job_id} permanently failed after {retry_count + 1} attempt(s)."
        )
        await redis.publish(
            f"job:complete:{job_id}",
            json.dumps({"status": "failed", "error": str(error), "user_id": user_id}),
        )


def _is_final_attempt(ctx) -> bool:
    return _retry_count(ctx) + 1 >= WorkerSettings.max_tries


async def generate_openai_image_task(ctx, user_ip: str, user_id: str, **kwargs):
    """
    Background task to generate a logo using the GPT image model.
    Uses LLMService stored in ARQ context for connection reuse.
    Publishes completion event to Redis for WebSocket subscribers.
    """
    llm = ctx.get("llm_openai_image") if hasattr(ctx, "get") else None

    if not llm:
        openai_client = Clients.get_openai_client()
        repo = LogoRepository(AsyncSessionLocal)
        llm = LLMService(None, openai_client, repository=repo)

    job_id = ctx.get("job_id")
    redis = ctx.get("redis")
    generation_requests.labels(generator="gpt-image-2-2026-04-21").inc()
    started = time.perf_counter()

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

        generation_latency.labels(generator="gpt-image-2-2026-04-21", status="success").observe(
            time.perf_counter() - started
        )
        return result

    except Exception as exc:
        logger.error(f"[OpenAI Image Worker] Generation failed: {exc}")
        errors_total.labels(error_type=type(exc).__name__, source="openai_image_worker").inc()
        job_retries_total.labels(generator="gpt-image-2-2026-04-21", source="openai_image_worker").inc()
        generation_latency.labels(generator="gpt-image-2-2026-04-21", status="failed").observe(
            time.perf_counter() - started
        )
        if _is_final_attempt(ctx):
            await _handle_permanent_failure(ctx, user_id, exc, "dlq:dalle", kwargs.get("text", ""))
            if job_id and redis:
                await redis.publish(
                    f"job:complete:{job_id}",
                    json.dumps({"status": "failed", "error": str(exc), "user_id": user_id}),
                )
        raise


async def startup(ctx):
    logger.info("[OpenAI Image Worker] Starting up...")
    openai_client = Clients.get_openai_client()
    repo = LogoRepository(AsyncSessionLocal)
    ctx["llm_openai_image"] = LLMService(None, openai_client, repository=repo)
    worker_max_jobs.labels(queue="openai_image_queue").set(WorkerSettings.max_jobs)


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
    max_tries = int(os.getenv("DALLE_WORKER_MAX_TRIES", "3"))
    job_timeout = int(os.getenv("DALLE_WORKER_TIMEOUT", "100"))
    max_jobs = int(os.getenv("DALLE_WORKER_MAX_JOBS", "5"))

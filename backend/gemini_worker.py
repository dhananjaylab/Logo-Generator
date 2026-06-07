import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from arq import worker
from google import genai

from config import REDIS_URL, REDIS_SETTINGS
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
        dlq_jobs_total.labels(queue=queue_name, generator="gemini").inc()
        logger.error(
            f"[Gemini Worker] Job {job_id} permanently failed after {retry_count + 1} attempt(s)."
        )
        await redis.publish(
            f"job:complete:{job_id}",
            json.dumps({"status": "failed", "error": str(error), "user_id": user_id}),
        )


def _is_final_attempt(ctx) -> bool:
    return _retry_count(ctx) + 1 >= WorkerSettings.max_tries

async def generate_gemini_task(ctx, user_ip: str, user_id: str, **kwargs):
    """
    Background task to generate a logo using Gemini.
    Uses LLMService stored in ARQ context for connection reuse.
    Publishes completion event to Redis for WebSocket subscribers.
    """
    # Try to get LLMService from context (reused), fallback to create new one
    llm = ctx.get("llm_gemini") if hasattr(ctx, "get") else None
    
    if not llm:
        gemini_client = Clients.get_gemini_client()
        repo = LogoRepository(AsyncSessionLocal)
        llm = LLMService(gemini_client, None, repository=repo)
    
    job_id = ctx.get("job_id")
    redis = ctx.get("redis")
    generation_requests.labels(generator="gemini").inc()
    started = time.perf_counter()

    logger.info(f"[Gemini Worker] Starting generation for '{kwargs.get('text')}' (job={job_id})")
    
    try:
        path, prompt = await llm.generate_logo_with_gemini(user_ip=user_ip, user_id=user_id, **kwargs)
        result = {"result": [path], "generator": "gemini", "prompt": prompt, "status": "completed"}

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

        generation_latency.labels(generator="gemini", status="success").observe(time.perf_counter() - started)
        return result

    except Exception as exc:
        logger.error(f"[Gemini Worker] Generation failed: {exc}")
        errors_total.labels(error_type=type(exc).__name__, source="gemini_worker").inc()
        job_retries_total.labels(generator="gemini", source="gemini_worker").inc()
        generation_latency.labels(generator="gemini", status="failed").observe(time.perf_counter() - started)
        if _is_final_attempt(ctx):
            await _handle_permanent_failure(ctx, user_id, exc, "dlq:gemini", kwargs.get("text", ""))
            if job_id and redis:
                await redis.publish(
                    f"job:complete:{job_id}",
                    json.dumps({"status": "failed", "error": str(exc), "user_id": user_id}),
                )
        raise

async def startup(ctx):
    logger.info("[Gemini Worker] Starting up...")
    gemini_client = Clients.get_gemini_client()
    # Store LLMService in context for reuse across tasks
    repo = LogoRepository(AsyncSessionLocal)
    ctx["llm_gemini"] = LLMService(gemini_client, None, repository=repo)
    worker_max_jobs.labels(queue="gemini_queue").set(WorkerSettings.max_jobs)

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
    max_tries = int(os.getenv("GEMINI_WORKER_MAX_TRIES", "3"))
    job_timeout = int(os.getenv("GEMINI_WORKER_TIMEOUT", "60"))
    max_jobs = int(os.getenv("GEMINI_WORKER_MAX_JOBS", "10"))

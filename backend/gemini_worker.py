import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone

from google import genai

from config import REDIS_URL, REDIS_SETTINGS
from database import AsyncSessionLocal
from prom_metrics import (
    generation_requests, generation_latency, errors_total,
    job_retries_total, dlq_jobs_total, worker_max_jobs,
    generation_cost_usd_total,   # P3.2
)
from repository import LogoRepository, AuditRepository   # P3.4
from services import LLMService
from dependencies import Clients
from models import LogoGenerationParams   # P3.6
from circuit_breaker import close_all as close_circuit_breakers

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

    P3.6: kwargs are wrapped into a LogoGenerationParams dataclass and passed
    as one object — identical interface to the OpenAI worker, and the same
    object is what gets forwarded unchanged if Gemini quota is exhausted and
    LLMService falls back to the OpenAI path internally.
    """
    llm = ctx.get("llm_gemini") if hasattr(ctx, "get") else None
    if not llm:
        gemini_client = Clients.get_gemini_client()
        repo = LogoRepository(AsyncSessionLocal)
        llm = LLMService(gemini_client, None, repository=repo)

    audit = ctx.get("audit_repo") if hasattr(ctx, "get") else None
    if not audit:
        audit = AuditRepository(AsyncSessionLocal)

    job_id = ctx.get("job_id")
    redis  = ctx.get("redis")
    generation_requests.labels(generator="gemini").inc()
    started = time.perf_counter()

    params = LogoGenerationParams(**kwargs)

    logger.info(f"[Gemini Worker] Starting generation for '{params.text}' (job={job_id})")

    try:
        path, prompt, cost = await llm.generate_logo_with_gemini(
            params, user_id=user_id, user_ip=user_ip
        )
        # NOTE: if Gemini quota was exhausted, LLMService transparently fell
        # back to GPT image generation internally — `result["generator"]`
        # below would still read "gemini" since that's the queue this task
        # ran on, but the saved DB row's `generator` column (set inside
        # generate_logo_with_openai_image when the fallback fires) correctly
        # reflects "gpt-image-2-2026-04-21". This mirrors prior behaviour.
        result = {"result": [path], "generator": "gemini", "prompt": prompt, "status": "completed"}

        generation_cost_usd_total.labels(generator="gemini").inc(cost)

        if job_id and redis:
            event = json.dumps({
                "status": "completed",
                "user_id": user_id,
                "result": {
                    "result":    result["result"],
                    "generator": result["generator"],
                    "prompt":    result["prompt"],
                    "brand":     params.text,
                    "style":     params.style,
                    "palette":   params.palette,
                },
            })
            await redis.publish(f"job:complete:{job_id}", event)

        generation_latency.labels(generator="gemini", status="success").observe(
            time.perf_counter() - started
        )

        await audit.log(
            event_type="generation_completed",
            user_id=user_id,
            ip_hash=user_ip,
            brand_name=params.text,
            generator="gemini",
            cost_usd=cost,
            detail=f"job_id={job_id}",
        )

        return result

    except Exception as exc:
        logger.error(f"[Gemini Worker] Generation failed: {exc}")
        errors_total.labels(error_type=type(exc).__name__, source="gemini_worker").inc()
        job_retries_total.labels(generator="gemini", source="gemini_worker").inc()
        generation_latency.labels(generator="gemini", status="failed").observe(
            time.perf_counter() - started
        )
        if _is_final_attempt(ctx):
            await _handle_permanent_failure(ctx, user_id, exc, "dlq:gemini", params.text)
            if job_id and redis:
                await redis.publish(
                    f"job:complete:{job_id}",
                    json.dumps({"status": "failed", "error": str(exc), "user_id": user_id}),
                )
            await audit.log(
                event_type="generation_failed",
                user_id=user_id,
                ip_hash=user_ip,
                brand_name=params.text,
                generator="gemini",
                detail=f"job_id={job_id} error={str(exc)[:300]}",
            )
        raise


async def startup(ctx):
    logger.info("[Gemini Worker] Starting up...")
    gemini_client = Clients.get_gemini_client()
    repo = LogoRepository(AsyncSessionLocal)
    ctx["llm_gemini"] = LLMService(gemini_client, None, repository=repo)
    ctx["audit_repo"] = AuditRepository(AsyncSessionLocal)
    worker_max_jobs.labels(queue="gemini_queue").set(WorkerSettings.max_jobs)


async def shutdown(ctx):
    logger.info("[Gemini Worker] Shutting down...")
    await close_circuit_breakers()
    logger.info("[Gemini Worker] Circuit breaker connections closed")


class WorkerSettings:
    """ARQ worker settings for Gemini."""
    functions   = [generate_gemini_task]
    redis_settings = REDIS_SETTINGS
    queue_name  = "gemini_queue"
    on_startup  = startup
    on_shutdown = shutdown
    result_ttl  = 172_800   # 2 days
    max_tries   = int(os.getenv("GEMINI_WORKER_MAX_TRIES", "3"))
    job_timeout = int(os.getenv("GEMINI_WORKER_TIMEOUT", "60"))
    max_jobs    = int(os.getenv("GEMINI_WORKER_MAX_JOBS", "10"))

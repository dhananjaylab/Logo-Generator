import asyncio
import json
import os
import secrets
import logging
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, Depends, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from sqlalchemy import select, desc, text
from google import genai
from openai import AsyncOpenAI

from models import (
    LogoGenerationRequest,
    LogoGenerationResponse,
    HealthResponse,
    LogoJobResponse,
    JobStatusResponse,
    HistoryEntryResponse,
    WsTicketResponse,
)
from database import get_db, LogoGeneration
from dependencies import get_gemini_client, get_openai_client, Clients, validate_clerk_token
from config import LOGO_STYLES, COLOR_PALETTES, SUPPORTED_GENERATORS
from limiter import limiter
from prom_metrics import queue_depth, component_ready
from utils import anonymise_ip   # P1.4

router = APIRouter(prefix="/api/v1", tags=["logo"])
logger = logging.getLogger(__name__)

# Job result TTL matches worker result_ttl (2 days in seconds).
# The queue-mapping key must live at least as long as the result so status
# lookups never fail while a result is still retrievable.
_JOB_QUEUE_KEY_TTL = 172_800   # 2 days

# Per-user daily quota; override via USER_DAILY_QUOTA env var.
_USER_DAILY_QUOTA = int(os.getenv("USER_DAILY_QUOTA", "50"))


async def get_redis(request: Request):
    """Dependency: return ARQ redis pool or raise 503 if unavailable."""
    redis = getattr(request.app.state, "redis", None)
    if redis is None:
        raise HTTPException(503, "Queue service temporarily unavailable")
    return redis


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
async def health_check(redis=Depends(get_redis), db=Depends(get_db)):
    health: dict = {
        "status": "ok",
        "gemini_ready": Clients.is_gemini_ready(),
        "openai_ready": Clients.is_openai_ready(),
        "redis_ready": False,
        "db_ready": False,
    }
    if not health["gemini_ready"] or not health["openai_ready"]:
        health["status"] = "degraded"

    component_ready.labels(component="api").set(1)
    component_ready.labels(component="gemini").set(1 if health["gemini_ready"] else 0)
    component_ready.labels(component="openai").set(1 if health["openai_ready"] else 0)

    try:
        await redis.ping()
        health["redis_ready"] = True
        component_ready.labels(component="redis").set(1)
    except Exception as exc:
        health["status"] = "degraded"
        component_ready.labels(component="redis").set(0)
        logger.warning(f"[Health] Redis ping failed: {exc}")

    if db:
        try:
            await db.execute(text("SELECT 1"))
            health["db_ready"] = True
            component_ready.labels(component="db").set(1)
        except Exception as exc:
            health["status"] = "degraded"
            component_ready.labels(component="db").set(0)
            logger.warning(f"[Health] DB probe failed: {exc}")

    return JSONResponse(content=health, status_code=200 if health["status"] == "ok" else 503)


# ── Generate ──────────────────────────────────────────────────────────────────

@router.post("/generate", response_model=LogoJobResponse)
@limiter.limit(os.getenv("RATE_LIMIT_PER_MINUTE", "10/minute"))
@limiter.limit(os.getenv("RATE_LIMIT_PER_DAY", "200/day"))
async def generate_logo(
    logo_request: LogoGenerationRequest,
    request: Request,
    redis=Depends(get_redis),
    gemini_client: genai.Client = Depends(get_gemini_client),
    openai_client: AsyncOpenAI  = Depends(get_openai_client),
    user: dict = Depends(validate_clerk_token),
):
    user_id  = user.get("sub", "anonymous")
    raw_ip   = request.client.host if request.client else None
    user_ip_hash = anonymise_ip(raw_ip)   # P1.4 — hash before any storage

    # ── P2.8: Per-user daily generation quota ─────────────────────────────
    # This sits inside the authenticated endpoint so user_id is always known.
    # The key format guarantees reset at UTC midnight; a 25-hour TTL covers
    # users in UTC+14 whose "day" extends past UTC midnight.
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    quota_key = f"user_quota:{user_id}:{today}"
    try:
        daily_count = int(await redis.incr(quota_key) or 0)
        await redis.expire(quota_key, 90_000)   # 25 h — covers timezone drift
        if daily_count > _USER_DAILY_QUOTA:
            logger.warning(f"[Quota] User {user_id} exceeded daily limit ({daily_count})")
            raise HTTPException(
                429,
                f"Daily generation limit of {_USER_DAILY_QUOTA} reached. "
                "Try again after midnight UTC.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        # Redis quota check failure must not block generation — log and continue.
        logger.warning(f"[Quota] Redis quota check failed for {user_id}: {exc}")

    logger.info(f"[API] Generation #{daily_count} today for user: {user_id}")

    # ── Validate ──────────────────────────────────────────────────────────
    if logo_request.generator == "gpt-image-2-2026-04-21":
        if not openai_client:
            raise HTTPException(500, "OpenAI API client not initialised.")
    elif logo_request.generator == "gemini":
        if not gemini_client:
            raise HTTPException(500, "Gemini API client not initialised.")
    else:
        raise HTTPException(
            400, f"Invalid generator. Choose from: {', '.join(SUPPORTED_GENERATORS)}",
        )

    if logo_request.style not in LOGO_STYLES:
        raise HTTPException(400, f"Invalid style. Choose from: {', '.join(LOGO_STYLES.keys())}")
    if logo_request.palette not in COLOR_PALETTES:
        raise HTTPException(400, f"Invalid palette. Choose from: {', '.join(COLOR_PALETTES.keys())}")
    if not logo_request.text and not logo_request.description:
        raise HTTPException(400, "Provide at least a brand name or description.")

    variation_index = getattr(logo_request, "variation_index", 0) or 0

    common = dict(
        text=logo_request.text,
        description=logo_request.description or "",
        style=LOGO_STYLES.get(logo_request.style, LOGO_STYLES["minimalist"]),
        palette=COLOR_PALETTES.get(logo_request.palette, COLOR_PALETTES["monochrome"]),
        tagline=logo_request.tagline or "",
        typography=logo_request.typography or "",
        elements_to_include=logo_request.elements_to_include or "",
        elements_to_avoid=logo_request.elements_to_avoid or "",
        brand_mission=logo_request.brand_mission or "",
        variation_hint=logo_request.variation_hint or "",
        variation_index=variation_index,
    )

    queue_name = (
        "openai_image_queue"
        if logo_request.generator == "gpt-image-2-2026-04-21"
        else "gemini_queue"
    )
    function_name = (
        "generate_openai_image_task"
        if logo_request.generator == "gpt-image-2-2026-04-21"
        else "generate_gemini_task"
    )

    job = await redis.enqueue_job(
        function_name,
        user_ip=user_ip_hash,
        user_id=user_id,
        _queue_name=queue_name,
        **common,
    )

    # ── P2.2: Store job→queue mapping for O(1) status lookup ─────────────
    # Without this, get_job_status() scans three queues sequentially (3 Redis
    # round-trips). With this key, it resolves in one GET. The TTL matches the
    # worker result_ttl so the key is always present while the result exists.
    await redis.setex(f"job_queue:{job.job_id}", _JOB_QUEUE_KEY_TTL, queue_name)

    try:
        depth = await redis.llen(queue_name)
        queue_depth.labels(queue=queue_name).set(depth)
    except Exception as exc:
        logger.warning(f"[Queue] Failed to refresh depth for {queue_name}: {exc}")

    return {"job_id": job.job_id, "status": "enqueued"}


# ── Job Status ────────────────────────────────────────────────────────────────

@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    redis=Depends(get_redis),
    user: dict = Depends(validate_clerk_token),
):
    """
    Check the status of a background job.

    P2.2: Uses the job_queue:{job_id} Redis key set at enqueue time to
    resolve which queue the job is on in a single GET, rather than probing
    three queues sequentially (3 round-trips → 1 round-trip).
    Falls back to the sequential scan for jobs enqueued before this change.
    """
    user_id = user.get("sub", "anonymous")
    from arq.jobs import Job

    try:
        # ── Fast path: O(1) queue lookup via stored mapping ───────────────
        stored_queue = await redis.get(f"job_queue:{job_id}")
        if stored_queue:
            queue_name = (
                stored_queue.decode() if isinstance(stored_queue, bytes) else stored_queue
            )
            job_instance = Job(job_id, redis, _queue_name=queue_name)
            status = await job_instance.status()
            if status == "not_found":
                # Mapping exists but job gone — clean up and fall through
                await redis.delete(f"job_queue:{job_id}")
                job_instance = None
        else:
            job_instance = None
            status = "not_found"

        # ── Slow path: legacy sequential scan (pre-P2.2 jobs) ────────────
        if job_instance is None or status == "not_found":
            for q in ["openai_image_queue", "gemini_queue", "arq:queue"]:
                temp = Job(job_id, redis, _queue_name=q)
                status = await temp.status()
                if status != "not_found":
                    job_instance = temp
                    break

        if not job_instance or status == "not_found":
            raise HTTPException(404, f"Job {job_id} not found")

        result_info = await job_instance.result_info()

        # Ownership check
        job_user_id = result_info.kwargs.get("user_id") if result_info else None
        if job_user_id and job_user_id != user_id and user_id != "developer":
            logger.warning(f"[API] Ownership check failed: {job_user_id} != {user_id}")
            raise HTTPException(403, "You don't have permission to access this job")

        if status == "complete" and result_info:
            res_data = result_info.result
            if res_data.get("status") == "failed":
                return {"job_id": job_id, "status": "failed", "error": res_data.get("error")}
            return {
                "job_id": job_id,
                "status": "completed",
                "result": {
                    "result":    res_data.get("result"),
                    "generator": res_data.get("generator"),
                    "prompt":    res_data.get("prompt"),
                    "brand":     result_info.kwargs.get("text"),
                    "style":     result_info.kwargs.get("style"),
                    "palette":   result_info.kwargs.get("palette"),
                },
            }

        status_str = status.value if hasattr(status, "value") else str(status)
        return {"job_id": job_id, "status": status_str}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[API] Error fetching job status: {exc}")
        raise HTTPException(500, f"Error fetching job status: {exc}")


# ── History ───────────────────────────────────────────────────────────────────

@router.get("/history", response_model=List[HistoryEntryResponse])
async def get_generation_history(
    limit: int = 20,
    db=Depends(get_db),
    user: dict = Depends(validate_clerk_token),
):
    """P1.6: response_model=HistoryEntryResponse excludes ip_hash and user_id."""
    user_id = user.get("sub", "anonymous")
    if not db:
        return []
    try:
        stmt = (
            select(LogoGeneration)
            .where(LogoGeneration.user_id == user_id)
            .order_by(desc(LogoGeneration.created_at))
            .limit(max(1, min(limit, 100)))
        )
        result = await db.execute(stmt)
        return result.scalars().all()
    except Exception as exc:
        logger.error(f"[DB] Failed to fetch history: {exc}")
        return []


# ── WebSocket Ticket ──────────────────────────────────────────────────────────

@router.post("/ws/ticket", response_model=WsTicketResponse)
async def create_ws_ticket(
    user: dict = Depends(validate_clerk_token),
    redis=Depends(get_redis),
):
    """P1.2: Exchange JWT for a 30-second single-use WebSocket ticket."""
    ticket  = secrets.token_urlsafe(32)
    user_id = user.get("sub", "anonymous")
    await redis.setex(f"ws_ticket:{ticket}", 30, user_id)
    return {"ticket": ticket, "expires_in": 30}


# ── Admin / DLQ ───────────────────────────────────────────────────────────────

@router.get("/admin/dlq")
async def inspect_dlq(
    queue: str = "dalle",
    limit: int = 20,
    redis=Depends(get_redis),
    user: dict = Depends(validate_clerk_token),
):
    """List permanently failed jobs from a dead-letter queue."""
    _ = user
    queue_name = queue if queue in {"dalle", "gemini"} else "dalle"
    limit = max(1, min(limit, 100))
    items = await redis.lrange(f"dlq:{queue_name}", 0, limit - 1)
    return [
        json.loads(item.decode("utf-8") if isinstance(item, bytes) else item)
        for item in items
    ]


# ── WebSocket Progress ────────────────────────────────────────────────────────

@router.websocket("/ws/progress/{job_id}")
async def ws_progress(websocket: WebSocket, job_id: str):
    """P1.2: Ticket-based auth. P2.2: uses job_queue mapping for fast lookup."""
    from arq.jobs import Job

    redis = getattr(websocket.app.state, "redis", None)
    if redis is None:
        await websocket.close(code=1011, reason="Service temporarily unavailable")
        return

    # ── Ticket validation (P1.2) ──────────────────────────────────────────
    raw_ticket = websocket.query_params.get("ticket", "")
    if not raw_ticket:
        await websocket.close(code=1008, reason="Missing authentication ticket")
        return

    user_id_bytes = await redis.getdel(f"ws_ticket:{raw_ticket}")
    if not user_id_bytes:
        await websocket.close(code=1008, reason="Invalid or expired ticket")
        return

    user_id = user_id_bytes.decode() if isinstance(user_id_bytes, bytes) else user_id_bytes

    await websocket.accept()
    channel = f"job:complete:{job_id}"
    pubsub  = None

    try:
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel)

        # Check if job already completed while subscribing
        queues = ["openai_image_queue", "gemini_queue", "arq:queue"]

        # P2.2: fast path — check queue mapping first
        stored_queue = await redis.get(f"job_queue:{job_id}")
        if stored_queue:
            q_name = stored_queue.decode() if isinstance(stored_queue, bytes) else stored_queue
            queues = [q_name] + [q for q in queues if q != q_name]

        for q in queues:
            job_obj    = Job(job_id, redis, _queue_name=q)
            status     = await job_obj.status()
            status_str = status.value if hasattr(status, "value") else str(status)
            if status_str == "complete":
                info = await job_obj.result_info()
                job_owner = info.kwargs.get("user_id") if info else None
                if job_owner and job_owner != user_id and user_id != "developer":
                    await websocket.send_json({"status": "failed", "error": "Unauthorized"})
                    return
                if info and info.result:
                    res = info.result
                    if res.get("status") == "failed":
                        await websocket.send_json({"status": "failed", "error": res.get("error")})
                    else:
                        await websocket.send_json({
                            "status": "completed",
                            "result": {
                                "result":    res.get("result"),
                                "generator": res.get("generator"),
                                "prompt":    res.get("prompt"),
                                "brand":     info.kwargs.get("text"),
                                "style":     info.kwargs.get("style"),
                                "palette":   info.kwargs.get("palette"),
                            },
                        })
                return

        await websocket.send_json({"status": "queued"})

        try:
            async with asyncio.timeout(300):
                async for message in pubsub.listen():
                    if message["type"] != "message":
                        continue
                    data = json.loads(message["data"])
                    published_owner = data.pop("user_id", None)
                    if published_owner and published_owner != user_id and user_id != "developer":
                        await websocket.send_json({"status": "failed", "error": "Unauthorized"})
                        break
                    await websocket.send_json(data)
                    break
        except asyncio.TimeoutError:
            await websocket.send_json({"status": "failed", "error": "Job timed out"})

    except WebSocketDisconnect:
        logger.info(f"[WS] Client disconnected for job {job_id}")
    except Exception as exc:
        logger.error(f"[WS] Unexpected error for job {job_id}: {exc}")
        try:
            await websocket.send_json({"status": "error", "error": str(exc)})
        except Exception:
            pass
    finally:
        if pubsub:
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.close()
            except Exception:
                pass
        try:
            await websocket.close()
        except Exception:
            pass

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
    DataDeletionResponse,
)
from database import get_db, LogoGeneration, AsyncSessionLocal
from dependencies import get_gemini_client, get_openai_client, Clients, validate_clerk_token
from config import LOGO_STYLES, COLOR_PALETTES, SUPPORTED_GENERATORS, R2_BUCKET_NAME
from limiter import limiter
from prom_metrics import queue_depth, component_ready, moderation_blocked_total
from utils import anonymise_ip            # P1.4
from moderation import moderate_text       # P3.1 — HIGH-05 fix
from repository import LogoRepository, AuditRepository   # P3.4
from services import get_r2_client, r2_key_from_url       # P3.3

router = APIRouter(prefix="/api/v1", tags=["logo"])
logger = logging.getLogger(__name__)

# Job result TTL matches worker result_ttl (2 days in seconds). The
# queue-mapping key must live at least as long as the result.
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
    user_id      = user.get("sub", "anonymous")
    raw_ip       = request.client.host if request.client else None
    user_ip_hash = anonymise_ip(raw_ip)   # P1.4 — hash before any storage

    audit = AuditRepository(AsyncSessionLocal)   # P3.4

    # ── P2.8: Per-user daily generation quota ─────────────────────────────
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    quota_key = f"user_quota:{user_id}:{today}"
    daily_count = 0
    try:
        daily_count = int(await redis.incr(quota_key) or 0)
        await redis.expire(quota_key, 90_000)   # 25h — covers timezone drift
        if daily_count > _USER_DAILY_QUOTA:
            logger.warning(f"[Quota] User exceeded daily limit ({daily_count})")
            raise HTTPException(
                429,
                f"Daily generation limit of {_USER_DAILY_QUOTA} reached. "
                "Try again after midnight UTC.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning(f"[Quota] Redis quota check failed: {exc}")

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

    # ── P3.1 (HIGH-05): Content moderation on all user-controlled free text ──
    # Moderates the concatenation of every free-text field the user controls,
    # BEFORE a job is enqueued. This blocks adversarial prompt injection
    # instantly, with zero provider cost incurred, rather than letting a
    # flagged request consume a worker slot and fail later.
    combined_text = " ".join(filter(None, [
        logo_request.text,
        logo_request.description,
        logo_request.tagline,
        logo_request.brand_mission,
        logo_request.elements_to_include,
        logo_request.elements_to_avoid,
        logo_request.variation_hint,
    ]))
    moderation = await moderate_text(combined_text)

    if moderation.flagged:
        for category in (moderation.categories or ["unspecified"]):
            moderation_blocked_total.labels(category=category).inc()

        await audit.log(
            event_type="generation_blocked",
            user_id=user_id,
            ip_hash=user_ip_hash,
            brand_name=logo_request.text,
            generator=logo_request.generator,
            moderation_flagged=True,
            moderation_categories=",".join(moderation.categories),
        )
        raise HTTPException(
            400,
            "Your request was flagged by our content safety system "
            f"({', '.join(moderation.categories) or 'policy violation'}). "
            "Please revise your brand description and try again.",
        )

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

    # P2.2: job→queue mapping for O(1) status lookup
    await redis.setex(f"job_queue:{job.job_id}", _JOB_QUEUE_KEY_TTL, queue_name)

    # P3.4: audit the accepted request (moderation already passed at this point)
    await audit.log(
        event_type="generation_requested",
        user_id=user_id,
        ip_hash=user_ip_hash,
        brand_name=logo_request.text,
        generator=logo_request.generator,
        moderation_flagged=False,
        detail=f"job_id={job.job_id} daily_count={daily_count}",
    )

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
    resolve which queue the job is on in a single GET, falling back to the
    sequential 3-queue scan for jobs enqueued before this change.
    """
    user_id = user.get("sub", "anonymous")
    from arq.jobs import Job

    try:
        stored_queue = await redis.get(f"job_queue:{job_id}")
        if stored_queue:
            queue_name = stored_queue.decode() if isinstance(stored_queue, bytes) else stored_queue
            job_instance = Job(job_id, redis, _queue_name=queue_name)
            status = await job_instance.status()
            if status == "not_found":
                await redis.delete(f"job_queue:{job_id}")
                job_instance = None
        else:
            job_instance = None
            status = "not_found"

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

        job_user_id = result_info.kwargs.get("user_id") if result_info else None
        if job_user_id and job_user_id != user_id and user_id != "developer":
            logger.warning("[API] Job ownership check failed")
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
    """P1.6: response_model=HistoryEntryResponse excludes ip_hash/user_id/cost_usd."""
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


# ── GDPR / CCPA Data Deletion ──────────────────────────────────────────────────

@router.delete("/me/data", response_model=DataDeletionResponse)
async def delete_my_data(user: dict = Depends(validate_clerk_token)):
    """
    P3.3 — GDPR Article 17 / CCPA right-to-deletion endpoint.

    Hard-deletes every LogoGeneration row owned by the authenticated user
    and best-effort removes the corresponding image objects from R2.
    AuditLog rows are anonymised (user_id → 'deleted-user' sentinel) rather
    than deleted — see AuditRepository.anonymise_user() for the rationale.
    """
    user_id = user.get("sub", "anonymous")
    if user_id == "anonymous":
        raise HTTPException(400, "Cannot delete data for an unauthenticated session.")

    repo  = LogoRepository(AsyncSessionLocal)
    audit = AuditRepository(AsyncSessionLocal)

    deleted_urls = await repo.delete_for_user(user_id)

    deleted_images = 0
    client = get_r2_client()
    if client and R2_BUCKET_NAME:
        for url in deleted_urls:
            key = r2_key_from_url(url)
            if not key:
                continue
            try:
                client.delete_object(Bucket=R2_BUCKET_NAME, Key=key)
                deleted_images += 1
            except Exception as exc:
                logger.warning(f"[GDPR] Failed to delete R2 object {key}: {exc}")

    await audit.anonymise_user(user_id)
    await audit.log(
        event_type="data_deletion_requested",
        user_id="deleted-user",
        detail=f"deleted_generations={len(deleted_urls)} deleted_images={deleted_images}",
    )

    logger.info(
        f"[GDPR] Deleted {len(deleted_urls)} generation(s), "
        f"{deleted_images} R2 object(s) for a user-initiated erasure request"
    )

    return {
        "deleted_generations": len(deleted_urls),
        "deleted_images": deleted_images,
        "message": "Your generation history and associated images have been permanently deleted.",
    }


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

        queues = ["openai_image_queue", "gemini_queue", "arq:queue"]
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

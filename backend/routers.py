import asyncio
import json
import os
import logging
from typing import List, Optional
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
    JobStatusResponse
)
from services import LLMService
from database import get_db, LogoGeneration
from dependencies import get_gemini_client, get_openai_client, Clients, validate_clerk_token
from config import LOGO_STYLES, COLOR_PALETTES, SUPPORTED_GENERATORS
from limiter import limiter

router = APIRouter(prefix="/api/v1", tags=["logo"])
logger = logging.getLogger(__name__)

_ROUTE_TIMEOUT = 90   # hard ceiling for the entire /generate request (s)


async def get_redis(request: Request):
    """Dependency to get ARQ redis pool from app state (created at startup)"""
    return request.app.state.redis


@router.get("/health", response_model=HealthResponse)
async def health_check(
    redis=Depends(get_redis),
    db=Depends(get_db),
):
    health: dict = {
        "status": "ok",
        "gemini_ready": Clients.is_gemini_ready(),
        "openai_ready": Clients.is_openai_ready(),
        "redis_ready": False,
        "db_ready": False,
    }

    if not health["gemini_ready"] or not health["openai_ready"]:
        health["status"] = "degraded"

    try:
        await redis.ping()
        health["redis_ready"] = True
    except Exception as exc:
        health["status"] = "degraded"
        logger.warning(f"[Health] Redis ping failed: {exc}")

    if db:
        try:
            await db.execute(text("SELECT 1"))
            health["db_ready"] = True
        except Exception as exc:
            health["status"] = "degraded"
            logger.warning(f"[Health] DB probe failed: {exc}")

    status_code = 200 if health["status"] == "ok" else 503
    return JSONResponse(content=health, status_code=status_code)


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
    user_ip = request.client.host if request.client else None
    user_id = user.get("sub", "anonymous")
    print(f"[API] Logo request from user: {user_id} (IP: {user_ip})")
    # ── Validate ──────────────────────────────────────────────────────────
    if logo_request.generator == "gpt-image-2-2026-04-21":
        if not openai_client:
            raise HTTPException(500, "OpenAI API client not initialised.")
    elif logo_request.generator == "gemini":
        if not gemini_client:
            raise HTTPException(500, "Gemini API client not initialised.")
    else:
        raise HTTPException(
            400,
            f"Invalid generator. Choose from: {', '.join(SUPPORTED_GENERATORS)}",
        )

    if logo_request.style not in LOGO_STYLES:
        raise HTTPException(400, f"Invalid style. Choose from: {', '.join(LOGO_STYLES.keys())}")
    if logo_request.palette not in COLOR_PALETTES:
        raise HTTPException(400, f"Invalid palette. Choose from: {', '.join(COLOR_PALETTES.keys())}")
    if not logo_request.text and not logo_request.description:
        raise HTTPException(400, "Provide at least a brand name or description.")

    # Extract variation_index (0 = first generation, >0 = regeneration)
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

    # Enqueue the job to the specific queue
    queue_name = "openai_image_queue" if logo_request.generator == "gpt-image-2-2026-04-21" else "gemini_queue"
    function_name = "generate_openai_image_task" if logo_request.generator == "gpt-image-2-2026-04-21" else "generate_gemini_task"
    
    job = await redis.enqueue_job(
        function_name,
        user_ip=user_ip,
        user_id=user_id,
        _queue_name=queue_name,
        **common
    )

    return {
        "job_id": job.job_id,
        "status": "enqueued"
    }


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str, 
    redis=Depends(get_redis),
    user: dict = Depends(validate_clerk_token),
):
    """
    Check the status of a background job (requires authentication).
    Verifies job ownership to prevent enumeration attacks.
    """
    user_id = user.get("sub", "anonymous")
    print(f"[API] Job status request from user: {user_id}, job: {job_id}")
    
    from arq.jobs import Job
    
    # Check all specialized queues to find where the job is currently living
    queues_to_search = ["openai_image_queue", "gemini_queue", "arq:queue"]
    job_instance = None
    status = "not_found"
    
    try:
        for q in queues_to_search:
            temp_job = Job(job_id, redis, _queue_name=q)
            status = await temp_job.status()
            if status != "not_found":
                job_instance = temp_job
                break
        
        if not job_instance or status == "not_found":
            raise HTTPException(404, f"Job {job_id} not found")

        result_info = await job_instance.result_info()
        
        # ── Job Ownership Check ─────────────────────────────────────────────
        # Verify the job belongs to the requesting user (prevent enumeration)
        job_user_id = result_info.kwargs.get("user_id") if result_info else None
        if job_user_id and job_user_id != user_id and user_id != "developer":
            print(f"[API] Job ownership check failed: {job_user_id} != {user_id}")
            raise HTTPException(403, "You don't have permission to access this job")
        
        if status == "complete" and result_info:
            # Map the result back to LogoGenerationResponse
            res_data = result_info.result
            if res_data.get("status") == "failed":
                return {
                    "job_id": job_id,
                    "status": "failed",
                    "error": res_data.get("error")
                }
            
            # Reconstruct the response
            return {
                "job_id": job_id,
                "status": "completed",
                "result": {
                    "result": res_data.get("result"),
                    "generator": res_data.get("generator"),
                    "prompt": res_data.get("prompt"),
                    "brand": result_info.kwargs.get("text"),
                    "style": result_info.kwargs.get("style"),
                    "palette": result_info.kwargs.get("palette"),
                }
            }
        else:
            # Handle JobStatus enum or string
            status_str = status.value if hasattr(status, "value") else str(status)
            return {
                "job_id": job_id,
                "status": status_str
            }
    except HTTPException:
        # Re-raise HTTPExceptions to avoid them being caught by the generic block
        raise
    except Exception as e:
        print(f"[API] Error fetching job status: {e}")
        raise HTTPException(500, f"Error fetching job status: {e}")


@router.get("/history")
async def get_generation_history(
    limit: int = 20,
    db = Depends(get_db),
    user: dict = Depends(validate_clerk_token),
):
    """Retrieve the latest logo generation history (requires authentication)."""
    user_id = user.get("sub", "anonymous")
    print(f"[API] History request from user: {user_id}")
    
    if not db:
        return []
        
    try:
        # Filter by user_id to prevent enumeration attacks
        # Only return the user's own generations
        stmt = (
            select(LogoGeneration)
            .where(LogoGeneration.user_id == user_id)  # Job ownership check
            .order_by(desc(LogoGeneration.created_at))
            .limit(limit)
        )
        result = await db.execute(stmt)
        history = result.scalars().all()
        return history
    except Exception as e:
        print(f"[DB] ⚠ Failed to fetch history: {e}")
        return []


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
    decoded = []
    for item in items:
        if isinstance(item, bytes):
            item = item.decode("utf-8")
        decoded.append(json.loads(item))
    return decoded

@router.websocket("/ws/progress/{job_id}")
async def ws_progress(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint. Uses Redis Pub/Sub push instead of polling.
    Scales to thousands of concurrent connections.
    Token passed as query param: ?token=<value>
    """
    from arq.jobs import Job
    from urllib.parse import unquote
    from dependencies import validate_token_string
    import json

    # ── Auth ───────────────────────────────────────────────────────────────
    raw_token = websocket.query_params.get("token")
    if raw_token:
        raw_token = unquote(raw_token)
    try:
        user = await validate_token_string(raw_token)
        user_id = user.get("sub", "anonymous")
    except HTTPException as exc:
        await websocket.close(code=1008, reason=exc.detail)
        return

    await websocket.accept()
    redis = websocket.app.state.redis
    channel = f"job:complete:{job_id}"
    pubsub = None

    try:
        # Subscribe FIRST — before checking job status — to eliminate the
        # race condition where the job completes between our check and subscribe.
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel)

        # Check if job already completed while we were subscribing.
        queues = ["openai_image_queue", "gemini_queue", "arq:queue"]
        for q in queues:
            job_obj = Job(job_id, redis, _queue_name=q)
            status = await job_obj.status()
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
                                "result": res.get("result"),
                                "generator": res.get("generator"),
                                "prompt": res.get("prompt"),
                                "brand": info.kwargs.get("text"),
                                "style": info.kwargs.get("style"),
                                "palette": info.kwargs.get("palette"),
                            }
                        })
                return  # done — already had the result

        # Job is still pending — tell the client and wait for the pub/sub push.
        await websocket.send_json({"status": "queued"})

        try:
            async with asyncio.timeout(300):  # 5-minute hard ceiling
                async for message in pubsub.listen():
                    if message["type"] != "message":
                        continue
                    data = json.loads(message["data"])

                    # Ownership check on streamed result
                    published_owner = data.pop("user_id", None)
                    if published_owner and published_owner != user_id and user_id != "developer":
                        await websocket.send_json({"status": "failed", "error": "Unauthorized"})
                        break

                    await websocket.send_json(data)
                    break  # single-shot — one event per job

        except asyncio.TimeoutError:
            await websocket.send_json({"status": "failed", "error": "Job timed out waiting for result"})

    except WebSocketDisconnect:
        logger.info(f"[WS] Client disconnected for job {job_id}")
    except Exception as e:
        logger.error(f"[WS] Unexpected error for job {job_id}: {e}")
        try:
            await websocket.send_json({"status": "error", "error": str(e)})
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

import asyncio
import os
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Request, WebSocket, WebSocketDisconnect
from sqlalchemy import select, desc
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

router = APIRouter(prefix="/api", tags=["logo"])

_ROUTE_TIMEOUT = 90   # hard ceiling for the entire /generate request (s)


async def get_redis(request: Request):
    """Dependency to get ARQ redis pool from app state (created at startup)"""
    return request.app.state.redis


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return {
        "status": "ok",
        "gemini_ready": Clients.is_gemini_ready(),
        "openai_ready": Clients.is_openai_ready(),
    }


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
    if logo_request.generator == "dalle-3":
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
    queue_name = "dalle_queue" if logo_request.generator == "dalle-3" else "gemini_queue"
    function_name = "generate_dalle_task" if logo_request.generator == "dalle-3" else "generate_gemini_task"
    
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
async def get_job_status(job_id: str, redis=Depends(get_redis)):
    """Check the status of a background job across all specialized queues."""
    from arq.jobs import Job
    
    # We check all specialized queues to find where the job is currently living
    queues_to_search = ["dalle_queue", "gemini_queue", "arq:queue"]
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
    db = Depends(get_db)
):
    """Retrieve the latest logo generation history."""
    if not db:
        return []
        
    try:
        stmt = select(LogoGeneration).order_by(desc(LogoGeneration.created_at)).limit(limit)
        result = await db.execute(stmt)
        history = result.scalars().all()
        return history
    except Exception as e:
        print(f"[DB] ⚠ Failed to fetch history: {e}")
        return []

@router.websocket("/ws/progress/{job_id}")
async def ws_progress(websocket: WebSocket, job_id: str):
    """WebSocket endpoint to push real-time progress for a job."""
    await websocket.accept()
    from arq.jobs import Job
    import asyncio
    
    # Get redis pool from app state (created at startup)
    redis = websocket.app.state.redis
    queues = ["dalle_queue", "gemini_queue", "arq:queue"]
    
    try:
        while True:
            status = "not_found"
            job_instance = None
            for q in queues:
                temp_job = Job(job_id, redis, _queue_name=q)
                temp_status = await temp_job.status()
                # Handle enum string value mapping properly
                temp_status_str = temp_status.value if hasattr(temp_status, "value") else str(temp_status)
                if temp_status_str != "not_found":
                    status = temp_status_str
                    job_instance = temp_job
                    break
                    
            if not job_instance or status == "not_found":
                # Polling might hit before job is visible.
                await websocket.send_json({"status": "queued"})
                await asyncio.sleep(1)
                continue
                
            if status == "complete":
                info = await job_instance.result_info()
                if info and info.result:
                    res_data = info.result
                    if res_data.get("status") == "failed":
                         await websocket.send_json({"status": "failed", "error": res_data.get("error")})
                    else:
                        await websocket.send_json({
                            "status": "completed",
                            "result": {
                                "result": res_data.get("result"),
                                "generator": res_data.get("generator"),
                                "prompt": res_data.get("prompt"),
                                "brand": info.kwargs.get("text"),
                                "style": info.kwargs.get("style"),
                                "palette": info.kwargs.get("palette"),
                            }
                        })
                else:
                    await websocket.send_json({"status": "completed"})
                break
                
            elif status == "in_progress":
                await websocket.send_json({"status": "in_progress"})
                await asyncio.sleep(2)
            else:
                await websocket.send_json({"status": status})
                await asyncio.sleep(2)
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WS] Error: {e}")
        try:
            await websocket.close()
        except:
            pass

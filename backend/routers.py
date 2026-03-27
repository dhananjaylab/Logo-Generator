import asyncio
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy import select, desc
from google import genai
from openai import AsyncOpenAI
from arq import create_pool
from arq.connections import RedisSettings

from models import (
    LogoGenerationRequest, 
    LogoGenerationResponse, 
    HealthResponse, 
    LogoJobResponse, 
    JobStatusResponse
)
from services import LLMService
from database import get_db, LogoGeneration
from dependencies import get_gemini_client, get_openai_client, Clients
from config import LOGO_STYLES, COLOR_PALETTES, SUPPORTED_GENERATORS, REDIS_URL

router = APIRouter(prefix="/api", tags=["logo"])

_ROUTE_TIMEOUT = 90   # hard ceiling for the entire /generate request (s)


async def get_redis():
    """Dependency to get ARQ redis pool"""
    return await create_pool(RedisSettings.from_dsn(REDIS_URL))


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return {
        "status": "ok",
        "gemini_ready": Clients.is_gemini_ready(),
        "openai_ready": Clients.is_openai_ready(),
    }


@router.post("/generate", response_model=LogoJobResponse)
async def generate_logo(
    request: LogoGenerationRequest,
    fastapi_request: Request,
    redis=Depends(get_redis),
    gemini_client: genai.Client = Depends(get_gemini_client),
    openai_client: AsyncOpenAI  = Depends(get_openai_client),
):
    user_ip = fastapi_request.client.host if fastapi_request.client else None
    # ── Validate ──────────────────────────────────────────────────────────
    if request.generator == "dalle-3":
        if not openai_client:
            raise HTTPException(500, "OpenAI API client not initialised.")
    elif request.generator == "gemini":
        if not gemini_client:
            raise HTTPException(500, "Gemini API client not initialised.")
    else:
        raise HTTPException(
            400,
            f"Invalid generator. Choose from: {', '.join(SUPPORTED_GENERATORS)}",
        )

    if request.style not in LOGO_STYLES:
        raise HTTPException(400, f"Invalid style. Choose from: {', '.join(LOGO_STYLES.keys())}")
    if request.palette not in COLOR_PALETTES:
        raise HTTPException(400, f"Invalid palette. Choose from: {', '.join(COLOR_PALETTES.keys())}")
    if not request.text and not request.description:
        raise HTTPException(400, "Provide at least a brand name or description.")

    # Extract variation_index (0 = first generation, >0 = regeneration)
    variation_index = getattr(request, "variation_index", 0) or 0

    common = dict(
        text=request.text,
        description=request.description or "",
        style=LOGO_STYLES.get(request.style, LOGO_STYLES["minimalist"]),
        palette=COLOR_PALETTES.get(request.palette, COLOR_PALETTES["monochrome"]),
        tagline=request.tagline or "",
        typography=request.typography or "",
        elements_to_include=request.elements_to_include or "",
        elements_to_avoid=request.elements_to_avoid or "",
        brand_mission=request.brand_mission or "",
        variation_hint=request.variation_hint or "",
        variation_index=variation_index,
    )

    # Enqueue the job
    job = await redis.enqueue_job(
        "generate_logo_task",
        generator=request.generator,
        user_ip=user_ip,
        **common
    )

    return {
        "job_id": job.job_id,
        "status": "enqueued"
    }


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str, redis=Depends(get_redis)):
    """Check the status of a background job."""
    from arq.jobs import Job
    job_instance = Job(job_id, redis)
    
    try:
        status = await job_instance.status()
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
        elif status == "not_found":
            raise HTTPException(404, f"Job {job_id} not found")
        else:
            # Handle JobStatus enum or string
            status_str = status.value if hasattr(status, "value") else str(status)
            return {
                "job_id": job_id,
                "status": status_str
            }
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
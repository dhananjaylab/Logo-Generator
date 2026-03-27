"""
routers.py – API endpoints.

variation_index is now forwarded to services so filenames are unique per call
and the prompt builder can steer visually distinct compositions.
"""

import asyncio
from typing import List
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy import select, desc
from google import genai
from openai import AsyncOpenAI

from models import LogoGenerationRequest, LogoGenerationResponse, HealthResponse
from services import LLMService
from database import get_db, LogoGeneration
from dependencies import get_gemini_client, get_openai_client, Clients
from config import LOGO_STYLES, COLOR_PALETTES, SUPPORTED_GENERATORS

router = APIRouter(prefix="/api", tags=["logo"])

_ROUTE_TIMEOUT = 90   # hard ceiling for the entire /generate request (s)


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return {
        "status": "ok",
        "gemini_ready": Clients.is_gemini_ready(),
        "openai_ready": Clients.is_openai_ready(),
    }


@router.post("/generate", response_model=LogoGenerationResponse)
async def generate_logo(
    request: LogoGenerationRequest,
    fastapi_request: Request,
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

    llm = LLMService(gemini_client, openai_client)

    async def _run():
        if request.generator == "dalle-3":
            path, prompt = await llm.generate_logo_with_dalle(user_ip=user_ip, **common)
            return {"result": [path], "generator": "dalle-3", "prompt": prompt}
        else:
            path, prompt = await llm.generate_logo_with_gemini(user_ip=user_ip, **common)
            return {"result": [path], "generator": "gemini", "prompt": prompt}

    try:
        result = await asyncio.wait_for(_run(), timeout=_ROUTE_TIMEOUT)
    except asyncio.TimeoutError:
        raise HTTPException(
            504,
            f"Generation timed out after {_ROUTE_TIMEOUT} s. "
            "The AI model may be overloaded — please retry.",
        )
    except Exception as exc:
        raise HTTPException(500, f"Generation failed: {exc}")

    return {
        **result,
        "brand":   request.text,
        "style":   request.style,
        "palette": request.palette,
    }


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
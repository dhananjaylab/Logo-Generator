from fastapi import APIRouter, HTTPException, Depends
from google import genai
from openai import AsyncOpenAI

from models import LogoGenerationRequest, LogoGenerationResponse, HealthResponse
from services import LLMService
from dependencies import get_gemini_client, get_openai_client, Clients
from config import LOGO_STYLES, COLOR_PALETTES, SUPPORTED_GENERATORS

router = APIRouter(prefix="/api", tags=["logo"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "gemini_ready": Clients.is_gemini_ready(),
        "openai_ready": Clients.is_openai_ready(),
    }


@router.post("/generate", response_model=LogoGenerationResponse)
async def generate_logo(
    request: LogoGenerationRequest,
    gemini_client: genai.Client = Depends(get_gemini_client),
    openai_client: AsyncOpenAI = Depends(get_openai_client)
):
    """
    Generate a logo using the specified generator with advanced branding options.
    
    **Generator Modes:**
    - **dalle-3**: Uses OpenAI GPT-4 Turbo for prompt refinement + DALL-E 3 for generation
    - **gemini**: Uses Gemini 2.0 Flash for both refinement and image generation
    
    **Parameters:**
    - **text**: Brand name (required)
    - **description**: Brand description (optional)
    - **style**: Logo style (minimalist, tech, vintage, abstract, mascot, luxury)
    - **palette**: Color palette (monochrome, ocean, sunset, forest, royal, neon)
    - **generator**: Image generator (dalle-3 or gemini)
    - **tagline**: Brand tagline/slogan (optional, advanced)
    - **typography**: Typography preference (optional, advanced)
    - **elements_to_include**: Specific elements to include (optional, advanced)
    - **elements_to_avoid**: Specific elements to avoid (optional, advanced)
    - **brand_mission**: Core purpose of the brand (optional, advanced)
    """
    
    # Validate required clients based on generator choice
    if request.generator == "dalle-3":
        if not openai_client:
            raise HTTPException(status_code=500, detail="OpenAI API Client not initialized.")
    elif request.generator == "gemini":
        if not gemini_client:
            raise HTTPException(status_code=500, detail="Gemini API Client not initialized.")
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid generator. Choose from: {', '.join(SUPPORTED_GENERATORS)}"
        )

    # Validate style
    if request.style not in LOGO_STYLES:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid style. Choose from: {', '.join(LOGO_STYLES.keys())}"
        )

    # Validate palette
    if request.palette not in COLOR_PALETTES:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid palette. Choose from: {', '.join(COLOR_PALETTES.keys())}"
        )

    # At least brand name or description is required
    if not request.text and not request.description:
        raise HTTPException(
            status_code=400,
            detail="Please provide at least a brand name or description."
        )

    try:
        llm_service = LLMService(gemini_client, openai_client)

        style_prompt = LOGO_STYLES.get(request.style, LOGO_STYLES['minimalist'])
        palette_desc = COLOR_PALETTES.get(request.palette, COLOR_PALETTES['monochrome'])

        # Route to appropriate generator
        if request.generator == "dalle-3":
            # DALL-E 3 path: GPT-4 refinement + DALL-E 3 generation
            image_url, optimized_prompt = await llm_service.generate_logo_with_dalle(
                text=request.text,
                description=request.description or "",
                style=style_prompt,
                palette=palette_desc,
                tagline=request.tagline or "",
                typography=request.typography or "",
                elements_to_include=request.elements_to_include or "",
                elements_to_avoid=request.elements_to_avoid or "",
                brand_mission=request.brand_mission or ""
            )
            return {
                "result": [image_url],
                "brand": request.text,
                "style": request.style,
                "palette": request.palette,
                "prompt": optimized_prompt,
                "generator": "dalle-3"
            }
        
        else:  # gemini
            # Gemini path: Gemini-only (no external refinement)
            image_path, prompt = await llm_service.generate_logo_with_gemini(
                text=request.text,
                description=request.description or "",
                style=style_prompt,
                palette=palette_desc,
                tagline=request.tagline or "",
                typography=request.typography or "",
                elements_to_include=request.elements_to_include or "",
                elements_to_avoid=request.elements_to_avoid or "",
                brand_mission=request.brand_mission or ""
            )
            return {
                "result": [image_path],
                "brand": request.text,
                "style": request.style,
                "palette": request.palette,
                "prompt": prompt,
                "generator": "gemini"
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

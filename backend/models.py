from pydantic import BaseModel, Field
from typing import Optional, List


class LogoGenerationRequest(BaseModel):
    """Request model for logo generation with advanced options"""
    # Core fields
    text: str = Field(..., min_length=1, description="Brand name")
    description: Optional[str] = Field("", description="Brand description")
    style: str = Field("minimalist", description="Logo style")
    palette: str = Field("monochrome", description="Color palette")
    generator: str = Field("dalle-3", description="Image generator: 'dalle-3' or 'gemini'")
    
    # Advanced branding fields
    tagline: Optional[str] = Field("", description="Brand tagline or slogan")
    typography: Optional[str] = Field("", description="Typography preference (e.g., Modern Sans-Serif)")
    elements_to_include: Optional[str] = Field("", description="Specific elements to include in logo")
    elements_to_avoid: Optional[str] = Field("", description="Specific elements to avoid in logo")
    brand_mission: Optional[str] = Field("", description="Core purpose or mission of the brand")


class LogoGenerationResponse(BaseModel):
    """Response model for logo generation"""
    result: List[str] = Field(..., description="List of generated image URLs or paths")
    brand: str = Field(..., description="Brand name")
    style: str = Field(..., description="Logo style used")
    palette: str = Field(..., description="Color palette used")
    prompt: str = Field(..., description="Final prompt used for generation")
    generator: str = Field(..., description="Generator used")


class LogoModificationRequest(BaseModel):
    """Request model for logo modification"""
    instructions: str = Field(..., min_length=1, description="Modification instructions")
    generator: str = Field("dalle-3", description="Image generator: 'dalle-3' or 'gemini'")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    gemini_ready: bool = Field(..., description="Gemini client ready")
    openai_ready: bool = Field(..., description="OpenAI client ready")


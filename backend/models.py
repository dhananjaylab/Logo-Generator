from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class LogoGenerationRequest(BaseModel):
    """Request model for logo generation with advanced options"""
    # Core fields
    text: str = Field(..., min_length=1, description="Brand name")
    description: Optional[str] = Field("", description="Brand description")
    style: str = Field("minimalist", description="Logo style")
    palette: str = Field("monochrome", description="Color palette")
    generator: str = Field(
        "gpt-image-2-2026-04-21",
        description="Image generator: 'gpt-image-2-2026-04-21' or 'gemini'",
    )

    # Advanced branding fields
    tagline: Optional[str] = Field("", description="Brand tagline or slogan")
    typography: Optional[str] = Field("", description="Typography preference")
    elements_to_include: Optional[str] = Field("", description="Specific elements to include")
    elements_to_avoid: Optional[str] = Field("", description="Specific elements to avoid")
    brand_mission: Optional[str] = Field("", description="Core purpose or mission of the brand")

    # Variation control
    variation_hint: Optional[str] = Field("", description="Creative direction for regeneration.")
    variation_index: Optional[int] = Field(
        0, ge=0, description="0 = fresh generation; >0 = Nth regeneration.",
    )


class LogoGenerationResponse(BaseModel):
    """Response model for logo generation"""
    result: List[str] = Field(..., description="List of generated image URLs or paths")
    brand: str = Field(..., description="Brand name")
    style: str = Field(..., description="Logo style used")
    palette: str = Field(..., description="Color palette used")
    prompt: str = Field(..., description="Final prompt used for generation")
    generator: str = Field(..., description="Generator used")


class HealthResponse(BaseModel):
    """Health check response — used for liveness and readiness checks."""
    status: str = Field(..., description="ok | degraded | error")
    gemini_ready: bool = Field(..., description="Gemini client key configured")
    openai_ready: bool = Field(..., description="OpenAI client key configured")
    redis_ready: bool = Field(False, description="Redis reachable")
    db_ready: bool = Field(False, description="PostgreSQL reachable")


class LogoJobResponse(BaseModel):
    """Initial response when a job is enqueued"""
    job_id: str = Field(..., description="The unique ID of the background job")
    status: str = Field("enqueued", description="Initial status of the job")


class JobStatusResponse(BaseModel):
    """Response model for checking job status"""
    job_id: str = Field(..., description="The unique ID of the job")
    status: str = Field(..., description="Current status: 'enqueued', 'running', 'completed', 'failed'")
    result: Optional[LogoGenerationResponse] = Field(None, description="The generation result if completed")
    error: Optional[str] = Field(None, description="Error message if failed")


# SECURITY FIX (P1.6): Scoped history response model.
# The full LogoGeneration ORM object contains ip_hash and user_id which
# must never be returned to clients. This model whitelists only the fields
# that are safe to expose. FastAPI will serialize ONLY these fields.
class HistoryEntryResponse(BaseModel):
    """
    Safe public representation of a generation history entry.
    Explicitly excludes: ip_hash, user_id.
    """
    id: int
    brand_name: str
    prompt: str
    generator: str
    image_url: str
    created_at: datetime

    class Config:
        from_attributes = True  # allows construction from SQLAlchemy ORM objects


# SECURITY FIX (P1.2): WebSocket ticket response model.
# Clients exchange their JWT (via POST /ws/ticket) for a short-lived,
# single-use ticket that can safely appear in the WebSocket URL query string
# without leaking the long-lived bearer token to server access logs.
class WsTicketResponse(BaseModel):
    """Short-lived WebSocket authentication ticket."""
    ticket: str = Field(..., description="Single-use ticket (URL-safe, 32 random bytes)")
    expires_in: int = Field(30, description="Ticket TTL in seconds")

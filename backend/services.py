"""
services.py – Logo generation services.

This module now uses the GPT image model for OpenAI-backed generation.

Key behaviors:
1. Prompt construction still enforces "logo mark only" constraints first.
2. Every generated file gets a timestamp+variation suffix so repeated calls
   never reuse stale files.
3. GPT image responses arrive as base64 payloads, so we decode them and upload
   the resulting bytes directly to R2.
4. Style and palette remain at the front of the prompt so they retain weight.
"""

import base64
import binascii
import io
import os
import asyncio
import time
from typing import Tuple

import boto3
from botocore.config import Config
from PIL import Image
from google import genai
from google.genai import types
from openai import AsyncOpenAI

from utils import sanitize_filename
from config import (
    R2_BUCKET_NAME,
    R2_ACCESS_KEY_ID,
    R2_SECRET_ACCESS_KEY,
    R2_ENDPOINT_URL,
    R2_PUBLIC_DOMAIN,
    DATABASE_URL,
)
from database import AsyncSessionLocal, LogoGeneration

# ─────────────────────────────────────────────────────────────────────────────
# Cloudflare R2 / S3 Client
# ─────────────────────────────────────────────────────────────────────────────

def get_r2_client():
    """Initialize a boto3 S3 client for Cloudflare R2."""
    if not all([R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ENDPOINT_URL]):
        return None
        
    return boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT_URL,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",  # R2 expects 'auto' or a specific region
    )


def upload_to_r2(data: bytes, filename: str, content_type: str = "image/png") -> str:
    """
    Upload bytes to R2. Raises RuntimeError on any failure so the caller
    (worker task) can mark the job as failed and surface a real error.
    """
    client = get_r2_client()
    if not client or not R2_BUCKET_NAME:
        raise RuntimeError(
            "R2 upload failed: storage client not configured. "
            "Set R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ENDPOINT_URL, R2_BUCKET_NAME."
        )
    try:
        client.put_object(
            Bucket=R2_BUCKET_NAME,
            Key=filename,
            Body=data,
            ContentType=content_type,
        )
        if R2_PUBLIC_DOMAIN:
            return f"{R2_PUBLIC_DOMAIN}/{filename}"
        return f"{R2_ENDPOINT_URL}/{R2_BUCKET_NAME}/{filename}"
    except Exception as exc:
        raise RuntimeError(f"R2 upload failed for '{filename}': {exc}") from exc


# ─────────────────────────────────────────────────────────────────────────────
# Filename Generator
# ─────────────────────────────────────────────────────────────────────────────


def _unique_filename(brand: str, generator: str, variation_index: int) -> str:
    """
    Produce a filename that is unique per call so disk never caches a stale image.
    Format: <brand>_<unix_ts>_v<variation>.png
    """
    ts    = int(time.time())
    safe  = sanitize_filename(brand.replace(" ", "_") or "logo")
    return f"{generator}_{safe}_{ts}_v{variation_index}.png"


# ─────────────────────────────────────────────────────────────────────────────
# Prompt builder
# ─────────────────────────────────────────────────────────────────────────────

# Hard constraints injected at the START of every prompt.
# They appear before any brand/style instructions so GPT image and Gemini
# don't drift into "scene" or "mockup" mode.
_LOGO_HARD_CONSTRAINTS = (
    "OUTPUT REQUIREMENT: A single, isolated, flat 2D logo mark on a pure white background. "
    "STRICTLY NO: 3D renders, drop-shadows, gradients unless part of the palette, "
    "business-card mockups, product staging, photo-realistic scenes, textures, "
    "hands, people, environments, or any context other than the logo itself. "
    "The entire image must show ONLY the logo symbol / wordmark centred on white. "
)


def build_logo_prompt(
    text: str,
    description: str,
    style: str,
    palette: str,
    tagline: str = "",
    typography: str = "",
    elements_to_include: str = "",
    elements_to_avoid: str = "",
    brand_mission: str = "",
    variation_hint: str = "",
    variation_index: int = 0,
) -> str:
    """
    Build a rich logo-specific prompt.
    Hard output constraints come FIRST so they are not overridden by
    later creative instructions.
    Style and palette come SECOND so the model weights them heavily.
    """
    parts = [_LOGO_HARD_CONSTRAINTS]

    # Style and palette upfront — most important creative parameters
    parts.append(
        f"DESIGN STYLE: {style}. "
        f"COLOR PALETTE: Use ONLY these colors — {palette}. "
        "Do not introduce colors outside this palette."
    )

    parts.append(f"Brand name: '{text}'.")

    if description:
        parts.append(f"Brand context: {description}.")
    if tagline:
        parts.append(f"Brand tagline: '{tagline}'.")
    if brand_mission:
        parts.append(f"Brand mission: {brand_mission}.")
    if typography:
        parts.append(f"Typography style: {typography}.")
    if elements_to_include:
        parts.append(f"Incorporate these visual elements: {elements_to_include}.")
    if elements_to_avoid:
        parts.append(f"Do NOT include: {elements_to_avoid}.")

    # Variation steering — ensures each regeneration is visually distinct
    if variation_hint:
        parts.append(
            f"VARIATION DIRECTION (important — this call must look clearly different "
            f"from any previous version): {variation_hint}."
        )
    elif variation_index > 0:
        # Even without an explicit hint, tell the model it's a new variant
        parts.append(
            f"This is variation #{variation_index}. "
            "Explore a completely different composition, icon concept, and layout "
            "compared to the default version."
        )

    parts += [
        "Keep the composition centered and balanced.",
        "Vector-quality edges, professional finish, scalable to any size.",
        f"Brand name '{text}' may appear as a wordmark only if it integrates naturally.",
    ]

    return " ".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Gemini service
# ─────────────────────────────────────────────────────────────────────────────

_GEMINI_MODEL_TIMEOUT = 45

_GEMINI_IMAGE_MODELS = [
    "gemini-2.5-flash-image",     # if your API key has access
]


class GeminiService:
    def __init__(self, client: genai.Client):
        self.client = client

    def _call_model(self, model: str, prompt: str):
        return self.client.models.generate_content(
            model=model,
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )

    async def _try_model(self, model: str, prompt: str):
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._call_model, model, prompt),
                timeout=_GEMINI_MODEL_TIMEOUT,
            )
        except asyncio.TimeoutError:
            print(f"[Gemini] '{model}' timed out after {_GEMINI_MODEL_TIMEOUT} s")
            return None
        except Exception as exc:
            print(f"[Gemini] '{model}' failed: {exc}")
            return None

    async def generate_logo(
        self,
        text: str,
        description: str,
        style: str,
        palette: str,
        tagline: str = "",
        typography: str = "",
        elements_to_include: str = "",
        elements_to_avoid: str = "",
        brand_mission: str = "",
        variation_hint: str = "",
        variation_index: int = 0,
    ) -> Tuple[str, str]:
        prompt = build_logo_prompt(
            text, description, style, palette,
            tagline, typography,
            elements_to_include, elements_to_avoid,
            brand_mission, variation_hint, variation_index,
        )

        for model in _GEMINI_IMAGE_MODELS:
            print(f"[Gemini] Trying {model}  variation={variation_index} …")
            response = await self._try_model(model, prompt)
            if response is None:
                continue

            try:
                response_parts = response.candidates[0].content.parts
            except (IndexError, AttributeError) as exc:
                print(f"[Gemini] '{model}': could not read parts — {exc}")
                continue

            for part in response_parts:
                inline = getattr(part, "inline_data", None)
                if inline and getattr(inline, "data", None):
                    fname = _unique_filename(text, "gemini", variation_index)
                    # Upload directly to R2
                    url = await asyncio.to_thread(upload_to_r2, inline.data, f"gemini/{fname}")
                    print(f"[Gemini] ✓ uploaded → {url}")
                    return url, prompt

            print(f"[Gemini] '{model}': response had no inline image data")

        raise ValueError(
            "Gemini image generation failed — all model attempts exhausted. "
            "Verify GEMINI_API_KEY has access to image generation models."
        )


# ─────────────────────────────────────────────────────────────────────────────
# GPT image service (decodes base64 payloads and stores the result in R2)
# ─────────────────────────────────────────────────────────────────────────────

_OPENAI_IMAGE_TIMEOUT = 50   # seconds for the OpenAI images.generate call


def _decode_image_payload(b64_json: str) -> bytes:
    """Decode GPT image base64 payloads into raw image bytes."""
    if not b64_json:
        raise ValueError("OpenAI image response did not include image data")

    image_bytes = base64.b64decode(b64_json)
    with Image.open(io.BytesIO(image_bytes)) as img:
        img.load()
    return image_bytes


class OpenAIImageService:
    def __init__(self, client: AsyncOpenAI):
        self.client = client

    async def generate_logo(
        self, prompt: str, brand: str = "logo", variation_index: int = 0
    ) -> str:
        """
        Generate an image with GPT image, validate it, and upload it to R2.
        Returns the public URL for the stored image.
        """
        try:
            response = await asyncio.wait_for(
                self.client.images.generate(
                    model="gpt-image-2-2026-04-21",
                    prompt=prompt,
                    n=1,
                    size="1024x1024",
                    quality="high",
                    background="opaque",
                    user=brand,
                ),
                timeout=_OPENAI_IMAGE_TIMEOUT,
            )
        except asyncio.TimeoutError:
            raise RuntimeError(
                f"GPT image did not respond within {_OPENAI_IMAGE_TIMEOUT} s. "
                "Try again or switch to Gemini."
            )

        try:
            image_data = _decode_image_payload(response.data[0].b64_json)
        except (IndexError, AttributeError, ValueError, binascii.Error) as exc:
            raise RuntimeError(f"GPT image response did not include valid image bytes: {exc}") from exc

        fname = _unique_filename(brand, "openai", variation_index)
        try:
            url = await asyncio.to_thread(upload_to_r2, image_data, f"openai/{fname}")
            print(f"[OpenAI Image] ✓ uploaded → {url}")
            return url
        except Exception as exc:
            raise RuntimeError(f"OpenAI image upload failed: {exc}") from exc


# ─────────────────────────────────────────────────────────────────────────────
# Unified LLMService facade
# ─────────────────────────────────────────────────────────────────────────────

class LLMService:
    def __init__(self, gemini_client: genai.Client, openai_client: AsyncOpenAI):
        self.gemini = GeminiService(gemini_client)
        self.openai_image = OpenAIImageService(openai_client)

    async def _save_to_db(
        self, 
        brand: str, 
        prompt: str, 
        generator: str, 
        url: str, 
        ip: str = None,
        user_id: str = None
    ) -> None:
        """Asynchronously save generation metadata to PostgreSQL."""
        if not AsyncSessionLocal:
            print("[DB] ⚠ DATABASE_URL not set; skipping history save")
            return

        async with AsyncSessionLocal() as session:
            try:
                new_entry = LogoGeneration(
                    brand_name=brand,
                    prompt=prompt,
                    generator=generator,
                    image_url=url,
                    ip_address=ip,
                    user_id=user_id
                )
                session.add(new_entry)
                await session.commit()
                print(f"[DB] ✓ Logged generation for '{brand}' ({generator})")
            except Exception as e:
                print(f"[DB] ⚠ Failed to save history: {e}")
                await session.rollback()

    async def generate_logo_with_openai_image(self, user_ip: str = None, **kwargs) -> Tuple[str, str]:
        """
        Generate a logo using the GPT image model.
        
        Explicitly extracts parameters from kwargs to avoid collisions
        where 'text' or other parameter names could shadow function arguments.
        """
        # Extract special parameters that aren't part of the prompt
        user_id = kwargs.pop("user_id", None)
        variation_index = kwargs.pop("variation_index", 0)
        
        # Extract all prompt-building parameters explicitly
        text = kwargs.pop("text", "logo")
        description = kwargs.pop("description", "")
        style = kwargs.pop("style", "minimalist")
        palette = kwargs.pop("palette", "monochrome")
        tagline = kwargs.pop("tagline", "")
        typography = kwargs.pop("typography", "")
        elements_to_include = kwargs.pop("elements_to_include", "")
        elements_to_avoid = kwargs.pop("elements_to_avoid", "")
        brand_mission = kwargs.pop("brand_mission", "")
        variation_hint = kwargs.pop("variation_hint", "")
        
        # Any remaining kwargs would be an error, so we could log them
        if kwargs:
            print(f"[OpenAI Image] ⚠ Unexpected kwargs: {kwargs.keys()}")
        
        # Build prompt with explicit parameters (no ** unpacking)
        prompt = build_logo_prompt(
            text=text,
            description=description,
            style=style,
            palette=palette,
            tagline=tagline,
            typography=typography,
            elements_to_include=elements_to_include,
            elements_to_avoid=elements_to_avoid,
            brand_mission=brand_mission,
            variation_hint=variation_hint,
            variation_index=variation_index,
        )
        
        local_path = await self.openai_image.generate_logo(prompt, brand=text, variation_index=variation_index)
        
        # Save to DB
        await self._save_to_db(text, prompt, "gpt-image-2-2026-04-21", local_path, user_ip, user_id)
        
        return local_path, prompt

    async def generate_logo_with_gemini(self, user_ip: str = None, **kwargs) -> Tuple[str, str]:
        """
        Generate a logo using Gemini.
        
        Explicitly extracts parameters from kwargs to avoid collisions.
        """
        # Extract special parameters that aren't part of the prompt
        user_id = kwargs.pop("user_id", None)
        variation_index = kwargs.pop("variation_index", 0)
        
        # Extract all prompt-building parameters explicitly
        text = kwargs.pop("text", "logo")
        description = kwargs.pop("description", "")
        style = kwargs.pop("style", "minimalist")
        palette = kwargs.pop("palette", "monochrome")
        tagline = kwargs.pop("tagline", "")
        typography = kwargs.pop("typography", "")
        elements_to_include = kwargs.pop("elements_to_include", "")
        elements_to_avoid = kwargs.pop("elements_to_avoid", "")
        brand_mission = kwargs.pop("brand_mission", "")
        variation_hint = kwargs.pop("variation_hint", "")
        
        # Any remaining kwargs would be an error, so we could log them
        if kwargs:
            print(f"[Gemini] ⚠ Unexpected kwargs: {kwargs.keys()}")
        
        # Call generate_logo with explicit parameters (no ** unpacking)
        url, prompt = await self.gemini.generate_logo(
            text=text,
            description=description,
            style=style,
            palette=palette,
            tagline=tagline,
            typography=typography,
            elements_to_include=elements_to_include,
            elements_to_avoid=elements_to_avoid,
            brand_mission=brand_mission,
            variation_hint=variation_hint,
            variation_index=variation_index,
        )
        
        # Save to DB
        await self._save_to_db(text, prompt, "gemini", url, user_ip, user_id)
        
        return url, prompt

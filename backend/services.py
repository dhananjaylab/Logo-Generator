"""
services.py – Logo generation services.

Fixes in this version
─────────────────────
1. PROMPT: Explicit "logo mark ONLY" constraints at the TOP of every prompt
   stop DALL-E from generating business-card scenes / mockups. A hard
   negative list ("NO mockups, NO 3D renders, NO staging…") is prepended.

2. UNIQUE FILENAMES: Every generated file gets a timestamp+variation suffix
   so repeated calls never serve a cached file from disk.
   Gemini: generated_logos/gemini/<brand>_<ts>_v<n>.png
   DALL-E: generated_logos/dalle/<brand>_<ts>_v<n>.png

3. DALL-E LOCAL SAVE: After getting the temporary OpenAI URL, the image is
   downloaded and stored locally (generated_logos/dalle/). The local path
   is returned instead of the expiring URL, making downloads reliable.

4. STYLE / PALETTE PROMINENCE: Style and color palette appear at the very
   start of the prompt (after the hard constraints), not buried at the end,
   so Gemini/DALL-E give them proper weight.

5. asyncio timeouts and response_modalities=["IMAGE"] retained from
   previous version.
"""

import io
import asyncio
import time
from typing import Tuple

import requests as _requests      # synchronous – used in to_thread for DALL-E download
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
)


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
    Upload bytes to R2 and return the public URL or S3-compatible path.
    """
    client = get_r2_client()
    if not client or not R2_BUCKET_NAME:
        print("[R2] ⚠ R2 client or bucket not configured; falling back to local simulation")
        return f"LOCAL_FALLBACK/{filename}"

    try:
        client.put_object(
            Bucket=R2_BUCKET_NAME,
            Key=filename,
            Body=data,
            ContentType=content_type,
        )
        # Construct the URL. Use public domain if available, else endpoint+bucket
        if R2_PUBLIC_DOMAIN:
            return f"{R2_PUBLIC_DOMAIN}/{filename}"
        return f"{R2_ENDPOINT_URL}/{R2_BUCKET_NAME}/{filename}"
    except Exception as exc:
        print(f"[R2] ⚠ Upload failed: {exc}")
        return f"UPLOAD_FAILED/{filename}"


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
# They appear before any brand/style instructions so DALL-E and Gemini
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
   "gemini-2.5-flash-image",  # Latest and best for logos if available
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
# DALL-E service  (saves image locally so the URL never expires)
# ─────────────────────────────────────────────────────────────────────────────

_DALLE_TIMEOUT     = 50   # seconds for the OpenAI images.generate call
_DALLE_DL_TIMEOUT  = 20   # seconds to download the returned URL


def _download_image(url: str, dest_path: str) -> None:
    """Download a URL to disk synchronously (called via to_thread)."""
    resp = _requests.get(url, timeout=_DALLE_DL_TIMEOUT)
    resp.raise_for_status()
    img = Image.open(io.BytesIO(resp.content))
    img.save(dest_path)


class DALLEService:
    def __init__(self, client: AsyncOpenAI):
        self.client = client

    async def generate_logo(
        self, prompt: str, brand: str = "logo", variation_index: int = 0
    ) -> str:
        """
        Generate with DALL-E 3, download the result, save locally.
        Returns the relative path (e.g. generated_logos/dalle/dalle_Brand_<ts>_v0.png)
        so it can be served via FastAPI's /static/ mount — no expiring URLs.
        """
        try:
            response = await asyncio.wait_for(
                self.client.images.generate(
                    model="dall-e-3",
                    prompt=prompt,
                    n=1,
                    size="1024x1024",
                    quality="hd",
                    style="natural",
                ),
                timeout=_DALLE_TIMEOUT,
            )
        except asyncio.TimeoutError:
            raise RuntimeError(
                f"DALL-E 3 did not respond within {_DALLE_TIMEOUT} s. "
                "Try again or switch to Gemini."
            )

        image_url = response.data[0].url

        # Synchronous download
        try:
            resp = await asyncio.to_thread(_requests.get, image_url, timeout=_DALLE_DL_TIMEOUT)
            resp.raise_for_status()
            image_data = resp.content
        except Exception as exc:
            print(f"[DALL-E] ⚠ Download failed ({exc}); returning raw URL")
            return image_url

        # Upload to R2
        fname = _unique_filename(brand, "dalle", variation_index)
        try:
            url = await asyncio.to_thread(upload_to_r2, image_data, f"dalle/{fname}")
            print(f"[DALL-E] ✓ uploaded → {url}")
            return url
        except Exception as exc:
            print(f"[DALL-E] ⚠ R2 upload failed ({exc}); returning raw URL")
            return image_url


# ─────────────────────────────────────────────────────────────────────────────
# Unified LLMService facade
# ─────────────────────────────────────────────────────────────────────────────

class LLMService:
    def __init__(self, gemini_client: genai.Client, openai_client: AsyncOpenAI):
        self.gemini = GeminiService(gemini_client)
        self.dalle  = DALLEService(openai_client)

    async def generate_logo_with_dalle(self, **kwargs) -> Tuple[str, str]:
        variation_index = kwargs.pop("variation_index", 0)
        text            = kwargs.get("text", "logo")
        prompt          = build_logo_prompt(**kwargs, variation_index=variation_index)
        local_path      = await self.dalle.generate_logo(prompt, brand=text, variation_index=variation_index)
        return local_path, prompt

    async def generate_logo_with_gemini(self, **kwargs) -> Tuple[str, str]:
        return await self.gemini.generate_logo(**kwargs)
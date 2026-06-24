"""
services.py – Logo generation services.

Phase 2 changes (carried forward)
──────────────────────────────────
HIGH-02  R2 client is a thread-local singleton (threading.local) — eliminates
         a TLS handshake on every upload.
MED-03   Image validation uses magic-byte prefix checking instead of PIL
         decompression — no pixel-buffer allocation just to validate format.
HIGH-04  Circuit breakers (dalle_cb, gemini_cb, r2_cb) use Redis-backed shared
         state across all API and worker processes.

Phase 3 changes (this revision)
────────────────────────────────
P3.6 (MED-02 fix)  LLMService.generate_logo_with_openai_image() and
         generate_logo_with_gemini() now both accept a single
         `LogoGenerationParams` dataclass instead of **kwargs. The Gemini
         quota-fallback path forwards that same object unchanged to the
         OpenAI path — no more manually-reconstructed `fallback_kwargs` dict
         and no more risk of pop-order drift between the two methods.
P3.2     Both generation methods now return a 3-tuple (url, prompt, cost_usd)
         and pass cost_usd through to LogoRepository.save() for budget
         tracking and the Grafana cost dashboard.
P3.3/4   New `r2_key_from_url()` helper reverses the URL construction done in
         upload_to_r2(), used by the GDPR deletion endpoint (routers.py) and
         the data-retention purge cron job (maintenance_worker.py) to find
         and remove the corresponding R2 object.
"""

import base64
import binascii
import io
import os
import asyncio
import threading
import time
from typing import Optional, Tuple

import boto3
from botocore.config import Config
from google import genai
from google.genai import types
from openai import AsyncOpenAI

from circuit_breaker import dalle_cb, gemini_cb, r2_cb
from prom_metrics import errors_total, r2_upload_latency
from utils import sanitize_filename
from models import LogoGenerationParams
from config import (
    R2_BUCKET_NAME,
    R2_ACCESS_KEY_ID,
    R2_SECRET_ACCESS_KEY,
    R2_SESSION_TOKEN,
    R2_ENDPOINT_URL,
    R2_PUBLIC_DOMAIN,
    GENERATION_COST_USD,
)
from repository import LogoRepository


# ─────────────────────────────────────────────────────────────────────────────
# Cloudflare R2 / S3 Client  (HIGH-02 FIX)
# ─────────────────────────────────────────────────────────────────────────────

_r2_thread_local = threading.local()


def get_r2_client():
    """
    Return a thread-local R2 (S3-compatible) client, creating it on first use.

    boto3 clients are not thread-safe; threading.local() gives each thread in
    asyncio's executor pool its own connection-pooled client, reused across
    every upload that lands on that thread, eliminating a fresh TLS handshake
    per request.
    """
    if not all([R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ENDPOINT_URL]):
        return None

    client = getattr(_r2_thread_local, "client", None)
    if client is None:
        _r2_thread_local.client = boto3.client(
            "s3",
            endpoint_url=R2_ENDPOINT_URL,
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            aws_session_token=R2_SESSION_TOKEN or None,
            config=Config(
                signature_version="s3v4",
                max_pool_connections=5,
                connect_timeout=5,
                read_timeout=30,
            ),
            region_name="auto",
        )
    return _r2_thread_local.client


def upload_to_r2(data: bytes, filename: str, content_type: str = "image/png") -> str:
    """Upload bytes to R2. Raises RuntimeError on failure."""
    client = get_r2_client()
    if not client or not R2_BUCKET_NAME:
        raise RuntimeError(
            "R2 upload failed: storage client not configured. "
            "Set R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ENDPOINT_URL, R2_BUCKET_NAME."
        )

    started = time.perf_counter()
    try:
        client.put_object(
            Bucket=R2_BUCKET_NAME,
            Key=filename,
            Body=data,
            ContentType=content_type,
        )
    except Exception as exc:
        r2_upload_latency.labels(status="failed").observe(time.perf_counter() - started)
        errors_total.labels(error_type=type(exc).__name__, source="r2").inc()
        message = str(exc)
        if "Unauthorized" in message or "401" in message:
            message += (
                " Check that the R2 token has Object Read & Write permission "
                "for this bucket. If you are using temporary R2 credentials, "
                "set R2_SESSION_TOKEN too."
            )
        raise RuntimeError(f"R2 upload failed for '{filename}': {message}") from exc
    else:
        r2_upload_latency.labels(status="success").observe(time.perf_counter() - started)
        if R2_PUBLIC_DOMAIN:
            return f"{R2_PUBLIC_DOMAIN}/{filename}"
        return f"{R2_ENDPOINT_URL}/{R2_BUCKET_NAME}/{filename}"


def r2_key_from_url(url: str) -> Optional[str]:
    """
    P3.3/P3.4 — Reverse of the URL construction in upload_to_r2(): given a
    stored image_url, return the R2 object key, or None if the URL doesn't
    match either format we generate (public CDN domain, or raw R2 endpoint).

    Used by:
      - DELETE /api/v1/me/data (routers.py) — GDPR/CCPA erasure
      - maintenance_worker.purge_expired_generations() — retention purge
    """
    if not url:
        return None

    if R2_PUBLIC_DOMAIN and url.startswith(R2_PUBLIC_DOMAIN):
        return url[len(R2_PUBLIC_DOMAIN):].lstrip("/")

    if R2_ENDPOINT_URL and R2_BUCKET_NAME:
        prefix = f"{R2_ENDPOINT_URL}/{R2_BUCKET_NAME}/"
        if url.startswith(prefix):
            return url[len(prefix):]

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Filename Generator
# ─────────────────────────────────────────────────────────────────────────────

def _unique_filename(brand: str, generator: str, variation_index: int) -> str:
    ts   = int(time.time())
    safe = sanitize_filename(brand.replace(" ", "_") or "logo")
    return f"{generator}_{safe}_{ts}_v{variation_index}.png"


# ─────────────────────────────────────────────────────────────────────────────
# Cost Estimation  (P3.2)
# ─────────────────────────────────────────────────────────────────────────────

def _estimate_cost_usd(generator: str) -> float:
    """
    Rough per-generation cost estimate, used to populate cost_usd on each
    saved record and to feed the Grafana cost dashboard / budget alerts.
    Not penny-accurate billing — see config.GENERATION_COST_USD for notes.
    """
    if generator == "gpt-image-2-2026-04-21":
        quality = os.getenv("OPENAI_IMAGE_QUALITY", "low")
        table = GENERATION_COST_USD.get(generator, {})
        return table.get(quality, 0.04) if isinstance(table, dict) else 0.04

    if generator == "gemini":
        cost = GENERATION_COST_USD.get("gemini", 0.02)
        return cost if isinstance(cost, (int, float)) else 0.02

    return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Prompt builder
# ─────────────────────────────────────────────────────────────────────────────

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
    parts = [
        _LOGO_HARD_CONSTRAINTS,
        f"DESIGN STYLE: {style}. COLOR PALETTE: Use ONLY these colors — {palette}.",
        f"Brand name: '{text}'.",
    ]
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
    if variation_hint:
        parts.append(
            f"VARIATION DIRECTION (important — this call must look clearly different "
            f"from any previous version): {variation_hint}."
        )
    elif variation_index > 0:
        parts.append(
            f"This is variation #{variation_index}. "
            "Explore a completely different composition, icon concept, and layout "
            "compared to the default version."
        )
    parts += [
        "Centered, balanced composition.",
        "Flat vector-style logo, clean edges, white background.",
        f"Use the brand name '{text}' only if it fits naturally.",
    ]
    return " ".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Image Validation  (MED-03)
# ─────────────────────────────────────────────────────────────────────────────

_MAGIC_BYTES: dict[str, bytes] = {
    "jpeg": b"\xff\xd8\xff",
    "png":  b"\x89PNG",
    "webp": b"RIFF",
    "gif":  b"GIF8",
}
_MIN_MAGIC_LEN = max(len(m) for m in _MAGIC_BYTES.values())


def _validate_image_bytes(data: bytes) -> str:
    """Validate image bytes via magic-byte prefix. Returns format name or raises."""
    if len(data) < _MIN_MAGIC_LEN:
        raise ValueError(f"Image data too short ({len(data)} bytes) to be a valid image")

    for fmt, magic in _MAGIC_BYTES.items():
        if data[: len(magic)] == magic:
            return fmt

    raise ValueError(
        f"Unrecognised image format. Magic bytes: {data[:8].hex()} — "
        f"expected JPEG (ffd8ff), PNG (89504e47), WebP (52494646), or GIF (47494638)."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Gemini Service
# ─────────────────────────────────────────────────────────────────────────────

_GEMINI_MODEL_TIMEOUT = 45
_GEMINI_IMAGE_MODELS = [
    os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image"),
]


class GeminiService:
    def __init__(self, client: genai.Client):
        self.client = client

    def _call_model(self, model: str, prompt: str):
        return self.client.models.generate_content(
            model=model,
            contents=[prompt],
            config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
        )

    async def _try_model(self, model: str, prompt: str):
        try:
            return await gemini_cb.call(
                asyncio.wait_for(
                    asyncio.to_thread(self._call_model, model, prompt),
                    timeout=_GEMINI_MODEL_TIMEOUT,
                )
            )
        except asyncio.TimeoutError:
            print(f"[Gemini] '{model}' timed out after {_GEMINI_MODEL_TIMEOUT}s")
            return None
        except RuntimeError as exc:
            if "[CB:" in str(exc):
                raise
            print(f"[Gemini] '{model}' failed: {exc}")
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
                    try:
                        fmt = _validate_image_bytes(inline.data)
                        print(f"[Gemini] Detected format: {fmt}")
                    except ValueError as exc:
                        print(f"[Gemini] Image validation failed: {exc}")
                        continue

                    fname = _unique_filename(text, "gemini", variation_index)
                    url = await r2_cb.call(
                        asyncio.to_thread(upload_to_r2, inline.data, f"gemini/{fname}")
                    )
                    print(f"[Gemini] ✓ uploaded → {url}")
                    return url, prompt

            print(f"[Gemini] '{model}': response had no valid inline image data")

        raise ValueError(
            "Gemini image generation failed — all model attempts exhausted. "
            "Verify GEMINI_API_KEY has access to image generation models."
        )


# ─────────────────────────────────────────────────────────────────────────────
# OpenAI GPT Image Service
# ─────────────────────────────────────────────────────────────────────────────

_OPENAI_IMAGE_TIMEOUT     = int(os.getenv("OPENAI_IMAGE_TIMEOUT", "180"))
_OPENAI_IMAGE_QUALITY     = os.getenv("OPENAI_IMAGE_QUALITY", "low")
_OPENAI_IMAGE_SIZE        = os.getenv("OPENAI_IMAGE_SIZE", "1024x1024")
_OPENAI_IMAGE_FORMAT      = os.getenv("OPENAI_IMAGE_FORMAT", "jpeg")
_OPENAI_IMAGE_COMPRESSION = int(os.getenv("OPENAI_IMAGE_COMPRESSION", "85"))


def _decode_image_payload(b64_json: str) -> bytes:
    """Decode + validate (magic bytes, MED-03) a base64 image payload."""
    if not b64_json:
        raise ValueError("OpenAI image response did not include image data")

    try:
        image_bytes = base64.b64decode(b64_json)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"Failed to base64-decode image payload: {exc}") from exc

    _validate_image_bytes(image_bytes)
    return image_bytes


class OpenAIImageService:
    def __init__(self, client: AsyncOpenAI):
        self.client = client

    async def generate_logo(
        self, prompt: str, brand: str = "logo", variation_index: int = 0
    ) -> str:
        try:
            response = await dalle_cb.call(
                asyncio.wait_for(
                    self.client.images.generate(
                        model="gpt-image-2-2026-04-21",
                        prompt=prompt,
                        n=1,
                        size=_OPENAI_IMAGE_SIZE,
                        quality=_OPENAI_IMAGE_QUALITY,
                        background="opaque",
                        output_format=_OPENAI_IMAGE_FORMAT,
                        output_compression=_OPENAI_IMAGE_COMPRESSION,
                        user=brand,
                    ),
                    timeout=_OPENAI_IMAGE_TIMEOUT,
                ),
            )
        except asyncio.TimeoutError:
            raise RuntimeError(
                f"GPT image did not respond within {_OPENAI_IMAGE_TIMEOUT}s. "
                "The model may still be processing a complex prompt."
            )

        try:
            image_data = _decode_image_payload(response.data[0].b64_json)
        except (IndexError, AttributeError, ValueError, binascii.Error) as exc:
            raise RuntimeError(
                f"GPT image response did not include valid image bytes: {exc}"
            ) from exc

        fname = _unique_filename(brand, "openai", variation_index)
        try:
            url = await r2_cb.call(
                asyncio.to_thread(upload_to_r2, image_data, f"openai/{fname}")
            )
            print(f"[OpenAI Image] ✓ uploaded → {url}")
            return url
        except Exception as exc:
            raise RuntimeError(f"OpenAI image upload failed: {exc}") from exc


# ─────────────────────────────────────────────────────────────────────────────
# Unified LLMService facade  (P3.6 — dataclass-based interface)
# ─────────────────────────────────────────────────────────────────────────────

class LLMService:
    def __init__(
        self,
        gemini_client: Optional[genai.Client],
        openai_client: Optional[AsyncOpenAI],
        repository: Optional[LogoRepository] = None,
    ):
        self.gemini       = GeminiService(gemini_client) if gemini_client else None
        self.openai_image = OpenAIImageService(openai_client) if openai_client else None
        self._repo         = repository

    @staticmethod
    def _is_gemini_quota_error(exc: Exception) -> bool:
        message = str(exc)
        return (
            "RESOURCE_EXHAUSTED" in message
            or "quota" in message.lower()
            or "429" in message
            or "rate limit" in message.lower()
        )

    async def generate_logo_with_openai_image(
        self,
        params: LogoGenerationParams,
        user_id: Optional[str] = None,
        user_ip: Optional[str] = None,   # already an ip_hash by the time it reaches here
    ) -> Tuple[str, str, float]:
        """Returns (image_url, prompt, cost_usd)."""
        prompt = build_logo_prompt(
            text=params.text,
            description=params.description,
            style=params.style,
            palette=params.palette,
            tagline=params.tagline,
            typography=params.typography,
            elements_to_include=params.elements_to_include,
            elements_to_avoid=params.elements_to_avoid,
            brand_mission=params.brand_mission,
            variation_hint=params.variation_hint,
            variation_index=params.variation_index,
        )

        if not self.openai_image:
            raise RuntimeError("OpenAI image client is not configured.")

        local_path = await self.openai_image.generate_logo(
            prompt, brand=params.text, variation_index=params.variation_index
        )
        cost = _estimate_cost_usd("gpt-image-2-2026-04-21")

        if self._repo:
            await self._repo.save(
                params.text, prompt, "gpt-image-2-2026-04-21", local_path,
                user_id, user_ip, cost_usd=cost,
            )

        return local_path, prompt, cost

    async def generate_logo_with_gemini(
        self,
        params: LogoGenerationParams,
        user_id: Optional[str] = None,
        user_ip: Optional[str] = None,
    ) -> Tuple[str, str, float]:
        """Returns (image_url, prompt, cost_usd)."""
        try:
            if not self.gemini:
                raise RuntimeError("Gemini client is not configured.")

            url, prompt = await self.gemini.generate_logo(
                text=params.text,
                description=params.description,
                style=params.style,
                palette=params.palette,
                tagline=params.tagline,
                typography=params.typography,
                elements_to_include=params.elements_to_include,
                elements_to_avoid=params.elements_to_avoid,
                brand_mission=params.brand_mission,
                variation_hint=params.variation_hint,
                variation_index=params.variation_index,
            )
        except Exception as exc:
            if self._is_gemini_quota_error(exc):
                print("[Gemini] ⚠ Quota exhausted; falling back to GPT image generation")
                # P3.6 — `params` is forwarded unchanged. No manual kwargs
                # reconstruction, no risk of pop-order drift between paths.
                return await self.generate_logo_with_openai_image(
                    params, user_id=user_id, user_ip=user_ip
                )
            raise

        cost = _estimate_cost_usd("gemini")

        if self._repo:
            await self._repo.save(
                params.text, prompt, "gemini", url, user_id, user_ip, cost_usd=cost,
            )

        return url, prompt, cost

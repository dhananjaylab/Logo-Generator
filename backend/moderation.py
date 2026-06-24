"""
backend/moderation.py

HIGH-05 FIX — Content moderation pipeline.

Previously, generated images went directly from API → R2 → history with no
content-safety check at all. Both GPT Image 2 and Gemini have their own
built-in safety filters, but those can be probed and occasionally bypassed
via adversarial prompt injection through the free-text fields the user
controls: `description`, `tagline`, `brand_mission`, `elements_to_include`,
`elements_to_avoid`, and `variation_hint`.

This module moderates the CONCATENATION of those user-supplied free-text
fields using the OpenAI Moderation API *before* a job is ever enqueued. This:
  1. Blocks harmful requests instantly (sub-second) with a clear 400 response,
     rather than wasting a worker slot and provider cost on a doomed job.
  2. Doesn't require duplicating the server-controlled prompt-construction
     logic in services.py — we only need to check the parts of the prompt
     the user actually controls. The hard-coded "logo mark only" constraints
     and style/palette mappings are safe by construction.
  3. Works regardless of which generator (OpenAI or Gemini) is selected,
     since moderation uses a dedicated OpenAI client independent of the
     chosen image generator.

Fails OPEN (treats moderation as "not flagged") if the OpenAI client isn't
configured or the moderation API call itself errors, so a moderation-service
outage degrades to "no extra check" rather than blocking all generation.
This is logged loudly so an operator notices and can investigate; for a
stricter compliance posture, flip `_FAIL_OPEN` to False to block on any
moderation-check failure instead.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List

from dependencies import Clients

logger = logging.getLogger(__name__)

# Set to False to fail CLOSED (block the request) if the moderation API call
# itself errors out, rather than allowing the request through unchecked.
_FAIL_OPEN = True


@dataclass
class ModerationResult:
    flagged: bool
    categories: List[str] = field(default_factory=list)
    checked: bool = True   # False if the check was skipped/failed (fail-open)


async def moderate_text(text: str) -> ModerationResult:
    """
    Run `text` through the OpenAI Moderation API.

    Returns a ModerationResult; never raises — callers should check
    `.flagged` and decide what to do (block, log, etc.) themselves.
    """
    text = (text or "").strip()
    if not text:
        return ModerationResult(flagged=False, categories=[], checked=True)

    client = Clients.get_openai_client()
    if not client:
        logger.warning(
            "[Moderation] Skipped — OPENAI_API_KEY not configured. "
            "Content moderation is unavailable until an OpenAI client can be created."
        )
        return ModerationResult(flagged=False, categories=[], checked=False)

    try:
        response = await client.moderations.create(input=text)
        result = response.results[0]

        if result.flagged:
            categories = [
                name for name, is_flagged in result.categories.model_dump().items()
                if is_flagged
            ]
            logger.warning(f"[Moderation] Content flagged: {categories}")
            return ModerationResult(flagged=True, categories=categories, checked=True)

        return ModerationResult(flagged=False, categories=[], checked=True)

    except Exception as exc:
        logger.error(f"[Moderation] Check failed ({exc}); failing {'OPEN' if _FAIL_OPEN else 'CLOSED'}")
        if _FAIL_OPEN:
            return ModerationResult(flagged=False, categories=[], checked=False)
        return ModerationResult(flagged=True, categories=["moderation_check_failed"], checked=False)

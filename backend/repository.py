"""
Data persistence layer for logo generation history.
Keeps infrastructure concerns out of the service layer.
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import async_sessionmaker

from database import LogoGeneration

logger = logging.getLogger(__name__)


class LogoRepository:
    """Persists logo generation metadata to PostgreSQL."""

    def __init__(self, session_factory: Optional[async_sessionmaker]):
        self._factory = session_factory

    async def save(
        self,
        brand: str,
        prompt: str,
        generator: str,
        image_url: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        """
        Persist a generation record. Failures are logged but not re-raised
        so that a DB write error never causes a completed generation to appear
        failed to the end user.
        """
        if not self._factory:
            logger.warning("[Repo] No database configured - skipping history save")
            return

        async with self._factory() as session:
            try:
                session.add(
                    LogoGeneration(
                        brand_name=brand,
                        prompt=prompt,
                        generator=generator,
                        image_url=image_url,
                        user_id=user_id,
                        ip_address=ip_address,
                    )
                )
                await session.commit()
                logger.info(f"[Repo] Saved generation for '{brand}' ({generator})")
            except Exception as exc:
                await session.rollback()
                logger.error(f"[Repo] Failed to save generation: {exc}")

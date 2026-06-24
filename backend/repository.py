"""
Data persistence layer for logo generation history and the audit trail.
Keeps infrastructure concerns out of the service layer.
"""

from __future__ import annotations

import logging
from typing import Optional, List

from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from database import LogoGeneration, AuditLog

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
        ip_hash: Optional[str] = None,
        cost_usd: Optional[float] = None,   # P3.2
    ) -> None:
        """
        Persist a generation record.

        SECURITY NOTE (P1.4): The `ip_hash` parameter receives an already-
        anonymised value (16-char hex) from utils.anonymise_ip(). Raw IP
        addresses must never be passed here — anonymisation must happen in
        the caller (routers.py) before the job is enqueued, so the raw IP
        never leaves the request-handling process.

        Failures are logged but not re-raised so that a DB write error
        never causes a completed generation to appear failed to the user.
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
                        ip_hash=ip_hash,          # anonymised — never raw IP
                        cost_usd=cost_usd,
                    )
                )
                await session.commit()
                logger.info(
                    f"[Repo] Saved generation for '{brand}' "
                    f"({generator}, ${cost_usd or 0:.4f})"
                )
            except Exception as exc:
                await session.rollback()
                logger.error(f"[Repo] Failed to save generation: {exc}")

    async def delete_for_user(self, user_id: str) -> List[str]:
        """
        P3.3 — GDPR Art. 17 / CCPA right-to-deletion: hard-delete all
        generation rows belonging to `user_id`.

        Returns the list of image_url values that were deleted so the caller
        can best-effort remove the corresponding objects from R2 storage too.
        """
        if not self._factory:
            return []

        async with self._factory() as session:
            try:
                result = await session.execute(
                    select(LogoGeneration.image_url).where(LogoGeneration.user_id == user_id)
                )
                urls = [row[0] for row in result.all()]

                await session.execute(
                    delete(LogoGeneration).where(LogoGeneration.user_id == user_id)
                )
                await session.commit()
                logger.info(f"[Repo] Deleted {len(urls)} generation(s) for user")
                return urls
            except Exception as exc:
                await session.rollback()
                logger.error(f"[Repo] Failed to delete generations for user: {exc}")
                return []


class AuditRepository:
    """
    P3.4 — Append-only audit trail writer.

    Every method here logs its own failures and never raises — an audit-log
    write failure must never block, fail, or even slow down the user-facing
    request it's trying to record.
    """

    def __init__(self, session_factory: Optional[async_sessionmaker]):
        self._factory = session_factory

    async def log(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        ip_hash: Optional[str] = None,
        brand_name: Optional[str] = None,
        generator: Optional[str] = None,
        moderation_flagged: Optional[bool] = None,
        moderation_categories: Optional[str] = None,
        cost_usd: Optional[float] = None,
        detail: Optional[str] = None,
    ) -> None:
        if not self._factory:
            return
        async with self._factory() as session:
            try:
                session.add(
                    AuditLog(
                        event_type=event_type,
                        user_id=user_id,
                        ip_hash=ip_hash,
                        brand_name=brand_name,
                        generator=generator,
                        moderation_flagged=moderation_flagged,
                        moderation_categories=moderation_categories,
                        cost_usd=cost_usd,
                        detail=detail,
                    )
                )
                await session.commit()
            except Exception as exc:
                await session.rollback()
                logger.error(f"[Audit] Failed to write event '{event_type}': {exc}")

    async def anonymise_user(self, user_id: str, sentinel: str = "deleted-user") -> int:
        """
        P3.3 — Replace `user_id` with a sentinel value across all audit rows
        rather than deleting them outright.

        Security/compliance audit trails are typically retained under GDPR
        Art. 17(3)(b) (legal-obligation exemption) even after a user
        exercises their right to erasure of their personal data. Anonymising
        the identifier removes the personal-data linkage while preserving
        the integrity of the audit trail itself.

        Returns the number of rows updated.
        """
        if not self._factory:
            return 0
        async with self._factory() as session:
            try:
                result = await session.execute(
                    update(AuditLog)
                    .where(AuditLog.user_id == user_id)
                    .values(user_id=sentinel)
                )
                await session.commit()
                return result.rowcount or 0
            except Exception as exc:
                await session.rollback()
                logger.error(f"[Audit] Failed to anonymise user: {exc}")
                return 0

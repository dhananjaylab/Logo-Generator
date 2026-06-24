"""
backend/maintenance_worker.py

P3.3 — Scheduled data-retention purge (GDPR Article 5(1)(e)).

This is a separate ARQ worker process whose only job is a daily cron task
that permanently deletes generation history — and the corresponding R2
image objects — older than `DATA_RETENTION_DAYS` (config.py, default 365,
override via the DATA_RETENTION_DAYS env var).

This complements, but does not replace, the on-demand erasure endpoint
DELETE /api/v1/me/data (routers.py): that endpoint lets a user delete their
own data immediately; this cron job enforces a retention ceiling on
everyone's data automatically, even if they never ask.

Run it as its own process, alongside the existing two generation workers:

    arq maintenance_worker.WorkerSettings

It has no `functions` (no job-queue tasks to consume) — only `cron_jobs` —
so it never competes with openai_image_worker / gemini_worker for
generation jobs.
"""

import logging
from datetime import datetime, timedelta, timezone

from arq.cron import cron
from sqlalchemy import select, delete

from config import REDIS_SETTINGS, DATA_RETENTION_DAYS, R2_BUCKET_NAME
from database import AsyncSessionLocal, LogoGeneration
from services import get_r2_client, r2_key_from_url
from repository import AuditRepository

logger = logging.getLogger(__name__)


async def purge_expired_generations(ctx) -> None:
    """
    Daily cron job: delete LogoGeneration rows (and their R2 images) older
    than DATA_RETENTION_DAYS.

    The DB row is the source of truth for "is this still personal data we're
    responsible for" — it is deleted first, inside a single transaction.
    R2 cleanup happens afterward on a best-effort basis: a failure to delete
    an R2 object is logged but does not roll back the DB deletion, since
    re-running this job tomorrow won't find that row again to retry the R2
    delete. (A future enhancement could write orphaned keys to a cleanup
    queue; for now this mirrors the best-effort pattern already used by the
    GDPR deletion endpoint.)
    """
    if not AsyncSessionLocal:
        logger.warning("[Maintenance] No database configured — skipping purge")
        return

    cutoff = datetime.now(timezone.utc) - timedelta(days=DATA_RETENTION_DAYS)
    logger.info(f"[Maintenance] Purging generations created before {cutoff.isoformat()}")

    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(LogoGeneration.id, LogoGeneration.image_url)
                .where(LogoGeneration.created_at < cutoff)
            )
            rows = result.all()

            if not rows:
                logger.info("[Maintenance] Nothing to purge")
                return

            ids = [row[0] for row in rows]
            urls = [row[1] for row in rows]

            await session.execute(delete(LogoGeneration).where(LogoGeneration.id.in_(ids)))
            await session.commit()
        except Exception as exc:
            await session.rollback()
            logger.error(f"[Maintenance] Purge query failed: {exc}")
            return

    # Best-effort R2 cleanup — see docstring note above.
    client = get_r2_client()
    deleted_images = 0
    if client and R2_BUCKET_NAME:
        for url in urls:
            key = r2_key_from_url(url)
            if not key:
                continue
            try:
                client.delete_object(Bucket=R2_BUCKET_NAME, Key=key)
                deleted_images += 1
            except Exception as exc:
                logger.warning(f"[Maintenance] Failed to delete R2 object {key}: {exc}")

    audit = AuditRepository(AsyncSessionLocal)
    await audit.log(
        event_type="retention_purge",
        detail=(
            f"deleted_rows={len(ids)} deleted_images={deleted_images} "
            f"retention_days={DATA_RETENTION_DAYS} cutoff={cutoff.isoformat()}"
        ),
    )

    logger.info(
        f"[Maintenance] Purged {len(ids)} generation(s), {deleted_images} R2 object(s)"
    )


async def startup(ctx):
    logger.info(
        f"[Maintenance Worker] Starting up — retention window: {DATA_RETENTION_DAYS} days"
    )


async def shutdown(ctx):
    logger.info("[Maintenance Worker] Shutting down...")


class WorkerSettings:
    """
    ARQ cron-only worker. No `functions` (no queue-consumed job tasks) —
    only a scheduled `cron_jobs` entry. Run as its own process:
        arq maintenance_worker.WorkerSettings
    """
    cron_jobs = [
        cron(purge_expired_generations, hour=3, minute=0),  # 03:00 UTC daily
    ]
    redis_settings = REDIS_SETTINGS
    on_startup = startup
    on_shutdown = shutdown

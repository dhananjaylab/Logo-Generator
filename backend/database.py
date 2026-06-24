import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, DateTime, Float, Boolean, func, event
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

# Get DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

# Neon.tech provides postgresql:// URLs, but for asyncpg we need postgresql+asyncpg://
if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# SECURITY FIX (P1.5): SQL echo is ALWAYS disabled.
# Previously, echo=True in development logged every SQL statement including
# INSERT parameter values, exposing user_id, brand_name, and prompt in logs.
# Controlled debug logging is done via the event listener below instead.
_echo_sql = False

if engine := create_async_engine(
    DATABASE_URL,
    echo=_echo_sql,
    pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
    pool_pre_ping=True,
) if DATABASE_URL else None:

    # Safe debug logging: logs the SQL statement shape but NEVER parameter values.
    # Only active when LOG_LEVEL=DEBUG is explicitly set.
    if os.getenv("LOG_LEVEL", "").upper() == "DEBUG":
        @event.listens_for(engine.sync_engine, "before_cursor_execute")
        def _log_query_shape(conn, cursor, statement, parameters, context, executemany):
            # Truncate to 200 chars — enough to identify the query, never enough
            # to reconstruct PII from long INSERT statements.
            logger.debug("[DB] SQL: %.200s", statement.replace("\n", " "))

    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
else:
    AsyncSessionLocal = None


class Base(DeclarativeBase):
    pass


class LogoGeneration(Base):
    __tablename__ = "logo_generations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # SECURITY FIX (P1.4 / VULN-04): Raw IP addresses are personal data under GDPR
    # Article 4(1) and CCPA. The raw ip_address column has been replaced with a
    # 16-character hex hash derived from SHA-256(IP_HASH_SALT + ":" + ip).
    # See Alembic migration 003_anonymise_ip.py and utils.anonymise_ip().
    ip_hash: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)

    brand_name: Mapped[str] = mapped_column(String(255))
    prompt: Mapped[str] = mapped_column(Text)
    generator: Mapped[str] = mapped_column(String(50))
    image_url: Mapped[str] = mapped_column(Text)

    # P3.2 — Estimated cost in USD for this generation (see config.GENERATION_COST_USD).
    # Nullable so historical rows created before this column existed remain valid.
    cost_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class AuditLog(Base):
    """
    P3.4 — Application-level audit trail for AI generation events and
    privacy-relevant actions (data deletion, retention purges).

    This is "tamper-evident by convention" rather than cryptographically
    tamper-proof: rows are only ever inserted or have user_id anonymised,
    never deleted by application code (except by direct DBA action). It
    satisfies Harvard checklist F19 (logging/audit info for operational
    support) and ESM §6/§7 (security audit trail, ethical review evidence).

    NOTE on GDPR interaction: when a user exercises their right to erasure
    via DELETE /api/v1/me/data, their LogoGeneration rows are hard-deleted,
    but their AuditLog rows are anonymised (user_id → 'deleted-user') rather
    than removed. Security/compliance audit trails are typically retained
    under GDPR Art. 17(3)(b) (legal-obligation exemption) even after erasure
    of the underlying personal data.
    """
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(50), index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    ip_hash: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    brand_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    generator: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    moderation_flagged: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    moderation_categories: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cost_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), index=True)


async def init_db():
    if not engine:
        return
    env = os.getenv("ENV", "development")
    if env == "production":
        logger.info("[DB] Production mode — schema managed by Alembic. Skipping create_all.")
    else:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("[DB] ✓ Tables created/verified (development mode)")


async def get_db():
    if not AsyncSessionLocal:
        yield None
        return

    async with AsyncSessionLocal() as session:
        yield session

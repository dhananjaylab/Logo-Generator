import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, DateTime, func
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Get DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

# Neon.tech provides postgresql:// URLs, but for asyncpg we need postgresql+asyncpg://
if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Production: disable SQL echo to avoid stdout flooding. Development: show SQL.
_echo_sql = os.getenv("ENV", "development") != "production"

if engine := create_async_engine(
    DATABASE_URL,
    echo=_echo_sql,
    pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
    pool_pre_ping=True,   # detect stale connections without a query failure
) if DATABASE_URL else None:
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
else:
    AsyncSessionLocal = None

class Base(DeclarativeBase):
    pass

class LogoGeneration(Base):
    __tablename__ = "logo_generations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    brand_name: Mapped[str] = mapped_column(String(255))
    prompt: Mapped[str] = mapped_column(Text)
    generator: Mapped[str] = mapped_column(String(50))
    image_url: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

async def init_db():
    if not engine:
        return
    env = os.getenv("ENV", "development")
    if env == "production":
        # Production schema is managed by Alembic migrations.
        # Run `alembic upgrade head` before starting the server.
        import logging
        logger = logging.getLogger(__name__)
        logger.info("[DB] Production mode — schema managed by Alembic. Skipping create_all.")
    else:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        import logging
        logger = logging.getLogger(__name__)
        logger.info("[DB] ✓ Tables created/verified (development mode)")

async def get_db():
    if not AsyncSessionLocal:
        # Fallback or informative error
        yield None
        return
        
    async with AsyncSessionLocal() as session:
        yield session

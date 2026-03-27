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

if engine := create_async_engine(DATABASE_URL, echo=True) if DATABASE_URL else None:
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
    if engine:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

async def get_db():
    if not AsyncSessionLocal:
        # Fallback or informative error
        yield None
        return
        
    async with AsyncSessionLocal() as session:
        yield session

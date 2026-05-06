from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
# SQLite (used in tests) does not support pool_size / max_overflow.
_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

_engine_kwargs: dict[str, Any] = {
    "echo": settings.DEBUG,
    "future": True,
}
if not _is_sqlite:
    _engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
    _engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
    _engine_kwargs["pool_pre_ping"] = True          # recycle stale connections
    _engine_kwargs["pool_recycle"] = 1800           # recycle every 30 min

engine: AsyncEngine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


# ---------------------------------------------------------------------------
# Table initialisation (dev / test convenience — production uses Alembic)
# ---------------------------------------------------------------------------
async def init_db() -> None:
    """Create all tables that are registered on Base.metadata.

    Only runs in test environment. In production, Alembic handles migrations.
    """
    if settings.ENVIRONMENT == "test":
        import app.models  # noqa: F401
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialised (test mode)")


async def close_db() -> None:
    """Dispose the engine connection pool (call on app shutdown)."""
    await engine.dispose()
    logger.info("Database engine disposed")


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an AsyncSession and handle commit / rollback automatically.

    Usage::

        @router.get("/")
        async def handler(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

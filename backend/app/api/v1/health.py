from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def health(
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis)
):
    """Health check endpoint with database and Redis connectivity tests."""
    db_status = "connected"
    redis_status = "connected"

    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    try:
        await redis.ping()
    except Exception:
        redis_status = "error"

    overall_status = "healthy" if db_status == "connected" and redis_status == "connected" else "degraded"

    return {
        "status": overall_status,
        "version": settings.APP_VERSION,
        "database": db_status,
        "redis": redis_status,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

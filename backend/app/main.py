from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.database import close_db, init_db
from app.core.redis import close_redis, init_redis
from app.api.v1.router import api_router
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Rate limiter with Redis storage for persistence across restarts
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- startup ----
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    await init_redis()
    # init_db() creates tables when running without Alembic (tests / dev)
    await init_db()
    
    # Check ffmpeg availability
    from app.services.transcription_service import _check_ffmpeg
    ffmpeg_available = await _check_ffmpeg()
    if not ffmpeg_available:
        logger.warning(
            "ffmpeg not found — audio/video processing may be limited. "
            "Install ffmpeg for full functionality."
        )
    app.state.ffmpeg_available = ffmpeg_available
    
    yield
    # ---- shutdown ----
    await close_redis()
    await close_db()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # Rate limiter
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID middleware
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "unknown")
        
        # Log full details internally — never send to client
        logger.error(
            "Unhandled exception",
            extra={
                "request_id": request_id,
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
                "path": str(request.url),
                "method": request.method,
            },
            exc_info=True
        )
        
        # Send ONLY generic message to client
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An internal error occurred. Please try again later.",
                "request_id": request_id  # Safe — just a UUID
            }
        )

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    return app


app = create_app()

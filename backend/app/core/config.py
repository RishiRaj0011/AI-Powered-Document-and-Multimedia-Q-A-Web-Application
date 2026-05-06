from __future__ import annotations

import json
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ------------------------------------------------------------------ App
    APP_NAME: str = "DocQA API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "production"  # override to "test" in tests

    # ------------------------------------------------------------------ Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ------------------------------------------------------------------ Database
    DATABASE_URL: str
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # ------------------------------------------------------------------ Redis
    REDIS_URL: str = "redis://redis:6379/0"
    CACHE_TTL: int = 3600

    # ------------------------------------------------------------------ Pinecone
    PINECONE_API_KEY: str
    PINECONE_ENVIRONMENT: str
    PINECONE_INDEX_NAME: str = "docqa-index"

    # ------------------------------------------------------------------ OpenAI
    OPENAI_API_KEY: str
    OPENAI_CHAT_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # ------------------------------------------------------------------ File upload
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: List[str] = ["pdf", "mp3", "mp4", "wav", "m4a", "webm"]
    UPLOAD_DIR: str = "uploads"

    # ------------------------------------------------------------------ CORS
    # Accepts either a JSON array string or a comma-separated string from .env
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors(cls, v: object) -> List[str]:
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            stripped = v.strip()
            if stripped.startswith("["):
                return json.loads(stripped)
            return [origin.strip() for origin in stripped.split(",") if origin.strip()]
        raise ValueError(f"Cannot parse CORS_ORIGINS from {v!r}")

    @field_validator("ALLOWED_EXTENSIONS", mode="before")
    @classmethod
    def _parse_extensions(cls, v: object) -> List[str]:
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            stripped = v.strip()
            if stripped.startswith("["):
                return json.loads(stripped)
            return [e.strip().lstrip(".").lower() for e in stripped.split(",") if e.strip()]
        raise ValueError(f"Cannot parse ALLOWED_EXTENSIONS from {v!r}")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()

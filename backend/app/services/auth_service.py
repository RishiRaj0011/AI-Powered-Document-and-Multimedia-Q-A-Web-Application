from __future__ import annotations

from datetime import datetime, timezone

import redis.asyncio as aioredis
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.repositories.user_repository import UserRepository
from app.schemas.user import TokenResponse, UserOut


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = UserRepository(db)

    # ------------------------------------------------------------------
    # Register
    # ------------------------------------------------------------------

    async def register(
        self,
        email: str,
        password: str,
        full_name: str | None = None,
    ) -> TokenResponse:
        if await self.repo.get_by_email(email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email already exists",
            )

        user = await self.repo.create(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
        )

        return TokenResponse(
            access_token=create_access_token({"sub": str(user.id)}),
            refresh_token=create_refresh_token({"sub": str(user.id)}),
            user=UserOut.model_validate(user),
        )

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self.repo.get_by_email(email)

        # Deliberate: same error for wrong email OR wrong password (no enumeration)
        if user is None or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated",
            )

        await self.repo.update_last_login(user.id)

        return TokenResponse(
            access_token=create_access_token({"sub": str(user.id)}),
            refresh_token=create_refresh_token({"sub": str(user.id)}),
            user=UserOut.model_validate(user),
        )

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    async def refresh_tokens(self, refresh_token: str, redis: aioredis.Redis) -> TokenResponse:
        payload = decode_token(refresh_token)

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type — refresh token required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        old_jti = payload.get("jti")
        if not old_jti:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token structure",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if already blacklisted (prevents token reuse)
        if await redis.exists(f"blacklist:{old_jti}"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token already used",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            user_id = int(payload["sub"])
        except (KeyError, ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token subject",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = await self.repo.get_by_id(user_id)
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Blacklist the old refresh token
        exp = payload.get("exp", 0)
        ttl = max(int(exp - datetime.now(timezone.utc).timestamp()), 1)
        await redis.set(f"blacklist:{old_jti}", "1", ex=ttl)

        return TokenResponse(
            access_token=create_access_token({"sub": str(user.id)}),
            refresh_token=create_refresh_token({"sub": str(user.id)}),
            user=UserOut.model_validate(user),
        )

    # ------------------------------------------------------------------
    # Logout  (blacklist the access token's jti in Redis)
    # ------------------------------------------------------------------

    @staticmethod
    async def logout(token: str, redis: aioredis.Redis) -> None:
        """Store the token's jti in Redis until the token naturally expires.

        Any subsequent request carrying this token will be rejected by
        get_current_user once it checks the blacklist.
        """
        try:
            payload = decode_token(token)
        except HTTPException:
            # Already invalid — nothing to blacklist
            return

        jti: str | None = payload.get("jti")
        exp: int | None = payload.get("exp")

        if not jti:
            return

        # TTL = seconds remaining until the token expires (minimum 1 s)
        if exp:
            ttl = max(1, exp - int(datetime.now(timezone.utc).timestamp()))
        else:
            ttl = 1800  # fallback: 30 min

        await redis.set(f"blacklist:{jti}", "1", ex=ttl)

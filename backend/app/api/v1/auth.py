from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import Optional

from app.core.dependencies import get_current_user, get_db
from app.core.redis import get_redis
from app.models.user import User
from app.schemas.user import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

_bearer = HTTPBearer(auto_error=False)
limiter = Limiter(key_func=get_remote_address)


# ---------------------------------------------------------------------------
# POST /register
# ---------------------------------------------------------------------------

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(
    request: Request,
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Create a new account and return a token pair."""
    return await AuthService(db).register(
        email=body.email,
        password=body.password,
        full_name=body.full_name,
    )


# ---------------------------------------------------------------------------
# POST /login
# ---------------------------------------------------------------------------

@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate and return a token pair."""
    return await AuthService(db).login(email=body.email, password=body.password)


# ---------------------------------------------------------------------------
# POST /refresh
# ---------------------------------------------------------------------------

@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
async def refresh(
    request: Request,
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis),
) -> TokenResponse:
    """Exchange a valid refresh token for a new token pair."""
    return await AuthService(db).refresh_tokens(body.refresh_token, redis)


# ---------------------------------------------------------------------------
# GET /me
# ---------------------------------------------------------------------------

@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)) -> UserOut:
    """Return the profile of the currently authenticated user."""
    return UserOut.model_validate(current_user)


# ---------------------------------------------------------------------------
# POST /logout
# ---------------------------------------------------------------------------

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    redis=Depends(get_redis),
) -> dict:
    """Blacklist the supplied access token's jti in Redis.

    The token remains cryptographically valid until expiry, but
    get_current_user will reject it once the jti appears in the blacklist.
    Clients should discard both tokens on receipt of this response.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    await AuthService.logout(credentials.credentials, redis)
    return {"message": "Successfully logged out"}

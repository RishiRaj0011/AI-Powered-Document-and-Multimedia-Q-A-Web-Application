from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator


# ---------------------------------------------------------------------------
# Outbound
# ---------------------------------------------------------------------------

class UserOut(BaseModel):
    id: int
    email: str
    full_name: str | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------------------------------------------------------------------------
# Inbound
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None

    @field_validator("password")
    @classmethod
    def _validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


# ---------------------------------------------------------------------------
# Legacy aliases kept so existing imports don't break
# ---------------------------------------------------------------------------
UserCreate = RegisterRequest
UserLogin = LoginRequest
UserResponse = UserOut

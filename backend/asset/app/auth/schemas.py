import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from app.domain.user import Role


class PasswordMixin:
    @staticmethod
    def validate_password_strength(v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit.")
        if not re.search(r"[@$!%*?&_#^+-]", v):
            raise ValueError("Password must contain at least one special character (e.g. @, $, !, %, *, ?, &, _, #).")
        return v


class UserSignupRequest(BaseModel, PasswordMixin):
    email: EmailStr
    password: str = Field(..., description="Plain-text password enforcing enterprise complexity constraints")
    name: str = Field(..., min_length=2, max_length=100)

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return cls.validate_password_strength(v)


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    name: str
    role: Role
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel, PasswordMixin):
    token: str
    new_password: str = Field(..., description="New plain-text password enforcing complexity constraints")

    @field_validator("new_password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return cls.validate_password_strength(v)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False

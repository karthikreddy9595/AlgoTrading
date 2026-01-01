from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    phone: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone: Optional[str] = None


class UserResponse(UserBase):
    id: UUID
    is_active: bool
    is_admin: bool
    email_verified: bool
    phone_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    exp: datetime
    type: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


class PasswordReset(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)


class BrokerConnectionCreate(BaseModel):
    broker: str = Field(..., pattern="^(fyers|zerodha|angel|upstox)$")
    api_key: Optional[str] = None
    api_secret: Optional[str] = None


class BrokerConnectionResponse(BaseModel):
    id: UUID
    broker: str
    is_active: bool
    token_expiry: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


from typing import Optional
from pydantic import BaseModel, EmailStr, UUID4
from datetime import datetime


# Shared properties
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str


# Properties to receive via API on creation (POST /auth/register)
class UserCreate(UserBase):
    password: str


# Properties to receive via API on admin creation (POST /auth/admin/register)
class AdminCreate(UserCreate):
    admin_secret: str


# Properties to receive via API on update (PATCH /auth/me)
class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None


class UserInDBBase(UserBase):
    id: UUID4
    role: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Properties returned via API
class User(UserInDBBase):
    pass


# Compact user for nested responses (admin booking view)
class UserSummary(BaseModel):
    id: UUID4
    full_name: str
    email: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: User


class TokenPayload(BaseModel):
    sub: Optional[str] = None

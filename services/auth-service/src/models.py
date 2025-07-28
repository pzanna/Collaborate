"""
Database models for the Authentication Service

Using SQLModel for both database models and Pydantic data models.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field
from sqlmodel import SQLModel


class UserBase(SQLModel):
    """Base user model with common fields."""
    username: str = Field(index=True, max_length=50)
    email: EmailStr = Field(index=True)
    full_name: Optional[str] = Field(default=None, max_length=100)
    role: str = Field(default="researcher", max_length=20)


class User(UserBase, table=True):
    """User table model."""
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    is_disabled: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class UserCreate(UserBase):
    """User creation model."""
    password: str = Field(min_length=8, max_length=100)


class UserUpdate(SQLModel):
    """User update model."""
    username: Optional[str] = Field(default=None, max_length=50)
    email: Optional[EmailStr] = Field(default=None)
    full_name: Optional[str] = Field(default=None, max_length=100)
    password: Optional[str] = Field(default=None, min_length=8, max_length=100)
    role: Optional[str] = Field(default=None, max_length=20)


class UserPublic(UserBase):
    """Public user model (without sensitive data)."""
    id: int
    is_disabled: bool
    created_at: datetime


class UserInDB(User):
    """User model for internal use (includes hashed password)."""
    pass


class Token(BaseModel):
    """JWT token response model."""
    access_token: str
    refresh_token: str
    token_type: str


class TokenData(BaseModel):
    """Token data model for validation."""
    username: Optional[str] = None


class LoginRequest(BaseModel):
    """Login request model."""
    username: str
    password: str

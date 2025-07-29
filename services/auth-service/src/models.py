"""
Database models for the Authentication Service

Using SQLModel for both database models and Pydantic data models.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field
from sqlmodel import SQLModel, Field as SQLField


class UserBase(SQLModel):
    """Base user model with common fields."""
    email: EmailStr = SQLField(index=True, unique=True)
    full_name: Optional[str] = SQLField(default=None, max_length=100)
    role: str = SQLField(default="researcher", max_length=20)


class User(UserBase, table=True):
    """User table model."""
    id: Optional[int] = SQLField(default=None, primary_key=True)
    hashed_password: str
    is_disabled: bool = SQLField(default=False)
    # 2FA fields
    totp_secret: Optional[str] = SQLField(default=None)  # TOTP secret key
    is_2fa_enabled: bool = SQLField(default=False)  # Whether 2FA is enabled
    backup_codes: Optional[str] = SQLField(default=None)  # JSON string of backup codes
    # Timestamps
    created_at: datetime = SQLField(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = SQLField(default=None)


class UserCreate(UserBase):
    """User creation model."""
    password: str = Field(min_length=8, max_length=100)


class UserUpdate(SQLModel):
    """User update model."""
    email: Optional[EmailStr] = Field(default=None)
    full_name: Optional[str] = Field(default=None, max_length=100)
    password: Optional[str] = Field(default=None, min_length=8, max_length=100)
    role: Optional[str] = Field(default=None, max_length=20)


class UserPublic(UserBase):
    """Public user model (without sensitive data)."""
    id: int
    is_disabled: bool
    is_2fa_enabled: bool
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
    email: str


class LoginRequest(BaseModel):
    """Login request model."""
    email: str
    password: str


class LoginWith2FARequest(BaseModel):
    """Login request model with 2FA."""
    email: str
    password: str
    totp_code: Optional[str] = Field(default=None, min_length=6, max_length=6)


class Setup2FAResponse(BaseModel):
    """2FA setup response model."""
    secret_key: str
    qr_code_url: str
    backup_codes: list[str]


class Verify2FARequest(BaseModel):
    """2FA verification request model."""
    totp_code: str = Field(min_length=6, max_length=6)


class Disable2FARequest(BaseModel):
    """2FA disable request model."""
    password: str
    totp_code: Optional[str] = Field(default=None, min_length=6, max_length=6)
    backup_code: Optional[str] = Field(default=None)


class BackupCodeRequest(BaseModel):
    """Backup code usage request model."""
    backup_code: str

"""
Configuration settings for the Authentication Service.
"""

import os
import secrets
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    DATABASE_URL: str = "sqlite:///./auth.db"
    
    # JWT Settings
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Service Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8013
    DEBUG: bool = False
    
    # CORS Settings
    ALLOWED_ORIGINS: list = ["http://localhost:3000", "http://localhost:8001"]
    
    model_config = {"env_file": ".env", "case_sensitive": True}


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()

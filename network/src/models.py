"""
Data models and schemas for the network service.

This module defines the standard data models used across the service,
including request/response schemas, database models, and internal data structures.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


# Standard service information models
class ServiceInfo(BaseModel):
    """Service information model."""
    name: str
    version: str
    description: str
    status: str = "running"
    timestamp: datetime = Field(default_factory=datetime.now)




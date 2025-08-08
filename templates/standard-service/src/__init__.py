"""
Standard Service Package

This package provides the standardized structure and common functionality
for all Eunice Research Platform services and agents.
"""

__version__ = "1.0.0"
__author__ = "Eunice Research Platform"
__email__ = "support@eunice-platform.com"

# Service metadata
SERVICE_NAME = "SERVICE_NAME_PLACEHOLDER"
SERVICE_VERSION = __version__
SERVICE_DESCRIPTION = "SERVICE_DESCRIPTION_PLACEHOLDER"

# Export main components
from .main import main
from .config import Config, get_config
from .health_check import HealthCheck

__all__ = [
    "main",
    "Config",
    "get_config", 
    "HealthCheck",
    "SERVICE_NAME",
    "SERVICE_VERSION",
    "SERVICE_DESCRIPTION"
]

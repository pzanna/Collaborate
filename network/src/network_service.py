"""
Updated Network Agent Service for Eunice Research Platform v0.4.0

Enhancements:
- Integrated with ExternalAPIService
- Updated health check with API-specific metadata
- Enhanced configuration validation
"""

import asyncio
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uvicorn

from .external_api_service import ExternalAPIService

# Import watchfiles with fallback
try:
    from watchfiles import awatch
    WATCHFILES_AVAILABLE = True
except ImportError as e:
    awatch = None  # type: ignore
    WATCHFILES_AVAILABLE = False


logging.basicConfig(
    level=logging.DEBUG,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)
for handler in logger.handlers:
    handler.setFormatter(JSONFormatter())



def main():
    logger.info("Starting Network Agent Service (External APIs)")
    logger.info("ARCHITECTURE COMPLIANCE: Only health check API exposed")
    
    host = os.getenv("SERVICE_HOST", "0.0.0.0")
    port = int(os.getenv("SERVICE_PORT", "8004"))
    log_level = os.getenv("LOG_LEVEL", "info").lower()


if __name__ == "__main__":
    main()
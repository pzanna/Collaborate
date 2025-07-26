"""
API Gateway Service Configuration

Centralized configuration management for the containerized API Gateway service.
"""

import os
from typing import Dict, Any, Optional


class Config:
    """API Gateway service configuration"""
    
    # Server Configuration
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8001"))
    
    # MCP Server Configuration
    MCP_SERVER_HOST = os.getenv("MCP_SERVER_HOST", "mcp-server")
    MCP_SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", "9000"))
    MCP_SERVER_URL = f"ws://{MCP_SERVER_HOST}:{MCP_SERVER_PORT}"
    
    # Database Configuration (if needed for future features)
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@postgres:5432/eunice")
    
    # Redis Configuration (for caching and sessions)
    REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
    
    # Authentication Service (for future integration)
    AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8007")
    
    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    # CORS Configuration
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
    
    # API Configuration
    API_TITLE = "Eunice Research Platform API Gateway"
    API_DESCRIPTION = "Unified API gateway for the Eunice research system - Containerized Phase 3"
    API_VERSION = "3.0.0"
    DOCS_URL = "/docs"
    REDOC_URL = "/redoc"
    
    # Service Health Configuration
    HEALTH_CHECK_TIMEOUT = int(os.getenv("HEALTH_CHECK_TIMEOUT", "5"))
    MCP_CONNECTION_RETRY_ATTEMPTS = int(os.getenv("MCP_CONNECTION_RETRY_ATTEMPTS", "3"))
    MCP_CONNECTION_RETRY_DELAY = int(os.getenv("MCP_CONNECTION_RETRY_DELAY", "5"))
    
    # Rate Limiting (future feature)
    RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "1000"))
    RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "3600"))  # 1 hour
    
    @classmethod
    def get_mcp_config(cls) -> Dict[str, Any]:
        """Get MCP client configuration"""
        return {
            "host": cls.MCP_SERVER_HOST,
            "port": cls.MCP_SERVER_PORT,
            "url": cls.MCP_SERVER_URL,
            "retry_attempts": cls.MCP_CONNECTION_RETRY_ATTEMPTS,
            "retry_delay": cls.MCP_CONNECTION_RETRY_DELAY
        }
    
    @classmethod
    def get_server_config(cls) -> Dict[str, Any]:
        """Get server configuration"""
        return {
            "host": cls.HOST,
            "port": cls.PORT,
            "log_level": cls.LOG_LEVEL.lower(),
            "access_log": True
        }
    
    @classmethod
    def get_cors_config(cls) -> Dict[str, Any]:
        """Get CORS configuration"""
        return {
            "allow_origins": cls.CORS_ORIGINS,
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"]
        }
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate configuration settings"""
        required_vars = [
            "MCP_SERVER_HOST",
            "MCP_SERVER_PORT"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not hasattr(cls, var) or getattr(cls, var) is None:
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required configuration variables: {missing_vars}")
        
        return True

"""
Configuration management for the database service.

This module provides standardized configuration loading from:
- Environment variables
- Configuration files (JSON)
- Default values
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class ServiceConfig(BaseModel):
    """Service-specific configuration."""
    name: str = "database"
    version: str = "1.0.0"
    description: str = "SERVICE_DESCRIPTION_PLACEHOLDER"
    host: str = Field(default="0.0.0.0", env="SERVICE_HOST")
    port: int = Field(default=8000, env="SERVICE_PORT")
    debug: bool = Field(default=False, env="DEBUG")


class MCPConfig(BaseModel):
    """MCP client configuration."""
    server_url: str = Field(default="ws://mcp-server:9000", env="MCP_SERVER_URL")
    timeout: int = Field(default=30, env="MCP_TIMEOUT")
    retry_attempts: int = Field(default=3, env="MCP_RETRY_ATTEMPTS")
    retry_delay: int = Field(default=5, env="MCP_RETRY_DELAY")


class DatabaseConfig(BaseModel):
    """Database configuration."""
    url: str = Field(default="postgresql://postgres:password@postgres:5432/eunice", env="DATABASE_URL")
    pool_size: int = Field(default=10, env="DB_POOL_SIZE")
    max_overflow: int = Field(default=20, env="DB_MAX_OVERFLOW")
    pool_timeout: int = Field(default=30, env="DB_POOL_TIMEOUT")


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(default="INFO", env="LOG_LEVEL")
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_logging: bool = Field(default=False, env="LOG_TO_FILE")
    log_file: str = "/app/logs/database.log"


class HealthCheckConfig(BaseModel):
    """Health check configuration."""
    enabled: bool = Field(default=True, env="HEALTH_CHECK_ENABLED")
    interval: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")
    timeout: int = Field(default=5, env="HEALTH_CHECK_TIMEOUT")
    endpoint: str = "/health"


class SecurityConfig(BaseModel):
    """Security configuration."""
    cors_enabled: bool = Field(default=True, env="CORS_ENABLED")
    cors_origins: List[str] = Field(default=["http://localhost:3000"], env="CORS_ORIGINS")
    rate_limiting: bool = Field(default=True, env="RATE_LIMITING_ENABLED")
    max_requests_per_minute: int = Field(default=100, env="MAX_REQUESTS_PER_MINUTE")
    secret_key: str = Field(default="change-in-production", env="SECRET_KEY")


class Config(BaseModel):
    """Main configuration class that combines all configuration sections."""
    service: ServiceConfig = Field(default_factory=ServiceConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    health_check: HealthCheckConfig = Field(default_factory=HealthCheckConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    capabilities: List[str] = Field(default=["health_check", "metrics", "logging"])
    service_specific: Dict[str, Any] = Field(default_factory=dict)


# Global configuration instance
_config_instance: Optional[Config] = None


def load_config_from_file(config_path: str = "config/config.json") -> Dict[str, Any]:
    """Load configuration from JSON file."""
    config_file = Path(config_path)
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load config file {config_path}: {e}")
            return {}
    else:
        print(f"Warning: Config file {config_path} not found, using defaults and environment variables")
        return {}


def load_config_from_env() -> Dict[str, Any]:
    """Load configuration from environment variables."""
    env_config = {}
    
    # Service configuration
    if os.getenv("SERVICE_NAME"):
        env_config.setdefault("service", {})["name"] = os.getenv("SERVICE_NAME")
    if os.getenv("SERVICE_HOST"):
        env_config.setdefault("service", {})["host"] = os.getenv("SERVICE_HOST")
    if os.getenv("SERVICE_PORT"):
        env_config.setdefault("service", {})["port"] = int(os.getenv("SERVICE_PORT"))
    if os.getenv("DEBUG"):
        env_config.setdefault("service", {})["debug"] = os.getenv("DEBUG").lower() == "true"
    
    # MCP configuration
    if os.getenv("MCP_SERVER_URL"):
        env_config.setdefault("mcp", {})["server_url"] = os.getenv("MCP_SERVER_URL")
    if os.getenv("MCP_TIMEOUT"):
        env_config.setdefault("mcp", {})["timeout"] = int(os.getenv("MCP_TIMEOUT"))
    
    # Database configuration
    if os.getenv("DATABASE_URL"):
        env_config.setdefault("database", {})["url"] = os.getenv("DATABASE_URL")
    
    # Logging configuration
    if os.getenv("LOG_LEVEL"):
        env_config.setdefault("logging", {})["level"] = os.getenv("LOG_LEVEL")
    if os.getenv("LOG_TO_FILE"):
        env_config.setdefault("logging", {})["file_logging"] = os.getenv("LOG_TO_FILE").lower() == "true"
    
    # Security configuration
    if os.getenv("SECRET_KEY"):
        env_config.setdefault("security", {})["secret_key"] = os.getenv("SECRET_KEY")
    if os.getenv("CORS_ORIGINS"):
        env_config.setdefault("security", {})["cors_origins"] = os.getenv("CORS_ORIGINS").split(",")
    
    return env_config


def merge_configs(file_config: Dict[str, Any], env_config: Dict[str, Any]) -> Dict[str, Any]:
    """Merge file and environment configurations, with environment taking precedence."""
    merged = file_config.copy()
    
    for key, value in env_config.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key].update(value)
        else:
            merged[key] = value
    
    return merged


def get_config(config_path: str = "config/config.json") -> Config:
    """Get the global configuration instance."""
    global _config_instance
    
    if _config_instance is None:
        # Load configuration from file and environment
        file_config = load_config_from_file(config_path)
        env_config = load_config_from_env()
        
        # Merge configurations (environment takes precedence)
        merged_config = merge_configs(file_config, env_config)
        
        # Create Config instance
        _config_instance = Config(**merged_config)
    
    return _config_instance


def reload_config(config_path: str = "config/config.json") -> Config:
    """Reload configuration from file and environment."""
    global _config_instance
    _config_instance = None
    return get_config(config_path)


# Development helper to validate configuration
def validate_config() -> bool:
    """Validate the current configuration."""
    try:
        config = get_config()
        # Add custom validation logic here
        return True
    except Exception as e:
        print(f"Configuration validation failed: {e}")
        return False


if __name__ == "__main__":
    # Test configuration loading
    config = get_config()
    print("Configuration loaded successfully:")
    print(f"Service: {config.service.name} v{config.service.version}")
    print(f"Host: {config.service.host}:{config.service.port}")
    print(f"Debug: {config.service.debug}")
    print(f"Log Level: {config.logging.level}")
    
    # Validate configuration
    is_valid = validate_config()
    print(f"Configuration valid: {is_valid}")

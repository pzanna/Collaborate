"""Simple configuration management without external dependencies."""

import json
import os
from typing import Dict, Any


class SimpleConfig:
    """Simple configuration class that loads from JSON and environment variables."""
    
    def __init__(self, config_path: str = "config/config.json"):
        self.config_data = self._load_config(config_path)
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from JSON file with environment overrides."""
        
        # Default configuration
        default_config = {
            "service": {
                "name": "api_gateway",
                "version": "1.0.0", 
                "description": "Eunice api-gateway service",
                "environment": "development"
            },
            "server": {
                "host": "0.0.0.0",
                "port": 8001
            },
            "database": {
                "url": "postgresql://eunice:eunice@database:5432/eunice",
                "echo": False,
                "pool_size": 10,
                "max_overflow": 20
            },
            "logging": {
                "level": "DEBUG",
                "file": "/app/logs/service.log",
                "max_file_size": "100MB",
                "backup_count": 5
            },
            "security": {
                "cors_origins": ["*"],
                "cors_methods": ["GET", "POST", "PUT", "DELETE"],
                "cors_headers": ["*"]
            },
            "health_check": {
                "enabled": True,
                "interval": 30,
                "timeout": 10
            }
        }
        
        # Try to load from file if it exists
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    file_config = json.load(f)
                    # Merge with defaults
                    default_config.update(file_config)
            except Exception as e:
                print(f"Warning: Could not load config file {config_path}: {e}")
        
        # Apply environment variable overrides
        if "server" in default_config:
            default_config["server"]["host"] = os.getenv("SERVICE_HOST", default_config["server"]["host"])
            default_config["server"]["port"] = int(os.getenv("SERVICE_PORT", str(default_config["server"]["port"])))
        
        if "database" in default_config:
            default_config["database"]["url"] = os.getenv("DATABASE_URL", default_config["database"]["url"])
        
        if "logging" in default_config:
            default_config["logging"]["level"] = os.getenv("LOG_LEVEL", default_config["logging"]["level"])
        
        return default_config
    
    @property
    def service(self):
        """Get service configuration."""
        return ConfigSection(self.config_data.get("service", {}))
    
    @property
    def server(self):
        """Get server configuration."""
        return ConfigSection(self.config_data.get("server", {}))
    
    @property
    def database(self):
        """Get database configuration."""
        return ConfigSection(self.config_data.get("database", {}))
    
    @property
    def logging(self):
        """Get logging configuration."""
        return ConfigSection(self.config_data.get("logging", {}))
    
    @property
    def security(self):
        """Get security configuration."""
        return ConfigSection(self.config_data.get("security", {}))
    
    @property
    def health_check(self):
        """Get health check configuration."""
        return ConfigSection(self.config_data.get("health_check", {}))


class ConfigSection:
    """Wrapper for configuration sections that allows dot notation access."""
    
    def __init__(self, data: Dict[str, Any]):
        self._data = data
    
    def __getattr__(self, name: str):
        if name in self._data:
            value = self._data[name]
            if isinstance(value, dict):
                return ConfigSection(value)
            return value
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    def __getitem__(self, key: str):
        return self._data[key]
    
    def get(self, key: str, default=None):
        return self._data.get(key, default)


def get_config() -> SimpleConfig:
    """Get the configuration instance."""
    return SimpleConfig()

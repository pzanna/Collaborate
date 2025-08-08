"""
Unit tests for network configuration module.
"""

import json
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

from src.config import Config, get_config, load_config_file


class TestConfig:
    """Test cases for Config class."""
    
    def test_config_creation_with_defaults(self):
        """Test config creation with default values."""
        config = Config()
        
        assert config.service.name == "service"
        assert config.service.version == "1.0.0"
        assert config.service.environment == "development"
        assert config.server.host == "0.0.0.0"
        assert config.server.port == 8000
        assert not config.server.debug
    
    def test_config_from_environment_variables(self):
        """Test config creation from environment variables."""
        env_vars = {
            "SERVICE_NAME": "test-service",
            "SERVICE_VERSION": "2.0.0",
            "SERVICE_ENVIRONMENT": "production",
            "SERVICE_HOST": "localhost",
            "SERVICE_PORT": "9000",
            "SERVICE_DEBUG": "true",
            "LOG_LEVEL": "ERROR",
            "DATABASE_URL": "postgresql://user:pass@localhost/db",
            "MCP_SERVER_URL": "ws://localhost:8081"
        }
        
        with patch.dict(os.environ, env_vars):
            config = Config()
            
            assert config.service.name == "test-service"
            assert config.service.version == "2.0.0"
            assert config.service.environment == "production"
            assert config.server.host == "localhost"
            assert config.server.port == 9000
            assert config.server.debug
            assert config.logging.level == "ERROR"
            assert config.database.url == "postgresql://user:pass@localhost/db"
            assert config.mcp.server_url == "ws://localhost:8081"
    
    def test_config_boolean_parsing(self):
        """Test boolean environment variable parsing."""
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False),
            ("no", False),
            ("", False),
            ("invalid", False)
        ]
        
        for env_value, expected in test_cases:
            with patch.dict(os.environ, {"SERVICE_DEBUG": env_value}):
                config = Config()
                assert config.server.debug == expected
    
    def test_config_port_parsing(self):
        """Test port number parsing from environment."""
        with patch.dict(os.environ, {"SERVICE_PORT": "8080"}):
            config = Config()
            assert config.server.port == 8080
        
        # Test invalid port falls back to default
        with patch.dict(os.environ, {"SERVICE_PORT": "invalid"}):
            config = Config()
            assert config.server.port == 8000


class TestConfigFile:
    """Test cases for configuration file loading."""
    
    def test_load_config_file_json(self, temp_directory):
        """Test loading JSON configuration file."""
        config_data = {
            "service": {
                "name": "file-service",
                "version": "3.0.0"
            },
            "server": {
                "port": 9999
            }
        }
        
        config_file = temp_directory / "config.json"
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        result = load_config_file(str(config_file))
        
        assert result["service"]["name"] == "file-service"
        assert result["service"]["version"] == "3.0.0"
        assert result["server"]["port"] == 9999
    
    def test_load_config_file_yaml(self, temp_directory):
        """Test loading YAML configuration file."""
        config_content = """
        service:
          name: yaml-service
          version: 4.0.0
        server:
          port: 7777
        """
        
        config_file = temp_directory / "config.yaml"
        with open(config_file, 'w') as f:
            f.write(config_content)
        
        result = load_config_file(str(config_file))
        
        assert result["service"]["name"] == "yaml-service"
        assert result["service"]["version"] == "4.0.0"
        assert result["server"]["port"] == 7777
    
    def test_load_config_file_nonexistent(self):
        """Test loading non-existent configuration file."""
        result = load_config_file("/nonexistent/config.json")
        assert result == {}
    
    def test_load_config_file_invalid_json(self, temp_directory):
        """Test loading invalid JSON configuration file."""
        config_file = temp_directory / "invalid.json"
        with open(config_file, 'w') as f:
            f.write("{ invalid json }")
        
        result = load_config_file(str(config_file))
        assert result == {}
    
    def test_load_config_file_invalid_yaml(self, temp_directory):
        """Test loading invalid YAML configuration file."""
        config_file = temp_directory / "invalid.yaml"
        with open(config_file, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        result = load_config_file(str(config_file))
        assert result == {}


class TestGetConfig:
    """Test cases for get_config function."""
    
    def test_get_config_default(self):
        """Test get_config with default settings."""
        config = get_config()
        
        assert isinstance(config, Config)
        assert config.service.name == "service"
    
    def test_get_config_with_file(self, temp_directory):
        """Test get_config with configuration file."""
        config_data = {
            "service": {
                "name": "config-file-service"
            }
        }
        
        config_file = temp_directory / "test_config.json"
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        with patch.dict(os.environ, {"CONFIG_FILE": str(config_file)}):
            config = get_config()
            
            assert config.service.name == "config-file-service"
    
    def test_get_config_env_override_file(self, temp_directory):
        """Test that environment variables override file config."""
        config_data = {
            "service": {
                "name": "file-service",
                "version": "1.0.0"
            }
        }
        
        config_file = temp_directory / "test_config.json"
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        env_vars = {
            "CONFIG_FILE": str(config_file),
            "SERVICE_NAME": "env-service",
            "SERVICE_VERSION": "2.0.0"
        }
        
        with patch.dict(os.environ, env_vars):
            config = get_config()
            
            # Environment should override file
            assert config.service.name == "env-service"
            assert config.service.version == "2.0.0"
    
    @patch('src.config.load_config_file')
    def test_get_config_caching(self, mock_load_config):
        """Test that get_config caches the result."""
        mock_load_config.return_value = {}
        
        # Call get_config twice
        config1 = get_config()
        config2 = get_config()
        
        # Should be the same instance (cached)
        assert config1 is config2
        
        # Should only load file once
        assert mock_load_config.call_count <= 1


class TestConfigValidation:
    """Test cases for configuration validation."""
    
    def test_config_validation_invalid_port(self):
        """Test config validation with invalid port."""
        with patch.dict(os.environ, {"SERVICE_PORT": "-1"}):
            config = Config()
            # Should fall back to default port
            assert config.server.port == 8000
        
        with patch.dict(os.environ, {"SERVICE_PORT": "65536"}):
            config = Config()
            # Should fall back to default port
            assert config.server.port == 8000
    
    def test_config_validation_log_level(self):
        """Test log level validation."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        for level in valid_levels:
            with patch.dict(os.environ, {"LOG_LEVEL": level}):
                config = Config()
                assert config.logging.level == level
        
        # Test invalid level falls back to default
        with patch.dict(os.environ, {"LOG_LEVEL": "INVALID"}):
            config = Config()
            assert config.logging.level == "INFO"
    
    def test_config_validation_environment(self):
        """Test environment validation."""
        valid_envs = ["development", "staging", "production", "test"]
        
        for env in valid_envs:
            with patch.dict(os.environ, {"SERVICE_ENVIRONMENT": env}):
                config = Config()
                assert config.service.environment == env
    
    def test_config_to_dict(self):
        """Test config serialization to dictionary."""
        config = Config()
        config_dict = config.model_dump()
        
        assert isinstance(config_dict, dict)
        assert "service" in config_dict
        assert "server" in config_dict
        assert "database" in config_dict
        assert "mcp" in config_dict
        assert "logging" in config_dict
        assert "health_check" in config_dict
        assert "security" in config_dict
    
    def test_config_json_serialization(self):
        """Test config JSON serialization."""
        config = Config()
        config_json = config.model_dump_json()
        
        assert isinstance(config_json, str)
        
        # Should be valid JSON
        imported_config = json.loads(config_json)
        assert isinstance(imported_config, dict)


# Integration tests
class TestConfigIntegration:
    """Integration tests for configuration system."""
    
    def test_full_config_loading_cycle(self, temp_directory):
        """Test complete configuration loading with file and environment."""
        # Create config file
        config_data = {
            "service": {
                "name": "integration-service",
                "description": "Integration test service"
            },
            "database": {
                "url": "sqlite:///test.db"
            },
            "logging": {
                "level": "DEBUG",
                "file": "/tmp/test.log"
            }
        }
        
        config_file = temp_directory / "integration_config.json"
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        # Set environment variables
        env_vars = {
            "CONFIG_FILE": str(config_file),
            "SERVICE_VERSION": "integration-1.0.0",
            "SERVICE_ENVIRONMENT": "test",
            "SERVICE_PORT": "8888",
            "MCP_SERVER_URL": "ws://test-mcp:8081"
        }
        
        with patch.dict(os.environ, env_vars):
            config = get_config()
            
            # Verify file values
            assert config.service.name == "integration-service"
            assert config.service.description == "Integration test service"
            assert config.database.url == "sqlite:///test.db"
            assert config.logging.level == "DEBUG"
            assert config.logging.file == "/tmp/test.log"
            
            # Verify environment overrides
            assert config.service.version == "integration-1.0.0"
            assert config.service.environment == "test"
            assert config.server.port == 8888
            assert config.mcp.server_url == "ws://test-mcp:8081"

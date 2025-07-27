"""
Configuration Manager for Planning Agent

Provides a simple interface to access configuration values from config.json
and environment variables, compatible with the cost_estimator requirements.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union


class ConfigManager:
    """Simple configuration manager compatible with cost_estimator requirements"""
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "config.json"
        
        self.config_path = str(config_path)
        self._config_data = self._load_config()
        
        # Create a simple object to hold research_manager config
        self.config = self._create_config_object()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: Config file not found at {self.config_path}")
            return {}
        except json.JSONDecodeError as e:
            print(f"Warning: Invalid JSON in config file: {e}")
            return {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation
        
        Args:
            key: Configuration key in dot notation (e.g., 'cost_settings.token_costs')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self._config_data
        
        try:
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            return value
        except (KeyError, TypeError):
            return default
    
    def _create_config_object(self):
        """Create a simple object structure for compatibility"""
        class ResearchManagerConfig:
            def __init__(self, config_data: Dict[str, Any]):
                # Default to OpenAI GPT-4o-mini if not specified
                research_config = config_data.get('research_manager', {})
                self.provider = research_config.get('provider', 'openai')
                self.model = research_config.get('model', 'gpt-4o-mini')
        
        class ConfigObject:
            def __init__(self, config_data: Dict[str, Any]):
                self.research_manager = ResearchManagerConfig(config_data)
        
        return ConfigObject(self._config_data)
    
    def reload(self):
        """Reload configuration from file"""
        self._config_data = self._load_config()
        self.config = self._create_config_object()

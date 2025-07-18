"""Configuration management for the Collaborate application."""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import AIConfig from models
try:
    from ..models.data_models import AIConfig as AIProviderConfig
except ImportError:
    # If running as a script, try different import path
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from models.data_models import AIConfig as AIProviderConfig


class ConversationConfig(BaseModel):
    """Configuration for conversation management."""
    max_context_tokens: int = 8000
    auto_save: bool = True
    max_response_length: int = 1500


class StorageConfig(BaseModel):
    """Configuration for data storage."""
    database_path: str = "data/collaborate.db"
    export_path: str = "exports/"


class LoggingConfig(BaseModel):
    """Configuration for logging."""
    level: str = "INFO"
    file: str = "logs/collaborate.log"


class CoordinationConfig(BaseModel):
    """Configuration for AI coordination."""
    base_participation_chance: float = 0.4
    max_consecutive_turns: int = 2
    mention_boost: float = 0.8
    question_boost: float = 0.3
    engagement_boost: float = 0.2


class Config(BaseModel):
    """Main configuration class."""
    ai_providers: Dict[str, AIProviderConfig] = Field(default_factory=dict)
    conversation: ConversationConfig = Field(default_factory=ConversationConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    coordination: CoordinationConfig = Field(default_factory=CoordinationConfig)


class ConfigManager:
    """Manages application configuration."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._get_default_config_path()
        self.config = self._load_config()
    
    def _get_default_config_path(self) -> str:
        """Get the default configuration file path."""
        return os.getenv("COLLABORATE_CONFIG_PATH", "config/default_config.json")
    
    def _load_config(self) -> Config:
        """Load configuration from file or create default."""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                config_data = json.load(f)

            # Fix provider field in ai_providers
            if 'ai_providers' in config_data:
                for provider_name, provider_config in config_data['ai_providers'].items():
                    if 'provider' not in provider_config:
                        provider_config['provider'] = provider_name
            
            return Config(**config_data)
        else:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
    
    def save_config(self) -> None:
        """Save current configuration to file."""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self.config.model_dump(), f, indent=4)
    
    def get_api_key(self, provider: str) -> str:
        """Get API key for a provider from environment variables."""
        if provider == "openai":
            return os.getenv("OPENAI_API_KEY", "")
        elif provider == "xai":
            return os.getenv("XAI_API_KEY", "")
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def update_provider_config(self, provider: str, **kwargs) -> None:
        """Update configuration for a specific provider."""
        if provider not in self.config.ai_providers:
            self.config.ai_providers[provider] = AIProviderConfig(provider=provider, model="")
        
        for key, value in kwargs.items():
            if hasattr(self.config.ai_providers[provider], key):
                setattr(self.config.ai_providers[provider], key, value)

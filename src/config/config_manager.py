"""Configuration management for the Collaborate application."""

import os
import yaml
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
    response_coordination: bool = True


class StorageConfig(BaseModel):
    """Configuration for data storage."""
    database_path: str = "data/collaborate.db"
    export_path: str = "exports/"


class LoggingConfig(BaseModel):
    """Configuration for logging."""
    level: str = "INFO"
    file: str = "logs/collaborate.log"


class Config(BaseModel):
    """Main configuration class."""
    ai_providers: Dict[str, AIProviderConfig] = Field(default_factory=dict)
    conversation: ConversationConfig = Field(default_factory=ConversationConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


class ConfigManager:
    """Manages application configuration."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._get_default_config_path()
        self.config = self._load_config()
    
    def _get_default_config_path(self) -> str:
        """Get the default configuration file path."""
        return os.getenv("COLLABORATE_CONFIG_PATH", "config/default_config.yaml")
    
    def _load_config(self) -> Config:
        """Load configuration from file or create default."""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Fix provider field in ai_providers
            if 'ai_providers' in config_data:
                for provider_name, provider_config in config_data['ai_providers'].items():
                    if 'provider' not in provider_config:
                        provider_config['provider'] = provider_name
            
            return Config(**config_data)
        else:
            return self._create_default_config()
    
    def _create_default_config(self) -> Config:
        """Create default configuration."""
        return Config(
            ai_providers={
                "openai": AIProviderConfig(
                    provider="openai",
                    model="gpt-4.1-mini",
                    temperature=0.7,
                    max_tokens=2000,
                    system_prompt="You are a helpful research assistant participating in a collaborative discussion.",
                    role_adaptation=True
                ),
                "xai": AIProviderConfig(
                    provider="xai",
                    model="grok-3-mini",
                    temperature=0.7,
                    max_tokens=2000,
                    system_prompt="You are a knowledgeable AI assistant contributing to collaborative research.",
                    role_adaptation=True
                )
            }
        )
    
    def save_config(self) -> None:
        """Save current configuration to file."""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w') as f:
            yaml.dump(self.config.model_dump(), f, default_flow_style=False)
    
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

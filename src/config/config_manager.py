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


class MCPServerConfig(BaseModel):
    """Configuration for MCP server."""
    host: str = "127.0.0.1"
    port: int = 9000
    max_concurrent_tasks: int = 10
    task_timeout: int = 300
    retry_attempts: int = 3
    log_level: str = "INFO"
    enable_task_logging: bool = True
    task_log_file: str = "logs/mcp_tasks.log"


class AgentConfig(BaseModel):
    """Configuration for an individual agent."""
    type: str
    capabilities: list = Field(default_factory=list)
    max_concurrent: int = 1
    timeout: int = 60


class ResearchTasksConfig(BaseModel):
    """Configuration for research tasks."""
    default_priority: str = "normal"
    max_task_queue_size: int = 50
    result_cache_ttl: int = 3600
    enable_task_persistence: bool = True
    task_db: str = "data/research_tasks.db"


class ResearchManagerConfig(BaseModel):
    """Configuration for Research Manager."""
    provider: str = "openai"
    model: str = "gpt-4.1-mini"
    name: str = "Sky"
    max_tokens: int = 2000
    system_prompt: str = ""


class Config(BaseModel):
    """Main configuration class."""
    ai_providers: Dict[str, AIProviderConfig] = Field(default_factory=dict)
    conversation: ConversationConfig = Field(default_factory=ConversationConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    coordination: CoordinationConfig = Field(default_factory=CoordinationConfig)
    mcp_server: MCPServerConfig = Field(default_factory=MCPServerConfig)
    agents: Dict[str, AgentConfig] = Field(default_factory=dict)
    research_tasks: ResearchTasksConfig = Field(default_factory=ResearchTasksConfig)
    research_manager: ResearchManagerConfig = Field(default_factory=ResearchManagerConfig)


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
    
    def get_mcp_config(self) -> Dict[str, Any]:
        """Get MCP server configuration."""
        if hasattr(self.config, 'mcp_server') and self.config.mcp_server:
            return self.config.mcp_server if isinstance(self.config.mcp_server, dict) else self.config.mcp_server.dict()
        return {
            'host': 'localhost',
            'port': 9000,
            'max_connections': 50,
            'heartbeat_interval': 30
        }
    
    def get_research_config(self) -> Dict[str, Any]:
        """Get research task configuration."""
        if hasattr(self.config, 'research_tasks') and self.config.research_tasks:
            return self.config.research_tasks if isinstance(self.config.research_tasks, dict) else self.config.research_tasks.dict()
        return {
            'max_concurrent_tasks': 5,
            'task_timeout': 300,
            'retry_attempts': 3,
            'search_depth': 'comprehensive'
        }
    
    def get_agent_config(self) -> Dict[str, Any]:
        """Get agent configuration."""
        if hasattr(self.config, 'agents') and self.config.agents:
            return self.config.agents if isinstance(self.config.agents, dict) else self.config.agents.dict()
        return {
            'retriever': {'enabled': True, 'max_results': 10},
            'reasoner': {'enabled': True, 'model': 'gpt-4'},
            'executor': {'enabled': True, 'timeout': 60},
            'memory': {'enabled': True, 'max_entries': 1000}
        }

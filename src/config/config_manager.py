"""Configuration management for the Eunice application."""

import os
import json
import logging
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
    database_path: str = "data/eunice.db"
    export_path: str = "exports/"


class LoggingConfig(BaseModel):
    """Configuration for logging."""
    level: str = "INFO"
    file: str = "logs/eunice.log"
    enable_ai_api_logging: bool = True
    ai_api_log_file: str = "logs/ai_api.log"
    ai_api_log_level: str = "INFO"


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
        return os.getenv("EUNICE_CONFIG_PATH", "config/default_config.json")
    
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
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Get a configuration value using dotted notation (e.g., 'storage.database_path')."""
        keys = key_path.split('.')
        value = self.config.model_dump()
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
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
            'task_timeout': 600,
            'retry_attempts': 3,
            'search_depth': 'comprehensive'
        }
    
    def get_agent_config(self) -> Dict[str, Any]:
        """Get agent configuration."""
        if hasattr(self.config, 'agents') and self.config.agents:
            return self.config.agents if isinstance(self.config.agents, dict) else self.config.agents.dict()
        return {
            'retriever': {'enabled': True, 'max_results': 10},
            'planning': {'enabled': True, 'model': 'gpt-4'},
            'executor': {'enabled': True, 'timeout': 60},
            'memory': {'enabled': True, 'max_entries': 1000}
        }
    
    def setup_logging(self) -> None:
        """Set up logging configuration based on config settings."""
        try:
            # Get logging configuration
            logging_config = self.config.logging
            
            # Ensure logs directory exists
            log_file_path = Path(logging_config.file)
            log_file_path.parent.mkdir(exist_ok=True)
            
            # Configure logging
            logging.basicConfig(
                level=getattr(logging, logging_config.level.upper()),
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(logging_config.file),
                    logging.StreamHandler()
                ],
                force=True  # Override any existing configuration
            )
            
            # Set up AI API logging if enabled
            if logging_config.enable_ai_api_logging:
                ai_api_log_path = Path(logging_config.ai_api_log_file)
                ai_api_log_path.parent.mkdir(exist_ok=True)
                
                # Create dedicated logger for AI API calls
                ai_api_logger = logging.getLogger('ai_api')
                ai_api_logger.setLevel(getattr(logging, logging_config.ai_api_log_level.upper()))
                
                # Create file handler for AI API logs
                ai_api_handler = logging.FileHandler(logging_config.ai_api_log_file)
                ai_api_handler.setFormatter(logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                ))
                ai_api_logger.addHandler(ai_api_handler)
                
                # Prevent propagation to root logger to avoid duplicate logs
                ai_api_logger.propagate = False
                
                # Also set up individual AI client loggers
                for client_name in ['ai_clients.openai_client', 'ai_clients.xai_client', 'core.ai_client_manager']:
                    client_logger = logging.getLogger(client_name)
                    client_logger.setLevel(getattr(logging, logging_config.ai_api_log_level.upper()))
                    client_logger.addHandler(ai_api_handler)
                    client_logger.propagate = False
            
            # Set up MCP task logging if enabled
            if hasattr(self.config, 'mcp_server') and self.config.mcp_server.enable_task_logging:
                task_log_path = Path(self.config.mcp_server.task_log_file)
                task_log_path.parent.mkdir(exist_ok=True)
                
                # Create a separate logger for MCP tasks
                mcp_logger = logging.getLogger('mcp_tasks')
                mcp_handler = logging.FileHandler(self.config.mcp_server.task_log_file)
                mcp_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
                mcp_logger.addHandler(mcp_handler)
                mcp_logger.setLevel(getattr(logging, self.config.mcp_server.log_level.upper()))
                mcp_logger.propagate = False
            
            logging.getLogger(__name__).info("Logging configuration set up successfully")
            
        except Exception as e:
            # If logging setup fails, at least ensure basic console logging
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                force=True
            )
            logging.getLogger(__name__).error(f"Failed to set up logging: {e}")
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        if hasattr(self.config, 'logging') and self.config.logging:
            return self.config.logging if isinstance(self.config.logging, dict) else self.config.logging.dict()
        return {
            'level': 'INFO',
            'file': 'logs/eunice.log'
        }

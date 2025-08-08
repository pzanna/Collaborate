"""Configuration management for the Eunice application."""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

# Try to import optional dependencies
try:
    from dotenv import load_dotenv
    load_dotenv()
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

try:
    from pydantic import BaseModel, Field
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    # Create fallback base class if pydantic is not available
    class BaseModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
        
        def model_dump(self):
            return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
    
    def Field(**kwargs):
        return kwargs.get('default_factory', lambda: kwargs.get('default'))() if callable(kwargs.get('default_factory')) else kwargs.get('default')


class ServiceConfig(BaseModel):
    """Configuration for service settings."""
    
    name: str = "api_gateway"
    version: str = "1.0.0"
    description: str = "Eunice api-gateway service"
    environment: str = "development"


class ServerConfig(BaseModel):
    """Configuration for server settings."""
    
    host: str = Field(default_factory=lambda: os.getenv("SERVICE_HOST", "0.0.0.0"))
    port: int = Field(default_factory=lambda: int(os.getenv("SERVICE_PORT", "8001")))
    debug: bool = False


class DatabaseConfig(BaseModel):
    """Configuration for database settings."""
    
    url: str = Field(default_factory=lambda: os.getenv("DATABASE_URL", "postgresql://eunice:eunice@database:5432/eunice"))
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 20


class MCPConfig(BaseModel):
    """Configuration for MCP settings."""
    
    server_url: str = Field(default_factory=lambda: os.getenv("MCP_SERVER_URL", "ws://mcp-server:8081"))
    timeout: int = 30
    retry_attempts: int = 3


class SecurityConfig(BaseModel):
    """Configuration for security settings."""
    
    cors_origins: list = Field(default_factory=lambda: ["*"])
    cors_methods: list = Field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE"])
    cors_headers: list = Field(default_factory=lambda: ["*"])


class HealthCheckConfig(BaseModel):
    """Configuration for health check settings."""
    
    enabled: bool = True
    interval: int = 30
    timeout: int = 10


class ConversationConfig(BaseModel):
    """Configuration for conversation management."""

    max_context_tokens: int = 8000
    auto_save: bool = True
    max_response_length: int = 1500


class StorageConfig(BaseModel):
    """Configuration for data storage."""

    database_path: str = Field(
        default_factory=lambda: os.path.join(
            os.getenv("EUNICE_DATA_PATH", "data"), "eunice.db"
        )
    )
    export_path: str = "exports/"


class LoggingConfig(BaseModel):
    """Configuration for logging."""

    level: str = Field(default_factory=lambda: os.getenv("EUNICE_LOG_LEVEL", "INFO"))
    file: str = Field(
        default_factory=lambda: os.path.join(
            os.getenv("EUNICE_LOG_PATH", "logs"), "eunice.log"
        )
    )
    enable_ai_api_logging: bool = True
    ai_api_log_file: str = Field(
        default_factory=lambda: os.path.join(
            os.getenv("EUNICE_LOG_PATH", "logs"), "ai_api.log"
        )
    )
    ai_api_log_level: str = Field(
        default_factory=lambda: os.getenv("EUNICE_LOG_LEVEL", "INFO")
    )


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
    task_timeout: int = 300
    retry_attempts: int = 3
    log_level: str = Field(
        default_factory=lambda: os.getenv("EUNICE_LOG_LEVEL", "INFO")
    )
    enable_task_logging: bool = True
    task_log_file: str = Field(
        default_factory=lambda: os.path.join(
            os.getenv("EUNICE_LOG_PATH", "logs"), "mcp_tasks.log"
        )
    )


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
    task_db: str = Field(
        default_factory=lambda: os.path.join(
            os.getenv("EUNICE_DATA_PATH", "data"), "research_tasks.db"
        )
    )


class ResearchManagerConfig(BaseModel):
    """Configuration for Research Manager."""

    provider: str = "openai"
    model: str = "gpt-4.1-mini"
    name: str = "Sky"
    max_tokens: int = 2000
    system_prompt: str = ""


class AIProviderConfig(BaseModel):
    """AI configuration model."""

    provider: str  # openai, xai
    model: str
    temperature: float = 0.7
    max_tokens: int = 2000
    system_prompt: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


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
    research_manager: ResearchManagerConfig = Field(
        default_factory=ResearchManagerConfig
    )


class APIGatewayConfig(BaseModel):
    """Main API Gateway configuration class."""
    
    service: ServiceConfig = Field(default_factory=ServiceConfig)
    server: ServerConfig = Field(default_factory=ServerConfig) 
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    health_check: HealthCheckConfig = Field(default_factory=HealthCheckConfig)


class ConfigManager:
    """Manages application configuration."""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._get_default_config_path()
        self.config = self._load_config()

    def _get_default_config_path(self) -> str:
        """Get the default configuration file path."""
        return os.getenv("EUNICE_CONFIG_PATH", "config/default_config.json")

    def _load_config(self) -> Config:
        """Load configuration from file and apply environment variable overrides."""
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                config_data = json.load(f)

            # Apply environment variable overrides
            self._apply_env_overrides(config_data)

            # Fix provider field in ai_providers
            if "ai_providers" in config_data:
                for provider_name, provider_config in config_data[
                    "ai_providers"
                ].items():
                    if "provider" not in provider_config:
                        provider_config["provider"] = provider_name

            return Config(**config_data)
        else:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

    def _apply_env_overrides(self, config_data: dict) -> None:
        """Apply environment variable overrides to config data."""
        # Data path overrides
        data_path = os.getenv("EUNICE_DATA_PATH")
        if data_path:
            if "storage" not in config_data:
                config_data["storage"] = {}
            config_data["storage"]["database_path"] = os.path.join(
                data_path, "eunice.db"
            )

            if "research_tasks" not in config_data:
                config_data["research_tasks"] = {}
            config_data["research_tasks"]["task_db"] = os.path.join(
                data_path, "research_tasks.db"
            )

            # Update agent memory storage path
            if "agents" in config_data and "memory" in config_data["agents"]:
                if "storage" not in config_data["agents"]["memory"]:
                    config_data["agents"]["memory"]["storage"] = {}
                config_data["agents"]["memory"]["storage"]["context_db"] = os.path.join(
                    data_path, "context.db"
                )

        # Log path and level overrides
        log_path = os.getenv("EUNICE_LOG_PATH")
        log_level = os.getenv("EUNICE_LOG_LEVEL")

        if log_path or log_level:
            if "logging" not in config_data:
                config_data["logging"] = {}

            if log_path:
                config_data["logging"]["file"] = os.path.join(log_path, "eunice.log")
                config_data["logging"]["ai_api_log_file"] = os.path.join(
                    log_path, "ai_api.log"
                )

            if log_level:
                config_data["logging"]["level"] = log_level
                config_data["logging"]["ai_api_log_level"] = log_level

            # Update MCP server log settings
            if "mcp_server" not in config_data:
                config_data["mcp_server"] = {}

            if log_path:
                config_data["mcp_server"]["task_log_file"] = os.path.join(
                    log_path, "mcp_tasks.log"
                )

            if log_level:
                config_data["mcp_server"]["log_level"] = log_level

        # Server configuration overrides
        host = os.getenv("EUNICE_HOST")
        mcp_port = os.getenv("EUNICE_MCP_PORT")

        if host or mcp_port:
            if "mcp_server" not in config_data:
                config_data["mcp_server"] = {}

            if host:
                config_data["mcp_server"]["host"] = host

            if mcp_port:
                config_data["mcp_server"]["port"] = int(mcp_port)

    def save_config(self) -> None:
        """Save current configuration to file."""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(self.config.model_dump(), f, indent=4)

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get a configuration value using dotted notation (e.g., 'storage.database_path')."""
        keys = key_path.split(".")
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
        elif provider == "anthropic":
            return os.getenv("ANTHROPIC_API_KEY", "")
        elif provider == "semantic_scholar":
            return os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
        elif provider == "pubmed":
            return os.getenv("PUBMED_API_KEY", "")
        elif provider == "ncbi":
            return os.getenv("NCBI_API_KEY", "")
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def update_provider_config(self, provider: str, **kwargs) -> None:
        """Update configuration for a specific provider."""
        if provider not in self.config.ai_providers:
            self.config.ai_providers[provider] = AIProviderConfig(
                provider=provider, model=""
            )

        for key, value in kwargs.items():
            if hasattr(self.config.ai_providers[provider], key):
                setattr(self.config.ai_providers[provider], key, value)

    def get_mcp_config(self) -> Dict[str, Any]:
        """Get MCP server configuration."""
        if hasattr(self.config, "mcp_server") and self.config.mcp_server:
            return (
                self.config.mcp_server
                if isinstance(self.config.mcp_server, dict)
                else self.config.mcp_server.dict()
            )
        return {
            "host": "localhost",
            "port": 9000,
            "max_connections": 50,
            "heartbeat_interval": 30,
        }

    def get_research_config(self) -> Dict[str, Any]:
        """Get research task configuration."""
        if hasattr(self.config, "research_tasks") and self.config.research_tasks:
            return (
                self.config.research_tasks
                if isinstance(self.config.research_tasks, dict)
                else self.config.research_tasks.dict()
            )
        return {
            "max_concurrent_tasks": 5,
            "task_timeout": 600,
            "retry_attempts": 3,
            "search_depth": "comprehensive",
        }

    def get_agent_config(self) -> Dict[str, Any]:
        """Get agent configuration."""
        if hasattr(self.config, "agents") and self.config.agents:
            return (
                self.config.agents
                if isinstance(self.config.agents, dict)
                else self.config.agents.dict()
            )
        return {
            "literature": {"enabled": True, "max_results": 10},
            "planning": {"enabled": True, "model": "gpt-4"},
            "executor": {"enabled": True, "timeout": 60},
            "memory": {"enabled": True, "max_entries": 1000},
        }

    def setup_logging(self) -> None:
        """Set up logging configuration based on config settings."""
        try:
            # Get logging configuration
            logging_config = self.config.logging
            log_level = getattr(logging, logging_config.level.upper())

            # Get the root logger and remove all existing handlers
            root_logger = logging.getLogger()
            root_logger.handlers.clear()
            root_logger.setLevel(log_level)

            # Ensure logs directory exists
            log_file_path = Path(logging_config.file)
            log_file_path.parent.mkdir(exist_ok=True)

            # Create a formatter
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s-%(message)s"
            )

            # Add a stream handler to the root logger (for console output)
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(formatter)
            root_logger.addHandler(stream_handler)

            # Add a file handler for the main log file to the root logger
            file_handler = logging.FileHandler(logging_config.file)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

            # Set up AI API logging if enabled
            if logging_config.enable_ai_api_logging:
                ai_api_log_path = Path(logging_config.ai_api_log_file)
                ai_api_log_path.parent.mkdir(exist_ok=True)
                ai_api_handler = logging.FileHandler(logging_config.ai_api_log_file)
                ai_api_handler.setFormatter(formatter)

                ai_client_names = [
                    "src.ai_clients.openai_client",
                    "src.ai_clients.xai_client",
                    "src.core.ai_client_manager",
                ]
                for client_name in ai_client_names:
                    client_logger = logging.getLogger(client_name)
                    client_logger.handlers.clear()
                    client_logger.addHandler(ai_api_handler)
                    client_logger.setLevel(
                        getattr(logging, logging_config.ai_api_log_level.upper())
                    )
                    client_logger.propagate = False

            # Set up MCP task logging if enabled
            if (
                hasattr(self.config, "mcp_server")
                and self.config.mcp_server.enable_task_logging
            ):
                task_log_path = Path(self.config.mcp_server.task_log_file)
                task_log_path.parent.mkdir(exist_ok=True)
                mcp_logger = logging.getLogger("mcp_tasks")
                mcp_logger.handlers.clear()
                mcp_handler = logging.FileHandler(self.config.mcp_server.task_log_file)
                mcp_handler.setFormatter(
                    logging.Formatter("%(asctime)s - %(levelname)s-%(message)s")
                )
                mcp_logger.addHandler(mcp_handler)
                mcp_logger.setLevel(
                    getattr(logging, self.config.mcp_server.log_level.upper())
                )
                mcp_logger.propagate = False

            logging.getLogger(__name__).info(
                "Logging configuration set up successfully"
            )

        except Exception as e:
            # Fallback basic config
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s - %(name)s - %(levelname)s-%(message)s",
                force=True,
            )
            logging.getLogger(__name__).error(f"Failed to set up logging: {e}")

    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        if hasattr(self.config, "logging") and self.config.logging:
            return (
                self.config.logging
                if isinstance(self.config.logging, dict)
                else self.config.logging.dict()
            )
        return {"level": "INFO", "file": "logs / eunice.log"}


# API Gateway specific configuration loader
def load_api_gateway_config(config_path: str = "config/config.json") -> APIGatewayConfig:
    """Load API Gateway configuration from JSON file with environment overrides."""
    
    # Check if config file exists
    if not os.path.exists(config_path):
        # Create default config if it doesn't exist
        return APIGatewayConfig()
    
    # Load config from file
    with open(config_path, 'r') as f:
        config_data = json.load(f)
    
    # Apply environment variable overrides
    if "server" in config_data:
        config_data["server"]["host"] = os.getenv("SERVICE_HOST", config_data["server"].get("host", "0.0.0.0"))
        config_data["server"]["port"] = int(os.getenv("SERVICE_PORT", str(config_data["server"].get("port", 8001))))
    
    if "database" in config_data:
        config_data["database"]["url"] = os.getenv("DATABASE_URL", config_data["database"].get("url", "postgresql://eunice:eunice@database:5432/eunice"))
    
    if "logging" in config_data:
        config_data["logging"]["level"] = os.getenv("LOG_LEVEL", config_data["logging"].get("level", "INFO"))
    
    return APIGatewayConfig(**config_data)


def get_config() -> APIGatewayConfig:
    """Get the API Gateway configuration."""
    return load_api_gateway_config()


# For backward compatibility
_config_manager = None


def get_config_manager() -> ConfigManager:
    """Get the global config manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

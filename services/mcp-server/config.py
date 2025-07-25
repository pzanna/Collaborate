"""
Enhanced MCP Server Configuration for Phase 3.1
Containerized MCP Server with clustering and enhanced monitoring
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class EnhancedMCPServerConfig:
    """Enhanced MCP Server configuration for Phase 3.1"""
    
    # Core Server Settings
    host: str = os.getenv("MCP_HOST", "0.0.0.0")
    port: int = int(os.getenv("MCP_PORT", "9000"))
    max_connections: int = int(os.getenv("MCP_MAX_CONNECTIONS", "1000"))
    
    # WebSocket Configuration
    websocket_ping_interval: int = int(os.getenv("WS_PING_INTERVAL", "30"))
    websocket_ping_timeout: int = int(os.getenv("WS_PING_TIMEOUT", "60"))
    websocket_max_size: int = int(os.getenv("WS_MAX_SIZE", "1048576"))  # 1MB
    
    # Task Management
    max_concurrent_tasks: int = int(os.getenv("MCP_MAX_CONCURRENT_TASKS", "100"))
    task_timeout: int = int(os.getenv("MCP_TASK_TIMEOUT", "300"))
    retry_attempts: int = int(os.getenv("MCP_RETRY_ATTEMPTS", "3"))
    
    # Agent Registry
    agent_registry_ttl: int = int(os.getenv("AGENT_REGISTRY_TTL", "300"))
    heartbeat_interval: int = int(os.getenv("HEARTBEAT_INTERVAL", "30"))
    
    # Database Configuration
    database_url: str = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/eunice")
    database_pool_size: int = int(os.getenv("DB_POOL_SIZE", "20"))
    database_max_overflow: int = int(os.getenv("DB_MAX_OVERFLOW", "30"))
    
    # Redis Configuration
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_cluster_enabled: bool = os.getenv("REDIS_CLUSTER_ENABLED", "false").lower() == "true"
    redis_max_connections: int = int(os.getenv("REDIS_MAX_CONNECTIONS", "100"))
    
    # Load Balancing
    load_balance_strategy: str = os.getenv("LOAD_BALANCE_STRATEGY", "adaptive")
    circuit_breaker_enabled: bool = os.getenv("CIRCUIT_BREAKER_ENABLED", "true").lower() == "true"
    circuit_breaker_threshold: int = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "5"))
    
    # Clustering
    cluster_enabled: bool = os.getenv("CLUSTER_ENABLED", "false").lower() == "true"
    cluster_discovery_method: str = os.getenv("CLUSTER_DISCOVERY", "redis")  # redis, kubernetes, consul
    cluster_node_id: str = os.getenv("CLUSTER_NODE_ID", "")
    
    # Kubernetes Discovery
    kubernetes_namespace: str = os.getenv("KUBERNETES_NAMESPACE", "default")
    kubernetes_service_name: str = os.getenv("KUBERNETES_SERVICE_NAME", "mcp-server")
    
    # Consul Discovery
    consul_host: str = os.getenv("CONSUL_HOST", "localhost")
    consul_port: int = int(os.getenv("CONSUL_PORT", "8500"))
    
    # Security
    auth_service_url: str = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8007")
    jwt_secret: str = os.getenv("JWT_SECRET", "")
    enable_tls: bool = os.getenv("ENABLE_TLS", "false").lower() == "true"
    tls_cert_path: str = os.getenv("TLS_CERT_PATH", "")
    tls_key_path: str = os.getenv("TLS_KEY_PATH", "")
    
    # Monitoring and Metrics
    enable_metrics: bool = os.getenv("ENABLE_METRICS", "true").lower() == "true"
    metrics_port: int = int(os.getenv("METRICS_PORT", "9090"))
    enable_tracing: bool = os.getenv("ENABLE_TRACING", "false").lower() == "true"
    jaeger_endpoint: str = os.getenv("JAEGER_ENDPOINT", "")
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_format: str = os.getenv("LOG_FORMAT", "json")
    log_file: str = os.getenv("LOG_FILE", "/app/logs/mcp_server.log")
    
    # Resource Limits
    memory_limit: str = os.getenv("MEMORY_LIMIT", "2Gi")
    cpu_limit: str = os.getenv("CPU_LIMIT", "1000m")
    
    # Health Check
    health_check_enabled: bool = os.getenv("HEALTH_CHECK_ENABLED", "true").lower() == "true"
    health_check_interval: int = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))
    
    # Agent Configuration
    allowed_agent_types: List[str] = field(default_factory=lambda: os.getenv(
        "ALLOWED_AGENT_TYPES", 
        "research_manager,literature_search,screening_prisma,synthesis_review,writer,planning,executor,memory"
    ).split(","))
    
    def __post_init__(self):
        """Post-initialization validation"""
        if not self.cluster_node_id and self.cluster_enabled:
            import socket
            self.cluster_node_id = f"mcp-server-{socket.gethostname()}"
        
        if self.enable_tls and (not self.tls_cert_path or not self.tls_key_path):
            raise ValueError("TLS enabled but certificate or key path not provided")


def get_enhanced_config() -> EnhancedMCPServerConfig:
    """Get enhanced MCP server configuration"""
    return EnhancedMCPServerConfig()


# Configuration validation
def validate_config(config: EnhancedMCPServerConfig) -> bool:
    """Validate enhanced MCP server configuration"""
    try:
        # Validate port range
        if not (1024 <= config.port <= 65535):
            raise ValueError(f"Invalid port: {config.port}")
        
        # Validate strategy
        valid_strategies = ["round_robin", "weighted", "adaptive", "least_connections"]
        if config.load_balance_strategy not in valid_strategies:
            raise ValueError(f"Invalid load balance strategy: {config.load_balance_strategy}")
        
        # Validate discovery method
        valid_discovery = ["redis", "kubernetes", "consul"]
        if config.cluster_discovery_method not in valid_discovery:
            raise ValueError(f"Invalid cluster discovery method: {config.cluster_discovery_method}")
        
        return True
    except Exception as e:
        print(f"Configuration validation error: {e}")
        return False

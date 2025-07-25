"""
Structured JSON Logger for MCP Server

Provides structured logging with JSON formatting for improved observability
and integration with log analysis tools.
"""

import json
import logging
import sys
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class LogLevel(Enum):
    """Log level enumeration"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogEvent(Enum):
    """MCP server event types"""

    AGENT_REGISTRATION = "agent_registration"
    TASK_DISPATCH = "task_dispatch"
    TASK_COMPLETION = "task_completion"
    TASK_TIMEOUT = "task_timeout"
    TASK_RETRY = "task_retry"
    TASK_FAILURE = "task_failure"
    CLIENT_CONNECT = "client_connect"
    CLIENT_DISCONNECT = "client_disconnect"
    SERVER_START = "server_start"
    SERVER_STOP = "server_stop"
    ERROR_OCCURRED = "error_occurred"
    CAPABILITY_QUERY = "capability_query"
    QUEUE_OVERFLOW = "queue_overflow"


class StructuredTextFormatter(logging.Formatter):
    """Custom text formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as plain text"""
        # Base format similar to other logs: timestamp-module-level-message
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
        base_message = f"{timestamp} - {record.name} - {record.levelname}-{record.getMessage()}"
        
        # Add extra context if available
        extra_parts = []
        
        # Add important fields as key=value pairs
        for attr in [
            "event",
            "task_id", 
            "context_id",
            "agent_type",
            "agent_id",
            "client_id",
        ]:
            if hasattr(record, attr):
                extra_parts.append(f"{attr}={getattr(record, attr)}")
        
        # Add duration if present
        if hasattr(record, "duration"):
            extra_parts.append(f"duration={getattr(record, 'duration'):.3f}s")
            
        # Add details if present (but keep it concise)
        if hasattr(record, "details"):
            details = getattr(record, "details")
            if isinstance(details, dict) and "success" in details:
                extra_parts.append(f"success={details['success']}")
                if "capabilities" in details and isinstance(details["capabilities"], list):
                    extra_parts.append(f"capabilities_count={len(details['capabilities'])}")
        
        # Add exception information if present
        if record.exc_info:
            extra_parts.append(f"exception={self.formatException(record.exc_info)}")
        
        # Combine base message with extra context
        if extra_parts:
            return f"{base_message} [{', '.join(extra_parts)}]"
        else:
            return base_message


class MCPLogger:
    """Structured logger for MCP server components"""

    def __init__(
        self, name: Optional[str] = None, log_level: str = "INFO", config_manager=None
    ):
        logger_name = name or "mcp.default"
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(getattr(logging, log_level.upper()))

        # Clear existing handlers
        self.logger.handlers.clear()

        # Determine log file path
        if config_manager and hasattr(config_manager, 'config'):
            try:
                log_path = config_manager.config.logging.file.replace('eunice.log', 'mcp_server.log')
            except AttributeError:
                log_path = "logs/mcp_server.log"
        else:
            log_path = "logs/mcp_server.log"

        # Create logs directory if it doesn't exist
        import os
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

        # Add file handler with JSON formatter
        handler = logging.FileHandler(log_path)
        handler.setFormatter(StructuredTextFormatter())
        self.logger.addHandler(handler)

        # Prevent propagation to root logger
        self.logger.propagate = False

    def log_event(self, level: LogLevel, event: LogEvent, message: str, **kwargs):
        """Log a structured event"""
        extra = {"event": event.value, **kwargs}

        getattr(self.logger, level.value.lower())(message, extra=extra)

    def log_agent_registration(
        self,
        agent_id: str,
        agent_type: str,
        capabilities: list,
        success: bool = True,
        **kwargs,
    ):
        """Log agent registration event"""
        level = LogLevel.INFO if success else LogLevel.ERROR
        message = (
            f"Agent {agent_id} registered successfully"
            if success
            else f"Agent {agent_id} registration failed"
        )

        self.log_event(
            level,
            LogEvent.AGENT_REGISTRATION,
            message,
            agent_id=agent_id,
            agent_type=agent_type,
            details={"capabilities": capabilities, "success": success},
            **kwargs,
        )

    def log_task_dispatch(
        self, task_id: str, context_id: str, agent_type: str, action: str, **kwargs
    ):
        """Log task dispatch event"""
        self.log_event(
            LogLevel.INFO,
            LogEvent.TASK_DISPATCH,
            f"Task {task_id} dispatched to {agent_type}",
            task_id=task_id,
            context_id=context_id,
            agent_type=agent_type,
            details={"action": action},
            **kwargs,
        )

    def log_task_completion(
        self,
        task_id: str,
        context_id: str,
        agent_type: str,
        duration: float,
        success: bool = True,
        **kwargs,
    ):
        """Log task completion event"""
        level = LogLevel.INFO if success else LogLevel.ERROR
        status = "completed" if success else "failed"
        message = f"Task {task_id} {status} in {duration:.2f}s"

        self.log_event(
            level,
            LogEvent.TASK_COMPLETION,
            message,
            task_id=task_id,
            context_id=context_id,
            agent_type=agent_type,
            duration=duration,
            details={"success": success},
            **kwargs,
        )

    def log_task_timeout(
        self,
        task_id: str,
        context_id: str,
        agent_type: str,
        timeout_duration: int,
        **kwargs,
    ):
        """Log task timeout event"""
        self.log_event(
            LogLevel.WARNING,
            LogEvent.TASK_TIMEOUT,
            f"Task {task_id} timed out after {timeout_duration}s",
            task_id=task_id,
            context_id=context_id,
            agent_type=agent_type,
            details={"timeout_duration": timeout_duration},
            **kwargs,
        )

    def log_task_retry(
        self,
        task_id: str,
        context_id: str,
        agent_type: str,
        retry_attempt: int,
        reason: str,
        **kwargs,
    ):
        """Log task retry event"""
        self.log_event(
            LogLevel.WARNING,
            LogEvent.TASK_RETRY,
            f"Task {task_id} retry attempt {retry_attempt}: {reason}",
            task_id=task_id,
            context_id=context_id,
            agent_type=agent_type,
            details={"retry_attempt": retry_attempt, "reason": reason},
            **kwargs,
        )

    def log_client_connect(
        self, client_id: str, client_type: str = "unknown", **kwargs
    ):
        """Log client connection event"""
        self.log_event(
            LogLevel.INFO,
            LogEvent.CLIENT_CONNECT,
            f"Client {client_id} connected",
            client_id=client_id,
            details={"client_type": client_type},
            **kwargs,
        )

    def log_client_disconnect(self, client_id: str, reason: str = "normal", **kwargs):
        """Log client disconnection event"""
        level = LogLevel.INFO if reason == "normal" else LogLevel.WARNING
        self.log_event(
            level,
            LogEvent.CLIENT_DISCONNECT,
            f"Client {client_id} disconnected: {reason}",
            client_id=client_id,
            details={"reason": reason},
            **kwargs,
        )

    def log_error(
        self,
        message: str,
        error_code: Optional[str] = None,
        task_id: Optional[str] = None,
        context_id: Optional[str] = None,
        **kwargs,
    ):
        """Log error event"""
        self.log_event(
            LogLevel.ERROR,
            LogEvent.ERROR_OCCURRED,
            message,
            task_id=task_id,
            context_id=context_id,
            error_code=error_code,
            **kwargs,
        )

    def log_server_lifecycle(
        self, event: str, details: Optional[Dict[str, Any]] = None
    ):
        """Log server lifecycle events"""
        event_type = LogEvent.SERVER_START if event == "start" else LogEvent.SERVER_STOP
        message = f"MCP Server {event}"

        self.log_event(LogLevel.INFO, event_type, message, details=details or {})


def get_mcp_logger(component_name: str, log_level: str = "INFO", config_manager=None) -> MCPLogger:
    """Factory function to create MCP logger instances"""
    return MCPLogger(f"mcp.{component_name}", log_level, config_manager)


# Default logger instance for the MCP server
mcp_logger = get_mcp_logger("server")

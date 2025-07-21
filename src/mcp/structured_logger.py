"""
Structured JSON Logger for MCP Server

Provides structured logging with JSON formatting for improved observability
and integration with log analysis tools.
"""

import logging
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum


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


class StructuredJSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "component": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra fields if they exist
        for attr in ['event', 'task_id', 'context_id', 'agent_type', 'agent_id', 
                    'client_id', 'duration', 'details', 'error_code']:
            if hasattr(record, attr):
                log_entry[attr] = getattr(record, attr)
        
        # Add exception information if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, default=str)


class MCPLogger:
    """Structured logger for MCP server components"""
    
    def __init__(self, name: Optional[str] = None, log_level: str = "INFO", config_manager=None):
        # Support both old and new constructor signatures
        if config_manager is not None:
            # Old interface compatibility
            logger_name = "mcp.structured_logger"
        else:
            logger_name = name or "mcp.default"
            
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Add JSON formatter
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredJSONFormatter())
        self.logger.addHandler(handler)
        
        # Prevent propagation to root logger
        self.logger.propagate = False
    
    def log_event(self, level: LogLevel, event: LogEvent, message: str, **kwargs):
        """Log a structured event"""
        extra = {
            'event': event.value,
            **kwargs
        }
        
        getattr(self.logger, level.value.lower())(message, extra=extra)
    
    def log_agent_registration(self, agent_id: str, agent_type: str, 
                              capabilities: list, success: bool = True, **kwargs):
        """Log agent registration event"""
        level = LogLevel.INFO if success else LogLevel.ERROR
        message = f"Agent {agent_id} registered successfully" if success else f"Agent {agent_id} registration failed"
        
        self.log_event(
            level, LogEvent.AGENT_REGISTRATION, message,
            agent_id=agent_id,
            agent_type=agent_type,
            details={'capabilities': capabilities, 'success': success},
            **kwargs
        )
    
    def log_task_dispatch(self, task_id: str, context_id: str, agent_type: str, 
                         action: str, **kwargs):
        """Log task dispatch event"""
        self.log_event(
            LogLevel.INFO, LogEvent.TASK_DISPATCH,
            f"Task {task_id} dispatched to {agent_type}",
            task_id=task_id,
            context_id=context_id,
            agent_type=agent_type,
            details={'action': action},
            **kwargs
        )
    
    def log_task_completion(self, task_id: str, context_id: str, agent_type: str,
                           duration: float, success: bool = True, **kwargs):
        """Log task completion event"""
        level = LogLevel.INFO if success else LogLevel.ERROR
        status = "completed" if success else "failed"
        message = f"Task {task_id} {status} in {duration:.2f}s"
        
        self.log_event(
            level, LogEvent.TASK_COMPLETION, message,
            task_id=task_id,
            context_id=context_id,
            agent_type=agent_type,
            duration=duration,
            details={'success': success},
            **kwargs
        )
    
    def log_task_timeout(self, task_id: str, context_id: str, agent_type: str,
                        timeout_duration: int, **kwargs):
        """Log task timeout event"""
        self.log_event(
            LogLevel.WARNING, LogEvent.TASK_TIMEOUT,
            f"Task {task_id} timed out after {timeout_duration}s",
            task_id=task_id,
            context_id=context_id,
            agent_type=agent_type,
            details={'timeout_duration': timeout_duration},
            **kwargs
        )
    
    def log_task_retry(self, task_id: str, context_id: str, agent_type: str,
                      retry_attempt: int, reason: str, **kwargs):
        """Log task retry event"""
        self.log_event(
            LogLevel.WARNING, LogEvent.TASK_RETRY,
            f"Task {task_id} retry attempt {retry_attempt}: {reason}",
            task_id=task_id,
            context_id=context_id,
            agent_type=agent_type,
            details={'retry_attempt': retry_attempt, 'reason': reason},
            **kwargs
        )
    
    def log_client_connect(self, client_id: str, client_type: str = "unknown", **kwargs):
        """Log client connection event"""
        self.log_event(
            LogLevel.INFO, LogEvent.CLIENT_CONNECT,
            f"Client {client_id} connected",
            client_id=client_id,
            details={'client_type': client_type},
            **kwargs
        )
    
    def log_client_disconnect(self, client_id: str, reason: str = "normal", **kwargs):
        """Log client disconnection event"""
        level = LogLevel.INFO if reason == "normal" else LogLevel.WARNING
        self.log_event(
            level, LogEvent.CLIENT_DISCONNECT,
            f"Client {client_id} disconnected: {reason}",
            client_id=client_id,
            details={'reason': reason},
            **kwargs
        )
    
    def log_error(self, message: str, error_code: Optional[str] = None,
                 task_id: Optional[str] = None, context_id: Optional[str] = None, **kwargs):
        """Log error event"""
        self.log_event(
            LogLevel.ERROR, LogEvent.ERROR_OCCURRED, message,
            task_id=task_id,
            context_id=context_id,
            error_code=error_code,
            **kwargs
        )
    
    def log_server_lifecycle(self, event: str, details: Optional[Dict[str, Any]] = None):
        """Log server lifecycle events"""
        event_type = LogEvent.SERVER_START if event == "start" else LogEvent.SERVER_STOP
        message = f"MCP Server {event}"
        
        self.log_event(
            LogLevel.INFO, event_type, message,
            details=details or {}
        )
    
    # Backward compatibility methods for tests
    def legacy_log_event(self, component: str, event: str, data: Dict[str, Any], level: str = "INFO"):
        """Legacy log_event method for backward compatibility"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "component": component,
            "event": event,
            "data": data
        }
        getattr(self.logger, level.lower())(json.dumps(log_entry))
    
    def log_task_start(self, research_action):
        """Legacy log_task_start method for backward compatibility"""
        data = {
            "task_id": research_action.task_id,
            "agent_type": research_action.agent_type.value if hasattr(research_action.agent_type, 'value') else str(research_action.agent_type),
            "action": research_action.action
        }
        self.legacy_log_event("task_manager", "task_started", data, "INFO")
    
    def legacy_log_task_completion(self, task_id: str, result: Dict[str, Any]):
        """Legacy log_task_completion method for backward compatibility"""
        data = {
            "task_id": task_id,
            "result": result
        }
        self.legacy_log_event("task_manager", "task_completed", data, "INFO")
    
    def log_task_failure(self, task_id: str, error: str):
        """Legacy log_task_failure method for backward compatibility"""
        data = {
            "task_id": task_id,
            "error": error
        }
        self.legacy_log_event("task_manager", "task_failed", data, "ERROR")
    
    def legacy_log_agent_registration(self, agent_id: str, agent_type: str, capabilities: List[str]):
        """Legacy log_agent_registration method for backward compatibility"""
        data = {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "capabilities": capabilities
        }
        self.legacy_log_event("agent_registry", "agent_registered", data, "INFO")


def get_mcp_logger(component_name: str, log_level: str = "INFO") -> MCPLogger:
    """Factory function to create MCP logger instances"""
    return MCPLogger(f"mcp.{component_name}", log_level)


class StructuredLogger:
    """Legacy StructuredLogger class for backward compatibility with tests"""
    
    def __init__(self, config_manager=None):
        self.mcp_logger = MCPLogger("structured_logger", "INFO", config_manager)
    
    def __getattr__(self, name: str):
        """
        Delegate attribute access to the underlying MCPLogger instance.
        
        This method is called when an attribute is not found in the usual places.
        It delegates the attribute access to the `MCPLogger` instance, allowing
        the `StructuredLogger` class to act as a proxy for `MCPLogger`.
        
        Parameters:
            name (str): The name of the attribute being accessed.
            
        Returns:
            Any: The corresponding attribute or method from the `MCPLogger` instance.
        """
        return getattr(self.mcp_logger, name)
    
    def log_event(self, component: str, event: str, data: Dict[str, Any], level: str = "INFO"):
        """Log event method compatible with tests"""
        self.mcp_logger.legacy_log_event(component, event, data, level)
    
    def log_task_start(self, research_action):
        """Log task start method compatible with tests"""
        self.mcp_logger.log_task_start(research_action)
    
    def log_task_completion(self, task_id: str, result: Dict[str, Any]):
        """Log task completion method compatible with tests"""
        self.mcp_logger.legacy_log_task_completion(task_id, result)
    
    def log_task_failure(self, task_id: str, error: str):
        """Log task failure method compatible with tests"""
        self.mcp_logger.log_task_failure(task_id, error)
    
    def log_agent_registration(self, agent_id: str, agent_type: str, capabilities: List[str]):
        """Log agent registration method compatible with tests"""
        self.mcp_logger.legacy_log_agent_registration(agent_id, agent_type, capabilities)


# Default logger instance for the MCP server
mcp_logger = get_mcp_logger("server")

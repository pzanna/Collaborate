"""
Unit tests for Structured JSON Logging (Phase 1)

Tests for the structured logging implementation with JSON formatting
and event-based logging.
"""

import pytest
import json
import logging
from io import StringIO
from src.mcp.structured_logger import (
    MCPLogger, StructuredJSONFormatter, LogLevel, LogEvent, get_mcp_logger
)


class TestStructuredJSONFormatter:
    """Test the JSON formatter"""
    
    def test_basic_json_formatting(self):
        """Test basic JSON log formatting"""
        formatter = StructuredJSONFormatter()
        
        # Create a log record
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert log_data['level'] == 'INFO'
        assert log_data['message'] == 'Test message'
        assert log_data['component'] == 'test_logger'
        assert log_data['line'] == 10
        assert 'timestamp' in log_data
    
    def test_json_formatting_with_extra_fields(self):
        """Test JSON formatting with extra MCP fields"""
        formatter = StructuredJSONFormatter()
        
        record = logging.LogRecord(
            name="mcp.server",
            level=logging.INFO,
            pathname="server.py",
            lineno=20,
            msg="Task dispatched",
            args=(),
            exc_info=None
        )
        
        # Add extra fields
        record.event = "task_dispatch"
        record.task_id = "task-123"
        record.context_id = "context-123"
        record.agent_type = "Retriever"
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert log_data['event'] == 'task_dispatch'
        assert log_data['task_id'] == 'task-123'
        assert log_data['context_id'] == 'context-123'
        assert log_data['agent_type'] == 'Retriever'


class TestMCPLogger:
    """Test the MCP structured logger"""
    
    def setup_method(self):
        """Setup test logger with string capture"""
        self.log_capture = StringIO()
        self.logger = MCPLogger("test", "DEBUG")
        
        # Replace the handler with our capture handler
        self.logger.logger.handlers.clear()
        handler = logging.StreamHandler(self.log_capture)
        handler.setFormatter(StructuredJSONFormatter())
        self.logger.logger.addHandler(handler)
    
    def get_last_log(self):
        """Get the last log entry as parsed JSON"""
        content = self.log_capture.getvalue().strip()
        if not content:
            return None
        lines = content.split('\n')
        return json.loads(lines[-1])
    
    def test_log_event(self):
        """Test basic event logging"""
        self.logger.log_event(
            LogLevel.INFO, LogEvent.TASK_DISPATCH,
            "Test task dispatched",
            task_id="task-123",
            agent_type="Retriever"
        )
        
        log_data = self.get_last_log()
        assert log_data['level'] == 'INFO'
        assert log_data['event'] == 'task_dispatch'
        assert log_data['task_id'] == 'task-123'
        assert log_data['agent_type'] == 'Retriever'
        assert log_data['message'] == 'Test task dispatched'
    
    def test_log_agent_registration(self):
        """Test agent registration logging"""
        self.logger.log_agent_registration(
            agent_id="agent-123",
            agent_type="Retriever",
            capabilities=["search", "summarize"],
            success=True
        )
        
        log_data = self.get_last_log()
        assert log_data['level'] == 'INFO'
        assert log_data['event'] == 'agent_registration'
        assert log_data['agent_id'] == 'agent-123'
        assert log_data['agent_type'] == 'Retriever'
        assert log_data['details']['capabilities'] == ['search', 'summarize']
        assert log_data['details']['success'] is True
    
    def test_log_task_dispatch(self):
        """Test task dispatch logging"""
        self.logger.log_task_dispatch(
            task_id="task-123",
            context_id="context-123",
            agent_type="Retriever",
            action="search"
        )
        
        log_data = self.get_last_log()
        assert log_data['level'] == 'INFO'
        assert log_data['event'] == 'task_dispatch'
        assert log_data['task_id'] == 'task-123'
        assert log_data['context_id'] == 'context-123'
        assert log_data['agent_type'] == 'Retriever'
        assert log_data['details']['action'] == 'search'
    
    def test_log_task_completion(self):
        """Test task completion logging"""
        self.logger.log_task_completion(
            task_id="task-123",
            context_id="context-123",
            agent_type="Retriever",
            duration=2.5,
            success=True
        )
        
        log_data = self.get_last_log()
        assert log_data['level'] == 'INFO'
        assert log_data['event'] == 'task_completion'
        assert log_data['task_id'] == 'task-123'
        assert log_data['duration'] == 2.5
        assert log_data['details']['success'] is True
    
    def test_log_task_timeout(self):
        """Test task timeout logging"""
        self.logger.log_task_timeout(
            task_id="task-123",
            context_id="context-123",
            agent_type="Executor",
            timeout_duration=30
        )
        
        log_data = self.get_last_log()
        assert log_data['level'] == 'WARNING'
        assert log_data['event'] == 'task_timeout'
        assert log_data['task_id'] == 'task-123'
        assert log_data['details']['timeout_duration'] == 30
    
    def test_log_task_retry(self):
        """Test task retry logging"""
        self.logger.log_task_retry(
            task_id="task-123",
            context_id="context-123",
            agent_type="Retriever",
            retry_attempt=2,
            reason="Connection timeout"
        )
        
        log_data = self.get_last_log()
        assert log_data['level'] == 'WARNING'
        assert log_data['event'] == 'task_retry'
        assert log_data['task_id'] == 'task-123'
        assert log_data['details']['retry_attempt'] == 2
        assert log_data['details']['reason'] == "Connection timeout"
    
    def test_log_client_connect(self):
        """Test client connection logging"""
        self.logger.log_client_connect(
            client_id="client-123",
            client_type="research_manager"
        )
        
        log_data = self.get_last_log()
        assert log_data['level'] == 'INFO'
        assert log_data['event'] == 'client_connect'
        assert log_data['client_id'] == 'client-123'
        assert log_data['details']['client_type'] == 'research_manager'
    
    def test_log_client_disconnect(self):
        """Test client disconnection logging"""
        self.logger.log_client_disconnect(
            client_id="client-123",
            reason="error"
        )
        
        log_data = self.get_last_log()
        assert log_data['level'] == 'WARNING'
        assert log_data['event'] == 'client_disconnect'
        assert log_data['client_id'] == 'client-123'
        assert log_data['details']['reason'] == 'error'
    
    def test_log_error(self):
        """Test error logging"""
        self.logger.log_error(
            message="Test error occurred",
            error_code="E001",
            task_id="task-123"
        )
        
        log_data = self.get_last_log()
        assert log_data['level'] == 'ERROR'
        assert log_data['event'] == 'error_occurred'
        assert log_data['message'] == 'Test error occurred'
        assert log_data['error_code'] == 'E001'
        assert log_data['task_id'] == 'task-123'
    
    def test_log_server_lifecycle(self):
        """Test server lifecycle logging"""
        self.logger.log_server_lifecycle(
            event="start",
            details={"host": "127.0.0.1", "port": 9000}
        )
        
        log_data = self.get_last_log()
        assert log_data['level'] == 'INFO'
        assert log_data['event'] == 'server_start'
        assert log_data['details']['host'] == '127.0.0.1'
        assert log_data['details']['port'] == 9000


class TestLoggerFactory:
    """Test the logger factory function"""
    
    def test_get_mcp_logger(self):
        """Test creating logger instances"""
        logger = get_mcp_logger("test_component", "DEBUG")
        
        assert logger.logger.name == "mcp.test_component"
        assert logger.logger.level == logging.DEBUG
    
    def test_get_mcp_logger_default_level(self):
        """Test creating logger with default level"""
        logger = get_mcp_logger("test_component")
        
        assert logger.logger.level == logging.INFO


if __name__ == "__main__":
    pytest.main([__file__])

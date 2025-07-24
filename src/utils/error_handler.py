"""Enhanced error handling utilities for the Eunice application."""

import logging
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, Optional


class ErrorType(Enum):
    """Types of errors that can occur in the application."""

    NETWORK_ERROR = "network_error"
    API_ERROR = "api_error"
    DATABASE_ERROR = "database_error"
    CONFIGURATION_ERROR = "configuration_error"
    VALIDATION_ERROR = "validation_error"
    FILE_ERROR = "file_error"
    UNKNOWN_ERROR = "unknown_error"


class EuniceError(Exception):
    """Base exception class for Eunice application errors."""

    def __init__(
        self,
        message: str,
        error_type: ErrorType = ErrorType.UNKNOWN_ERROR,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.details = details or {}
        self.original_error = original_error
        self.timestamp = datetime.now()

    def __str__(self):
        return f"{self.error_type.value}: {self.message}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging / serialization."""
        return {
            "message": self.message,
            "error_type": self.error_type.value,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "original_error": str(self.original_error) if self.original_error else None,
        }


class NetworkError(EuniceError):
    """Network - related errors."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message, ErrorType.NETWORK_ERROR, details, original_error)


class APIError(EuniceError):
    """API - related errors."""

    def __init__(
        self,
        message: str,
        provider: str,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        details = details or {}
        details.update({"provider": provider, "status_code": status_code})
        super().__init__(message, ErrorType.API_ERROR, details, original_error)


class DatabaseError(EuniceError):
    """Database - related errors."""

    def __init__(
        self,
        message: str,
        operation: str,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        details = details or {}
        details.update({"operation": operation})
        super().__init__(message, ErrorType.DATABASE_ERROR, details, original_error)


class ConfigurationError(EuniceError):
    """Configuration - related errors."""

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        details = details or {}
        if config_key:
            details.update({"config_key": config_key})
        super().__init__(
            message, ErrorType.CONFIGURATION_ERROR, details, original_error
        )


class ValidationError(EuniceError):
    """Data validation errors."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        details = details or {}
        if field:
            details.update({"field": field, "value": str(value) if value else None})
        super().__init__(message, ErrorType.VALIDATION_ERROR, details, original_error)


class FileError(EuniceError):
    """File operation errors."""

    def __init__(
        self,
        message: str,
        file_path: str,
        operation: str,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        details = details or {}
        details.update({"file_path": file_path, "operation": operation})
        super().__init__(message, ErrorType.FILE_ERROR, details, original_error)


class ErrorHandler:
    """Central error handler for the application."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.error_counts: Dict[ErrorType, int] = {}
        self.recent_errors: list = []
        self.max_recent_errors = 50

    def handle_error(
        self, error: Exception, context: Optional[str] = None
    ) -> EuniceError:
        """Handle an error and convert it to a EuniceError if needed."""
        if isinstance(error, EuniceError):
            eunice_error = error
        else:
            eunice_error = self._convert_to_eunice_error(error, context)

        # Log the error
        self._log_error(eunice_error, context)

        # Track error statistics
        self._track_error(eunice_error)

        return eunice_error

    def _convert_to_eunice_error(
        self, error: Exception, context: Optional[str] = None
    ) -> EuniceError:
        """Convert a generic exception to a EuniceError."""
        error_str = str(error)

        # Network - related errors
        if any(
            keyword in error_str.lower()
            for keyword in ["connection", "timeout", "network", "dns"]
        ):
            return NetworkError(f"Network error: {error_str}", original_error=error)

        # API - related errors
        if any(
            keyword in error_str.lower()
            for keyword in ["api", "http", "request", "response"]
        ):
            return APIError(f"API error: {error_str}", "unknown", original_error=error)

        # Database - related errors
        if any(
            keyword in error_str.lower() for keyword in ["database", "sql", "sqlite"]
        ):
            return DatabaseError(
                f"Database error: {error_str}",
                context or "unknown",
                original_error=error,
            )

        # File - related errors
        if any(
            keyword in error_str.lower()
            for keyword in ["file", "directory", "path", "permission"]
        ):
            return FileError(
                f"File error: {error_str}",
                "unknown",
                context or "unknown",
                original_error=error,
            )

        # Configuration - related errors
        if any(
            keyword in error_str.lower()
            for keyword in ["config", "setting", "environment"]
        ):
            return ConfigurationError(
                f"Configuration error: {error_str}", original_error=error
            )

        # Generic error
        return EuniceError(f"Unexpected error: {error_str}", original_error=error)

    def _log_error(self, error: EuniceError, context: Optional[str] = None):
        """Log an error with appropriate level and formatting."""
        log_message = f"[{error.error_type.value}] {error.message}"
        if context:
            log_message = f"{log_message} (Context: {context})"

        error_dict = error.to_dict()

        # Log at appropriate level
        if error.error_type in [ErrorType.NETWORK_ERROR, ErrorType.API_ERROR]:
            self.logger.warning(log_message, extra={"error_details": error_dict})
        elif error.error_type in [
            ErrorType.DATABASE_ERROR,
            ErrorType.CONFIGURATION_ERROR,
        ]:
            self.logger.error(log_message, extra={"error_details": error_dict})
        else:
            self.logger.info(log_message, extra={"error_details": error_dict})

    def _track_error(self, error: EuniceError):
        """Track error statistics and recent errors."""
        # Update error counts
        self.error_counts[error.error_type] = (
            self.error_counts.get(error.error_type, 0) + 1
        )

        # Add to recent errors (maintain max size)
        self.recent_errors.append(error)
        if len(self.recent_errors) > self.max_recent_errors:
            self.recent_errors.pop(0)

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        return {
            "total_errors": sum(self.error_counts.values()),
            "error_counts": {
                error_type.value: count
                for error_type, count in self.error_counts.items()
            },
            "recent_errors_count": len(self.recent_errors),
            "recent_errors": [
                error.to_dict() for error in self.recent_errors[-10:]
            ],  # Last 10 errors
        }

    def reset_stats(self):
        """Reset error statistics."""
        self.error_counts.clear()
        self.recent_errors.clear()


# Global error handler instance
_error_handler = ErrorHandler()


def handle_errors(
    context: Optional[str] = None, reraise: bool = True, fallback_return: Any = None
) -> Callable:
    """Decorator for handling errors in functions."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                eunice_error = _error_handler.handle_error(e, context or func.__name__)
                if reraise:
                    raise eunice_error
                return fallback_return

        return wrapper

    return decorator


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    return _error_handler


def safe_execute(
    func: Callable,
    *args,
    context: Optional[str] = None,
    fallback_return: Any = None,
    **kwargs,
) -> Any:
    """Safely execute a function and handle any errors."""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        eunice_error = _error_handler.handle_error(e, context)
        print(f"❌ Error: {eunice_error.message}")
        return fallback_return


def format_error_for_user(error: EuniceError) -> str:
    """Format an error message for display to the user."""
    user_messages = {
        ErrorType.NETWORK_ERROR: "⚠️ Network connection issue. Please check your internet connection and try again.",
        ErrorType.API_ERROR: f"⚠️ AI service error. The {error.details.get('provider', 'AI')} service is temporarily "
        "unavailable.",
        ErrorType.DATABASE_ERROR: "⚠️ Database error. Your data may not be saved properly.",
        ErrorType.CONFIGURATION_ERROR: "⚠️ Configuration error. Please check your settings and API keys.",
        ErrorType.VALIDATION_ERROR: "⚠️ Invalid input. Please check your data and try again.",
        ErrorType.FILE_ERROR: "⚠️ File operation failed. Please check file permissions and try again.",
        ErrorType.UNKNOWN_ERROR: "⚠️ An unexpected error occurred. Please try again.",
    }

    base_message = user_messages.get(error.error_type, "⚠️ An error occurred.")

    # Add specific details for certain error types
    if error.error_type == ErrorType.API_ERROR and error.details.get("status_code"):
        base_message += f" (Status: {error.details['status_code']})"

    return base_message

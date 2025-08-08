"""
Service utilities and helper functions for research_manager.

This module provides common utility functions used across the service including:
- Logging utilities
- Data validation helpers
- File system operations
- Date/time utilities
- Async helpers
"""

import asyncio
import logging
import os
import json
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from functools import wraps
import aiofiles


logger = logging.getLogger("research_manager.utils")


def setup_logging(config: Dict[str, Any]) -> None:
    """
    Set up logging configuration for the service.
    
    Args:
        config: Logging configuration dictionary
    """
    try:
        # Configure logging from config
        logging.basicConfig(
            level=getattr(logging, config.get("level", "INFO").upper()),
            format=config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(config.get("file", "/app/logs/service.log"))
            ]
        )
        
        # Set specific logger levels
        loggers = config.get("loggers", {})
        for logger_name, logger_config in loggers.items():
            logger_obj = logging.getLogger(logger_name)
            logger_obj.setLevel(getattr(logging, logger_config.get("level", "INFO").upper()))
        
        logger.info("Logging configured successfully")
    except Exception as e:
        # Fallback to basic logging
        logging.basicConfig(level=logging.INFO)
        logger.error(f"Failed to configure logging: {e}")


def get_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def format_bytes(bytes_value: int) -> str:
    """
    Format bytes in human readable format.
    
    Args:
        bytes_value: Number of bytes
        
    Returns:
        Human readable string (e.g., "1.2 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f} PB"


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename


def validate_json(data: str) -> Optional[Dict[str, Any]]:
    """
    Validate and parse JSON string.
    
    Args:
        data: JSON string to validate
        
    Returns:
        Parsed JSON data or None if invalid
    """
    try:
        return json.loads(data)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}")
        return None


def deep_merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries.
    
    Args:
        dict1: First dictionary
        dict2: Second dictionary (takes precedence)
        
    Returns:
        Merged dictionary
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result


async def read_file_async(file_path: Union[str, Path]) -> Optional[str]:
    """
    Read file content asynchronously.
    
    Args:
        file_path: Path to file
        
    Returns:
        File content or None if error
    """
    try:
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
            return await file.read()
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        return None


async def write_file_async(file_path: Union[str, Path], content: str) -> bool:
    """
    Write content to file asynchronously.
    
    Args:
        file_path: Path to file
        content: Content to write
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure directory exists
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as file:
            await file.write(content)
        return True
    except Exception as e:
        logger.error(f"Failed to write file {file_path}: {e}")
        return False


async def read_json_file(file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """
    Read and parse JSON file asynchronously.
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        Parsed JSON data or None if error
    """
    content = await read_file_async(file_path)
    if content:
        return validate_json(content)
    return None


async def write_json_file(file_path: Union[str, Path], data: Dict[str, Any], indent: int = 2) -> bool:
    """
    Write data to JSON file asynchronously.
    
    Args:
        file_path: Path to JSON file
        data: Data to write
        indent: JSON indentation
        
    Returns:
        True if successful, False otherwise
    """
    try:
        content = json.dumps(data, indent=indent, default=str)
        return await write_file_async(file_path, content)
    except Exception as e:
        logger.error(f"Failed to write JSON file {file_path}: {e}")
        return False


async def read_yaml_file(file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """
    Read and parse YAML file asynchronously.
    
    Args:
        file_path: Path to YAML file
        
    Returns:
        Parsed YAML data or None if error
    """
    try:
        content = await read_file_async(file_path)
        if content:
            return yaml.safe_load(content)
        return None
    except Exception as e:
        logger.error(f"Failed to read YAML file {file_path}: {e}")
        return None


def retry_async(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator for retrying async functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retries
        delay: Initial delay between retries
        backoff: Backoff multiplier
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}")
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}")
            
            raise last_exception
        return wrapper
    return decorator


def timeout_async(seconds: float):
    """
    Decorator for adding timeout to async functions.
    
    Args:
        seconds: Timeout in seconds
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                logger.error(f"Function {func.__name__} timed out after {seconds} seconds")
                raise
        return wrapper
    return decorator


class AsyncContextManager:
    """Base class for async context managers."""
    
    async def __aenter__(self):
        """Enter async context."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        pass


class RateLimiter:
    """Simple rate limiter for async operations."""
    
    def __init__(self, max_calls: int, time_window: float):
        """
        Initialize rate limiter.
        
        Args:
            max_calls: Maximum calls allowed in time window
            time_window: Time window in seconds
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> bool:
        """
        Acquire permission to make a call.
        
        Returns:
            True if call is allowed, False otherwise
        """
        async with self._lock:
            now = datetime.now(timezone.utc).timestamp()
            
            # Remove old calls outside time window
            self.calls = [call_time for call_time in self.calls 
                         if now - call_time < self.time_window]
            
            # Check if we can make a new call
            if len(self.calls) < self.max_calls:
                self.calls.append(now)
                return True
            
            return False
    
    async def wait_and_acquire(self) -> None:
        """Wait until a call can be made and acquire permission."""
        while not await self.acquire():
            await asyncio.sleep(0.1)


class CircuitBreaker:
    """Circuit breaker pattern for handling failures."""
    
    def __init__(self, failure_threshold: int = 5, timeout: float = 60.0):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Time to wait before trying again
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
        self._lock = asyncio.Lock()
    
    async def call(self, func, *args, **kwargs):
        """
        Call function through circuit breaker.
        
        Args:
            func: Function to call
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        async with self._lock:
            if self.state == "open":
                if (datetime.now(timezone.utc).timestamp() - 
                    self.last_failure_time) > self.timeout:
                    self.state = "half-open"
                else:
                    raise Exception("Circuit breaker is open")
            
            try:
                result = await func(*args, **kwargs)
                
                # Reset on success
                if self.state == "half-open":
                    self.state = "closed"
                    self.failure_count = 0
                
                return result
                
            except Exception as e:
                self.failure_count += 1
                self.last_failure_time = datetime.now(timezone.utc).timestamp()
                
                if self.failure_count >= self.failure_threshold:
                    self.state = "open"
                
                raise e


def ensure_directory(path: Union[str, Path]) -> Path:
    """
    Ensure directory exists, create if it doesn't.
    
    Args:
        path: Directory path
        
    Returns:
        Path object
    """
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj


def get_file_size(file_path: Union[str, Path]) -> int:
    """
    Get file size in bytes.
    
    Args:
        file_path: Path to file
        
    Returns:
        File size in bytes, 0 if file doesn't exist
    """
    try:
        return Path(file_path).stat().st_size
    except FileNotFoundError:
        return 0


def is_valid_url(url: str) -> bool:
    """
    Validate URL format.
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid URL, False otherwise
    """
    import re
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return bool(url_pattern.match(url))


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate string to specified length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


class PerformanceTimer:
    """Context manager for measuring execution time."""
    
    def __init__(self, name: str = "operation"):
        """
        Initialize timer.
        
        Args:
            name: Name of the operation being timed
        """
        self.name = name
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        """Start timing."""
        self.start_time = datetime.now(timezone.utc)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing and log result."""
        self.end_time = datetime.now(timezone.utc)
        duration = (self.end_time - self.start_time).total_seconds()
        logger.info(f"{self.name} completed in {duration:.3f} seconds")
    
    @property
    def duration(self) -> Optional[float]:
        """Get duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

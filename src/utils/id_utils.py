"""
Utility functions for generating unique identifiers and managing constants.

This module provides standardized ID generation functions to avoid code duplication
and ensure consistent ID formats across the application.
"""

import uuid
from datetime import datetime
from typing import Optional

# Constants for ID generation and formatting
MAX_TASK_NAME_LENGTH = 50
TIMESTAMP_FORMAT = "%Y % m%d_ % H%M % S"


def generate_timestamped_id(prefix: str) -> str:
    """
    Generate a timestamped ID with the given prefix.

    Args:
        prefix: The prefix to use for the ID (e.g., 'topic', 'plan', 'task')

    Returns:
        A string ID in the format '{prefix}_{timestamp}'

    Example:
        >>> generate_timestamped_id('topic')
        'topic_20240721_143052'
    """
    timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
    return f"{prefix}_{timestamp}"


def generate_uuid_id(prefix: Optional[str] = None) -> str:
    """
    Generate a UUID - based ID with optional prefix.

    Args:
        prefix: Optional prefix to use for the ID

    Returns:
        A string ID with UUID format, optionally prefixed

    Example:
        >>> generate_uuid_id('plan')
        'plan_a1b2c3d4 - e5f6 - 7890 - abcd - ef1234567890'
    """
    uuid_str = str(uuid.uuid4())
    return f"{prefix}_{uuid_str}" if prefix else uuid_str


def truncate_task_name(query: str, max_length: int = MAX_TASK_NAME_LENGTH) -> str:
    """
    Truncate a query string to create a task name within the specified length.

    Args:
        query: The original query string
        max_length: Maximum length for the task name (default: MAX_TASK_NAME_LENGTH)

    Returns:
        Truncated string with ellipsis if needed

    Example:
        >>> truncate_task_name("This is a very long research query that needs truncation")
        "This is a very long research query that needs..."
    """
    if len(query) <= max_length:
        return query
    return f"{query[:max_length]}..."


def generate_task_name(query: str, provided_name: Optional[str] = None) -> str:
    """
    Generate a task name from a query, using provided name if available.

    Args:
        query: The research query string
        provided_name: Optional pre - provided task name

    Returns:
        A formatted task name

    Example:
        >>> generate_task_name("machine learning algorithms", None)
        "Research: machine learning algorithms"
        >>> generate_task_name("neural networks", "ML Research Task")
        "ML Research Task"
    """
    if provided_name:
        return provided_name

    truncated_query = truncate_task_name(query)
    return f"Research: {truncated_query}"

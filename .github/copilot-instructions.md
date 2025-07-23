# Programming Best Practices

This file contains guidelines and best practices for development in this project.

## Things to NEVER Do!!!

- Do not EVER use mock / simulated data, always use real data or properly mocked objects.
- Do not EVER hardcode data into code, always use configuration files or environment variables.

## Documentation Standards

- Use Markdown format for all documentation files.
- Write clear, concise, and informative docstrings for all public modules, classes, and functions.
- Use Google or NumPy style for docstrings.
- Keep documentation up-to-date with code changes.
- Always fix lint errors.
- Markdown fenced-code-language: Fenced code blocks must have a language specified.

## Code Style and Formatting

### PEP 8 Compliance

- Follow PEP 8 style guide for Python code
- Use 4 spaces for indentation (never tabs)
- Limit lines to 79 characters for code, 72 for docstrings/comments
- Use snake_case for variables and functions
- Use PascalCase for class names
- Use UPPER_CASE for constants

### Import Organization

- Group imports in this order:
  1. Standard library imports
  2. Related third-party imports
  3. Local application/library imports
- Use absolute imports when possible
- Avoid wildcard imports (`from module import *`)

```python
# Good
import os
import sys
from collections import defaultdict

import requests
import numpy as np

from src.utils import helper_function
```

## Code Structure and Organization

### Function Design

- Keep functions small and focused on a single responsibility
- Use descriptive function names that explain what they do
- Limit function parameters (ideally 3 or fewer)
- Use type hints for better code documentation

```python
def calculate_average_score(scores: List[float]) -> float:
    """Calculate the average of a list of scores."""
    return sum(scores) / len(scores)
```

### Class Design

- Follow the Single Responsibility Principle
- Use `__init__` for initialization only
- Implement `__str__` and `__repr__` for better debugging
- Use property decorators for getters/setters

### Error Handling

- Use specific exception types rather than bare `except:`
- Handle exceptions at the appropriate level
- Use context managers (`with` statements) for resource management
- Log errors appropriately

```python
# Good
try:
    with open('file.txt', 'r') as f:
        data = f.read()
except FileNotFoundError:
    logger.error("File not found: file.txt")
    return None
```

## Documentation and Comments

### Docstrings

- Use docstrings for all public modules, classes, and functions
- Follow Google or NumPy docstring conventions
- Include parameter types, return types, and examples when helpful

```python
def process_data(data: List[Dict], threshold: float = 0.5) -> List[Dict]:
    """Process data by filtering based on threshold.

    Args:
        data: List of dictionaries containing data points
        threshold: Minimum value for filtering (default: 0.5)

    Returns:
        Filtered list of dictionaries

    Raises:
        ValueError: If threshold is negative
    """
```

### Comments

- Write comments that explain "why", not "what"
- Keep comments up-to-date with code changes
- Use TODO comments for future improvements

## Testing Best Practices

### Test Structure

- Use pytest for testing framework
- Organize tests in a separate `tests/` directory
- Mirror the source code structure in tests
- Use descriptive test function names

### Test Writing

- Follow AAA pattern: Arrange, Act, Assert
- Write tests before or alongside code (TDD/BDD)
- Test edge cases and error conditions
- Use fixtures for common test data

```python
def test_calculate_average_score_with_valid_scores():
    # Arrange
    scores = [80.0, 85.0, 90.0]
    expected = 85.0

    # Act
    result = calculate_average_score(scores)

    # Assert
    assert result == expected
```

## Performance and Optimization

### General Guidelines

- Profile before optimizing
- Use built-in functions and libraries when possible
- Prefer list comprehensions over loops when appropriate
- Use generators for large datasets

```python
# Good - List comprehension
squares = [x**2 for x in range(10)]

# Good - Generator for large datasets
def process_large_file(filename):
    with open(filename, 'r') as f:
        for line in f:
            yield process_line(line)
```

### Memory Management

- Use `__slots__` for classes with many instances
- Delete large objects explicitly when done
- Use context managers for resource cleanup

## Security Best Practices

### Input Validation

- Validate all user inputs
- Use parameterized queries for database operations
- Sanitize data before processing

### Secrets Management

- Never commit secrets to version control
- Use environment variables for configuration
- Use secure random number generation

```python
import os
import secrets

# Good - Environment variables
api_key = os.environ.get('API_KEY')

# Good - Secure random generation
token = secrets.token_hex(16)
```

## Dependencies and Virtual Environments

### Dependency Management

- Use virtual environments for project isolation
- Pin dependency versions in requirements.txt
- Regularly update dependencies for security
- Use `pip-tools` for dependency resolution

### Package Structure

- Use `setup.py` or `pyproject.toml` for installable packages
- Include proper metadata and classifiers
- Use semantic versioning

## Logging and Monitoring

### Logging Best Practices

- Use the `logging` module instead of print statements
- Configure appropriate log levels
- Include contextual information in log messages
- Use structured logging for production applications

```python
import logging

logger = logging.getLogger(__name__)

def process_user_data(user_id: str):
    logger.info(f"Processing data for user {user_id}")
    try:
        # Process data
        pass
    except Exception as e:
        logger.error(f"Failed to process data for user {user_id}: {str(e)}")
```

## Version Control Best Practices

### Git Workflow

- Use meaningful commit messages
- Make small, focused commits
- Use feature branches for development
- Write good pull request descriptions

### .gitignore

- Exclude virtual environments
- Exclude compiled Python files (\*.pyc, **pycache**)
- Exclude IDE-specific files
- Exclude sensitive configuration files

## Code Review Guidelines

### What to Look For

- Code functionality and correctness
- Code style and consistency
- Test coverage and quality
- Documentation completeness
- Security vulnerabilities
- Performance implications

### Review Process

- Review code in small chunks
- Provide constructive feedback
- Ask questions when unclear
- Suggest improvements, not just problems

## Tools and Automation

### Recommended Tools

- **Linting**: flake8, pylint, or ruff
- **Formatting**: black or autopep8
- **Type Checking**: mypy or pyright
- **Testing**: pytest
- **Documentation**: Sphinx
- **Dependencies**: pip-tools or poetry

### Pre-commit Hooks

- Set up pre-commit hooks for code quality
- Include linting, formatting, and basic tests
- Ensure consistent code style across the team

## Project-Specific Guidelines

### File Organization

- Keep related functionality in the same module
- Use clear, descriptive file and directory names
- Separate business logic from presentation logic
- Create utility modules for common functions

### Configuration Management

- Use configuration files (JSON, YAML, or TOML)
- Separate development and production configurations
- Document all configuration options

Remember: These are guidelines, not rigid rules. Use judgment to determine when exceptions are appropriate, and always prioritize code clarity and maintainability.

# Development Guide - Eunice Research Platform

## Overview

This guide provides comprehensive information for developers contributing to the Eunice Research Platform. The platform has been recently optimized with 93.7% code quality improvement and is now production-ready.

## Getting Started

### Prerequisites for Development

- **Python 3.11+** (required for optimal compatibility)
- **Node.js 18+** (for frontend development)
- **Git** (latest version)
- **VS Code** (recommended IDE)
- **Virtual Environment** (mandatory)

### Development Environment Setup

#### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/pzanna/Eunice.git
cd Eunice

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies
```

#### 2. Development Tools Setup

```bash
# Install development tools (if not in requirements-dev.txt)
pip install pytest pytest-asyncio pytest-cov
pip install black isort autoflake flake8
pip install pre-commit

# Set up pre-commit hooks (if .pre-commit-config.yaml exists)
pre-commit install
```

#### 3. IDE Configuration

**VS Code Extensions (Recommended):**

- Python
- Black Formatter
- isort
- autoflake
- Flake8
- GitLens
- Thunder Client (for API testing)

**VS Code Settings (.vscode/settings.json):**

```json
{
    "python.defaultInterpreterPath": "./.venv/bin/python",
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--line-length", "120"],
    "python.linting.flake8Enabled": true,
    "python.linting.flake8Args": ["--max-line-length=120"],
    "python.isortEnabled": true,
    "python.isortArgs": ["--profile", "black"],
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    }
}
```

## Code Standards and Guidelines

### Code Style (ENFORCED)

The platform uses professional code formatting standards:

#### 1. Python Code Style

- **Formatter**: Black with 120 character line length
- **Import Sorting**: isort with black profile
- **Unused Import Removal**: autoflake
- **Linting**: flake8 with 120 character line length

```bash
# Apply formatting (required before commits)
python -m black src/ --line-length 120
python -m isort src/ --profile black
python -m autoflake --remove-all-unused-imports --recursive src/

# Check code quality
python -m flake8 src/ --count --statistics --max-line-length=120
```

#### 2. Code Quality Standards

**Current Status**: 515/8,212 issues remaining (93.7% improvement)

**Acceptable Standards**:

- Flake8 issues should not exceed 600 total
- No syntax errors allowed
- All critical (E9xx, F8xx) errors must be fixed
- Long lines (E501) should be manually reviewed

#### 3. Naming Conventions

```python
# Variables and functions: snake_case
user_data = get_user_information()

# Classes: PascalCase
class ResearchManager:
    pass

# Constants: UPPER_CASE
MAX_RETRY_ATTEMPTS = 3

# Private methods: leading underscore
def _internal_helper(self):
    pass

# File names: snake_case
research_manager.py
```

### Documentation Standards

#### 1. Docstring Format

Use Google-style docstrings:

```python
def process_research_data(data: Dict[str, Any], threshold: float = 0.5) -> List[Dict]:
    """Process research data by filtering based on threshold.

    Args:
        data: Dictionary containing research data points
        threshold: Minimum value for filtering (default: 0.5)

    Returns:
        List of filtered dictionaries

    Raises:
        ValueError: If threshold is negative
        TypeError: If data is not a dictionary

    Example:
        >>> data = {"study1": 0.8, "study2": 0.3}
        >>> result = process_research_data(data, 0.6)
        >>> len(result)
        1
    """
    if threshold < 0:
        raise ValueError("Threshold must be non-negative")
    
    # Implementation here
```

#### 2. Code Comments

```python
# Good: Explain why, not what
# Use exponential backoff to handle rate limiting
retry_delay = base_delay * (2 ** attempt)

# Bad: Explain what (obvious)
# Set retry_delay to base_delay times 2 to the power of attempt
retry_delay = base_delay * (2 ** attempt)
```

### Git Workflow

#### 1. Branch Strategy

```bash
# Main branches
main                    # Production-ready code
Literature_Reviews      # Current development branch
feature/feature-name    # Feature development
bugfix/issue-description # Bug fixes
hotfix/critical-issue   # Critical production fixes
```

#### 2. Commit Messages

Follow conventional commits:

```bash
# Format: type(scope): brief description
feat(agents): add memory optimization for research manager
fix(api): resolve authentication timeout issue
docs(readme): update installation instructions
refactor(core): optimize database connection handling
test(literature): add unit tests for search functionality
style(all): apply black formatting to entire codebase
```

#### 3. Pull Request Process

1. **Create Feature Branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes and Test**

   ```bash
   # Make your changes
   python -m pytest tests/
   python -m flake8 src/ --count --statistics --max-line-length=120
   ```

3. **Apply Code Formatting**

   ```bash
   python -m black src/ --line-length 120
   python -m isort src/ --profile black
   python -m autoflake --remove-all-unused-imports --recursive src/
   ```

4. **Commit Changes**

   ```bash
   git add .
   git commit -m "feat(scope): description of changes"
   ```

5. **Create Pull Request**
   - Provide clear description
   - Reference related issues
   - Include test results
   - Ensure CI passes

## Testing Guidelines

### Test Structure

```
tests/
├── __init__.py
├── unit/                 # Unit tests
│   ├── test_agents/
│   ├── test_core/
│   └── test_utils/
├── integration/          # Integration tests
│   ├── test_api/
│   └── test_database/
├── e2e/                 # End-to-end tests
└── fixtures/            # Test data and fixtures
```

### Writing Tests

#### 1. Unit Tests

```python
import pytest
from unittest.mock import Mock, patch
from src.core.research_manager import ResearchManager

class TestResearchManager:
    @pytest.fixture
    def research_manager(self):
        """Create a research manager instance for testing."""
        config = Mock()
        return ResearchManager(config)
    
    def test_initialize_project(self, research_manager):
        """Test project initialization."""
        project_data = {
            "title": "Test Project",
            "description": "Test Description"
        }
        
        result = research_manager.initialize_project(project_data)
        
        assert result is not None
        assert result.title == "Test Project"
    
    @pytest.mark.asyncio
    async def test_async_research_operation(self, research_manager):
        """Test async research operations."""
        with patch('src.core.research_manager.external_api_call') as mock_call:
            mock_call.return_value = {"status": "success"}
            
            result = await research_manager.perform_research("test query")
            
            assert result["status"] == "success"
            mock_call.assert_called_once()
```

#### 2. Integration Tests

```python
import pytest
from src.api.v2_hierarchical_api import app
from fastapi.testclient import TestClient

class TestAPIIntegration:
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_health_endpoint(self, client):
        """Test API health endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_research_endpoint(self, client):
        """Test research endpoint."""
        research_data = {
            "query": "test research query",
            "type": "literature_review"
        }
        
        response = client.post("/api/v2/research", json=research_data)
        
        assert response.status_code == 200
        assert "task_id" in response.json()
```

### Running Tests

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=src --cov-report=html

# Run specific test file
python -m pytest tests/unit/test_research_manager.py

# Run tests with verbose output
python -m pytest -v

# Run tests matching pattern
python -m pytest -k "test_research"
```

## Architecture Guidelines

### Project Structure

```
src/
├── __init__.py
├── main.py                 # Application entry point
├── agents/                 # Agent implementations
│   ├── base_agent.py
│   ├── literature_agent.py
│   └── research_manager.py
├── api/                    # API layer
│   ├── v2_hierarchical_api.py
│   └── middleware/
├── core/                   # Core business logic
│   ├── research_manager.py
│   └── context_manager.py
├── config/                 # Configuration management
│   └── config_manager.py
├── mcp/                    # MCP server components
│   ├── server.py
│   └── protocols.py
├── models/                 # Data models
│   └── research_models.py
├── storage/                # Database layer
│   └── systematic_review_database.py
└── utils/                  # Utility functions
    └── error_handler.py
```

### Design Principles

#### 1. Separation of Concerns

- **API Layer**: Handle HTTP requests/responses
- **Core Layer**: Business logic and orchestration
- **Storage Layer**: Database operations
- **Utils Layer**: Shared utilities

#### 2. Dependency Injection

```python
# Good: Inject dependencies
class ResearchManager:
    def __init__(self, config: ConfigManager, database: Database):
        self.config = config
        self.database = database

# Bad: Hard-coded dependencies
class ResearchManager:
    def __init__(self):
        self.config = ConfigManager()  # Hard-coded
        self.database = Database()     # Hard-coded
```

#### 3. Error Handling

```python
# Use custom exceptions with proper error handling
from src.utils.error_handler import ResearchError, handle_errors

@handle_errors
async def perform_research(query: str) -> Dict[str, Any]:
    """Perform research with proper error handling."""
    try:
        result = await external_api_call(query)
        return result
    except APIError as e:
        raise ResearchError(f"Research failed: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error in research: {e}")
        raise ResearchError("Internal research error") from e
```

## Performance Guidelines

### Database Operations

```python
# Use async database operations
async def get_research_data(self, query: str) -> List[Dict]:
    """Get research data with async database operation."""
    async with self.database.get_connection() as conn:
        result = await conn.execute(
            "SELECT * FROM research_data WHERE query LIKE ?",
            (f"%{query}%",)
        )
        return await result.fetchall()

# Use connection pooling and prepared statements
# Implement proper indexing on frequently queried columns
```

### Memory Management

```python
# Use generators for large datasets
def process_large_dataset(data_source):
    """Process large dataset with generator."""
    for batch in data_source.get_batches(batch_size=1000):
        yield process_batch(batch)

# Implement proper cleanup
async def cleanup_resources(self):
    """Clean up resources properly."""
    if self.connection:
        await self.connection.close()
    if self.cache:
        self.cache.clear()
```

### Caching Strategies

```python
# Implement intelligent caching
from functools import lru_cache
from typing import Optional

@lru_cache(maxsize=128)
def get_cached_research_result(query: str) -> Optional[Dict]:
    """Get cached research result."""
    # Implementation here
    pass

# Use time-based cache invalidation for API responses
```

## Debugging and Troubleshooting

### Logging Standards

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Use structured logging
logger.info(
    "Research operation completed",
    extra={
        "query": query,
        "results_count": len(results),
        "duration": duration,
        "user_id": user_id
    }
)
```

### Debugging Tools

```bash
# Debug with pdb
python -m pdb src/main.py

# Debug with VS Code debugger (recommended)
# Set breakpoints in VS Code and use F5 to start debugging

# Profile performance
python -m cProfile -o profile.stats src/main.py
python -c "import pstats; pstats.Stats('profile.stats').sort_stats('tottime').print_stats()"
```

### Common Issues and Solutions

#### 1. Import Errors

```bash
# Ensure PYTHONPATH is set
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Use absolute imports
from src.core.research_manager import ResearchManager

# Not relative imports
from ..core.research_manager import ResearchManager  # Avoid
```

#### 2. Async/Await Issues

```python
# Ensure proper async context
async def main():
    async with ResearchManager() as manager:
        result = await manager.perform_research("query")

# Use asyncio.run for top-level async calls
if __name__ == "__main__":
    asyncio.run(main())
```

## Deployment and Production

### Environment Management

```bash
# Use environment-specific configuration
# .env.development
DEBUG=True
LOG_LEVEL=DEBUG
DATABASE_URL=sqlite:///./data/dev_eunice.db

# .env.production
DEBUG=False
LOG_LEVEL=INFO
DATABASE_URL=postgresql://user:pass@prod-db:5432/eunice
```

### Health Checks

```python
# Implement comprehensive health checks
async def health_check() -> Dict[str, str]:
    """Comprehensive health check."""
    checks = {
        "database": "unknown",
        "external_apis": "unknown",
        "memory_usage": "unknown"
    }
    
    try:
        # Database check
        await database.ping()
        checks["database"] = "healthy"
    except Exception:
        checks["database"] = "unhealthy"
    
    # Additional checks...
    
    return checks
```

### Monitoring

```python
# Add performance monitoring
import time
from contextlib import contextmanager

@contextmanager
def monitor_performance(operation_name: str):
    """Monitor operation performance."""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        logger.info(f"{operation_name} completed in {duration:.2f}s")
```

## Contributing

### Before Contributing

1. **Read the Documentation**: Understand the platform architecture
2. **Set Up Development Environment**: Follow the setup guide exactly
3. **Run Tests**: Ensure all tests pass before making changes
4. **Check Code Quality**: Verify flake8 shows acceptable issue count

### Contribution Checklist

- [ ] Code follows style guidelines (black, isort, flake8)
- [ ] Tests are written and passing
- [ ] Documentation is updated
- [ ] Commit messages follow conventional format
- [ ] No syntax errors or critical flake8 issues
- [ ] Performance impact considered
- [ ] Security implications reviewed

### Code Review Process

1. **Self Review**: Review your own code first
2. **Automated Checks**: Ensure CI passes
3. **Peer Review**: Address feedback promptly
4. **Final Approval**: Maintainer approval required

## Resources

### Documentation

- **Installation Guide**: `docs/Installation_Guide.md`
- **Troubleshooting**: `docs/Troubleshooting.md`
- **API Documentation**: `docs/` directory
- **Architecture Overview**: `docs/Architecture.md`

### Tools and Extensions

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Code linting
- **pytest**: Testing framework
- **VS Code**: Recommended IDE

### Support

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and community support
- **Documentation**: Comprehensive guides in `docs/` directory

---

**Platform Status**: ✅ Production Ready (v2.0.0)
**Code Quality**: 93.7% Optimized
**Development**: Ready for contributions and enhancement

Happy coding! 🚀

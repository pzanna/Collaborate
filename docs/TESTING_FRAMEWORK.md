# Testing Framework Documentation

## Overview

This document provides comprehensive documentation for the testing framework implemented for the Collaborate multi-agent research system. The testing framework ensures all components function correctly and meet performance requirements.

## Table of Contents

- [Overview](#overview)
- [Test Structure](#test-structure)
- [Test Categories](#test-categories)
- [Running Tests](#running-tests)
- [Test Configuration](#test-configuration)
- [Test Data Management](#test-data-management)
- [Performance Testing](#performance-testing)
- [Integration Testing](#integration-testing)
- [Continuous Integration](#continuous-integration)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Test Structure

The testing framework is organized in the `tests/` directory with the following structure:

```
tests/
├── __init__.py                     # Test package initialization
├── conftest.py                     # Shared fixtures and configuration
├── test_unit_ai_clients.py        # AI client unit tests (13 tests)
├── test_unit_mcp.py               # MCP protocol unit tests (24 tests)
├── test_unit_mcp_simple.py        # Simplified MCP tests (11 tests)
├── test_unit_storage.py           # Storage/database unit tests (29 tests)
├── test_unit_debug.py             # Debug functions unit tests (28 tests)
├── test_integration.py            # Integration tests (11 tests)
├── test_performance_e2e.py        # Performance and E2E tests (9 tests)
└── __pycache__/                   # Compiled test files
```

**Total Test Count**: 126+ test cases across all components

## Test Categories

### 1. Unit Tests

**Purpose**: Test individual components in isolation

**Files**:

- `test_unit_ai_clients.py` - OpenAI and xAI client testing (13 tests)
- `test_unit_mcp.py` - MCP protocol component testing (24 tests)
- `test_unit_mcp_simple.py` - Simplified MCP protocol tests (11 tests)
- `test_unit_storage.py` - Database and storage testing (29 tests)
- `test_unit_debug.py` - Debug functions and diagnostics (28 tests)

**Markers**:

- `@pytest.mark.unit` - Standard unit tests
- `@pytest.mark.fast` - Quick running tests

### 2. Integration Tests

**Purpose**: Test component interactions and workflows

**Files**:

- `test_integration.py` - Cross-component integration testing (11 tests)

**Markers**:

- `@pytest.mark.integration` - Integration test suite
- `@pytest.mark.asyncio` - Async integration tests

### 3. Performance Tests

**Purpose**: Validate performance characteristics and load handling

**Files**:

- `test_performance_e2e.py` - Performance and stress testing (9 tests)

**Markers**:

- `@pytest.mark.performance` - Performance benchmarks
- `@pytest.mark.slow` - Long-running stress tests

### 4. End-to-End Tests

**Purpose**: Test complete application workflows

**Files**:

- `test_performance_e2e.py` - Complete workflow testing

**Markers**:

- `@pytest.mark.e2e` - End-to-end workflow tests

## Running Tests

### Basic Test Execution

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit                    # Unit tests only
pytest -m integration            # Integration tests only
pytest -m performance           # Performance tests only
pytest -m e2e                   # End-to-end tests only

# Run fast tests (excluding slow performance tests)
pytest -m "not slow"

# Run specific test files
pytest tests/test_unit_ai_clients.py
pytest tests/test_integration.py
```

### Verbose Output

```bash
# Detailed output
pytest -v

# Show print statements
pytest -s

# Coverage reporting
pytest --cov=src --cov-report=html
```

### Parallel Test Execution

```bash
# Install pytest-xdist for parallel execution
pip install pytest-xdist

# Run tests in parallel
pytest -n auto                   # Auto-detect CPU cores
pytest -n 4                     # Use 4 workers
```

## Test Configuration

### pytest.ini Configuration

The `pytest.ini` file configures the test environment:

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --strict-markers
    --disable-warnings
    --tb=short
    -ra
markers =
    unit: Unit tests for individual components
    integration: Integration tests across components
    performance: Performance and load tests
    e2e: End-to-end workflow tests
    fast: Quick running tests
    slow: Long running tests (excluded by default)
    asyncio: Async tests requiring event loop
```

### Environment Variables

Set these environment variables for testing:

```bash
# Test configuration
export CONFIG_PATH="/path/to/test_config.json"
export TEST_DATABASE_PATH="/tmp/test.db"
export LOG_LEVEL="DEBUG"

# API keys (use test keys if available)
export OPENAI_API_KEY="test-key-or-real-key"
export XAI_API_KEY="test-key-or-real-key"
```

## Test Data Management

### Fixtures (conftest.py)

The `conftest.py` file provides shared fixtures:

#### Configuration Fixtures

- `config_manager`: Configured ConfigManager instance
- `temp_config_file`: Temporary configuration file

#### Database Fixtures

- `database_manager`: In-memory database instance
- `sample_project`: Test project data
- `sample_conversation`: Test conversation data
- `sample_message`: Test message data

#### Test Data Factory

- `TestDataFactory`: Generates realistic test data
  - `create_test_project()`: Generate test projects
  - `create_test_conversation()`: Generate test conversations
  - `create_test_message()`: Generate test messages

### Example Usage

```python
def test_database_operations(database_manager, sample_project):
    """Test using shared fixtures."""
    # Use pre-configured database and sample data
    created_project = database_manager.create_project(sample_project)
    assert created_project is not None
```

## Performance Testing

### Performance Test Categories

1. **Database Performance**

   - Bulk operation timing
   - Concurrent access testing
   - Memory usage monitoring
   - Connection stress testing

2. **AI Client Performance**

   - Response time benchmarks
   - Concurrent request handling
   - Rate limiting compliance

3. **Memory and Resource Usage**
   - Memory leak detection
   - Resource cleanup validation
   - Large dataset handling

### Performance Benchmarks

The performance tests establish these benchmarks:

- **Database Operations**:

  - 100 conversations: < 5 seconds
  - 500 messages: < 10 seconds
  - Concurrent operations: < 15 seconds
  - Memory usage increase: < 100MB for 1000 messages

- **AI Client Response**:
  - Mock response time: < 0.1 seconds
  - Error handling: Graceful degradation

### Running Performance Tests

```bash
# Run all performance tests
pytest -m performance

# Run excluding slow stress tests
pytest -m "performance and not slow"

# Run with timing output
pytest -m performance --durations=10
```

## Integration Testing

### Integration Test Scenarios

1. **AI Client Manager Integration**

   - Multiple client coordination
   - Response aggregation
   - Error handling across clients

2. **Database Integration**

   - CRUD operations workflow
   - Transaction management
   - Data consistency validation

3. **Context Manager Integration**

   - Context creation and tracking
   - Multi-conversation context
   - Context persistence

4. **End-to-End Workflow**
   - Complete research session
   - User interaction simulation
   - Multi-agent coordination

### Example Integration Test

```python
@pytest.mark.integration
async def test_complete_research_workflow(config_manager, database_manager):
    """Test complete research workflow integration."""
    # 1. Create project and conversation
    project = await create_test_project()
    conversation = await create_test_conversation(project.id)

    # 2. Process user query
    user_message = await process_user_input("Research topic")

    # 3. Generate AI responses
    responses = await generate_multi_agent_responses(user_message)

    # 4. Validate results
    assert len(responses) >= 1
    assert all(response.content for response in responses)
```

## Continuous Integration

### GitHub Actions Configuration

Create `.github/workflows/test.yml`:

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v3
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-test.txt

      - name: Run unit tests
        run: pytest -m "unit and fast" --cov=src

      - name: Run integration tests
        run: pytest -m integration

      - name: Run performance tests (fast only)
        run: pytest -m "performance and not slow"
```

### Pre-commit Hooks

Set up pre-commit hooks with `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: pytest-unit
        name: pytest unit tests
        entry: pytest -m "unit and fast"
        language: python
        pass_filenames: false
        always_run: true
```

## Best Practices

### Test Writing Guidelines

1. **Test Naming**

   ```python
   def test_should_create_project_when_valid_data_provided():
       """Test names should describe expected behavior."""
       pass
   ```

2. **AAA Pattern**

   ```python
   def test_example():
       # Arrange
       user_input = "test query"

       # Act
       result = process_input(user_input)

       # Assert
       assert result is not None
   ```

3. **Test Isolation**

   - Use fixtures for test data
   - Clean up resources after tests
   - Avoid test interdependencies

4. **Mock External Dependencies**
   ```python
   @patch('src.ai_clients.openai_client.OpenAI')
   def test_with_mocked_client(mock_openai):
       mock_openai.return_value.create.return_value = "mock response"
       # Test logic here
   ```

### Performance Test Guidelines

1. **Set Realistic Benchmarks**

   - Base benchmarks on actual usage patterns
   - Allow reasonable tolerances
   - Consider hardware variations

2. **Monitor Resource Usage**

   - Track memory consumption
   - Monitor CPU usage
   - Check database connection limits

3. **Test Failure Scenarios**
   - Network timeouts
   - Database connection failures
   - API rate limiting

### Debugging Test Failures

1. **Verbose Output**

   ```bash
   pytest -vvv --tb=long tests/test_file.py::test_function
   ```

2. **Debug Mode**

   ```bash
   pytest --pdb tests/test_file.py::test_function
   ```

3. **Logging Output**
   ```bash
   pytest -s --log-cli-level=DEBUG
   ```

## Troubleshooting

### Common Issues

1. **Database Lock Errors**

   ```python
   # Solution: Use proper database cleanup
   @pytest.fixture
   def database_manager():
       db = DatabaseManager(":memory:")
       yield db
       db.close()  # Ensure cleanup
   ```

2. **Async Test Issues**

   ```python
   # Solution: Use proper async markers
   @pytest.mark.asyncio
   async def test_async_function():
       result = await async_operation()
       assert result is not None
   ```

3. **Import Errors**

   ```bash
   # Solution: Ensure PYTHONPATH includes src
   export PYTHONPATH="${PYTHONPATH}:./src"
   pytest
   ```

4. **Fixture Scope Issues**
   ```python
   # Solution: Use appropriate fixture scope
   @pytest.fixture(scope="function")  # Recreated for each test
   def isolated_fixture():
       return create_resource()
   ```

### Performance Test Debugging

1. **Slow Tests**

   - Profile with `pytest-profiling`
   - Check database query efficiency
   - Optimize test data creation

2. **Memory Issues**

   - Use `pytest-memray` for memory profiling
   - Check for resource leaks
   - Validate cleanup procedures

3. **Flaky Tests**
   - Add retry logic for timing-sensitive tests
   - Use proper synchronization for async tests
   - Mock external dependencies

### Test Data Issues

1. **Data Consistency**

   - Use database transactions for test isolation
   - Reset database state between tests
   - Validate test data integrity

2. **Large Test Datasets**
   - Use data factories for dynamic generation
   - Implement data cleanup strategies
   - Consider using test database snapshots

## Monitoring and Reporting

### Coverage Reporting

```bash
# Generate HTML coverage report
pytest --cov=src --cov-report=html

# View coverage in terminal
pytest --cov=src --cov-report=term-missing
```

### Performance Monitoring

```bash
# Time test execution
pytest --durations=10

# Profile memory usage (requires pytest-memray)
pytest --memray tests/test_performance_e2e.py
```

### Test Result Reporting

```bash
# Generate JUnit XML for CI
pytest --junitxml=test-results.xml

# Generate test report
pytest --html=test-report.html --self-contained-html
```

## Maintenance

### Regular Maintenance Tasks

1. **Update Test Dependencies**

   ```bash
   pip install --upgrade pytest pytest-asyncio pytest-cov
   ```

2. **Review Test Performance**

   - Monitor test execution times
   - Identify slow-running tests
   - Optimize test efficiency

3. **Update Test Data**

   - Refresh fixture data periodically
   - Add new edge cases
   - Remove obsolete test scenarios

4. **Documentation Updates**
   - Keep test documentation current
   - Update configuration examples
   - Document new test patterns

This testing framework provides comprehensive coverage of the Collaborate application, ensuring reliability, performance, and maintainability of the multi-agent research system.

# API Gateway Test Suite

Comprehensive test suite for the Eunice API Gateway service, covering all REST API endpoints including project management, research topics, research plans, and execution endpoints.

## Overview

This test suite provides:

- **Complete API Coverage**: Tests for all endpoints in the API Gateway
- **CRUD Operations**: Create, Read, Update, Delete tests for all resources
- **Error Handling**: Tests for validation errors and edge cases
- **Integration Testing**: End-to-end workflow testing
- **Data Validation**: Schema and constraint validation tests
- **Performance Testing**: Basic response time and reliability tests

## Test Structure

### Test Files

- `test_api.py` - Main test suite with all API endpoint tests
- `conftest.py` - pytest configuration and fixtures
- `run_tests.py` - Test runner script with multiple execution options

### Test Categories

1. **Health Check Tests**
   - Service availability and status

2. **Project CRUD Tests**
   - Create, list, get, update, delete projects
   - Status filtering and pagination
   - Error handling for invalid data

3. **Research Topic CRUD Tests**
   - Topic management within projects
   - Project-scoped and direct topic operations
   - Status filtering and validation

4. **Research Plan CRUD Tests**
   - Plan creation and management
   - AI-generated plan testing
   - Plan approval workflows

5. **Research Execution Tests**
   - Task execution with different depths (undergraduate, masters, phd)
   - Different task types (literature_review, systematic_review, meta_analysis)
   - Execution progress tracking

6. **Statistics Tests**
   - Project, topic, and plan statistics
   - Hierarchy navigation
   - Cost and completion tracking

7. **Error Handling Tests**
   - Invalid input validation
   - Resource not found scenarios
   - Authorization and authentication edge cases

8. **Data Validation Tests**
   - Name validation (empty, whitespace-only)
   - Type constraints and enums
   - Required field validation

## Running Tests

### Prerequisites

1. **API Gateway Service**: Must be running on `http://localhost:8001`
2. **Database**: PostgreSQL database available
3. **Dependencies**: Install test dependencies:

```bash
pip install pytest pytest-asyncio httpx
```

### Quick Start

```bash
# Check if API Gateway is available
python testing/run_tests.py --check-service

# Run all tests
python testing/run_tests.py --all

# Run specific test
python testing/run_tests.py --test health_check

# Run tests with pytest and coverage
python testing/run_tests.py --pytest --coverage
```

### Test Runner Options

The `run_tests.py` script provides multiple options:

```bash
# Basic usage
python testing/run_tests.py [options]

# Options:
--all, -a              Run all tests
--test TEST, -t TEST    Run specific test
--pattern PATTERN      Run tests matching pattern
--check-service, -c     Check API Gateway availability
--verbose, -v           Verbose output
--coverage              Generate coverage report
--pytest               Use pytest runner
--no-check              Skip service availability check
```

### Examples

```bash
# Run all project-related tests
python testing/run_tests.py --pattern project

# Run specific test with verbose output
python testing/run_tests.py --test create_project --verbose

# Run tests and generate coverage report
python testing/run_tests.py --pytest --coverage --verbose

# Check service without running tests
python testing/run_tests.py --check-service
```

## Test Data

### Factory Classes

The test suite uses factory classes to generate consistent test data:

- `TestDataFactory.create_project_data()` - Generate project test data
- `TestDataFactory.create_topic_data()` - Generate topic test data  
- `TestDataFactory.create_plan_data()` - Generate plan test data
- `TestDataFactory.create_execution_data()` - Generate execution test data

### Test Constants

Available through `test_constants` fixture:

```python
PROJECT_STATUSES = ["pending", "active", "complete", "archived"]
TOPIC_STATUSES = ["active", "paused", "completed", "archived"]
PLAN_STATUSES = ["draft", "active", "completed", "cancelled"]
PLAN_TYPES = ["comprehensive", "quick", "deep", "custom"]
TASK_TYPES = ["research", "analysis", "synthesis", "validation", "literature_review", "systematic_review", "meta_analysis"]
RESEARCH_DEPTHS = ["undergraduate", "masters", "phd"]
```

## Configuration

### Environment Variables

```bash
API_GATEWAY_URL=http://localhost:8001    # API Gateway service URL
DATABASE_URL=postgresql://...            # Test database connection
SERVICE_HOST=localhost                   # Service host
SERVICE_PORT=8001                       # Service port
LOG_LEVEL=DEBUG                         # Logging level
```

### Test Configuration

Edit `conftest.py` to modify:

- Test timeouts
- Retry policies
- Database configuration
- Service endpoints

## API Endpoints Tested

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |

### Project Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v2/projects` | Create project |
| GET | `/v2/projects` | List projects |
| GET | `/v2/projects/{id}` | Get project |
| PUT | `/v2/projects/{id}` | Update project |
| DELETE | `/v2/projects/{id}` | Delete project |

### Research Topics

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v2/projects/{project_id}/topics` | Create topic |
| GET | `/v2/projects/{project_id}/topics` | List topics |
| GET | `/topics/{id}` | Get topic |
| GET | `/v2/projects/{project_id}/topics/{id}` | Get topic by project |
| PUT | `/topics/{id}` | Update topic |
| PUT | `/v2/projects/{project_id}/topics/{id}` | Update topic by project |
| DELETE | `/topics/{id}` | Delete topic |
| DELETE | `/v2/projects/{project_id}/topics/{id}` | Delete topic by project |

### Research Plans

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/topics/{topic_id}/plans` | Create plan |
| POST | `/topics/{topic_id}/ai-plans` | Create AI plan |
| GET | `/topics/{topic_id}/plans` | List plans |
| GET | `/plans/{id}` | Get plan |
| PUT | `/plans/{id}` | Update plan |
| DELETE | `/plans/{id}` | Delete plan |
| POST | `/plans/{id}/approve` | Approve plan |

### Research Execution

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v2/topics/{topic_id}/execute` | Execute research |
| GET | `/v2/executions/{execution_id}/progress` | Get progress |

### Statistics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v2/projects/{id}/stats` | Project statistics |
| GET | `/v2/topics/{id}/stats` | Topic statistics |
| GET | `/v2/plans/{id}/stats` | Plan statistics |
| GET | `/v2/projects/{id}/hierarchy` | Project hierarchy |

## Test Patterns

### Basic CRUD Pattern

```python
@pytest.mark.asyncio
async def test_create_resource():
    async with APITestClient() as client:
        # Create test data
        data = TestDataFactory.create_resource_data()
        
        # Make request
        response = await client.post("/endpoint", json=data)
        
        # Assertions
        assert response.status_code == 200
        result = response.json()
        assert result["name"] == data["name"]
```

### Error Handling Pattern

```python
@pytest.mark.asyncio
async def test_invalid_data():
    async with APITestClient() as client:
        # Invalid data
        invalid_data = {"name": ""}
        
        # Make request
        response = await client.post("/endpoint", json=invalid_data)
        
        # Assertions
        assert response.status_code == 422
```

### Integration Test Pattern

```python
@pytest.mark.asyncio
async def test_workflow():
    async with APITestClient() as client:
        # Step 1: Create project
        project_data = TestDataFactory.create_project_data()
        project_response = await client.post("/v2/projects", json=project_data)
        project_id = project_response.json()["id"]
        
        # Step 2: Create topic
        topic_data = TestDataFactory.create_topic_data()
        topic_response = await client.post(f"/v2/projects/{project_id}/topics", json=topic_data)
        topic_id = topic_response.json()["id"]
        
        # Step 3: Verify relationship
        response = await client.get(f"/v2/projects/{project_id}/topics")
        topics = response.json()
        assert len(topics) >= 1
```

## Troubleshooting

### Common Issues

1. **Service Not Available**

   ```
   ❌ API Gateway is not available at http://localhost:8001
   ```

   - Ensure API Gateway service is running
   - Check service configuration and port
   - Verify database connectivity

2. **Test Failures**

   ```
   ❌ test_create_project: 503 Service Unavailable
   ```

   - Check database connection
   - Verify service dependencies
   - Review service logs

3. **Import Errors**

   ```
   ModuleNotFoundError: No module named 'httpx'
   ```

   - Install test dependencies: `pip install pytest pytest-asyncio httpx`

### Debugging

1. **Verbose Output**

   ```bash
   python testing/run_tests.py --all --verbose
   ```

2. **Single Test Debug**

   ```bash
   python testing/run_tests.py --test health_check --verbose
   ```

3. **Service Logs**
   - Check API Gateway service logs for detailed error information
   - Enable DEBUG logging for more detailed output

## Contributing

### Adding New Tests

1. **Follow Naming Convention**: Test functions should start with `test_`
2. **Use Factories**: Use `TestDataFactory` for consistent test data
3. **Test Error Cases**: Include both success and failure scenarios
4. **Document Tests**: Add clear docstrings explaining test purpose

### Test Structure

```python
@pytest.mark.asyncio
async def test_new_endpoint():
    """Test description explaining what this test validates."""
    async with APITestClient() as client:
        # Arrange - set up test data
        
        # Act - make the API call
        
        # Assert - verify the results
```

### Best Practices

- **Independent Tests**: Each test should be self-contained
- **Clean Up**: Use fixtures for cleanup when needed
- **Meaningful Assertions**: Test specific behaviors, not just status codes
- **Edge Cases**: Include boundary conditions and error scenarios
- **Performance**: Consider response times for critical endpoints

## Test Results

The test suite generates comprehensive output including:

- ✅ Passed tests with execution time
- ❌ Failed tests with detailed error messages
- 📊 Summary statistics (passed/failed counts)
- 🔧 Environment configuration details
- 📈 Coverage reports (when enabled)

Example output:

```
🔧 Test environment configured
✅ API Gateway is available at http://localhost:8001
🚀 Running all tests...

✅ test_health_check
✅ test_create_project
✅ test_list_projects
...

📊 Test Results: 45 passed, 0 failed
```

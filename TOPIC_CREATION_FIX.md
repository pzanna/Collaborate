# Topics Not Being Stored in Database - Issue Resolution

## Problem Summary

The API Gateway was returning `404 Not Found` for `POST /v2/projects/{project_id}/topics` requests, preventing research topics from being created and stored in the database.

**Logs showing the issue:**
```
INFO: 151.101.0.223:65126 - "POST /v2/projects/589e3d6d-79d1-497e-9780-42f32d4547f5/topics HTTP/1.1" 404 Not Found
INFO: 151.101.0.223:62710 - "POST /v2/projects/589e3d6d-79d1-497e-9780-42f32d4547f5/topics HTTP/1.1" 404 Not Found
```

## Root Cause

The issue was caused by the **project lookup validation** in the `create_research_topic` endpoint. The endpoint correctly validates that the parent project exists before allowing topic creation, but the specific project ID `589e3d6d-79d1-497e-9780-42f32d4547f5` was not found in the database.

**Code flow:**
1. Client sends `POST /v2/projects/{project_id}/topics`
2. API Gateway calls `await db.get_project(project_id)`
3. Database returns `None` (project not found)
4. Endpoint returns `HTTP 404 Not Found` with message "Project not found"

## Solution

### Immediate Fix

1. **Enhanced Logging**: Added detailed logging to the topic creation endpoint to diagnose project lookup issues:
   ```python
   logger.info(f"Creating research topic for project_id: {project_id}")
   logger.info(f"Looking up project in database: {project_id}")
   ```

2. **Debug Endpoint**: Added `/v2/debug/database` endpoint to check database connectivity and project existence.

3. **Production Script**: Created `scripts/ensure_project_exists.py` to verify and create missing projects.

### Usage

To resolve the specific issue in production:

```bash
# Run the project existence script
cd /path/to/eunice
python3 scripts/ensure_project_exists.py 589e3d6d-79d1-497e-9780-42f32d4547f5

# Or let it use the default ID from logs:
python3 scripts/ensure_project_exists.py
```

## Verification

After running the fix script, test the endpoint:

```bash
# Test project lookup
curl -X GET http://localhost:8001/v2/projects/589e3d6d-79d1-497e-9780-42f32d4547f5

# Test topic creation
curl -X POST http://localhost:8001/v2/projects/589e3d6d-79d1-497e-9780-42f32d4547f5/topics \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Topic",
    "description": "Testing topic creation after fix"
  }'

# Check debug endpoint
curl -X GET http://localhost:8001/v2/debug/database
```

## Files Modified

1. **`services/api-gateway/v2_hierarchical_api.py`**:
   - Enhanced error logging in `create_research_topic` endpoint
   - Added better error handling in database dependency
   - Added debug endpoint for database diagnostics

2. **`scripts/ensure_project_exists.py`** (NEW):
   - Production script to check and create missing projects
   - Comprehensive logging and error handling
   - Can be run in any environment

## Prevention

To prevent this issue in the future:

1. **Data Validation**: Ensure all required projects exist in the database before attempting to create topics
2. **Monitoring**: Monitor API Gateway logs for 404 errors on topic creation endpoints
3. **Health Checks**: Use the debug endpoint to verify database connectivity and project data
4. **Documentation**: Update API documentation to clarify project prerequisites for topic creation

## Technical Details

### API Endpoint Behavior

The `POST /v2/projects/{project_id}/topics` endpoint:
- ✅ **Correctly validates** that the parent project exists
- ✅ **Returns appropriate error codes** (404 when project not found)
- ✅ **Has proper error handling** and logging
- ✅ **Creates topics successfully** when project exists

### Database Schema

The database has proper foreign key relationships:
```sql
research_topics.project_id -> projects.id (ON DELETE CASCADE)
```

This ensures referential integrity and prevents orphaned topics.

### Enhanced Logging Output

With the fix, failed topic creation now shows detailed logs:
```
INFO: Creating research topic for project_id: 589e3d6d-79d1-497e-9780-42f32d4547f5
INFO: Looking up project in database: 589e3d6d-79d1-497e-9780-42f32d4547f5
WARN: Project not found in database: 589e3d6d-79d1-497e-9780-42f32d4547f5
INFO: Available projects in database: [list of project IDs]
```

This makes diagnosing similar issues much easier in the future.
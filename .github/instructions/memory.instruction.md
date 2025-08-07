---
applyTo: "**"
---

# User Memory and Preferences

## Development Environment Preferences

- **Container Management**: User prefers using `./start_dev.sh` for container operations
- **Logging**: User appreciates detailed step-by-step logging with visual indicators
- **Testing**: User values thorough verification of changes through log analysis

## Previous Conversation Context

### Literature Search Workflow Restructuring (August 2, 2025)

**Problem**: JSON object creation with only `id`, `title`, and `abstract` was happening in the wrong part of the workflow
**Root Cause**: Simplified JSON creation was occurring during AI review instead of immediately after search result cleanup
**Solution Implemented**:

#### Correct Workflow Order

1. ✅ Complete literature provider search
2. ✅ Clean up results (normalize, remove empty abstracts)
3. ✅ **Create JSON object with only id, title, abstract** ← MOVED HERE
4. ✅ Store JSON in initial_literature_results column
5. ✅ Send JSON to AI for review
6. ✅ AI returns filtered list
7. ✅ Store updated JSON in reviewed_literature_results column
8. ✅ **Reconcile full results with filtered list and store in literature_records table** ← ADDED

#### Code Changes Made

- **service.py**: Added `_create_simplified_json_records()` helper method
- **service.py**: Modified workflow to create simplified JSON before database storage
- **service.py**: Added reconciliation step to match reviewed articles with full records
- **ai_integration.py**: Removed JSON simplification (now handled earlier)
- **ai_integration.py**: Updated to expect simplified JSON input
- **ai_integration.py**: Fixed validation to expect "abstract" instead of "Abstract"

#### Technical Details

- Literature search now creates simplified JSON immediately after filtering abstracts
- AI integration receives pre-simplified data instead of creating it
- Full literature records are stored in literature_records table after AI review
- Enhanced logging shows the complete data flow through all stages

### MCP Communication Fixes (Prior Session)

**Problem**: "No pending response found" warnings in literature agent logs
**Root Cause**: Response routing conflicts between AI and database integrations
**Solution**: Fixed response handling logic to return False when task doesn't belong to integration

#### Files Modified

- `ai_integration.py`: Fixed `handle_task_result()` return logic for proper task ownership
- `database_integration.py`: Fixed `handle_task_result()` return logic  
- `service.py`: Enhanced message handling with explicit handler tracking
- Increased AI processing timeout from 30 to 60 seconds

#### Current System Status

- ✅ All MCP communication issues resolved
- ✅ Literature search workflow properly ordered
- ✅ Simplified JSON creation moved to correct position
- ✅ Full reconciliation and storage implemented
- ✅ Enhanced logging throughout the pipeline

## User Interaction Patterns

- Appreciates comprehensive problem analysis before implementation
- Values step-by-step progress tracking with visual indicators
- Prefers thorough testing and verification of changes
- Likes detailed explanations of architectural decisions and workflow improvements

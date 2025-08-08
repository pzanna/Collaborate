#!/usr/bin/env python3
"""Script to convert MCP response handling to direct database responses."""

import re

def fix_mcp_responses():
    """Fix all MCP response patterns in the v2 API file."""
    
    file_path = "/Users/paulzanna/Github/Eunice/api-gateway/src/v2_hierarchical_api_clean.py"
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Pattern 1: Create operations (result.success -> result is None)
    # result = await mcp_db.create_X(...)
    # if not result.success: -> if result is None:
    content = re.sub(
        r'result = await mcp_db\.(create_\w+)\(([^)]+)\)\s*\n\s*if not result\.success:\s*\n\s*raise HTTPException\(status_code=500, detail=f"Failed to create \w+: \{result\.error\.message\}"\)',
        r'result = await mcp_db.\1(\2)\n        if result is None:\n            raise HTTPException(status_code=500, detail="Failed to create: No result returned")',
        content,
        flags=re.MULTILINE
    )
    
    # Pattern 2: Update operations (result.success -> result is None)  
    content = re.sub(
        r'result = await mcp_db\.(update_\w+)\(([^)]+)\)\s*\n\s*if not result\.success:\s*\n\s*raise HTTPException\(status_code=500, detail=f"Failed to update \w+: \{result\.error\.message\}"\)',
        r'result = await mcp_db.\1(\2)\n        if result is None:\n            raise HTTPException(status_code=500, detail="Failed to update: No result returned")',
        content,
        flags=re.MULTILINE
    )
    
    # Pattern 3: Delete operations (no result checking needed, just await)
    content = re.sub(
        r'result = await mcp_db\.(delete_\w+)\(([^)]+)\)\s*\n\s*if not result\.success:\s*\n\s*raise HTTPException\(status_code=500, detail=f"Failed to delete \w+: \{result\.error\.message\}"\)',
        r'await mcp_db.\1(\2)',
        content,
        flags=re.MULTILINE
    )
    
    # Pattern 4: Approve operations
    content = re.sub(
        r'result = await mcp_db\.(approve_\w+)\(([^)]+)\)\s*\n\s*if not result\.success:\s*\n\s*raise HTTPException\(status_code=500, detail=f"Failed to approve \w+: \{result\.error\.message\}"\)',
        r'result = await mcp_db.\1(\2)\n        if result is None:\n            raise HTTPException(status_code=500, detail="Failed to approve: No result returned")',
        content,
        flags=re.MULTILINE
    )
    
    # Fix logging statements - replace result.data with result for create/update, remove for delete
    content = re.sub(
        r'logger\.info\(f"(Created|Updated|Approved) (\w+) \{(\w+)\} via MCP: \{result\.data\}"\)',
        r'logger.info(f"\1 \2 {\3} via database: {result}")',
        content
    )
    
    content = re.sub(
        r'logger\.info\(f"Deleted (\w+) \{(\w+)\} via MCP: \{result\.data\}"\)',
        r'logger.info(f"Deleted \1 {\2} via database")',
        content
    )
    
    # Fix any remaining "via MCP" references
    content = content.replace("via MCP", "via database")
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("Fixed MCP response patterns")

if __name__ == "__main__":
    fix_mcp_responses()

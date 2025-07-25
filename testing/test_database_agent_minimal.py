#!/usr/bin/env python3
"""
Minimal Database Agent test that avoids problematic imports.
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("🚀 Starting Minimal Database Agent Test")
print("=" * 50)

try:
    # Import Database Agent directly to avoid problematic __init__.py imports
    from src.agents.database.database_agent import DatabaseAgent
    print("✅ Successfully imported DatabaseAgent")
    
    from src.config.config_manager import ConfigManager
    print("✅ Successfully imported ConfigManager")
    
    from src.mcp.protocols import ResearchAction, AgentResponse
    print("✅ Successfully imported MCP protocols")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

async def test_database_agent_initialization():
    """Test DatabaseAgent can be instantiated."""
    print("\n🧪 Testing Database Agent Initialization")
    
    # Create temporary database 
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
        db_path = tmp_db.name

    try:
        # Create config manager
        config_manager = ConfigManager()
        print("✅ Created ConfigManager")
        
        # Create database agent
        agent = DatabaseAgent(config_manager, db_path)
        print("✅ Created DatabaseAgent instance")
        
        # Try to initialize
        await agent._initialize_agent()
        print("✅ Initialized DatabaseAgent")
        
        # Check agent name and type  
        print(f"✅ Agent ID: {agent.agent_id}")
        print(f"✅ Agent type: {agent.agent_type}")  
        
        # Test capabilities (should not be async)
        try:
            capabilities = agent._get_capabilities()
            print(f"✅ Got capabilities: {len(capabilities)} found")
            if capabilities:
                print(f"   First few: {capabilities[:3]}")
        except Exception as e:
            print(f"❌ Capabilities error: {e}")
        
        # Cleanup
        await agent._cleanup_agent()
        print("✅ Cleaned up agent")
        
        print("✅ Database Agent initialization test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up temp database
        if os.path.exists(db_path):
            os.unlink(db_path)
            print("🧹 Removed temporary database")

async def test_mcp_protocol_structure():
    """Test MCP protocol message creation."""
    print("\n🧪 Testing MCP Protocol Structures")
    
    try:
        # Test ResearchAction creation
        action = ResearchAction(
            task_id="test_123",
            context_id="test_context", 
            agent_type="database",
            action="create_project",
            payload={"name": "Test Project"}
        )
        print("✅ Created ResearchAction")
        print(f"   Task ID: {action.task_id}")
        print(f"   Action: {action.action}")
        print(f"   Payload keys: {list(action.payload.keys())}")
        
        # Test AgentResponse creation
        response = AgentResponse(
            task_id="test_123",
            context_id="test_context",
            agent_type="database", 
            status="completed",
            result={"project_id": "proj_456"}
        )
        print("✅ Created AgentResponse")
        print(f"   Status: {response.status}")
        print(f"   Result: {response.result}")
        
        print("✅ MCP protocol test completed successfully!")
        
    except Exception as e:
        print(f"❌ MCP protocol test failed: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Run minimal tests."""
    await test_database_agent_initialization()
    await test_mcp_protocol_structure()
    
    print("\n" + "=" * 50)
    print("🎉 Minimal Database Agent tests completed!")

if __name__ == "__main__":
    asyncio.run(main())

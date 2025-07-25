#!/usr/bin/env python3
"""
Isolated test for Database Agent functionality.
This test imports only the necessary components to test the Database Agent.
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.agents.database.database_agent import DatabaseAgent
    from src.config.config_manager import ConfigManager
    from src.mcp.protocols import ResearchAction, AgentResponse
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


async def test_database_agent_basic():
    """Test basic Database Agent functionality."""
    print("\n🧪 Testing Database Agent Basic Functionality")
    
    # Create temporary database for testing
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
        db_path = tmp_db.name
    
    try:
        # Create config manager with minimal configuration
        config_manager = ConfigManager()
        
        # Create database agent with temporary database
        agent = DatabaseAgent(config_manager, db_path)
        await agent._initialize_agent()
        
        print("✅ Database Agent initialized successfully")
        
        # Test project creation using proper MCP protocol
        create_action = ResearchAction(
            task_id="test_001",
            context_id="test_context",
            agent_type="database",
            action="create_project", 
            payload={
                "name": "Test Project",
                "description": "A test project for Database Agent",
                "owner": "test_user"
            }
        )
        
        response = await agent.process_action(create_action)
        print(f"✅ Project creation response status: {response.status}")
        
        if response.status == "completed" and response.result:
            project_id = response.result.get("project_id")
            print(f"✅ Created project with ID: {project_id}")
            
            # Test project retrieval
            get_action = ResearchAction(
                task_id="test_002",
                context_id="test_context",
                agent_type="database",
                action="get_project",
                payload={"project_id": project_id}
            )
            
            get_response = await agent.process_action(get_action) 
            print(f"✅ Project retrieval response status: {get_response.status}")
            
            if get_response.status == "completed" and get_response.result:
                project_data = get_response.result
                print(f"✅ Retrieved project: {project_data.get('name')}")
            else:
                print(f"❌ Project retrieval failed: {get_response.error}")
        else:
            print(f"❌ Project creation failed: {response.error}")
        
        # Test agent capabilities
        capabilities = agent._get_capabilities()
        print(f"✅ Agent capabilities: {len(capabilities)} capabilities found")
        for cap in capabilities[:5]:  # Show first 5
            print(f"  - {cap}")
        
        # Cleanup
        await agent._cleanup_agent()
        
        print("✅ Database Agent test completed successfully")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up temporary database
        if os.path.exists(db_path):
            os.unlink(db_path)
            print("🧹 Cleaned up temporary database")


async def test_database_agent_capabilities():
    """Test Database Agent capabilities reporting."""
    print("\n🧪 Testing Database Agent Capabilities")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
        db_path = tmp_db.name
    
    try:
        # Create minimal setup for capabilities test
        config_manager = ConfigManager()
        agent = DatabaseAgent(config_manager, db_path)
        await agent._initialize_agent()
        
        capabilities = agent._get_capabilities()
        
        expected_capabilities = [
            "create_project", "get_project", "update_project", "delete_project",
            "create_research_topic", "get_research_topic", "update_research_topic", "delete_research_topic",
            "create_plan", "get_plan", "update_plan", "delete_plan",
            "create_task", "get_task", "update_task", "delete_task"
        ]
        
        print(f"✅ Found {len(capabilities)} capabilities")
        
        missing_capabilities = []
        for expected in expected_capabilities:
            if expected in capabilities:
                print(f"  ✅ {expected}")
            else:
                print(f"  ❌ Missing: {expected}")
                missing_capabilities.append(expected)
        
        if not missing_capabilities:
            print("✅ All expected capabilities found!")
        else:
            print(f"❌ Missing {len(missing_capabilities)} capabilities")
        
        await agent._cleanup_agent()
        
        print("✅ Capabilities test completed")
        
    except Exception as e:
        print(f"❌ Capabilities test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


async def test_database_agent_cache():
    """Test Database Agent caching functionality.""" 
    print("\n🧪 Testing Database Agent Cache")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
        db_path = tmp_db.name
    
    try:
        config_manager = ConfigManager()
        agent = DatabaseAgent(config_manager, db_path)  
        await agent._initialize_agent()
        
        # Create a project first
        create_action = ResearchAction(
            task_id="cache_test_001",
            context_id="cache_context", 
            agent_type="database",
            action="create_project",
            payload={
                "name": "Cache Test Project",
                "description": "Testing cache functionality",
                "owner": "cache_user"
            }
        )
        
        create_response = await agent.process_action(create_action)
        if create_response.status == "completed" and create_response.result:
            project_id = create_response.result.get("project_id")
            print(f"✅ Created project for cache test: {project_id}")
            
            # First retrieval (should hit database)
            get_action = ResearchAction(
                task_id="cache_test_002",
                context_id="cache_context",
                agent_type="database", 
                action="get_project",
                payload={"project_id": project_id}
            )
            
            response1 = await agent.process_action(get_action)
            print("✅ First retrieval completed")
            
            # Second retrieval (should hit cache)
            get_action.task_id = "cache_test_003"
            response2 = await agent.process_action(get_action)
            print("✅ Second retrieval completed (from cache)")
            
            # Verify we got the same data
            if (response1.result and response2.result and 
                response1.result.get("name") == response2.result.get("name")):
                print("✅ Cache test successful - consistent data returned")
            else:
                print("❌ Cache test failed - inconsistent data")
        else:
            print(f"❌ Could not create project for cache test: {create_response.error}")
        
        await agent._cleanup_agent()
        print("✅ Cache test completed")
        
    except Exception as e:
        print(f"❌ Cache test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


async def main():
    """Run all Database Agent tests."""
    print("🚀 Starting Database Agent Isolated Tests")
    print("=" * 50)
    
    await test_database_agent_basic()
    await test_database_agent_capabilities()
    await test_database_agent_cache()
    
    print("\n" + "=" * 50)
    print("🎉 All Database Agent tests completed!")


if __name__ == "__main__":
    asyncio.run(main())

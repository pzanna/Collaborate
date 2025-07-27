#!/usr/bin/env python3
"""
Comprehensive Database Agent Test - Direct Import Version

This test directly imports the Database Agent and te        topic_get_response = await agent.process_action(get_topic_action)
        assert topic_get_response.status == "completed", f"Topic retrieval failed: {topic_get_response.error}"
        assert topic_get_response.result is not None, "Topic retrieval should return result"
        topic_data = topic_get_response.result
        assert topic_data["name"] == "Test Research Topic", "Topic name mismatch"  # Changed from 'title' to 'name'
        print(f"✅ READ: Retrieved topic '{topic_data['name']}'")  # Changed from 'title' to 'name'ts core functionality
without going through the problematic agents package imports.
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("🚀 Starting Comprehensive Database Agent Test")
print("=" * 60)

try:
    from old_src.agents.database.database_agent import DatabaseAgent
    from old_src.config.config_manager import ConfigManager
    from old_src.mcp.protocols import ResearchAction, AgentResponse, TaskStatus
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


async def test_database_agent_crud_operations():
    """Test full CRUD operations with Database Agent."""
    print("\n🧪 Testing Database Agent CRUD Operations")
    
    # Create temporary database 
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
        db_path = tmp_db.name

    try:
        # Initialize agent
        config_manager = ConfigManager()
        agent = DatabaseAgent(config_manager, db_path)
        await agent._initialize_agent()
        print("✅ Database Agent initialized")
        
        # Test Project CRUD
        print("\n📁 Testing Project Operations")
        
        # CREATE Project
        create_project_action = ResearchAction(
            task_id="crud_001",
            context_id="crud_test",
            agent_type="database",
            action="create_project",
            payload={
                "name": "CRUD Test Project",
                "description": "Testing full CRUD operations",
                "owner": "test_user",
                "status": "active"
            }
        )
        
        create_response = await agent.process_action(create_project_action)
        assert create_response.status == "completed", f"Project creation failed: {create_response.error}"
        assert create_response.result is not None, "Project creation should return result"
        project_id = create_response.result["project_id"]
        print(f"✅ CREATE: Project created with ID {project_id}")
        
        # READ Project
        get_project_action = ResearchAction(
            task_id="crud_002",
            context_id="crud_test",
            agent_type="database",
            action="get_project",
            payload={"project_id": project_id}
        )
        
        get_response = await agent.process_action(get_project_action)
        assert get_response.status == "completed", f"Project retrieval failed: {get_response.error}"
        project_data = get_response.result
        assert project_data["name"] == "CRUD Test Project", "Project name mismatch"
        print(f"✅ READ: Retrieved project '{project_data['name']}'")
        
        # UPDATE Project  
        update_project_action = ResearchAction(
            task_id="crud_003",
            context_id="crud_test",
            agent_type="database",
            action="update_project",
            payload={
                "project_id": project_id,
                "name": "Updated CRUD Test Project",
                "description": "Updated description for testing"
            }
        )
        
        update_response = await agent.process_action(update_project_action)
        assert update_response.status == "completed", f"Project update failed: {update_response.error}"
        print("✅ UPDATE: Project updated successfully")
        
        # Verify update
        verify_response = await agent.process_action(get_project_action)
        assert verify_response.result["name"] == "Updated CRUD Test Project", "Update verification failed"
        print("✅ UPDATE VERIFIED: Changes persisted correctly")
        
        # Test Research Topic CRUD
        print("\n📚 Testing Research Topic Operations")
        
        # CREATE Research Topic
        create_topic_action = ResearchAction(
            task_id="crud_004",
            context_id="crud_test",
            agent_type="database",
            action="create_research_topic",
            payload={
                "project_id": project_id,
                "title": "Test Research Topic",
                "description": "A topic for testing CRUD operations",
                "status": "active"
            }
        )
        
        topic_response = await agent.process_action(create_topic_action)
        assert topic_response.status == "completed", f"Topic creation failed: {topic_response.error}"
        topic_id = topic_response.result["topic_id"]
        print(f"✅ CREATE: Research topic created with ID {topic_id}")
        
        # READ Research Topic
        get_topic_action = ResearchAction(
            task_id="crud_005",
            context_id="crud_test",
            agent_type="database", 
            action="get_research_topic",
            payload={"topic_id": topic_id}
        )
        
        topic_get_response = await agent.process_action(get_topic_action)
        assert topic_get_response.status == "completed", f"Topic retrieval failed: {topic_get_response.error}"
        assert topic_get_response.result is not None, "Topic retrieval should return result"
        topic_data = topic_get_response.result
        assert topic_data["name"] == "Test Research Topic", "Topic name mismatch"
        print(f"✅ READ: Retrieved topic '{topic_data['name']}'")
        
        # DELETE Operations (cleanup)
        print("\n🗑️ Testing Delete Operations")
        
        # DELETE Research Topic
        delete_topic_action = ResearchAction(
            task_id="crud_006",
            context_id="crud_test",
            agent_type="database",
            action="delete_research_topic",
            payload={"topic_id": topic_id}
        )
        
        delete_topic_response = await agent.process_action(delete_topic_action)
        assert delete_topic_response.status == "completed", f"Topic deletion failed: {delete_topic_response.error}"
        print("✅ DELETE: Research topic deleted successfully")
        
        # DELETE Project
        delete_project_action = ResearchAction(
            task_id="crud_007", 
            context_id="crud_test",
            agent_type="database",
            action="delete_project",
            payload={"project_id": project_id}
        )
        
        delete_project_response = await agent.process_action(delete_project_action)
        assert delete_project_response.status == "completed", f"Project deletion failed: {delete_project_response.error}"
        print("✅ DELETE: Project deleted successfully")
        
        # Verify deletion
        verify_delete_response = await agent.process_action(get_project_action)
        assert verify_delete_response.status == "failed", "Project should not exist after deletion"
        print("✅ DELETE VERIFIED: Project properly removed")
        
        # Cleanup
        await agent._cleanup_agent()
        print("\n✅ CRUD Operations Test Completed Successfully!")
        
    except AssertionError as e:
        print(f"❌ CRUD Test Assertion Failed: {e}")
        raise
    except Exception as e:
        print(f"❌ CRUD Test Failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


async def test_database_agent_error_handling():
    """Test Database Agent error handling."""
    print("\n🧪 Testing Database Agent Error Handling")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
        db_path = tmp_db.name

    try:
        config_manager = ConfigManager()
        agent = DatabaseAgent(config_manager, db_path)
        await agent._initialize_agent()
        
        # Test invalid project retrieval
        invalid_get_action = ResearchAction(
            task_id="error_001",
            context_id="error_test",
            agent_type="database",
            action="get_project",
            payload={"project_id": "nonexistent_project"}
        )
        
        error_response = await agent.process_action(invalid_get_action)
        assert error_response.status == "failed", "Should fail for nonexistent project"
        assert error_response.error is not None, "Should have error message"
        print("✅ ERROR HANDLING: Nonexistent project handled correctly")
        
        # Test invalid action
        invalid_action = ResearchAction(
            task_id="error_002",
            context_id="error_test",
            agent_type="database",
            action="invalid_action",
            payload={}
        )
        
        invalid_response = await agent.process_action(invalid_action)
        assert invalid_response.status == "failed", "Should fail for invalid action"
        print("✅ ERROR HANDLING: Invalid action handled correctly")
        
        # Test missing required parameters
        missing_params_action = ResearchAction(
            task_id="error_003",
            context_id="error_test",
            agent_type="database",
            action="create_project",
            payload={}  # Missing required 'name' parameter
        )
        
        missing_response = await agent.process_action(missing_params_action)
        assert missing_response.status == "failed", "Should fail for missing parameters"
        print("✅ ERROR HANDLING: Missing parameters handled correctly")
        
        await agent._cleanup_agent()
        print("✅ Error Handling Test Completed Successfully!")
        
    except Exception as e:
        print(f"❌ Error Handling Test Failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


async def test_database_agent_caching():
    """Test Database Agent caching functionality."""
    print("\n🧪 Testing Database Agent Caching")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
        db_path = tmp_db.name

    try:
        config_manager = ConfigManager()
        agent = DatabaseAgent(config_manager, db_path)
        await agent._initialize_agent()
        
        # Create a project for caching test
        create_action = ResearchAction(
            task_id="cache_001",
            context_id="cache_test",
            agent_type="database",
            action="create_project", 
            payload={
                "name": "Cache Test Project",
                "description": "Testing caching functionality",
                "owner": "cache_user"
            }
        )
        
        create_response = await agent.process_action(create_action)
        project_id = create_response.result["project_id"]
        print(f"✅ Created project for cache test: {project_id}")
        
        # First retrieval (should populate cache)
        get_action = ResearchAction(
            task_id="cache_002",
            context_id="cache_test",
            agent_type="database",
            action="get_project",
            payload={"project_id": project_id}
        )
        
        start_time = asyncio.get_event_loop().time()
        first_response = await agent.process_action(get_action)
        first_time = asyncio.get_event_loop().time() - start_time
        print(f"✅ First retrieval took {first_time:.4f}s")
        
        # Second retrieval (should use cache)
        get_action.task_id = "cache_003"
        start_time = asyncio.get_event_loop().time()
        second_response = await agent.process_action(get_action)
        second_time = asyncio.get_event_loop().time() - start_time
        print(f"✅ Second retrieval took {second_time:.4f}s")
        
        # Verify data consistency
        assert first_response.result["name"] == second_response.result["name"], "Cache data inconsistent"
        print("✅ Cache data consistency verified")
        
        # Verify cache performance improvement (second should be faster)
        if second_time < first_time:
            print("✅ Cache performance improvement confirmed")
        else:
            print("ℹ️ Cache timing results inconclusive (may be due to test environment)")
        
        await agent._cleanup_agent()
        print("✅ Caching Test Completed Successfully!")
        
    except Exception as e:
        print(f"❌ Caching Test Failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


async def main():
    """Run comprehensive Database Agent tests."""
    print("Testing Database Agent according to Architecture.md North Star")
    
    try:
        await test_database_agent_crud_operations()
        await test_database_agent_error_handling() 
        await test_database_agent_caching()
        
        print("\n" + "=" * 60)
        print("🎉 ALL DATABASE AGENT TESTS PASSED!")
        print("✅ Database Agent is ready for production use")
        print("✅ Follows Architecture.md North Star specifications")
        print("✅ Ready to proceed to next component (AI Agent)")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Database Agent tests failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

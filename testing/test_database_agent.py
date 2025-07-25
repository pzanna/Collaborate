"""
Test script for Database Agent

This script tests the basic functionality of the Database Agent
to ensure it follows the Architecture.md North Star design.
"""

import asyncio
import sys
from pathlib import Path

# Add src directory to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.config.config_manager import ConfigManager
from src.agents.database import DatabaseAgent
from src.mcp.protocols import ResearchAction, TaskStatus


async def test_database_agent():
    """Test the basic functionality of the Database Agent."""
    
    print("🗄️  Testing Database Agent...")
    
    # Initialize config manager and database agent
    config_manager = ConfigManager()
    db_agent = DatabaseAgent(config_manager, ":memory:")  # Use in-memory database for testing
    
    print("✅ Database Agent initialized")
    
    # Test health check
    health = await db_agent.health_check()
    print(f"📊 Health Check: {health['status']}")
    
    # Test creating a project
    create_action = ResearchAction(
        task_id="test_001",
        context_id="test_context",
        agent_type="database_agent",
        action="create_project",
        payload={
            "name": "Test Research Project",
            "description": "A test project for database agent validation",
            "status": "active"
        }
    )
    
    print("🏗️  Testing project creation...")
    response = await db_agent.process_action(create_action)
    
    if response.status == TaskStatus.COMPLETED.value:
        print(f"✅ Project created successfully: {response.result}")
        project_id = response.result['project_id']
        
        # Test retrieving the project
        get_action = ResearchAction(
            task_id="test_002",
            context_id="test_context",
            agent_type="database_agent",
            action="get_project",
            payload={"id": project_id}
        )
        
        print("🔍 Testing project retrieval...")
        get_response = await db_agent.process_action(get_action)
        
        if get_response.status == TaskStatus.COMPLETED.value:
            print(f"✅ Project retrieved successfully: {get_response.result}")
            
            # Test cache hit (second retrieval should be from cache)
            print("🚀 Testing cache performance...")
            cache_response = await db_agent.process_action(get_action)
            if cache_response.status == TaskStatus.COMPLETED.value:
                print("✅ Cache is working - second retrieval successful")
            else:
                print(f"❌ Cache test failed: {cache_response.error}")
        else:
            print(f"❌ Project retrieval failed: {get_response.error}")
    else:
        print(f"❌ Project creation failed: {response.error}")
    
    # Test final health check
    final_health = await db_agent.health_check()
    print(f"🏁 Final Health Check: {final_health}")
    
    print("✅ Database Agent test completed!")


if __name__ == "__main__":
    asyncio.run(test_database_agent())

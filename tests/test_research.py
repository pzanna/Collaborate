#!/usr/bin/env python3
"""
Simple test script to verify research functionality
"""

import asyncio
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_research():
    """Test research functionality"""
    try:
        print("🧪 Testing Research Functionality...")
        
        # Import required modules
        from src.config.config_manager import ConfigManager
        from src.core.research_manager import ResearchManager
        
        # Initialize config
        config_manager = ConfigManager()
        
        # Create research manager
        research_manager = ResearchManager(config_manager)
        
        # Initialize research manager (without external MCP client)
        print("📡 Initializing Research Manager...")
        success = await research_manager.initialize()
        
        if success:
            print("✅ Research Manager initialized successfully")
            
            # Start a test research task
            print("🔍 Starting test research task...")
            task_id, cost_info = await research_manager.start_research_task(
                query="What is artificial intelligence?",
                user_id="test_user",
                conversation_id="test_conversation",
                options={'cost_override': True}  # Override cost checks for testing
            )
            
            print(f"📋 Task ID: {task_id}")
            print(f"💰 Cost Info: {cost_info}")
            
            # Check task status
            print("📊 Checking task status...")
            for i in range(10):  # Check for up to 10 seconds
                status = research_manager.get_task_status(task_id)
                if status:
                    print(f"   Status: {status['stage']} - Progress: {status['progress']:.1f}%")
                    
                    if status['stage'] in ['complete', 'failed']:
                        break
                
                await asyncio.sleep(1)
            
            print("🛑 Shutting down...")
            await research_manager.shutdown()
            
        else:
            print("❌ Failed to initialize Research Manager")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_research())

#!/usr/bin/env python3
"""Test search term generation and storage."""

import asyncio
import sys
import json
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.agents.literature_agent import LiteratureAgent
from src.config.config_manager import ConfigManager
from src.storage.hierarchical_database import HierarchicalDatabaseManager

async def test_search_term_storage():
    """Test search term generation and database storage."""
    print("🧪 Testing search term generation and storage...")
    
    try:
        # Initialize components
        config_manager = ConfigManager()
        lit_agent = LiteratureAgent(config_manager)
        await lit_agent.initialize()
        db = HierarchicalDatabaseManager()
        
        # Create test research plan
        research_plan = {
            "objective": "Test search term storage functionality",
            "population": "test algorithms",
            "intervention": "computational models",
            "outcomes": "efficiency metrics"
        }
        
        test_task_id = "test_search_storage_20250724_debug"
        
        print(f"📋 Testing with task ID: {test_task_id}")
        
        # Call search term generator
        print("🔍 Calling search_term_generator...")
        search_terms = await lit_agent.search_term_generator(
            plan=research_plan,
            task_id=test_task_id
        )
        
        print(f"✅ Generated {len(search_terms)} search terms")
        print(f"📝 Search terms: {search_terms[:3]}..." if len(search_terms) > 3 else search_terms)
        
        # Check database storage
        print("💾 Checking database storage...")
        task_data = db.get_research_task(test_task_id)
        
        if task_data:
            print(f"✅ Task found in database: {task_data['id']}")
            if task_data.get('metadata'):
                try:
                    metadata = json.loads(task_data['metadata']) if isinstance(task_data['metadata'], str) else task_data['metadata']
                    if 'search_term_generation' in metadata:
                        stored_terms = metadata['search_term_generation']['search_terms']
                        print(f"✅ Found {len(stored_terms)} stored search terms")
                        print(f"📝 Stored terms match: {stored_terms == search_terms}")
                    else:
                        print("❌ No search_term_generation in metadata")
                        print(f"📋 Available metadata keys: {list(metadata.keys())}")
                except (json.JSONDecodeError, TypeError) as e:
                    print(f"❌ Error parsing metadata: {e}")
                    print(f"📋 Raw metadata: {task_data['metadata']}")
            else:
                print("❌ No metadata in task")
        else:
            print(f"❌ Task {test_task_id} not found in database")
        
        print("🎉 Test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_search_term_storage())

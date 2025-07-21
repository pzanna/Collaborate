"""
Simple production test for PlanningAgent._plan_research function.

This script tests the _plan_research function using the actual production setup
with real configuration and AI clients - no mocking or bypassing.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Optional

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.agents.planning_agent import PlanningAgent
from src.config.config_manager import ConfigManager


async def test_plan_research_production(query: str, context: Optional[Dict] = None):
    """
    Test the _plan_research function using production setup.
    
    Args:
        query: Research query string
        context: Optional context dictionary
    
    Returns:
        Dict: Research plan result
    """
    print(f"🔍 Testing _plan_research with production setup")
    print(f"Query: '{query}'")
    if context:
        print(f"Context: {json.dumps(context, indent=2)}")
    print("=" * 80)
    
    agent = None  # Initialize to None for cleanup
    
    try:
        # Initialize actual config manager (no mocking)
        print("📋 Initializing ConfigManager...")
        config_manager = ConfigManager()
        
        # Create planning agent with real configuration
        print("🤖 Creating PlanningAgent...")
        agent = PlanningAgent(config_manager)
        
        # Initialize the agent (this will set up real AI clients)
        print("⚙️  Initializing agent with real AI clients...")
        await agent._initialize_agent()
        
        # Prepare the payload exactly as the function expects
        payload = {
            'query': query,
            'context': context or {}
        }
        
        print("🚀 Executing _plan_research function...")
        print("-" * 80)
        
        # Call the actual function
        result = await agent._plan_research(payload)
        
        # Display results
        print("\n✅ SUCCESS! Research plan generated")
        print("=" * 80)
        print(f"📝 Query: {result['query']}")
        print(f"🤖 Model Used: {result['planning_model']}")
        print(f"📊 Plan Structure: {list(result['plan'].keys())}")
        
        print("\n📋 GENERATED PLAN:")
        print("-" * 40)
        plan = result['plan']
        for section, content in plan.items():
            if section == 'raw_plan':
                continue  # Skip for brevity
            print(f"\n{section.upper().replace('_', ' ')}:")
            if content:
                # Truncate long content for readability
                content_str = str(content)
                if len(content_str) > 200:
                    print(f"  {content_str[:200]}...")
                else:
                    print(f"  {content_str}")
            else:
                print("  (No content extracted)")
        
        print(f"\n📄 RAW AI RESPONSE ({len(result['raw_response'])} characters):")
        print("-" * 40)
        print(result['raw_response'])
        
        return result
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback:\n{traceback.format_exc()}")
        raise
    
    finally:
        # Clean up
        try:
            if agent is not None:
                print("\n🧹 Cleaning up agent resources...")
                await agent._cleanup_agent()
        except Exception as cleanup_error:
            print(f"⚠️  Cleanup warning: {cleanup_error}")


async def main():
    """Main function to run production tests."""
    print("PlanningAgent._plan_research Production Test")
    print("=" * 80)
    print("This test uses real configuration and AI clients (no mocking)")
    print("=" * 80)
    
    # Test 1: Simple query
    print("\n🧪 TEST 1: Simple research query")
    try:
        result1 = await test_plan_research_production(
            query="What are the main benefits of renewable energy adoption?",
            context={
                'domain': 'energy',
                'focus': 'benefits',
                'scope': 'global'
            }
        )
        print("✅ Test 1 completed successfully!")
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
        return False
    
    print("\n" + "="*100 + "\n")
    
    # Test 2: Complex query with detailed context
    print("🧪 TEST 2: Complex research query with detailed context")
    try:
        result2 = await test_plan_research_production(
            query="How can artificial intelligence improve educational outcomes in K-12 schools?",
            context={
                'domain': 'education',
                'technology': 'artificial_intelligence',
                'target_audience': 'K-12_students',
                'stakeholders': ['teachers', 'students', 'parents', 'administrators'],
                'focus_areas': ['personalized_learning', 'assessment', 'accessibility'],
                'constraints': {
                    'budget': 'limited',
                    'privacy': 'FERPA_compliance',
                    'implementation': 'gradual_rollout'
                },
                'timeframe': '2024-2026',
                'expected_outcomes': ['improved_engagement', 'better_test_scores', 'reduced_achievement_gaps']
            }
        )
        print("✅ Test 2 completed successfully!")
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
        return False
    
    print("\n" + "="*100)
    print("🎉 ALL PRODUCTION TESTS COMPLETED SUCCESSFULLY!")
    print(f"📊 Generated research plans for 2 different queries")
    print("📝 Both tests used real AI clients and configuration")
    return True


if __name__ == "__main__":
    """
    Run the production test.
    
    Usage:
        python test_plan_research_production.py
        
    Requirements:
        - Valid API keys configured in environment or config
        - Internet connection for AI API calls
        - Proper project configuration setup
    """
    print("Starting production test for _plan_research function...")
    print("⚠️  This test requires valid API keys and internet connection")
    print()
    
    try:
        success = asyncio.run(main())
        if success:
            print("\n🏆 Production test completed successfully!")
            sys.exit(0)
        else:
            print("\n💥 Production test failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Production test failed with error: {e}")
        sys.exit(1)

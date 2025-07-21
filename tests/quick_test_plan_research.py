"""
Quick test runner for PlanningAgent._plan_research function.

Simple script to quickly test the _plan_research function with custom input.
Uses real production setup - no mocking.
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


async def quick_test(query: str, context: Optional[Dict] = None):
    """
    Quick test of _plan_research function.
    
    Args:
        query: Research query
        context: Optional context dict
    """
    print(f"🚀 Quick Test: {query}")
    print("=" * 60)
    
    agent = None
    try:
        # Setup
        config_manager = ConfigManager()
        agent = PlanningAgent(config_manager)
        await agent._initialize_agent()
        
        # Execute
        result = await agent._plan_research({
            'query': query,
            'context': context or {}
        })
        
        # Display results
        print(f"✅ Success! Model: {result['planning_model']}")
        print(f"📝 Generated plan with {len(result['raw_response'])} characters")
        print("\n📋 RESEARCH PLAN:")
        print("-" * 40)
        print(result['raw_response'])
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        if agent:
            await agent._cleanup_agent()
        
        # Ensure all logs are flushed before exit
        import logging
        for handler in logging.getLogger().handlers:
            if hasattr(handler, 'flush'):
                handler.flush()
        
        # Also flush AI API specific loggers
        for logger_name in ['ai_api', 'src.ai_clients.openai_client', 'src.ai_clients.xai_client']:
            logger = logging.getLogger(logger_name)
            for handler in logger.handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()


if __name__ == "__main__":
    # Quick test examples - modify these as needed
    
    if len(sys.argv) > 1:
        # Use command line argument as query
        query = " ".join(sys.argv[1:])
        asyncio.run(quick_test(query))
    else:
        # Default test queries
        print("PlanningAgent._plan_research Quick Test")
        print("=" * 50)
        
        # Test 1: Simple query
        asyncio.run(quick_test(
            "What are the benefits of electric vehicles?"
        ))
        
        print("\n" + "="*80 + "\n")
        
        # Test 2: Query with context
        asyncio.run(quick_test(
            "How can blockchain improve supply chain transparency?",
            context={
                'industry': 'manufacturing',
                'focus': 'transparency',
                'stakeholders': ['suppliers', 'manufacturers', 'consumers']
            }
        ))

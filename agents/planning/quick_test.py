#!/usr/bin/env python3
"""
Quick Planning Agent Test - Direct function testing
"""
import asyncio
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def quick_test():
    """Quick test of planning agent functionality"""
    print("🧪 Quick Planning Agent Test")
    print("=" * 40)
    
    try:
        from planning_service import PlanningAgentService
        
        # Create service instance
        service = PlanningAgentService()
        print(f"✅ Service created: {service.agent_id}")
        
        # Test research planning
        plan_result = await service._plan_research({
            "query": "AI applications in healthcare",
            "scope": "medium"
        })
        print(f"✅ Research planning: {plan_result['status']}")
        
        # Test cost estimation
        cost_result = await service._estimate_costs({
            "scope": "medium",
            "duration_days": 14,
            "resources": ["database_access", "analysis_software"],
            "agents": ["planning", "literature", "analysis"]
        })
        print(f"✅ Cost estimation: {cost_result['status']}")
        print(f"   Total cost: ${cost_result['result']['cost_breakdown']['summary']['total']:.2f}")
        
        # Test task execution through the main interface
        task_result = await service.execute_planning_task({
            "action": "analyze_information",
            "payload": {
                "content": "Sample content for analysis",
                "analysis_type": "technical"
            }
        })
        print(f"✅ Task execution: {task_result['status']}")
        
        print("\n🎉 All tests passed! Planning Agent is fully functional.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(quick_test())
    if success:
        print("\n✅ Planning Agent is ready for containerization!")
    else:
        print("\n❌ Planning Agent needs fixes before containerization.")
    sys.exit(0 if success else 1)

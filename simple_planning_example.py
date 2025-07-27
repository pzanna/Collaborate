#!/usr/bin/env python3
"""
Simple Planning Agent API Example

This script demonstrates how to create a research plan via the API Gateway
with the Planning Agent.
"""

from typing import Optional

import asyncio
import json
import httpx


async def create_research_plan(query: str, context: Optional[dict] = None):
    """Create a research plan via API Gateway"""
    api_gateway_url = "http://localhost:8001"  # Updated to correct port
    endpoint = f"{api_gateway_url}/queue/research/planning"  # Updated to correct endpoint
    
    # Default context if none provided
    if context is None:
        context = {
            "scope": "medium",
            "duration_days": 14,
            "budget_limit": 25.0
        }
    
    # Format request according to API Gateway's ResearchRequest schema
    payload = {
        "agent_type": "planning",
        "action": "plan_research",
        "payload": {
            "query": query,
            "context": context
        },
        "priority": "normal",
        "timeout": 300
    }
    
    print(f"🚀 Creating research plan...")
    print(f"Query: {query}")
    print(f"Context: {json.dumps(context, indent=2)}")
    print("-" * 50)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(endpoint, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                
                print("✅ Research plan created successfully!")
                print(f"Status: {result.get('status')}")
                
                if 'result' in result:
                    plan_result = result['result']
                    
                    # Display plan structure
                    if 'plan' in plan_result:
                        plan = plan_result['plan']
                        print(f"\n📋 Research Plan:")
                        
                        print(f"\n🎯 Objectives ({len(plan.get('objectives', []))}):")
                        for i, obj in enumerate(plan.get('objectives', []), 1):
                            print(f"   {i}. {obj}")
                        
                        print(f"\n🔍 Key Areas ({len(plan.get('key_areas', []))}):")
                        for area in plan.get('key_areas', []):
                            print(f"   • {area}")
                        
                        print(f"\n❓ Questions ({len(plan.get('questions', []))}):")
                        for question in plan.get('questions', []):
                            print(f"   ? {question}")
                        
                        print(f"\n📚 Sources ({len(plan.get('sources', []))}):")
                        for source in plan.get('sources', []):
                            print(f"   📖 {source}")
                        
                        print(f"\n🎯 Expected Outcomes ({len(plan.get('outcomes', []))}):")
                        for outcome in plan.get('outcomes', []):
                            print(f"   ✨ {outcome}")
                    
                    # Display cost estimate
                    if 'cost_estimate' in plan_result:
                        cost = plan_result['cost_estimate']
                        print(f"\n💰 Cost Estimate:")
                        print(f"   • Estimated Cost: ${cost.get('estimated_cost', 0):.4f}")
                        print(f"   • Tokens: {cost.get('tokens_estimated', 0):,}")
                        print(f"   • Complexity: {cost.get('complexity', 'N/A')}")
                        
                        if 'optimization_suggestions' in cost:
                            print(f"   • Optimization Tips ({len(cost['optimization_suggestions'])}):")
                            for tip in cost['optimization_suggestions']:
                                print(f"     💡 {tip}")
                    
                    # Display agent info
                    print(f"\n🤖 Agent Info:")
                    print(f"   • Agent ID: {plan_result.get('agent_id', 'N/A')}")
                    print(f"   • Processing Time: {plan_result.get('processing_time', 'N/A')}s")
                
                return result
                
            else:
                print(f"❌ Request failed with status {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return None


async def main():
    """Main function with example usage"""
    print("🧠 Planning Agent API Example")
    print("=" * 60)
    
    # Example 1: Simple research question
    print("\n1️⃣ Simple Research Question")
    result1 = await create_research_plan(
        "What are the benefits of renewable energy?",
        {
            "scope": "low",
            "duration_days": 7,
            "budget_limit": 10.0
        }
    )
    
    # Example 2: Complex research topic
    print("\n\n2️⃣ Complex Research Topic")
    result2 = await create_research_plan(
        "Analyze the impact of artificial intelligence on healthcare diagnostics",
        {
            "scope": "high", 
            "duration_days": 30,
            "budget_limit": 50.0,
            "project_id": "proj_ai_healthcare_2025",
            "research_depth": "comprehensive"
        }
    )
    
    # Example 3: Cost-optimized research
    print("\n\n3️⃣ Cost-Optimized Research")
    result3 = await create_research_plan(
        "Market trends in electric vehicle adoption",
        {
            "scope": "medium",
            "duration_days": 14,
            "budget_limit": 15.0,
            "single_agent_mode": True,
            "optimization_mode": "cost_effective"
        }
    )
    
    # Summary
    print("\n\n📊 Summary")
    print("=" * 60)
    successful = sum(1 for r in [result1, result2, result3] if r is not None)
    print(f"Plans Created: {successful}/3")
    
    if successful == 3:
        print("✅ All research plans created successfully!")
    elif successful > 0:
        print("⚠️ Some plans created - check errors above")
    else:
        print("❌ No plans created - check API Gateway availability")


if __name__ == "__main__":
    asyncio.run(main())

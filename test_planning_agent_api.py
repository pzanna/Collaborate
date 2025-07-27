#!/usr/bin/env python3
"""
API Gateway Planning Agent Test Script

This script tests the Planning Agent via the API Gateway, demonstrating
the complete research planning workflow with cost estimation.
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional

import httpx
import websockets


class PlanningAgentAPITest:
    """Test the Planning Agent via API Gateway"""
    
    def __init__(self, api_gateway_url: str = "http://localhost:8001",  # Updated to correct port
                 mcp_url: str = "ws://localhost:9000"):
        self.api_gateway_url = api_gateway_url
        self.mcp_url = mcp_url
        self.session = httpx.AsyncClient(timeout=30.0)
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.aclose()
    
    async def test_api_gateway_health(self) -> bool:
        """Test API Gateway health endpoint"""
        try:
            response = await self.session.get(f"{self.api_gateway_url}/health")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ API Gateway health check failed: {e}")
            return False
    
    async def test_mcp_connection(self) -> bool:
        """Test direct MCP server connection"""
        try:
            async with websockets.connect(self.mcp_url) as websocket:
                # Send ping to test connection
                ping_message = {
                    "jsonrpc": "2.0",
                    "method": "ping",
                    "id": 1
                }
                await websocket.send(json.dumps(ping_message))
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                return json.loads(response).get("result") == "pong"
        except Exception as e:
            print(f"❌ MCP connection test failed: {e}")
            return False
    
    async def create_research_plan_via_api(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a research plan via API Gateway"""
        endpoint = f"{self.api_gateway_url}/queue/research/planning"  # Updated to correct endpoint
        
        # Format request according to API Gateway's ResearchRequest schema
        payload = {
            "agent_type": "planning",
            "action": "plan_research", 
            "payload": {
                "query": query,
                "context": context or {}
            },
            "priority": "normal",
            "timeout": 300
        }
        
        print(f"🚀 Creating research plan via API Gateway...")
        print(f"   Query: {query}")
        print(f"   Context: {json.dumps(context, indent=2) if context else 'None'}")
        
        start_time = time.time()
        
        try:
            response = await self.session.post(endpoint, json=payload)
            processing_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Research plan created successfully in {processing_time:.2f}s")
                return {
                    "success": True,
                    "data": result,
                    "processing_time": processing_time,
                    "status_code": response.status_code
                }
            else:
                print(f"❌ API request failed with status {response.status_code}")
                print(f"   Response: {response.text}")
                return {
                    "success": False,
                    "error": response.text,
                    "processing_time": processing_time,
                    "status_code": response.status_code
                }
                
        except Exception as e:
            processing_time = time.time() - start_time
            print(f"❌ API request exception: {e}")
            return {
                "success": False,
                "error": str(e),
                "processing_time": processing_time,
                "status_code": None
            }
    
    async def create_research_plan_via_mcp(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a research plan via direct MCP connection"""
        try:
            async with websockets.connect(self.mcp_url) as websocket:
                # Send research planning request
                request = {
                    "jsonrpc": "2.0",
                    "method": "research_action",
                    "params": {
                        "agent_type": "planning",
                        "action": "plan_research",
                        "task_id": f"test_task_{int(time.time())}",
                        "payload": {
                            "query": query,
                            "context": context or {}
                        }
                    },
                    "id": int(time.time())
                }
                
                print(f"🔗 Creating research plan via MCP...")
                print(f"   Query: {query}")
                
                start_time = time.time()
                await websocket.send(json.dumps(request))
                response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                processing_time = time.time() - start_time
                
                result = json.loads(response)
                
                if "result" in result:
                    print(f"✅ MCP research plan created successfully in {processing_time:.2f}s")
                    return {
                        "success": True,
                        "data": result["result"],
                        "processing_time": processing_time
                    }
                else:
                    print(f"❌ MCP request failed: {result.get('error', 'Unknown error')}")
                    return {
                        "success": False,
                        "error": result.get('error', 'Unknown error'),
                        "processing_time": processing_time
                    }
                    
        except Exception as e:
            print(f"❌ MCP request exception: {e}")
            return {
                "success": False,
                "error": str(e),
                "processing_time": 0
            }
    
    def analyze_research_plan(self, plan_data: Dict[str, Any]) -> None:
        """Analyze and display research plan results"""
        if not plan_data.get("success"):
            print(f"❌ Cannot analyze failed plan: {plan_data.get('error')}")
            return
        
        data = plan_data["data"]
        
        print(f"\n📊 Research Plan Analysis:")
        print(f"=" * 50)
        
        # Basic info
        if "result" in data:
            result = data["result"]
            print(f"Query: {result.get('query', 'N/A')}")
            print(f"Agent ID: {result.get('agent_id', 'N/A')}")
            print(f"Processing Time: {result.get('processing_time', 'N/A')}s")
            
            # Plan structure
            if "plan" in result:
                plan = result["plan"]
                print(f"\n📋 Research Plan Structure:")
                print(f"   • Objectives: {len(plan.get('objectives', []))}")
                for i, obj in enumerate(plan.get('objectives', [])[:3], 1):
                    print(f"     {i}. {obj}")
                
                print(f"   • Key Areas: {len(plan.get('key_areas', []))}")
                for area in plan.get('key_areas', [])[:3]:
                    print(f"     - {area}")
                
                print(f"   • Questions: {len(plan.get('questions', []))}")
                for question in plan.get('questions', [])[:2]:
                    print(f"     ? {question}")
                
                print(f"   • Sources: {len(plan.get('sources', []))}")
                for source in plan.get('sources', [])[:3]:
                    print(f"     📚 {source}")
            
            # Cost estimation
            if "cost_estimate" in result:
                cost = result["cost_estimate"]
                print(f"\n💰 Cost Estimation:")
                print(f"   • Estimated Cost: ${cost.get('estimated_cost', 0):.4f}")
                print(f"   • Tokens Estimated: {cost.get('tokens_estimated', 0):,}")
                print(f"   • Complexity: {cost.get('complexity', 'N/A')}")
                
                if "optimization_suggestions" in cost:
                    print(f"   • Optimization Tips: {len(cost['optimization_suggestions'])}")
                    for tip in cost['optimization_suggestions'][:2]:
                        print(f"     💡 {tip}")
        
        print(f"\n⏱️  Total Processing Time: {plan_data['processing_time']:.2f}s")
    
    def compare_api_vs_mcp(self, api_result: Dict[str, Any], mcp_result: Dict[str, Any]) -> None:
        """Compare API Gateway vs direct MCP results"""
        print(f"\n🔄 API Gateway vs MCP Comparison:")
        print(f"=" * 50)
        
        # Success comparison
        api_success = api_result.get("success", False)
        mcp_success = mcp_result.get("success", False)
        print(f"Success Rate:")
        print(f"   • API Gateway: {'✅' if api_success else '❌'}")
        print(f"   • Direct MCP:  {'✅' if mcp_success else '❌'}")
        
        # Performance comparison
        api_time = api_result.get("processing_time", 0)
        mcp_time = mcp_result.get("processing_time", 0)
        print(f"\nPerformance:")
        print(f"   • API Gateway: {api_time:.2f}s")
        print(f"   • Direct MCP:  {mcp_time:.2f}s")
        if mcp_time > 0:
            overhead = ((api_time - mcp_time) / mcp_time) * 100
            print(f"   • API Overhead: {overhead:.1f}%")
        
        # Data comparison
        if api_success and mcp_success:
            api_data = api_result["data"]
            mcp_data = mcp_result["data"]
            
            # Compare plan structure
            api_plan = api_data.get("result", {}).get("plan", {})
            mcp_plan = mcp_data.get("plan", {})
            
            print(f"\nPlan Structure:")
            print(f"   • API Objectives: {len(api_plan.get('objectives', []))}")
            print(f"   • MCP Objectives: {len(mcp_plan.get('objectives', []))}")
            print(f"   • API Key Areas: {len(api_plan.get('key_areas', []))}")
            print(f"   • MCP Key Areas: {len(mcp_plan.get('key_areas', []))}")


async def run_comprehensive_test():
    """Run comprehensive Planning Agent API test"""
    print("🧪 Planning Agent API Gateway Test Suite")
    print("=" * 60)
    
    async with PlanningAgentAPITest() as tester:
        # Test 1: Health checks
        print("\n1️⃣  Health Checks")
        api_healthy = await tester.test_api_gateway_health()
        mcp_healthy = await tester.test_mcp_connection()
        
        if not api_healthy:
            print("⚠️  API Gateway not available - skipping API tests")
        if not mcp_healthy:
            print("⚠️  MCP Server not available - skipping MCP tests")
        
        if not (api_healthy or mcp_healthy):
            print("❌ No services available - exiting")
            return
        
        # Test 2: Simple research planning
        print("\n2️⃣  Simple Research Planning")
        simple_query = "What are the benefits of renewable energy?"
        simple_context = {
            "scope": "low",
            "duration_days": 7
        }
        
        api_simple_result = None
        mcp_simple_result = None
        
        if api_healthy:
            api_simple_result = await tester.create_research_plan_via_api(
                simple_query, simple_context
            )
            tester.analyze_research_plan(api_simple_result)
        
        if mcp_healthy:
            mcp_simple_result = await tester.create_research_plan_via_mcp(
                simple_query, simple_context
            )
            tester.analyze_research_plan(mcp_simple_result)
        
        # Test 3: Complex research planning
        print("\n3️⃣  Complex Research Planning")
        complex_query = "Analyze the impact of artificial intelligence on healthcare diagnostics, including accuracy improvements, cost implications, and implementation challenges across different medical specialties"
        complex_context = {
            "scope": "high",
            "duration_days": 30,
            "budget_limit": 50.0,
            "project_id": "proj_ai_healthcare_2025",
            "research_depth": "comprehensive"
        }
        
        api_complex_result = None
        mcp_complex_result = None
        
        if api_healthy:
            api_complex_result = await tester.create_research_plan_via_api(
                complex_query, complex_context
            )
            tester.analyze_research_plan(api_complex_result)
        
        if mcp_healthy:
            mcp_complex_result = await tester.create_research_plan_via_mcp(
                complex_query, complex_context
            )
            tester.analyze_research_plan(mcp_complex_result)
        
        # Test 4: Cost-optimized planning
        print("\n4️⃣  Cost-Optimized Planning")
        budget_query = "Market analysis of electric vehicle adoption trends"
        budget_context = {
            "scope": "medium",
            "duration_days": 14,
            "budget_limit": 10.0,  # Low budget
            "single_agent_mode": True,
            "optimization_mode": "cost_effective"
        }
        
        if api_healthy:
            api_budget_result = await tester.create_research_plan_via_api(
                budget_query, budget_context
            )
            tester.analyze_research_plan(api_budget_result)
        
        # Test 5: Comparison analysis
        if api_healthy and mcp_healthy and api_simple_result and mcp_simple_result:
            print("\n5️⃣  API vs MCP Comparison")
            tester.compare_api_vs_mcp(api_simple_result, mcp_simple_result)
        
        # Test Summary
        print("\n📊 Test Summary")
        print("=" * 60)
        
        tests_run = 0
        tests_passed = 0
        
        if api_healthy:
            tests_run += 1
            if api_simple_result and api_simple_result.get("success"):
                tests_passed += 1
            
            tests_run += 1
            if api_complex_result and api_complex_result.get("success"):
                tests_passed += 1
        
        if mcp_healthy:
            tests_run += 1
            if mcp_simple_result and mcp_simple_result.get("success"):
                tests_passed += 1
            
            tests_run += 1
            if mcp_complex_result and mcp_complex_result.get("success"):
                tests_passed += 1
        
        print(f"Tests Run: {tests_run}")
        print(f"Tests Passed: {tests_passed}")
        print(f"Success Rate: {tests_passed/tests_run*100:.1f}%" if tests_run > 0 else "No tests run")
        
        if tests_passed == tests_run:
            print("✅ All tests passed - Planning Agent API integration working perfectly!")
        elif tests_passed > 0:
            print("⚠️  Some tests passed - Check failures above")
        else:
            print("❌ All tests failed - Check service availability and configuration")


async def quick_test(query: str):
    """Quick test with custom query"""
    print(f"🚀 Quick Planning Agent Test")
    print(f"Query: {query}")
    print("=" * 60)
    
    async with PlanningAgentAPITest() as tester:
        # Try API Gateway first
        result = await tester.create_research_plan_via_api(query, {
            "scope": "medium",
            "duration_days": 14
        })
        
        if result.get("success"):
            tester.analyze_research_plan(result)
        else:
            print("API Gateway failed, trying direct MCP...")
            mcp_result = await tester.create_research_plan_via_mcp(query)
            tester.analyze_research_plan(mcp_result)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Quick test mode with custom query
        query = " ".join(sys.argv[1:])
        asyncio.run(quick_test(query))
    else:
        # Comprehensive test mode
        asyncio.run(run_comprehensive_test())

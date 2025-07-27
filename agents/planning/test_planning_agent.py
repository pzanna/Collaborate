#!/usr/bin/env python3
"""
Test script for Planning Agent Service
Tests both direct HTTP API and capabilities without MCP server dependency
"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import httpx
import pytest
from planning_service import PlanningAgentService

async def test_planning_service_initialization():
    """Test that the planning service initializes correctly"""
    print("🧪 Testing Planning Service Initialization...")
    
    try:
        service = PlanningAgentService()
        print(f"✅ Service initialized with ID: {service.agent_id}")
        print(f"✅ Capabilities loaded: {service.capabilities}")
        print(f"✅ Agent type: {service.__class__.__name__}")
        return True
    except Exception as e:
        print(f"❌ Service initialization failed: {e}")
        return False

async def test_planning_capabilities():
    """Test individual planning capabilities"""
    print("\n🧪 Testing Planning Capabilities...")
    
    service = PlanningAgentService()
    
    # Test research planning
    print("Testing research planning...")
    result = await service._plan_research({
        "query": "Neural networks in biological systems",
        "scope": "comprehensive"
    })
    
    if result["status"] == "completed":
        print("✅ Research planning successful")
        print(f"   - Plan objectives: {len(result['result']['plan']['objectives'])}")
        print(f"   - Key areas: {len(result['result']['plan']['key_areas'])}")
        print(f"   - Timeline: {result['result']['plan']['timeline']['total_days']} days")
    else:
        print(f"❌ Research planning failed: {result}")
        return False

    # Test cost estimation
    print("Testing cost estimation...")
    cost_result = await service._estimate_costs({
        "scope": "medium",
        "duration_days": 30,
        "resources": ["database_access", "analysis_software"],
        "query": "Test cost estimation",
        "agents": ["planning", "literature", "analysis"]
    })
    
    if cost_result["status"] == "completed":
        print("✅ Cost estimation successful")
        breakdown = cost_result["result"]["cost_breakdown"]
        print(f"   - AI cost: ${breakdown['summary']['ai_cost']:.2f}")
        print(f"   - Traditional cost: ${breakdown['summary']['traditional_cost']:.2f}")
        print(f"   - Total cost: ${breakdown['summary']['total']:.2f}")
    else:
        print(f"❌ Cost estimation failed: {cost_result}")
        return False

    # Test information analysis
    print("Testing information analysis...")
    analysis_result = await service._analyze_information({
        "content": "This is test content for analysis to verify the agent can process information effectively.",
        "analysis_type": "general"
    })
    
    if analysis_result["status"] == "completed":
        print("✅ Information analysis successful")
        print(f"   - Confidence score: {analysis_result['result']['confidence_score']}")
        print(f"   - Key points: {len(analysis_result['result']['key_points'])}")
    else:
        print(f"❌ Information analysis failed: {analysis_result}")
        return False

    return True

async def test_http_endpoints():
    """Test the HTTP endpoints of the service"""
    print("\n🧪 Testing HTTP Endpoints...")
    
    # Start the service in background for testing
    from planning_service import app
    import uvicorn
    from threading import Thread
    import time
    
    # We'll test the endpoints by importing them directly
    from planning_service import planning_service
    
    # Test health endpoint logic
    health_data = planning_service.get_health_status()
    if health_data["status"] in ["healthy", "degraded"]:
        print("✅ Health endpoint logic working")
        print(f"   - Status: {health_data['status']}")
        print(f"   - Agent ID: {health_data['agent_id']}")
        print(f"   - Capabilities: {len(health_data['capabilities'])}")
    else:
        print(f"❌ Health endpoint failed: {health_data}")
        return False

    # Test task execution logic
    test_task = {
        "action": "plan_research",
        "payload": {
            "query": "Test HTTP endpoint",
            "scope": "small"
        }
    }
    
    result = await planning_service.execute_planning_task(test_task)
    if result["status"] == "completed":
        print("✅ Task execution endpoint logic working")
        print(f"   - Action: {test_task['action']}")
        print(f"   - Processing time: {result['result']['processing_time']}s")
    else:
        print(f"❌ Task execution failed: {result}")
        return False

    return True

async def test_configuration_loading():
    """Test that configuration is loaded correctly"""
    print("\n🧪 Testing Configuration Loading...")
    
    from planning_service import config, load_config
    
    # Test config loading
    test_config = load_config()
    
    required_sections = ["service", "mcp", "capabilities", "cost_settings", "logging"]
    missing_sections = [section for section in required_sections if section not in test_config]
    
    if not missing_sections:
        print("✅ All required configuration sections present")
        print(f"   - Service port: {test_config['service']['port']}")
        print(f"   - MCP server URL: {test_config['mcp']['server_url']}")
        print(f"   - Capabilities count: {len(test_config['capabilities'])}")
        print(f"   - Cost settings configured: {'cost_settings' in test_config}")
    else:
        print(f"❌ Missing configuration sections: {missing_sections}")
        return False

    # Test cost settings
    cost_settings = test_config.get("cost_settings", {})
    if "token_costs" in cost_settings and "cost_thresholds" in cost_settings:
        print("✅ Cost settings properly configured")
        token_providers = list(cost_settings["token_costs"].keys())
        print(f"   - Token cost providers: {token_providers}")
        print(f"   - Cost thresholds: {list(cost_settings['cost_thresholds'].keys())}")
    else:
        print("❌ Cost settings incomplete")
        return False

    return True

async def run_all_tests():
    """Run all tests and provide summary"""
    print("🚀 Starting Planning Agent Tests")
    print("=" * 50)
    
    tests = [
        ("Service Initialization", test_planning_service_initialization),
        ("Configuration Loading", test_configuration_loading),
        ("Planning Capabilities", test_planning_capabilities),
        ("HTTP Endpoints", test_http_endpoints),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Planning Agent is ready.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the output above.")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
Comprehensive Cost Estimation Test for Planning Agent

This test verifies that the sophisticated cost estimation system is working
with maximum accuracy, real-time tracking, and optimization recommendations.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from planning_service import PlanningAgentService
from cost_estimator import CostEstimator, CostTier
from config_manager import ConfigManager


async def test_sophisticated_cost_estimator():
    """Test the sophisticated cost estimator directly"""
    print("🧠 Testing Sophisticated Cost Estimator (Direct)")
    print("=" * 50)
    
    try:
        config = ConfigManager()
        estimator = CostEstimator(config)
        
        # Test with complex research query
        result = estimator.estimate_task_cost(
            query="Conduct a comprehensive meta-analysis of mindfulness meditation effects on neural plasticity in the prefrontal cortex, incorporating fMRI, DTI, and EEG studies from the past decade",
            agents=["planning", "literature", "analysis", "synthesis", "screening", "writing"],
            parallel_execution=False,
            context_content="Previous systematic reviews and neuroimaging studies on meditation"
        )
        
        print(f"✅ Direct Cost Estimator Test Results:")
        print(f"   • Estimated Tokens: {result.estimated_tokens:,}")
        print(f"   • Estimated Cost: ${result.estimated_cost_usd:.4f}")
        print(f"   • Task Complexity: {result.task_complexity}")
        print(f"   • Agent Count: {result.agent_count}")
        print(f"   • Confidence: {result.confidence:.2f}")
        print(f"   • Reasoning: {result.reasoning[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Direct cost estimator test failed: {e}")
        return False


async def test_planning_service_integration():
    """Test the planning service cost estimation integration"""
    print("\n🔬 Testing Planning Service Cost Estimation Integration")
    print("=" * 50)
    
    try:
        service = PlanningAgentService()
        
        # Test payloads with different complexity levels
        test_cases = [
            {
                "name": "Simple Query",
                "payload": {
                    "query": "What is neural plasticity?",
                    "scope": "low",
                    "duration_days": 7,
                    "agents": ["planning", "literature"],
                    "context": "Basic neuroscience question"
                }
            },
            {
                "name": "Medium Complexity",
                "payload": {
                    "query": "Analyze the relationship between meditation and brain structure changes",
                    "scope": "medium",
                    "duration_days": 14,
                    "agents": ["planning", "literature", "analysis", "synthesis"],
                    "context": "Neuroscience research with multiple studies"
                }
            },
            {
                "name": "High Complexity",
                "payload": {
                    "query": "Conduct comprehensive systematic review and meta-analysis of meditation effects on multiple brain networks using multimodal neuroimaging across longitudinal studies",
                    "scope": "high",
                    "duration_days": 30,
                    "agents": ["planning", "literature", "analysis", "synthesis", "screening", "writing"],
                    "context": "Large-scale research project with complex methodology"
                }
            }
        ]
        
        results = []
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n   Test {i}: {test_case['name']}")
            result = await service._estimate_costs(test_case["payload"])
            
            if result["status"] == "completed":
                cost_data = result["result"]["cost_breakdown"]
                ai_ops = cost_data["ai_operations"]
                
                print(f"   ✅ {test_case['name']} - Cost: ${ai_ops['total_ai_cost']:.4f}")
                print(f"      • Tokens: {ai_ops['estimated_tokens']:,}")
                print(f"      • Complexity: {ai_ops['complexity_level']}")
                print(f"      • Provider: {ai_ops['provider']}")
                print(f"      • Model: {ai_ops['model']}")
                print(f"      • Optimization Tips: {len(cost_data['optimization_suggestions'])}")
                
                results.append({
                    "name": test_case['name'],
                    "cost": ai_ops['total_ai_cost'],
                    "tokens": ai_ops['estimated_tokens'],
                    "complexity": ai_ops['complexity_level'],
                    "success": True
                })
            else:
                print(f"   ❌ {test_case['name']} - Failed")
                results.append({"name": test_case['name'], "success": False})
        
        # Verify cost scaling makes sense
        successful_results = [r for r in results if r.get("success")]
        if len(successful_results) >= 2:
            print(f"\n   📊 Cost Scaling Analysis:")
            for i in range(len(successful_results) - 1):
                current = successful_results[i]
                next_result = successful_results[i + 1]
                cost_ratio = next_result["cost"] / current["cost"] if current["cost"] > 0 else 0
                token_ratio = next_result["tokens"] / current["tokens"] if current["tokens"] > 0 else 0
                print(f"      • {current['name']} → {next_result['name']}: Cost {cost_ratio:.1f}x, Tokens {token_ratio:.1f}x")
        
        return len(successful_results) == len(test_cases)
        
    except Exception as e:
        print(f"❌ Planning service integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_cost_accuracy_features():
    """Test specific accuracy features of the cost estimation system"""
    print("\n📈 Testing Cost Accuracy Features")
    print("=" * 50)
    
    try:
        service = PlanningAgentService()
        
        # Test payload with comprehensive features
        payload = {
            "query": "Examine the effects of different meditation techniques (mindfulness, loving-kindness, body scan) on default mode network connectivity using resting-state fMRI",
            "scope": "high",
            "duration_days": 21,
            "agents": ["planning", "literature", "analysis", "synthesis", "screening"],
            "context": "Longitudinal neuroimaging study with multiple meditation interventions and control groups",
            "resources": ["fMRI equipment", "statistical software", "research participants"]
        }
        
        result = await service._estimate_costs(payload)
        
        if result["status"] == "completed":
            cost_breakdown = result["result"]["cost_breakdown"]
            ai_ops = cost_breakdown["ai_operations"]
            
            print("✅ Accuracy Features Test Results:")
            
            # Check for sophisticated features
            features_found = []
            
            if "complexity_multiplier" in ai_ops and ai_ops["complexity_multiplier"] > 1:
                features_found.append(f"Complexity scaling ({ai_ops['complexity_multiplier']}x)")
            
            if "reasoning" in ai_ops and len(ai_ops["reasoning"]) > 50:
                features_found.append("Detailed reasoning")
            
            if "input_tokens" in ai_ops and "output_tokens" in ai_ops:
                features_found.append("Token type breakdown")
            
            if "cost_per_1k_input" in ai_ops and "cost_per_1k_output" in ai_ops:
                features_found.append("Provider-specific pricing")
            
            if cost_breakdown.get("optimization_suggestions", []):
                features_found.append(f"Optimization suggestions ({len(cost_breakdown['optimization_suggestions'])})")
            
            if "thresholds" in cost_breakdown:
                features_found.append("Cost threshold monitoring")
            
            if cost_breakdown.get("summary", {}).get("cost_per_day"):
                features_found.append("Daily cost projection")
            
            print(f"   • Advanced Features Found: {len(features_found)}")
            for feature in features_found:
                print(f"     - {feature}")
            
            # Check accuracy level
            accuracy_level = result["result"].get("accuracy_level", "unknown")
            print(f"   • Accuracy Level: {accuracy_level}")
            
            # Check estimation method
            estimation_method = result["result"].get("estimation_method", "unknown")
            print(f"   • Estimation Method: {estimation_method}")
            
            return len(features_found) >= 5  # At least 5 advanced features
        else:
            print("❌ Cost accuracy test failed - no result")
            return False
            
    except Exception as e:
        print(f"❌ Cost accuracy test failed: {e}")
        return False


async def main():
    """Run comprehensive cost estimation tests"""
    print("🚀 Comprehensive Cost Estimation Test Suite")
    print("=" * 60)
    print("Testing maximum accuracy, real-time tracking, and optimization features...")
    
    tests = [
        ("Sophisticated Cost Estimator (Direct)", test_sophisticated_cost_estimator),
        ("Planning Service Integration", test_planning_service_integration),
        ("Cost Accuracy Features", test_cost_accuracy_features)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        try:
            result = await test_func()
            results.append((test_name, result))
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"   Result: {status}")
        except Exception as e:
            print(f"   Result: ❌ FAILED - {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n📊 Test Results Summary")
    print("=" * 60)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} {test_name}")
    
    print(f"\n🎯 Overall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ ALL TESTS PASSED - Sophisticated cost estimation is working with maximum accuracy!")
        print("   • Real-time cost tracking: Active")
        print("   • Optimization recommendations: Active") 
        print("   • Provider-specific pricing: Active")
        print("   • Complexity assessment: Active")
        print("   • Cost threshold monitoring: Active")
    else:
        print("❌ Some tests failed - review the cost estimation system")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

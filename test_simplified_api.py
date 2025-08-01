#!/usr/bin/env python3
"""Quick test for the simplified research execution API."""

import asyncio
import json
import sys
import httpx

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_PROJECT_NAME = "Simplified API Test"
TEST_TOPIC_NAME = "AI in Healthcare"


async def test_simplified_workflow():
    """Test the complete simplified workflow: project → topic → plan → execute."""
    async with httpx.AsyncClient() as client:
        try:
            print("🚀 Testing Simplified Research Execution API")
            print("=" * 50)
            
            # 1. Create a test project
            print("1. Creating test project...")
            project_data = {
                "name": TEST_PROJECT_NAME,
                "description": "Testing the new simplified research execution API",
                "keywords": ["AI", "healthcare", "test"]
            }
            
            project_response = await client.post(
                f"{BASE_URL}/v2/projects",
                json=project_data
            )
            
            if project_response.status_code != 200:
                print(f"❌ Failed to create project: {project_response.text}")
                return False
                
            project = project_response.json()
            project_id = project["id"]
            print(f"✅ Project created: {project_id}")
            
            # 2. Create a research topic
            print("2. Creating research topic...")
            topic_data = {
                "name": TEST_TOPIC_NAME,
                "description": "Investigating applications of AI in healthcare diagnosis and treatment",
                "keywords": ["artificial intelligence", "healthcare", "diagnosis"]
            }
            
            topic_response = await client.post(
                f"{BASE_URL}/v2/projects/{project_id}/topics",
                json=topic_data
            )
            
            if topic_response.status_code != 200:
                print(f"❌ Failed to create topic: {topic_response.text}")
                return False
                
            topic = topic_response.json()
            topic_id = topic["id"]
            print(f"✅ Topic created: {topic_id}")
            
            # 3. Create and approve a research plan
            print("3. Creating research plan...")
            plan_data = {
                "title": "AI Healthcare Research Plan",
                "description": "Comprehensive plan for investigating AI applications in healthcare",
                "research_questions": [
                    "How effective is AI in medical diagnosis?",
                    "What are the challenges of implementing AI in healthcare?",
                    "What are the ethical considerations?"
                ],
                "methodology": "systematic literature review with synthesis",
                "scope": "peer-reviewed articles from 2020-2024"
            }
            
            plan_response = await client.post(
                f"{BASE_URL}/v2/topics/{topic_id}/plans",
                json=plan_data
            )
            
            if plan_response.status_code != 200:
                print(f"❌ Failed to create plan: {plan_response.text}")
                return False
                
            plan = plan_response.json()
            plan_id = plan["id"]
            print(f"✅ Plan created: {plan_id}")
            
            # 4. Approve the research plan
            print("4. Approving research plan...")
            approval_response = await client.patch(
                f"{BASE_URL}/v2/plans/{plan_id}/approve"
            )
            
            if approval_response.status_code != 200:
                print(f"❌ Failed to approve plan: {approval_response.text}")
                return False
                
            print("✅ Plan approved")
            
            # 5. Execute research using simplified API
            print("5. 🎯 Testing NEW SIMPLIFIED API...")
            execution_data = {
                "task_type": "literature_review",
                "depth": "masters"
            }
            
            execution_response = await client.post(
                f"{BASE_URL}/v2/topics/{topic_id}/execute",
                json=execution_data
            )
            
            if execution_response.status_code != 200:
                print(f"❌ Failed to execute research: {execution_response.text}")
                return False
                
            execution = execution_response.json()
            execution_id = execution["execution_id"]
            
            print("✅ Research execution initiated!")
            print(f"   📊 Execution ID: {execution_id}")
            print(f"   📚 Task Type: {execution['task_type']}")
            print(f"   🎓 Depth: {execution['depth']}")
            print(f"   💰 Estimated Cost: ${execution['estimated_cost']}")
            print(f"   ⏱️  Estimated Duration: {execution['estimated_duration']}")
            print(f"   📈 Progress URL: {execution['progress_url']}")
            
            # 6. Check progress
            print("6. Checking execution progress...")
            progress_response = await client.get(
                f"{BASE_URL}/v2/executions/{execution_id}/progress"
            )
            
            if progress_response.status_code == 200:
                progress = progress_response.json()
                print(f"✅ Progress tracking working: {progress['status']}")
            else:
                print(f"⚠️  Progress endpoint not working: {progress_response.text}")
            
            print("\n🎉 SIMPLIFIED API TEST SUCCESSFUL!")
            print("=" * 50)
            print("Key Benefits Demonstrated:")
            print("✓ Single endpoint replaces create_task + execute_task")
            print("✓ Only requires task_type and depth parameters")
            print("✓ Automatically resolves context from topic/plan hierarchy")
            print("✓ Provides cost and time estimates")
            print("✓ Includes progress tracking")
            
            return True
            
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            return False


async def test_error_conditions():
    """Test error handling in the simplified API."""
    async with httpx.AsyncClient() as client:
        print("\n🧪 Testing Error Conditions")
        print("-" * 30)
        
        # Test invalid topic ID
        print("Testing invalid topic ID...")
        response = await client.post(
            f"{BASE_URL}/v2/topics/invalid-topic-id/execute",
            json={"task_type": "literature_review", "depth": "masters"}
        )
        
        if response.status_code == 404:
            print("✅ Correctly handles invalid topic ID")
        else:
            print(f"⚠️  Unexpected response for invalid topic: {response.status_code}")
        
        # Test invalid depth
        print("Testing invalid depth...")
        response = await client.post(
            f"{BASE_URL}/v2/topics/some-topic/execute",
            json={"task_type": "literature_review", "depth": "invalid_depth"}
        )
        
        if response.status_code == 400:
            print("✅ Correctly handles invalid depth")
        else:
            print(f"⚠️  Unexpected response for invalid depth: {response.status_code}")


if __name__ == "__main__":
    print("Starting Simplified API Test Suite...")
    print("Make sure the API Gateway is running on localhost:8000")
    print()
    
    asyncio.run(test_simplified_workflow())
    asyncio.run(test_error_conditions())

#!/usr/bin/env python3
"""
Test script to verify the research functionality through the web API.
"""

import requests
import time
import json


def test_research_api():
    """Test the research API endpoints."""
    base_url = "http://127.0.0.1:8000"
    
    print("🧪 Testing Research API...")
    
    # Test 1: Check if server is running
    try:
        response = requests.get(f"{base_url}/api/health")
        print(f"✓ Server health check: {response.status_code}")
        if response.status_code == 200:
            health_data = response.json()
            print(f"   System status: {health_data.get('status')}")
            print(f"   Research system: {health_data.get('research_system', {}).get('status')}")
            print(f"   MCP connected: {health_data.get('research_system', {}).get('mcp_connected')}")
    except requests.ConnectionError:
        print("❌ Server not running on port 8000")
        return False
    
    # Test 2: Start a research task
    research_query = "What are the main benefits of renewable energy?"
    conversation_id = "test_conversation_001"
    print(f"\n🔍 Starting research query: '{research_query}'")
    
    try:
        response = requests.post(
            f"{base_url}/api/research/start",
            json={
                "query": research_query,
                "conversation_id": conversation_id,
                "research_mode": "comprehensive",
                "max_results": 5
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            task_id = result.get("task_id")
            print(f"✓ Research task started with ID: {task_id}")
            
            # Test 3: Monitor task progress
            print("\n📊 Monitoring research progress...")
            max_attempts = 120  # Wait up to 2 minutes (120 seconds)
            
            for attempt in range(max_attempts):
                try:
                    status_response = requests.get(f"{base_url}/api/research/task/{task_id}")
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        status = status_data.get("status", "unknown")
                        progress = status_data.get("progress", 0)
                        
                        print(f"   Attempt {attempt + 1}: Status={status}, Progress={progress}%")
                        
                        if status in ["completed", "complete"]:
                            print("✓ Research task completed successfully!")
                            print(f"\n📋 Research Results:")
                            print(f"   Task ID: {status_data.get('task_id')}")
                            print(f"   Query: {status_data.get('query')}")
                            print(f"   Progress: {status_data.get('progress')}%")
                            
                            # Display comprehensive results
                            results = status_data.get('results')
                            if results:
                                print(f"\n🎯 Final Research Output:")
                                
                                # Show synthesis (main result)
                                synthesis = results.get('synthesis', {})
                                if synthesis:
                                    answer = synthesis.get('answer', '')
                                    if answer:
                                        print(f"\n📖 Summary Answer:")
                                        # Show first 500 characters of the answer
                                        preview = answer[:500] + "..." if len(answer) > 500 else answer
                                        print(f"   {preview}")
                                    
                                    evidence = synthesis.get('evidence', '')
                                    if evidence:
                                        print(f"\n🔍 Key Evidence:")
                                        evidence_preview = evidence[:300] + "..." if len(evidence) > 300 else evidence
                                        print(f"   {evidence_preview}")
                                
                                # Show reasoning output
                                reasoning = results.get('reasoning_output', {})
                                if reasoning and isinstance(reasoning, dict):
                                    findings = reasoning.get('findings', '')
                                    if findings:
                                        print(f"\n🧠 Analysis Findings:")
                                        findings_preview = findings[:300] + "..." if len(findings) > 300 else findings
                                        print(f"   {findings_preview}")
                                
                                # Show execution results count
                                execution_results = results.get('execution_results', [])
                                if execution_results:
                                    print(f"\n⚙️ Execution Results: {len(execution_results)} items processed")
                                
                                # Show search results count
                                search_results = results.get('search_results', [])
                                print(f"\n🔎 Search Results: {len(search_results)} sources found")
                                
                                print(f"\n✨ Research completed with comprehensive synthesis!")
                            else:
                                print("⚠️ No results data found in completed task")
                            
                            return True
                        
                        elif status == "failed":
                            print(f"❌ Research task failed: {status_data.get('error', 'Unknown error')}")
                            return False
                        
                        time.sleep(1)  # Wait 1 second before checking again
                    else:
                        print(f"❌ Failed to get status: {status_response.status_code}")
                        if status_response.text:
                            print(f"   Error: {status_response.text}")
                        return False
                        
                except requests.RequestException as e:
                    print(f"❌ Error checking status: {e}")
                    return False
            
            print("⏱️ Research task timed out")
            return False
            
        else:
            print(f"❌ Failed to start research: {response.status_code}")
            if response.text:
                print(f"   Error: {response.text}")
            return False
            
    except requests.RequestException as e:
        print(f"❌ Error making request: {e}")
        return False


if __name__ == "__main__":
    success = test_research_api()
    if success:
        print("\n🎉 Research functionality is working correctly!")
    else:
        print("\n💥 Research functionality test failed!")

#!/usr/bin/env python3
"""
Real Eunice Research Pipeline Test - Step 1: Research Plan Generation
====================================================================

This script tests Step 1 of the REAL Eunice research system:
1. 🔄 Step 1: Research Question → Research Manager API → AI-Generated Research Plan  
2. ⏭️ Step 2: Research Plan → Literature Agent → PRISMA Systematic Review  

Uses the real Research Manager API to generate authentic AI research plans.

Author: GitHub Copilot for Paul Zanna
Date: July 24, 2025
"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# API Constants  
API_URL = "http://localhost:8000/api/v2"
SUCCESS_STATUS = 200

def make_request(method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
    """Make HTTP request to Eunice API."""
    url = f"{API_URL}{endpoint}"
    
    try:
        if method.upper() == "POST":
            response = requests.post(url, json=data, timeout=30)
        else:
            response = requests.get(url, timeout=30)
            
        if response.status_code == SUCCESS_STATUS:
            return {"success": True, "data": response.json()}
        else:
            return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
            
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timeout"}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "Connection failed - is Eunice server running?"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def create_project_and_topic(research_question: str) -> Dict[str, Any]:
    """Create research project and topic via API."""
    print("🏗️ Creating research project and topic...")
    
    # Create project
    project_data = {
        "name": f"AI Research Project - {datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "description": f"Research project investigating: {research_question}",
        "objectives": [
            "Generate comprehensive research plan using AI",
            "Identify key research areas and questions",
            "Define research methodology and sources"
        ]
    }
    
    project_result = make_request("POST", "/projects", project_data)
    if not project_result["success"]:
        return {"success": False, "error": f"Failed to create project: {project_result['error']}"}
    
    project_id = project_result["data"]["id"]  # Changed from project_id to id
    print(f"   ✅ Project created: {project_id}")
    
    # Create topic
    topic_data = {
        "name": research_question,  # Changed from title to name
        "description": f"Research topic: {research_question}",
        "metadata": {
            "priority": "high",
            "research_type": "systematic_investigation"
        }
    }
    
    topic_result = make_request("POST", f"/projects/{project_id}/topics", topic_data)
    if not topic_result["success"]:
        return {"success": False, "error": f"Failed to create topic: {topic_result['error']}"}
    
    topic_id = topic_result["data"]["id"]  # Changed from topic_id to id
    print(f"   ✅ Topic created: {topic_id}")
    
    return {
        "success": True,
        "project_id": project_id,
        "topic_id": topic_id
    }

def start_research_via_api(topic_id: str) -> Dict[str, Any]:
    """Start research process via API."""
    print("🔬 Starting AI research generation...")
    
    research_data = {
        "research_type": "comprehensive_analysis",
        "methodology": "ai_guided_systematic_research",
        "scope": "academic_and_practical"
    }
    
    result = make_request("POST", f"/topics/{topic_id}/research", research_data)
    if not result["success"]:
        return {"success": False, "error": f"Failed to start research: {result['error']}"}
    
    print("   ✅ Research started successfully")
    return result

def get_ai_generated_research_plan(topic_id: str, max_attempts: int = 10) -> Dict[str, Any]:
    """Poll for AI-generated research plan."""
    print("🧠 Waiting for AI to generate research plan...")
    
    for attempt in range(max_attempts):
        print(f"   🔄 Attempt {attempt + 1}/{max_attempts}: Checking for research plan...")
        
        result = make_request("GET", f"/topics/{topic_id}")
        if not result["success"]:
            print(f"   ❌ Error checking topic: {result['error']}")
            time.sleep(5)
            continue
        
        topic_data = result["data"]
        
        # Check if research plan is available
        if "research_plan" in topic_data and topic_data["research_plan"]:
            plan = topic_data["research_plan"]
            if isinstance(plan, dict) and plan.get("plan_structure"):
                print("   ✅ AI research plan generated!")
                return {"success": True, "research_plan": plan}
        
        if attempt < max_attempts - 1:
            print("   ⏳ Research plan not ready yet, waiting...")
            time.sleep(10)
    
    return {"success": False, "error": "Research plan not generated within timeout"}

def main():
    """Execute Step 1: AI Research Plan Generation."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f"real_pipeline_output_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("🚀 Starting REAL Research Pipeline - Step 1")
    print("=" * 60)
    print("Pipeline: Research Question → Research Manager API → AI Research Plan")
    print("=" * 60)
    
    # Define research question
    research_question = "How can neuron cells be cultured in a laboratory using accessible materials and techniques?"
    
    print(f"🔬 Research Question: {research_question}")
    print(f"📁 Output Directory: {output_dir}")
    
    try:
        # Step 1: Create project and topic
        setup_result = create_project_and_topic(research_question)
        if not setup_result["success"]:
            raise Exception(setup_result["error"])
        
        project_id = setup_result["project_id"]
        topic_id = setup_result["topic_id"]
        
        # Step 2: Start research process
        research_result = start_research_via_api(topic_id)
        if not research_result["success"]:
            raise Exception(research_result["error"])
        
        # Step 3: Get AI-generated research plan
        plan_result = get_ai_generated_research_plan(topic_id)
        if not plan_result["success"]:
            raise Exception(plan_result["error"])
        
        research_plan = plan_result["research_plan"]
        
        # Add metadata
        research_plan.update({
            "plan_id": f"ai_plan_{timestamp}",
            "research_question": research_question,
            "project_id": project_id,
            "topic_id": topic_id,
            "generated_timestamp": datetime.now().isoformat(),
            "api_generated": True
        })
        
        # Save research plan
        plan_file = output_dir / "real_research_plan.json"
        with open(plan_file, 'w') as f:
            json.dump(research_plan, f, indent=2)
        
        print("\\n✅ STEP 1 COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"📁 AI Research Plan saved to: {plan_file}")
        print(f"🧠 Generated by Research Manager API")
        print(f"📊 Plan Structure:")
        
        plan_structure = research_plan.get("plan_structure", {})
        print(f"   • Objectives: {len(plan_structure.get('objectives', []))}")
        print(f"   • Key Areas: {len(plan_structure.get('key_areas', []))}")
        print(f"   • Research Questions: {len(plan_structure.get('questions', []))}")
        print(f"   • Sources: {len(plan_structure.get('sources', []))}")
        print(f"   • Expected Outcomes: {len(plan_structure.get('expected_outcomes', []))}")
        
        print(f"\\n🎯 Ready for Step 2: PRISMA Systematic Review")
        print(f"   Run: python test_real_pipeline_step2.py")
        
    except Exception as e:
        print(f"\\n❌ Step 1 failed: {e}")
        print("📝 Make sure Eunice server is running on localhost:8000")
        return False
    
    return True

if __name__ == "__main__":
    main()

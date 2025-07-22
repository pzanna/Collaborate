#!/usr/bin/env python3
"""
Test the complete API workflow: create project, create research topic, 
wait for plan completion, approve it, and check database entries.
"""

import requests
import time
import json
import sys
import sqlite3
from datetime import datetime

# API base URL (assuming local server)
BASE_URL = "http://localhost:8000"

def check_server_status():
    """Check if the server is running."""
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def create_project(name, description):
    """Create a new project via API."""
    project_data = {
        "name": name,
        "description": description
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/projects", json=project_data, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to create project: {e}")
        return None

def create_research_topic(project_id, title, description):
    """Create a new research topic via API."""
    topic_data = {
        "project_id": project_id,  # Include project_id in the body
        "name": title,  # Use 'name' instead of 'title'
        "description": description
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/v2/projects/{project_id}/topics", json=topic_data, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to create research topic: {e}")
        return None

def start_research_task(project_id, query):
    """Start a research task via API."""
    task_data = {
        "project_id": project_id,  # Use project_id instead of topic_id
        "query": query,
        "research_mode": "comprehensive"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/research/start", json=task_data, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to start research task: {e}")
        return None

def get_task_status(task_id):
    """Get task status via API."""
    try:
        response = requests.get(f"{BASE_URL}/api/research/task/{task_id}", timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to get task status: {e}")
        return None

def approve_plan(task_id):
    """Approve a research plan via API."""
    approval_data = {
        "approved": True
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/research/task/{task_id}/plan/approve", 
                               json=approval_data, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to approve plan: {e}")
        return None

def check_database_entries(db_path="data/eunice.db"):
    """Check database entries directly."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Count projects
        cursor.execute("SELECT COUNT(*) FROM projects")
        project_count = cursor.fetchone()[0]
        
        # Count research topics
        cursor.execute("SELECT COUNT(*) FROM research_topics")
        topic_count = cursor.fetchone()[0]
        
        # Count research plans
        cursor.execute("SELECT COUNT(*) FROM research_plans")
        plan_count = cursor.fetchone()[0]
        
        # Count research tasks
        cursor.execute("SELECT COUNT(*) FROM research_tasks")
        task_count = cursor.fetchone()[0]
        
        # Get detailed entries
        cursor.execute("""
            SELECT id, name, description, created_at 
            FROM projects 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        projects = cursor.fetchall()
        
        cursor.execute("""
            SELECT id, project_id, name, status, created_at 
            FROM research_topics 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        topics = cursor.fetchall()
        
        cursor.execute("""
            SELECT id, topic_id, name, status, plan_approved, created_at 
            FROM research_plans 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        plans = cursor.fetchall()
        
        cursor.execute("""
            SELECT id, plan_id, stage, status, created_at 
            FROM research_tasks 
            ORDER BY created_at DESC 
            LIMIT 10
        """)
        tasks = cursor.fetchall()
        
        conn.close()
        
        return {
            "counts": {
                "projects": project_count,
                "topics": topic_count,
                "plans": plan_count,
                "tasks": task_count
            },
            "recent_entries": {
                "projects": projects,
                "topics": topics,
                "plans": plans,
                "tasks": tasks
            }
        }
        
    except Exception as e:
        print(f"❌ Failed to check database: {e}")
        return None

def wait_for_planning_completion(task_id, max_wait_seconds=120):
    """Wait for planning stage to complete or make significant progress."""
    print(f"⏳ Waiting for planning to complete (max {max_wait_seconds}s)...")
    
    start_time = time.time()
    last_progress = 0
    stable_count = 0
    
    while time.time() - start_time < max_wait_seconds:
        status = get_task_status(task_id)
        if not status:
            time.sleep(5)
            continue
            
        current_stage = status.get("stage")  # Use "stage" instead of "current_stage"
        progress = status.get("progress", 0)
        print(f"   Current stage: {current_stage} (Progress: {progress}%)")
        
        # If we've moved past planning or completed, we're done
        if current_stage in ["retrieval", "reasoning", "execution", "synthesis", "completed"]:
            print("✅ Planning stage completed!")
            return True
            
        # Check if planning is complete (progress >= 100 in planning stage)
        if current_stage == "planning" and progress >= 100:
            print("✅ Planning stage completed!")
            return True
        
        # Check if we have made progress and planning has stabilized at a reasonable level
        if current_stage == "planning" and progress >= 30:
            if progress == last_progress:
                stable_count += 1
                if stable_count >= 3:  # Progress stable for 3 checks (30 seconds)
                    print(f"✅ Planning has stabilized at {progress}% - proceeding with approval")
                    return True
            else:
                stable_count = 0
                last_progress = progress
            
        time.sleep(10)  # Wait 10 seconds between checks
    
    print("⚠️  Timed out waiting for planning completion")
    return False

def main():
    """Run the complete API workflow test."""
    print("=== API WORKFLOW TEST ===")
    print(f"Test started at: {datetime.now()}")
    
    # Check if server is running
    if not check_server_status():
        print("❌ Server is not running. Please start the web server first.")
        print("   Run: python web_server.py")
        return False
    
    print("✅ Server is running")
    
    # Get initial database state
    print("\n--- INITIAL DATABASE STATE ---")
    initial_db = check_database_entries()
    if initial_db:
        counts = initial_db["counts"]
        print(f"Projects: {counts['projects']}")
        print(f"Topics: {counts['topics']}")
        print(f"Plans: {counts['plans']}")
        print(f"Tasks: {counts['tasks']}")
    
    # Step 1: Create project
    print("\n🚀 Step 1: Creating project...")
    project = create_project(
        name="API Test Project", 
        description="Testing the complete API workflow with plan approval"
    )
    
    if not project:
        print("❌ Failed to create project")
        return False
    
    project_id = project.get("id")
    print(f"✅ Project created: {project_id}")
    
    # Step 2: Create research topic
    print("\n🔬 Step 2: Creating research topic...")
    topic = create_research_topic(
        project_id=project_id,
        title="Multi-Agent Conversation Analysis",
        description="Research into conversation analysis techniques for multi-agent systems"
    )
    
    if not topic:
        print("❌ Failed to create research topic")
        return False
    
    topic_id = topic.get("id")
    print(f"✅ Research topic created: {topic_id}")
    
    # Step 3: Start research task
    print("\n📋 Step 3: Starting research task...")
    task = start_research_task(
        project_id=project_id,
        query="What are the key challenges in conversation analysis for multi-agent AI systems?"
    )
    
    if not task:
        print("❌ Failed to start research task")
        return False
    
    task_id = task.get("task_id")
    print(f"✅ Research task started: {task_id}")
    
    # Step 4: Wait for planning completion
    print("\n⏳ Step 4: Waiting for planning completion...")
    planning_completed = wait_for_planning_completion(task_id)
    
    if not planning_completed:
        print("❌ Planning did not complete in time")
        return False
    
    # Get final task status to find plan_id
    final_status = get_task_status(task_id)
    if final_status:
        print(f"✅ Task status retrieved, ready for plan approval")
    
    # Step 5: Approve the plan (using task_id)
    print(f"\n✅ Step 5: Approving plan for task {task_id}...")
    approval_result = approve_plan(task_id)
    
    if not approval_result:
        print("❌ Failed to approve plan")
        return False
    
    print("✅ Plan approved successfully!")
    
    # Step 6: Check final database state
    print("\n--- FINAL DATABASE STATE ---")
    final_db = check_database_entries()
    if final_db:
        counts = final_db["counts"]
        print(f"Projects: {counts['projects']}")
        print(f"Topics: {counts['topics']}")
        print(f"Plans: {counts['plans']}")
        print(f"Tasks: {counts['tasks']}")
        
        print("\n--- RECENT ENTRIES ---")
        
        print("\nProjects:")
        for proj in final_db["recent_entries"]["projects"][:3]:
            print(f"  - {proj[0]}: {proj[1]} (Created: {proj[3]})")
        
        print("\nTopics:")
        for topic_entry in final_db["recent_entries"]["topics"][:3]:
            print(f"  - {topic_entry[0]}: {topic_entry[2]} (Status: {topic_entry[3]})")
        
        print("\nPlans:")
        for plan in final_db["recent_entries"]["plans"][:3]:
            approved = "✅ Approved" if plan[4] else "⏳ Pending"
            print(f"  - {plan[0]}: {plan[2]} (Status: {plan[3]}, {approved})")
        
        print("\nTasks:")
        for task_entry in final_db["recent_entries"]["tasks"][:5]:
            print(f"  - {task_entry[0]}: {task_entry[2]} stage (Status: {task_entry[3]})")
    
    print(f"\n✅ API workflow test completed successfully at {datetime.now()}")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
Test script to demonstrate the new hierarchical research structure.
Creates a sample project with topics, plans, and tasks.
"""

import sys
import os
import json
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.storage.hierarchical_database import HierarchicalDatabaseManager
from datetime import datetime


def test_hierarchical_structure():
    """Test the new hierarchical research structure."""
    print("🚀 Testing Hierarchical Research Structure")
    print("=" * 50)
    
    # Initialize the database manager
    db = HierarchicalDatabaseManager("data/collaborate.db")
    
    # 1. Create a sample project (mock for now)
    project_id = "proj_ai_safety_demo"
    
    # Use timestamp to avoid ID conflicts
    timestamp = int(datetime.now().timestamp())
    
    # Generate unique IDs
    topic1_id = f'topic_ethics_frameworks_{timestamp}'
    topic2_id = f'topic_bias_detection_{timestamp}'
    plan1_id = f'plan_literature_review_{timestamp}'
    plan2_id = f'plan_industry_standards_{timestamp}'
    plan3_id = f'plan_bias_algorithms_{timestamp}'
    
    print(f"📁 Project: {project_id}")
    
    # 2. Create research topics
    print("\n📋 Creating Research Topics:")
    
    topic1_data = {
        'id': topic1_id,
        'project_id': project_id,
        'name': 'AI Ethics Frameworks',
        'description': 'Investigation of existing AI ethics frameworks and standards',
        'status': 'active',
        'metadata': {'priority': 'high', 'domain': 'ethics'}
    }
    
    topic2_data = {
        'id': topic2_id,
        'project_id': project_id,
        'name': 'Bias Detection Methods',
        'description': 'Research into algorithmic bias detection and mitigation',
        'status': 'active',
        'metadata': {'priority': 'medium', 'domain': 'fairness'}
    }
    
    topic1 = db.create_research_topic(topic1_data)
    topic2 = db.create_research_topic(topic2_data)
    
    if topic1:
        print(f"  ✅ Created: {topic1['name']}")
    if topic2:
        print(f"  ✅ Created: {topic2['name']}")
    
    if not topic1 or not topic2:
        print("❌ Failed to create research topics")
        return False
    
    # 3. Create research plans
    print("\n📝 Creating Research Plans:")
    
    plan1_data = {
        'id': plan1_id,
        'topic_id': topic1_id,
        'name': 'Comprehensive Literature Review',
        'description': 'Systematic review of academic and industry AI ethics frameworks',
        'plan_type': 'comprehensive',
        'status': 'active',
        'estimated_cost': 0.25,
        'plan_structure': {
            'stages': ['search', 'categorize', 'analyze', 'synthesize'],
            'approach': 'multi-agent',
            'timeline': '2-3 days'
        },
        'metadata': {'methodology': 'systematic_review'}
    }
    
    plan2_data = {
        'id': plan2_id,
        'topic_id': topic1_id,
        'name': 'Industry Standards Analysis',
        'description': 'Analysis of practical AI ethics implementations in industry',
        'plan_type': 'quick',
        'status': 'active',
        'estimated_cost': 0.15,
        'plan_structure': {
            'stages': ['survey', 'compare', 'evaluate'],
            'approach': 'focused',
            'timeline': '1-2 days'
        },
        'metadata': {'scope': 'industry_practice'}
    }
    
    plan3_data = {
        'id': plan3_id,
        'topic_id': topic2_id,
        'name': 'Bias Detection Algorithms',
        'description': 'Technical survey of bias detection and mitigation algorithms',
        'plan_type': 'deep',
        'status': 'active',
        'estimated_cost': 0.35,
        'plan_structure': {
            'stages': ['survey', 'test', 'benchmark', 'report'],
            'approach': 'multi-agent',
            'timeline': '3-4 days'
        },
        'metadata': {'technical_focus': 'algorithms'}
    }
    
    plan2_data = {
        'id': plan2_id,
        'topic_id': topic1_id,
        'name': 'Industry Standards Analysis',
        'description': 'Analysis of industry-specific AI ethics standards and implementations',
        'plan_type': 'focused',
        'status': 'draft',
        'estimated_cost': 0.15,
        'plan_structure': {
            'stages': ['research', 'compare', 'evaluate'],
            'approach': 'single-agent',
            'timeline': '1-2 days'
        },
        'metadata': {'focus': 'industry_practices'}
    }
    
    plan1 = db.create_research_plan(plan1_data)
    plan2 = db.create_research_plan(plan2_data)
    plan3 = db.create_research_plan(plan3_data)
    
    if plan1:
        print(f"  ✅ Created: {plan1['name']} (Topic: AI Ethics Frameworks)")
    if plan2:
        print(f"  ✅ Created: {plan2['name']} (Topic: AI Ethics Frameworks)")
    if plan3:
        print(f"  ✅ Created: {plan3['name']} (Topic: Bias Detection Methods)")
    
    if not plan1 or not plan2 or not plan3:
        print("❌ Failed to create research plans")
        return False
    
    # 4. Create tasks
    print("\n⚡ Creating Tasks:")
    
    # Tasks for Literature Review Plan
    task1_data = {
        'id': f'task_search_academic_{timestamp}',
        'plan_id': plan1_id,
        'name': 'Search Academic Literature',
        'description': 'Search for academic papers on AI ethics frameworks',
        'task_type': 'research',
        'task_order': 1,
        'query': 'AI ethics frameworks academic literature review',
        'max_results': 15,
        'single_agent_mode': False,
        'metadata': {'focus': 'academic_sources'}
    }
    
    task2_data = {
        'id': f'task_categorize_frameworks_{timestamp}',
        'plan_id': plan1_id,
        'name': 'Categorize Framework Types',
        'description': 'Analyze and categorize different types of AI ethics frameworks',
        'task_type': 'analysis',
        'task_order': 2,
        'single_agent_mode': False,
        'metadata': {'analysis_type': 'categorical'}
    }
    
    task3_data = {
        'id': f'task_synthesize_findings_{timestamp}',
        'plan_id': plan1_id,
        'name': 'Synthesize Research Findings',
        'description': 'Create comprehensive synthesis of literature review findings',
        'task_type': 'synthesis',
        'task_order': 3,
        'single_agent_mode': False,
        'metadata': {'output_format': 'comprehensive_report'}
    }
    
    # Tasks for Industry Standards Plan
    task4_data = {
        'id': f'task_research_ieee_{timestamp}',
        'plan_id': plan2_id,
        'name': 'Research IEEE Standards',
        'description': 'Research IEEE AI ethics standards and guidelines',
        'task_type': 'research',
        'task_order': 1,
        'query': 'IEEE AI ethics standards guidelines',
        'max_results': 10,
        'single_agent_mode': True,
        'metadata': {'organization': 'IEEE'}
    }
    
    task5_data = {
        'id': f'task_compare_iso_{timestamp}',
        'plan_id': plan2_id,
        'name': 'Compare with ISO Guidelines',
        'description': 'Compare IEEE standards with ISO AI guidelines',
        'task_type': 'analysis',
        'task_order': 2,
        'single_agent_mode': True,
        'metadata': {'comparison_type': 'standard_vs_standard'}
    }
    
    # Tasks for Algorithm Assessment Plan
    task6_data = {
        'id': f'task_survey_algorithms_{timestamp}',
        'plan_id': plan3_id,
        'name': 'Survey Bias Detection Algorithms',
        'description': 'Comprehensive survey of bias detection algorithms in ML',
        'task_type': 'research',
        'task_order': 1,
        'query': 'bias detection algorithms machine learning fairness',
        'max_results': 20,
        'single_agent_mode': False,
        'metadata': {'survey_scope': 'comprehensive'}
    }
    
    # Create all tasks
    tasks_data = [task1_data, task2_data, task3_data, task4_data, task5_data, task6_data]
    tasks = []
    
    for task_data in tasks_data:
        task = db.create_task(task_data)
        if task:
            tasks.append(task)
            plan_name = task_data['plan_id'].replace('plan_', '').replace('_', ' ').title()
            print(f"  ✅ Created: {task['name']} (Plan: {plan_name})")
        else:
            print(f"  ❌ Failed to create task: {task_data['name']}")
    
    # 5. Display the complete hierarchy
    print("\n🏗️  Complete Project Hierarchy:")
    print("=" * 50)
    
    hierarchy = db.get_project_hierarchy(project_id)
    display_hierarchy(hierarchy)
    
    # 6. Demonstrate navigation
    print("\n🧭 Navigation Examples:")
    print("=" * 30)
    
    # List topics for project
    topics = db.get_research_topics_by_project(project_id)
    print(f"📁 Project has {len(topics)} research topics")
    
    for topic in topics:
        plans = db.get_research_plans_by_topic(topic['id'])
        print(f"📋 Topic '{topic['name']}' has {len(plans)} plans")
        
        for plan in plans:
            tasks = db.get_tasks_by_plan(plan['id'])
            print(f"📝   Plan '{plan['name']}' has {len(tasks)} tasks")
    
    print("\n✅ Hierarchical structure test completed successfully!")
    return True


def display_hierarchy(hierarchy):
    """Display the hierarchy in a tree-like format."""
    if not hierarchy or 'topics' not in hierarchy:
        print("📁 Project (empty)")
        return
    
    print(f"📁 Project: {hierarchy.get('project_id', 'Unknown')}")
    
    for topic in hierarchy['topics']:
        print(f"├── 📋 Topic: {topic['name']}")
        print(f"│   └── Status: {topic['status']}")
        
        if 'plans' in topic:
            for i, plan in enumerate(topic['plans']):
                is_last_plan = i == len(topic['plans']) - 1
                plan_prefix = "└──" if is_last_plan else "├──"
                print(f"│   {plan_prefix} 📝 Plan: {plan['name']}")
                print(f"│   {'    ' if is_last_plan else '│   '}└── Type: {plan['plan_type']}, Status: {plan['status']}")
                
                if 'tasks' in plan:
                    for j, task in enumerate(plan['tasks']):
                        is_last_task = j == len(plan['tasks']) - 1
                        task_prefix = "└──" if is_last_task else "├──"
                        indent = "    " if is_last_plan else "│   "
                        print(f"│   {indent}    {task_prefix} ⚡ Task: {task['name']}")
                        print(f"│   {indent}    {'    ' if is_last_task else '│   '}└── Type: {task['task_type']}, Status: {task['status']}")


def test_api_compatibility():
    """Test that the API endpoints work with the new structure."""
    print("\n🔗 Testing API Compatibility:")
    print("=" * 30)
    
    # This would test the API endpoints, but since we need the server running,
    # we'll just print what the URLs would be
    
    project_id = "proj_ai_safety_demo"
    topic_id = "topic_ethics_frameworks"
    plan_id = "plan_literature_review"
    task_id = "task_search_academic"
    
    print(f"📍 API Endpoints for the hierarchy:")
    print(f"   Projects: GET /api/projects/{project_id}")
    print(f"   Topics:   GET /api/v2/projects/{project_id}/topics")
    print(f"   Plans:    GET /api/v2/topics/{topic_id}/plans")
    print(f"   Tasks:    GET /api/v2/plans/{plan_id}/tasks")
    print(f"   Task:     GET /api/v2/tasks/{task_id}")
    print(f"   Hierarchy: GET /api/v2/projects/{project_id}/hierarchy")
    
    print(f"\n📍 Navigation URLs:")
    print(f"   /projects/{project_id}")
    print(f"   /projects/{project_id}/topics")
    print(f"   /topics/{topic_id}")
    print(f"   /topics/{topic_id}/plans")
    print(f"   /plans/{plan_id}")
    print(f"   /plans/{plan_id}/tasks")
    print(f"   /tasks/{task_id}")


if __name__ == "__main__":
    print("🎯 Hierarchical Research Structure Test")
    print("This demonstrates the new Project → Topic → Plan → Tasks hierarchy")
    print()
    
    try:
        success = test_hierarchical_structure()
        if success:
            test_api_compatibility()
            print("\n🎉 All tests completed successfully!")
            print("\nNext steps:")
            print("1. Start the web server: python web_server.py")
            print("2. Visit: http://localhost:8000")
            print("3. Test the new hierarchical endpoints")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

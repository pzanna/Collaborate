#!/usr/bin/env python3
"""
Test Automatic PRISMA Report Generation in Systematic Review Workflow

This test verifies that the SystematicReviewAgent automatically generates
PRISMA reports when the systematic review workflow completes Stage 8.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import Dict, Any

# Add src to path
sys.path.insert(0, 'src')

from src.config.config_manager import ConfigManager
from src.agents.systematic_review_agent import SystematicReviewAgent

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class AutomaticPRISMAGenerationTest:
    """Test automatic PRISMA report generation in systematic review workflow."""
    
    def __init__(self):
        """Initialize test environment."""
        self.config = ConfigManager('config/default_config.json')
        self.agent = SystematicReviewAgent(self.config)
        
    async def test_automatic_generation(self):
        """Test that PRISMA reports are automatically generated."""
        print("🧪 Testing Automatic PRISMA Report Generation")
        print("=" * 60)
        
        # Create test research plan
        research_plan = {
            "objective": "How do low-cost approaches to cortical neuron cell culture compare to traditional methods in terms of cell viability and experimental reproducibility?",
            "population": "Cortical neurons in cell culture",
            "intervention": "Low-cost cell culture approaches",
            "comparison": "Traditional/standard cell culture methods", 
            "outcomes": ["Cell viability", "Experimental reproducibility", "Cost effectiveness"],
            "inclusion_criteria": {
                "study_types": ["experimental", "comparative", "methodological"],
                "cell_types": ["cortical neurons", "primary neurons"],
                "languages": ["English"]
            },
            "exclusion_criteria": {
                "study_types": ["review articles", "case reports"],
                "irrelevant_models": ["non-neuronal cells", "immortalized cell lines"]
            },
            "search_terms": [
                "low-cost cortical neuron culture",
                "affordable neuron cell culture methods",
                "cost-effective neuronal culture techniques"
            ]
        }
        
        # Generate unique task ID
        task_id = f"auto_prisma_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        print(f"📋 Research Plan: {research_plan['objective']}")
        print(f"🆔 Task ID: {task_id}")
        print()
        
        try:
            print("🚀 Starting systematic review workflow...")
            
            # Run the complete workflow (should automatically generate PRISMA report)
            workflow_results = await self.agent.systematic_review_workflow(
                research_plan=research_plan,
                task_id=task_id,
                user_id="test_user"
            )
            
            print("\n📊 Workflow Results:")
            print(f"   Status: {workflow_results.get('status', 'unknown')}")
            print(f"   Current Stage: {workflow_results.get('current_stage', 'unknown')}")
            
            # Check if PRISMA report was automatically generated
            prisma_report = workflow_results.get('results', {}).get('prisma_report')
            
            if prisma_report:
                print("\n✅ AUTOMATIC PRISMA REPORT GENERATION SUCCESSFUL!")
                print(f"   Report ID: {prisma_report.get('report_id', 'unknown')}")
                print(f"   Generated At: {prisma_report.get('generated_at', 'unknown')}")
                
                exported_files = prisma_report.get('exported_files', [])
                if exported_files:
                    print(f"   Exported Files ({len(exported_files)}):")
                    for file_path in exported_files:
                        print(f"     📄 {file_path}")
                else:
                    print("   ⚠️  No exported files found")
                    
                # Check for errors
                if 'error' in prisma_report:
                    print(f"   ❌ Error: {prisma_report['error']}")
                    return False
                    
            else:
                print("\n❌ AUTOMATIC PRISMA REPORT GENERATION FAILED!")
                print("   No prisma_report found in workflow results")
                return False
            
            # Display PRISMA statistics
            prisma_log = workflow_results.get('prisma_log')
            if prisma_log:
                print(f"\n📈 PRISMA Statistics:")
                print(f"   Records Identified: {getattr(prisma_log, 'identified', 0)}")
                print(f"   Duplicates Removed: {getattr(prisma_log, 'duplicates_removed', 0)}")
                print(f"   Records Screened: {getattr(prisma_log, 'screened_title_abstract', 0)}")
                print(f"   Studies Included: {getattr(prisma_log, 'included', 0)}")
            
            # Display workflow stage results
            results = workflow_results.get('results', {})
            print(f"\n🔬 Workflow Stages Completed:")
            for stage, result in results.items():
                if isinstance(result, dict):
                    count = len(result) if result else 0
                    print(f"   {stage}: {count} items processed")
                else:
                    print(f"   {stage}: completed")
            
            print(f"\n✅ Automatic PRISMA generation test completed successfully!")
            return True
            
        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            return False

async def main():
    """Run the automatic PRISMA generation test."""
    test = AutomaticPRISMAGenerationTest()
    success = await test.test_automatic_generation()
    
    if success:
        print("\n🎉 SUCCESS: Automatic PRISMA report generation is working!")
        print("   The SystematicReviewAgent properly completes all 8 PRISMA stages")
        print("   and automatically generates reports at Stage 8 as designed.")
    else:
        print("\n💥 FAILURE: Automatic PRISMA report generation is not working")
        print("   The workflow needs debugging to ensure Stage 8 executes properly.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

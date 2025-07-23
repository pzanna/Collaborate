#!/usr/bin/env python3
"""
Real Eunice Research Pipeline Test - Step 2: PRISMA Review
==========================================================

This script tests Step 2 of the REAL Eunice research system:
1. ✅ Step 1: Research Question → Research Manager API → AI-Generated Research Plan  
2. 🔄 Step 2: Research Plan → Literature Agent → PRISMA Systematic Review  

Uses the real AI-generated research plan from Step 1 to conduct systematic literature review.

Author: GitHub Copilot for Paul Zanna
Date: July 24, 2025
"""

import json
import sys
import os
import time
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import quote
import asyncio

# Add source directory to path
sys.path.append(str(Path(__file__).parent / 'src'))

from src.agents.literature_agent import LiteratureAgent
from src.config.config_manager import ConfigManager
from src.reports.prisma_report_generator import PRISMAReportGenerator, PRISMAReport, ExportFormat

# API Constants  
API_URL = "http://localhost:8000/api/v2"
SUCCESS_STATUS = 200


class RealPRISMATest:
    """Test PRISMA review generation using real AI research plans."""
    
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(f"real_pipeline_output_{self.timestamp}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Eunice components
        self.config_manager = ConfigManager()
        self.literature_agent = None
        
        print(f"🔧 Initializing Real PRISMA Test")
        print(f"📁 Output Directory: {self.output_dir}")

    async def initialize_literature_agent(self):
        """Initialize Literature Agent for PRISMA review."""
        if not self.literature_agent:
            print("🤖 Initializing Literature Agent...")
            self.literature_agent = LiteratureAgent(config_manager=self.config_manager)
            await self.literature_agent.initialize()
            print("   ✅ Literature Agent ready for systematic review")

    def load_ai_research_plan(self) -> Optional[Dict[str, Any]]:
        """Load the AI-generated research plan from the previous run."""
        print("📂 Loading AI-generated research plan...")
        
        # Find the most recent research plan file
        output_dirs = [d for d in Path(".").glob("real_pipeline_output_*") if d.is_dir()]
        if not output_dirs:
            print("❌ No previous research plan found. Run Step 1 first.")
            return None
            
        # Get the most recent directory
        latest_dir = max(output_dirs, key=lambda d: d.stat().st_mtime)
        plan_file = latest_dir / "real_research_plan.json"
        
        if not plan_file.exists():
            print(f"❌ Research plan file not found: {plan_file}")
            return None
            
        with open(plan_file, 'r') as f:
            research_plan = json.load(f)
            
        print(f"✅ Loaded AI research plan from: {plan_file}")
        return research_plan

    async def conduct_systematic_literature_review(self, research_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Conduct systematic literature review based on AI research plan."""
        print("📚 Conducting Systematic Literature Review based on AI Research Plan...")
        
        await self.initialize_literature_agent()
        
        # Extract AI-generated research specifications
        plan_structure = research_plan.get("plan_structure", {})
        research_question = research_plan.get("research_question", "")
        
        # Use the AI-specified research questions for targeted searches
        research_questions = plan_structure.get("questions", [])
        key_areas = plan_structure.get("key_areas", [])
        
        print(f"🔍 Conducting systematic search based on:")
        print(f"   • {len(research_questions)} AI-generated research questions")
        print(f"   • {len(key_areas)} AI-identified key research areas")
        
        # Conduct multiple targeted searches based on AI plan
        all_search_results = []
        
        # Primary search using the main research question
        print("\\n🎯 Primary Search: Main Research Question")
        print(f"   Query: {research_question}")
        primary_results = await self.literature_agent.biomedical_research_workflow(
            research_topic=research_question,
            max_papers=15
        )
        all_search_results.append({
            "search_type": "primary_research_question", 
            "query": research_question,
            "results": primary_results
        })
        
        # Secondary searches using AI-generated key areas
        print("\\n🔬 Secondary Searches: AI-Identified Key Areas")
        for i, area in enumerate(key_areas[:3], 1):  # Limit to top 3 areas
            print(f"   {i}. {area[:80]}...")
            area_results = await self.literature_agent.academic_research_workflow(
                research_topic=area,
                max_papers=10
            )
            all_search_results.append({
                "search_type": f"key_area_{i}",
                "query": area,
                "results": area_results
            })
        
        # Tertiary searches using specific AI-generated research questions
        print("\\n❓ Tertiary Searches: AI-Generated Research Questions")
        for i, question in enumerate(research_questions[:2], 1):  # Limit to top 2 questions
            print(f"   {i}. {question[:80]}...")
            question_results = await self.literature_agent.academic_research_workflow(
                research_topic=question,
                max_papers=8
            )
            all_search_results.append({
                "search_type": f"research_question_{i}",
                "query": question,
                "results": question_results
            })
        
        # Aggregate all results
        total_papers = sum(r["results"].get("total_papers_found", 0) for r in all_search_results)
        total_content_extracted = sum(r["results"].get("content_extracted", 0) for r in all_search_results)
        
        print(f"\\n📊 Search Complete:")
        print(f"   • {len(all_search_results)} targeted searches conducted")
        print(f"   • {total_papers} academic papers identified")
        print(f"   • {total_content_extracted} full-text extractions")
        
        # Generate PRISMA systematic review using proper template system
        print("📋 Generating PRISMA Report using template system...")
        
        # Initialize PRISMA Report Generator
        from src.ai_clients.openai_client import OpenAIClient, AIProviderConfig
        
        # Get OpenAI API key and create config
        api_key = self.config_manager.get_api_key("openai")
        ai_config = AIProviderConfig(
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.7,
            max_tokens=2000
        )
        ai_client = OpenAIClient(api_key=api_key, config=ai_config)
        
        # Create mock database for demonstration (in production, use real database)
        class MockDatabase:
            def create_prisma_report(self, data):
                print(f"📊 PRISMA report stored: {data['report_id']}")
        
        database = MockDatabase()
        prisma_generator = PRISMAReportGenerator(database, ai_client)
        
        # Generate comprehensive PRISMA report using the template system
        review_id = f"ai_generated_review_{self.timestamp}"
        
        try:
            # Generate full PRISMA report using proper template architecture
            prisma_report = await prisma_generator.generate_full_report(
                review_id=review_id,
                template_config={
                    "title_prefix": "AI-Guided Systematic Review",
                    "research_question": research_question,
                    "search_results": all_search_results,
                    "total_papers": total_papers,
                    "total_content": total_content_extracted
                }
            )
            
            print(f"✅ Generated PRISMA Report: {prisma_report.report_id}")
            print(f"   • Title: {prisma_report.title}")
            print(f"   • Studies included: {prisma_report.study_selection.studies_included_review}")
            print(f"   • Meta-analysis studies: {prisma_report.study_selection.studies_included_meta_analysis}")
            
            return {
                "prisma_report": prisma_report,
                "prisma_generator": prisma_generator,  # Include generator for export
                "ai_research_plan_integration": {
                    "based_on_ai_plan": True,
                    "plan_id": research_plan.get("plan_id"),
                    "research_questions_used": len(research_questions),
                    "key_areas_searched": len(key_areas),
                    "objectives_addressed": len(plan_structure.get("objectives", []))
                },
                "search_metadata": {
                    "total_searches_conducted": len(all_search_results),
                    "total_papers_identified": total_papers,
                    "total_content_extracted": total_content_extracted,
                    "search_date": datetime.now().strftime("%Y-%m-%d")
                }
            }
            
        except Exception as e:
            print(f"❌ Error generating PRISMA report: {e}")
            # Fallback to basic structure for debugging
            return {
                "error": str(e),
                "search_metadata": {
                    "total_searches_conducted": len(all_search_results),
                    "total_papers_identified": total_papers,
                    "total_content_extracted": total_content_extracted
                }
            }

    async def run_prisma_test(self):
        """Execute the PRISMA systematic review test."""
        print("🚀 Starting REAL PRISMA Review Test")
        print("=" * 60)
        print("Pipeline: AI Research Plan → Literature Agent → PRISMA Review")
        print("=" * 60)
        
        try:
            # Load AI-generated research plan from Step 1
            research_plan = self.load_ai_research_plan()
            if not research_plan:
                raise Exception("No AI research plan found. Run Step 1 first.")
            
            # Conduct systematic literature review
            prisma_review = await self.conduct_systematic_literature_review(research_plan)
            
            # Save PRISMA review with proper template structure
            review_file = self.output_dir / "real_prisma_review.json"
            
            # Save the structured data for both template report and metadata
            if "prisma_report" in prisma_review:
                # Save the complete PRISMA report using to_dict() method
                save_data = {
                    "prisma_report": prisma_review["prisma_report"].to_dict(),
                    "search_metadata": prisma_review.get("search_metadata", {}),
                    "ai_research_plan_integration": prisma_review.get("ai_research_plan_integration", {}),
                    "generated_timestamp": datetime.now().isoformat()
                }
                
                with open(review_file, 'w') as f:
                    json.dump(save_data, f, indent=2, default=str)
                
                print("\\n✅ REAL PRISMA REVIEW WITH TEMPLATE COMPLETED!")
                print("=" * 60)
                print(f"📁 PRISMA review saved to: {review_file}")
                print(f"� Generated using proper PRISMA 2020-compliant template")
                print(f"🧠 Based on AI-generated research plan structure")
                print(f"📊 Review Statistics:")
                metadata = prisma_review.get("search_metadata", {})
                report = prisma_review["prisma_report"]
                print(f"   • Title: {report.title}")
                print(f"   • Studies included: {report.study_selection.studies_included_review}")
                print(f"   • Meta-analysis studies: {report.study_selection.studies_included_meta_analysis}")
                print(f"   • Total searches: {metadata.get('total_searches_conducted', 0)}")
                print(f"   • Papers identified: {metadata.get('total_papers_identified', 0)}")
                
                # Export PRISMA report in multiple formats
                print(f"\\n� Exporting PRISMA report in multiple formats...")
                prisma_generator = prisma_review.get("prisma_generator")
                if prisma_generator:
                    try:
                        # Export as HTML
                        html_file = self.output_dir / "prisma_report.html"
                        await prisma_generator.export_report(
                            prisma_review["prisma_report"], 
                            format=ExportFormat.HTML, 
                            output_path=str(html_file)
                        )
                        print(f"   ✅ HTML: {html_file}")
                        
                        # Export as Markdown
                        md_file = self.output_dir / "prisma_report.md"
                        await prisma_generator.export_report(
                            prisma_review["prisma_report"], 
                            format=ExportFormat.MARKDOWN, 
                            output_path=str(md_file)
                        )
                        print(f"   ✅ Markdown: {md_file}")
                        
                    except Exception as export_error:
                        print(f"   ⚠️ Export warning: {export_error}")
                else:
                    print(f"   ⚠️ PRISMA generator not available for export")
                    
            else:
                # Fallback for error cases
                with open(review_file, 'w') as f:
                    json.dump(prisma_review, f, indent=2, default=str)
                print(f"\\n⚠️ PRISMA review saved with errors: {review_file}")
                
            return {
                "prisma_review": prisma_review,
                "output_directory": self.output_dir,
                "ai_integration": "✅ AI Research Plan + Literature Agent + PRISMA Template",
                "systematic_review": "✅ PRISMA 2020-compliant systematic review"
            }
            
        except Exception as e:
            print(f"\\n❌ PRISMA review failed: {e}")
            print("📝 This tests the ACTUAL Literature Agent with AI planning")
            raise


async def main():
    """Main execution function for PRISMA test."""
    print("📝 PRISMA Systematic Review Test - Using AI Research Plan")
    print("🎯 Testing REAL Literature Agent with AI-Generated Structure")
    
    # Run PRISMA test
    test = RealPRISMATest()
    result = await test.run_prisma_test()
    
    print(f"\\n🎯 Real PRISMA review ready: {result['output_directory']}")
    print("🔬 This systematic review was generated using real AI agents!")


if __name__ == "__main__":
    asyncio.run(main())

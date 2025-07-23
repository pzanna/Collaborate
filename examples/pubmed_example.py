#!/usr/bin/env python3
"""
PubMed Integration Example for Eunice Literature Agent

This example demonstrates how to use the new PubMed search functionality
integrated into the Literature Agent for biomedical research.

Usage:
    python examples/pubmed_example.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agents.literature_agent import LiteratureAgent
from src.config.config_manager import ConfigManager
from src.mcp.protocols import ResearchAction


async def example_direct_pubmed_search():
    """Example of direct PubMed API search."""
    print("🧬 Example 1: Direct PubMed Search")
    print("-" * 50)
    
    config_manager = ConfigManager()
    agent = LiteratureAgent(config_manager)
    
    try:
        await agent.initialize()
        
        # Direct search using the internal method
        results = await agent._search_pubmed("COVID-19 vaccine efficacy", max_results=5)
        
        print(f"Found {len(results)} biomedical articles from PubMed:")
        print()
        
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['title']}")
            print(f"   Authors: {result['metadata'].get('authors', 'N/A')}")
            print(f"   Journal: {result['metadata'].get('journal', 'N/A')}")
            print(f"   PMID: {result['metadata'].get('pmid', 'N/A')}")
            print(f"   URL: {result['url']}")
            print()
            
    except Exception as e:
        print(f"Error in direct PubMed search: {e}")
    finally:
        await agent.stop()


async def example_pubmed_action():
    """Example using PubMed search through the action interface."""
    print("🔬 Example 2: PubMed Search via Action Interface")
    print("-" * 50)
    
    config_manager = ConfigManager()
    agent = LiteratureAgent(config_manager)
    
    try:
        await agent.initialize()
        
        # Create a research action for PubMed search
        action = ResearchAction(
            task_id="pubmed_example",
            context_id="demo_context",
            agent_type="Literature",
            action="search_pubmed",
            payload={
                "query": "diabetes type 2 treatment metformin",
                "max_results": 3
            }
        )
        
        result = await agent.process_task(action)
        
        if result.status == "completed" and result.result:
            data = result.result
            print(f"Search completed successfully!")
            print(f"Query: {data['query']}")
            print(f"Total found: {data['total_found']}")
            print(f"Search method: {data['search_method']}")
            print()
            
            for i, article in enumerate(data['results'], 1):
                print(f"{i}. {article['title']}")
                metadata = article['metadata']
                print(f"   Authors: {metadata.get('authors', 'N/A')}")
                print(f"   Publication Date: {metadata.get('publication_date', 'N/A')}")
                print(f"   DOI: {metadata.get('doi', 'N/A')}")
                print()
        else:
            print(f"Search failed: {result.error if result else 'Unknown error'}")
            
    except Exception as e:
        print(f"Error in PubMed action: {e}")
    finally:
        await agent.stop()


async def example_biomedical_workflow():
    """Example of the complete biomedical research workflow."""
    print("🧪 Example 3: Complete Biomedical Research Workflow")
    print("-" * 50)
    
    config_manager = ConfigManager()
    agent = LiteratureAgent(config_manager)
    
    try:
        await agent.initialize()
        
        # Run biomedical research workflow
        action = ResearchAction(
            task_id="biomedical_workflow",
            context_id="demo_context",
            agent_type="Literature",
            action="biomedical_research_workflow",
            payload={
                "research_topic": "alzheimer disease treatment",
                "max_papers": 8
            }
        )
        
        result = await agent.process_task(action)
        
        if result.status == "completed" and result.result:
            data = result.result
            print(f"Biomedical research workflow completed!")
            print(f"Research Topic: {data['research_topic']}")
            print(f"Total Papers Found: {data['total_papers_found']}")
            print(f"Content Extracted: {data['content_extracted']}")
            print(f"Biomedical Focus: {data['biomedical_focus']}")
            print()
            
            # Show PubMed results
            if data.get('pubmed_search'):
                pubmed_count = len(data['pubmed_search']['results'])
                print(f"📚 PubMed Articles: {pubmed_count}")
                
                for i, article in enumerate(data['pubmed_search']['results'][:3], 1):
                    print(f"  {i}. {article['title'][:80]}...")
                    print(f"     PMID: {article['metadata']['pmid']}")
                print()
            
            # Show academic results
            if data.get('academic_search'):
                academic_count = len(data['academic_search']['results'])
                print(f"🎓 Academic Articles: {academic_count}")
                
                for i, article in enumerate(data['academic_search']['results'][:2], 1):
                    print(f"  {i}. {article['title'][:80]}...")
                print()
            
            # Show clinical results if any
            if data.get('clinical_search'):
                clinical_count = len(data['clinical_search']['results'])
                print(f"🏥 Clinical Studies: {clinical_count}")
                
        else:
            print(f"Workflow failed: {result.error if result else 'Unknown error'}")
            
    except Exception as e:
        print(f"Error in biomedical workflow: {e}")
    finally:
        await agent.stop()


async def example_comprehensive_pipeline_biomedical():
    """Example of comprehensive research pipeline with biomedical auto-detection."""
    print("🔍 Example 4: Comprehensive Pipeline with Biomedical Auto-Detection")
    print("-" * 50)
    
    config_manager = ConfigManager()
    agent = LiteratureAgent(config_manager)
    
    try:
        await agent.initialize()
        
        # Comprehensive pipeline with biomedical topic (should auto-include PubMed)
        action = ResearchAction(
            task_id="comprehensive_biomedical",
            context_id="demo_context",
            agent_type="Literature",
            action="comprehensive_research_pipeline",
            payload={
                "topic": "cancer immunotherapy checkpoint inhibitors",  # Biomedical keywords
                "include_academic": True,
                "include_news": False,
                "max_results": 6
            }
        )
        
        result = await agent.process_task(action)
        
        if result.status == "completed" and result.result:
            data = result.result
            print(f"Comprehensive research completed!")
            print(f"Topic: {data['topic']}")
            print()
            
            # Check if PubMed was auto-included
            if data.get('pubmed_search'):
                pubmed_count = len(data['pubmed_search']['results'])
                print(f"✅ PubMed auto-detected and included: {pubmed_count} articles")
            else:
                print("❌ PubMed was not included")
            
            # Show summary
            if 'summary' in data and data['summary']:
                summary = data['summary']
                print(f"\n📊 Research Summary:")
                print(f"  Total sources searched: {summary['total_sources_searched']}")
                print(f"  High-quality sources: {summary['high_quality_sources']}")
                print(f"  Content extracted: {summary['content_extracted']}")
                print(f"  Final ranked results: {summary['final_ranked_results']}")
                
        else:
            print(f"Pipeline failed: {result.error if result else 'Unknown error'}")
            
    except Exception as e:
        print(f"Error in comprehensive pipeline: {e}")
    finally:
        await agent.stop()


async def main():
    """Run all PubMed integration examples."""
    print("🧬 PubMed Integration Examples for Eunice Literature Agent")
    print("=" * 70)
    print()
    
    examples = [
        example_direct_pubmed_search,
        example_pubmed_action,
        example_biomedical_workflow,
        example_comprehensive_pipeline_biomedical
    ]
    
    for i, example_func in enumerate(examples, 1):
        try:
            await example_func()
            print("✅ Example completed successfully!")
        except Exception as e:
            print(f"❌ Example failed: {e}")
        
        if i < len(examples):
            print("\n" + "="*70 + "\n")
    
    print("\n🎉 All PubMed integration examples completed!")
    print("\nKey Features Demonstrated:")
    print("• Direct PubMed API search using NCBI E-utilities")
    print("• Integration with existing Literature Agent workflows")
    print("• Automatic biomedical topic detection")
    print("• Combined search across PubMed, academic, and web sources")
    print("• Proper handling of PMIDs, DOIs, and biomedical metadata")


if __name__ == "__main__":
    asyncio.run(main())

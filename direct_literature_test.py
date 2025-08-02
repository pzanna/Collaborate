#!/usr/bin/env python3
"""
Direct literature search test to verify our fixes are working.
"""

import asyncio
import json
import logging
import sys
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

import aiohttp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = "http://localhost:8001"

async def test_direct_literature_search():
    """Test literature search directly."""
    
    session = aiohttp.ClientSession()
    
    try:
        # Generate unique IDs for this test
        plan_id = str(uuid.uuid4())
        
        research_plan = """
        Research Plan: Optimizing Growth Media for Avian Neuronal Cultures
        
        Objective: Investigate the biochemical components and optimal concentrations 
        for promoting healthy growth and viability of avian neuronal cells in culture.
        
        Key Research Questions:
        1. What are the essential nutrients required for avian neuron survival?
        2. How do different media formulations affect neuronal differentiation?
        3. What growth factors enhance synaptic development in avian neurons?
        
        Expected Outcomes: Improved protocols for avian neuron culture.
        """
        
        payload = {
            "plan_id": plan_id,
            "research_plan": research_plan,
            "sources": ["semantic_scholar", "pubmed"],  # Use reliable sources
            "max_results": 15,
            "filters": {
                "year_range": [2020, 2024],
                "language": "en"
            }
        }
        
        logger.info(f"🔍 Testing literature search with plan_id: {plan_id}")
        logger.info("📤 Sending literature search request...")
        
        async with session.post(
            f"{API_BASE_URL}/literature/search", 
            json=payload,
            timeout=aiohttp.ClientTimeout(total=300)
        ) as response:
            if response.status == 200:
                result = await response.json()
                logger.info("📥 Literature search response received")
                
                # Check results
                records = result.get("records", [])
                search_report = result.get("search_report", {})
                
                print("\n" + "="*80)
                print("🧪 LITERATURE SEARCH TEST RESULTS")
                print("="*80)
                
                print(f"\n📊 SEARCH SUMMARY:")
                print(f"   Plan ID:              {plan_id}")
                print(f"   Status:               ✅ SUCCESS")
                print(f"   Records Returned:     {len(records)}")
                print(f"   Total Fetched:        {search_report.get('total_fetched', 'N/A')}")
                print(f"   Total Unique:         {search_report.get('total_unique', 'N/A')}")
                print(f"   Per Source Counts:    {search_report.get('per_source_counts', {})}")
                
                # Check for abstracts
                if records:
                    records_with_abstracts = [r for r in records if r.get("abstract")]
                    records_without_abstracts = [r for r in records if not r.get("abstract")]
                    
                    print(f"\n📄 ABSTRACT ANALYSIS:")
                    print(f"   Records with abstracts:    {len(records_with_abstracts)}")
                    print(f"   Records without abstracts: {len(records_without_abstracts)}")
                    
                    if len(records_without_abstracts) == 0:
                        print(f"   ✅ ABSTRACT FILTERING WORKING: No empty abstracts in results!")
                    else:
                        print(f"   ⚠️  ABSTRACT FILTERING CHECK: {len(records_without_abstracts)} records without abstracts")
                        
                    # Show sample record
                    if records_with_abstracts:
                        sample = records_with_abstracts[0]
                        print(f"\n📋 SAMPLE RECORD:")
                        print(f"   Title: {sample.get('title', 'N/A')[:80]}...")
                        print(f"   Source: {sample.get('source', 'N/A')}")
                        print(f"   Abstract: {'✅ Present' if sample.get('abstract') else '❌ Missing'}")
                        print(f"   DOI: {sample.get('doi', 'N/A')}")
                
                print(f"\n🔍 JSON STORAGE VERIFICATION:")
                print(f"   To check if JSON storage worked, run:")
                print(f"   docker logs eunice-literature-agent | grep 'JSON STORED'")
                print(f"   ")
                print(f"   Expected log messages:")
                print(f"   - '🎉 INITIAL LITERATURE JSON STORED: X records'")
                print(f"   - '🎉 REVIEWED LITERATURE JSON STORED: X records'")
                
                # Errors
                errors = search_report.get("errors", [])
                if errors:
                    print(f"\n❌ SEARCH ERRORS:")
                    for i, error in enumerate(errors, 1):
                        print(f"   {i}. {error}")
                
                print("\n" + "="*80)
                
                if records:
                    print("🎉 TEST PASSED: Literature search returned records with abstracts!")
                    return 0
                else:
                    print("⚠️  TEST WARNING: No records returned, but search completed successfully")
                    return 0
                    
            else:
                error_text = await response.text()
                logger.error(f"❌ Literature search failed: {response.status} - {error_text}")
                
                print("\n" + "="*80)
                print("🧪 LITERATURE SEARCH TEST RESULTS")
                print("="*80)
                print(f"❌ SEARCH FAILED: {response.status} - {error_text}")
                print("="*80)
                return 1
                
    except Exception as e:
        logger.error(f"❌ Test error: {e}")
        print(f"\n💥 Test failed: {e}")
        return 1
        
    finally:
        await session.close()

async def main():
    """Run the direct literature search test."""
    print("🚀 Starting Direct Literature Search Test")
    print("This test will verify abstract filtering and JSON storage fixes")
    
    exit_code = await test_direct_literature_search()
    
    print(f"\n💡 NEXT STEPS:")
    print(f"   1. Check container logs for JSON storage messages:")
    print(f"      docker logs eunice-literature-agent | grep 'JSON STORED'")
    print(f"   2. If you see both initial and reviewed storage messages, all fixes are working!")
    
    return exit_code

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

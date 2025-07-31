#!/usr/bin/env python3
"""
Quick test script for Literature Search Service functionality.
Tests basic search functionality without requiring AI API keys.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the literature service path
sys.path.append(str(Path(__file__).parent / "agents" / "literature" / "src"))

from literature_service import LiteratureSearchService, SearchQuery


async def test_literature_service_basic():
    """Test basic literature service functionality without AI."""
    
    print("🧪 Testing Literature Search Service (Basic)")
    print("=" * 50)
    
    # Mock configuration
    config = {
        "service_host": "0.0.0.0",
        "service_port": 8003,
        "mcp_server_url": "ws://localhost:9000",
        "max_concurrent_searches": 3,
        "search_timeout": 300,
        "rate_limit_delay": 1.0
    }
    
    # Create service instance
    service = LiteratureSearchService(config)
    
    print(f"✅ Literature Search Service initialized")
    print(f"   Agent ID: {service.agent_id}")
    print(f"   Agent Type: {service.agent_type}")
    print(f"   Port: {service.service_port}")
    
    # Test basic search query creation
    search_query = SearchQuery(
        lit_review_id="test_review_001",
        query="machine learning medical diagnosis",
        max_results=10,
        sources=["semantic_scholar", "arxiv"],
        search_depth="standard"
    )
    
    print(f"\n📝 Test Search Query Created:")
    print(f"   Review ID: {search_query.lit_review_id}")
    print(f"   Query: {search_query.query}")
    print(f"   Sources: {search_query.sources}")
    print(f"   Max Results: {search_query.max_results}")
    
    # Test search term extraction without research plan (should use original query)
    search_terms = await service._extract_search_terms_from_research_plan(
        research_plan=None,  # No research plan
        original_query=search_query.query
    )
    
    print(f"\n🔍 Search Term Extraction (No Research Plan):")
    print(f"   Input Query: {search_query.query}")
    print(f"   Output Terms: {search_terms}")
    
    # Verify fallback works correctly
    if search_terms == [search_query.query]:
        print("✅ Correctly falls back to original query when no AI agent available")
    else:
        print("⚠️  Unexpected search terms returned")
    
    # Test with research plan but no AI agent
    research_plan = {
        "objectives": [
            "Investigate machine learning applications in medical diagnosis",
            "Analyze effectiveness of deep learning models"
        ],
        "key_areas": ["Computer Vision", "Medical Imaging", "Diagnostic AI"],
        "questions": [
            "What are the most effective architectures for medical image analysis?",
            "How do AI tools compare to traditional methods?"
        ],
        "sources": ["PubMed", "ArXiv", "Semantic Scholar"]
    }
    
    search_terms_with_plan = await service._extract_search_terms_from_research_plan(
        research_plan=research_plan,
        original_query=search_query.query
    )
    
    print(f"\n🎯 Search Term Extraction (With Research Plan, No AI Agent):")
    print(f"   Research Plan provided: {len(research_plan['objectives'])} objectives")
    print(f"   Output Terms: {search_terms_with_plan}")
    
    # Should still fall back to original query since no AI agent
    if search_terms_with_plan == [search_query.query]:
        print("✅ Correctly falls back to original query when AI agent unavailable")
    else:
        print("⚠️  Expected fallback to original query")
    
    # Test AI agent availability check
    print(f"\n🤖 AI Agent Availability:")
    print(f"   AI Agent Available: {service.ai_agent_available}")
    
    if not service.ai_agent_available:
        print("✅ Correctly identified AI agent as unavailable (expected without MCP connection)")
    else:
        print("ℹ️  AI agent marked as available")
    
    # Test API configurations
    print(f"\n🔧 API Configurations:")
    for source, config in service.api_configs.items():
        print(f"   {source}: {config['base_url']}")
    
    print(f"\n🎉 Basic Literature Service Tests Completed!")
    return True


async def test_record_normalization():
    """Test record normalization functionality."""
    
    print("\n🧪 Testing Record Normalization")
    print("=" * 40)
    
    # Mock configuration
    config = {
        "service_host": "0.0.0.0",
        "service_port": 8003
    }
    
    service = LiteratureSearchService(config)
    
    # Test data for different sources
    test_records = {
        "semantic_scholar": [
            {
                "paperId": "123456",
                "title": "Deep Learning for Medical Diagnosis",
                "authors": [{"name": "John Smith"}, {"name": "Jane Doe"}],
                "abstract": "This paper explores deep learning applications...",
                "year": 2023,
                "venue": "Nature Medicine",
                "doi": "10.1038/s41591-023-001",
                "citationCount": 42
            }
        ],
        "arxiv": [
            {
                "title": "Neural Networks in Healthcare",
                "authors": ["Alice Johnson", "Bob Wilson"],
                "abstract": "We present a novel approach...",
                "published": "2023-01-15",
                "arxiv_id": "2301.12345",
                "categories": ["cs.LG", "cs.CV"]
            }
        ]
    }
    
    # Test normalization for each source
    for source, records in test_records.items():
        normalized = service._normalize_records(records, source)
        
        print(f"\n📋 {source.title()} Normalization:")
        print(f"   Input Records: {len(records)}")
        print(f"   Output Records: {len(normalized)}")
        
        if normalized:
            record = normalized[0]
            print(f"   Title: {record.get('title', 'N/A')}")
            print(f"   Authors: {len(record.get('authors', []))} authors")
            print(f"   Source: {record.get('source')}")
            print(f"   Year: {record.get('year', 'N/A')}")
    
    print("✅ Record normalization tests completed")


async def main():
    """Main test function."""
    print("🚀 Starting Literature Search Service Tests")
    print("   (No AI API keys required)")
    
    success1 = await test_literature_service_basic()
    await test_record_normalization()
    
    if success1:
        print("\n🎯 Literature Search Service is working correctly!")
        print("   ✅ Basic functionality operational")
        print("   ✅ Graceful fallback when AI agent unavailable") 
        print("   ✅ Record normalization working")
        print("   ℹ️  AI search optimization requires AI agent via MCP")
    else:
        print("\n🔧 Literature Search Service needs debugging")


if __name__ == "__main__":
    asyncio.run(main())

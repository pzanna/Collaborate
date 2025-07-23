#!/usr/bin/env python3
"""
Comprehensive LiteratureAgent Test Suite

This consolidated test file includes all major test categories:
1. Basic functionality tests
2. Workflow function tests  
3. Semantic Scholar API integration tests
4. Integration tests with the full Eunice system

Run with: python -m pytest tests/literature/test_literature_complete.py -v
Or directly: python tests/literature/test_literature_complete.py
"""

import asyncio
import logging
import sys
import time
import json
import pytest
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agents.literature_agent import LiteratureAgent
from src.config.config_manager import ConfigManager
from src.mcp.protocols import ResearchAction


class TestLiteratureAgent:
    """Comprehensive test suite for LiteratureAgent functionality."""
    
    @pytest.fixture(scope="function")
    async def literature_agent(self):
        """Create and initialize a LiteratureAgent for testing."""
        config_manager = ConfigManager()
        agent = LiteratureAgent(config_manager)
        await agent.initialize()
        yield agent
        await agent.stop()
    
    @pytest.mark.asyncio
    async def test_basic_search_functionality(self, literature_agent):
        """Test basic search functionality."""
        action = ResearchAction(
            task_id="test_search",
            context_id="test_context",
            agent_type="Literature", 
            action="search_information",
            payload={
                "query": "Python programming tutorial",
                "max_results": 3,
                "search_engines": ["google", "bing"]
            }
        )
        
        result = await literature_agent.process_task(action)
        
        assert result is not None
        assert result.status == "completed"
        assert "results" in result.result
        assert len(result.result["results"]) > 0
        
        # Verify result structure
        first_result = result.result["results"][0]
        required_fields = ["title", "url", "content", "source", "type"]
        for field in required_fields:
            assert field in first_result, f"Missing required field: {field}"
    
    @pytest.mark.asyncio
    async def test_semantic_scholar_integration(self, literature_agent):
        """Test Semantic Scholar API integration."""
        # Test direct API call
        results = await literature_agent._search_semantic_scholar(
            "machine learning transformers", max_results=5
        )
        
        assert len(results) > 0, "Semantic Scholar API should return results"
        
        # Verify result structure
        first_result = results[0]
        assert "title" in first_result
        assert "source" in first_result
        assert first_result["source"] == "semantic_scholar"
        assert "metadata" in first_result
        
        metadata = first_result["metadata"]
        expected_metadata_fields = ["paper_id", "authors", "year"]
        for field in expected_metadata_fields:
            assert field in metadata, f"Missing metadata field: {field}"
    
    @pytest.mark.asyncio
    async def test_academic_research_workflow(self, literature_agent):
        """Test academic research workflow functionality."""
        action = ResearchAction(
            task_id="test_academic",
            context_id="test_context",
            agent_type="Literature",
            action="academic_research_workflow",
            payload={
                "research_topic": "neural networks machine learning",
                "max_papers": 10
            }
        )
        
        result = await literature_agent.process_task(action)
        
        assert result.status == "completed"
        assert "broad_search" in result.result
        assert "total_papers_found" in result.result
        assert result.result["total_papers_found"] > 0
        
        # Verify academic paper structure
        if result.result["broad_search"]["results"]:
            paper = result.result["broad_search"]["results"][0]
            assert "title" in paper
            assert "type" in paper
            assert paper["type"] == "academic_paper"
    
    @pytest.mark.asyncio
    async def test_multi_source_validation(self, literature_agent):
        """Test multi-source validation workflow."""
        action = ResearchAction(
            task_id="test_validation",
            context_id="test_context",
            agent_type="Literature",
            action="multi_source_validation",
            payload={
                "claim": "Python is a programming language"
            }
        )
        
        result = await literature_agent.process_task(action)
        
        assert result.status == "completed"
        result_data = result.result
        
        # Should have different source types
        source_types = ["web_sources", "academic_sources", "news_sources"]
        for source_type in source_types:
            assert source_type in result_data
    
    @pytest.mark.asyncio 
    async def test_cost_optimized_search(self, literature_agent):
        """Test cost-optimized search with different budget levels."""
        budget_levels = ["low", "medium", "high"]
        
        for budget in budget_levels:
            action = ResearchAction(
                task_id=f"test_cost_{budget}",
                context_id="test_context",
                agent_type="Literature",
                action="cost_optimized_search",
                payload={
                    "query": "artificial intelligence",
                    "budget_level": budget
                }
            )
            
            result = await literature_agent.process_task(action)
            
            assert result.status == "completed"
            assert "results" in result.result
            assert "search_engines_used" in result.result
            
            # Verify budget constraints
            engines_used = result.result["search_engines_used"]
            if budget == "low":
                assert len(engines_used) <= 1
            elif budget == "medium":
                assert len(engines_used) <= 2
            elif budget == "high":
                assert len(engines_used) >= 2
    
    @pytest.mark.asyncio
    async def test_comprehensive_research_pipeline(self, literature_agent):
        """Test comprehensive research pipeline."""
        action = ResearchAction(
            task_id="test_pipeline",
            context_id="test_context",
            agent_type="Literature",
            action="comprehensive_research_pipeline",
            payload={
                "topic": "machine learning applications",
                "include_academic": True,
                "include_news": True,
                "max_results": 10
            }
        )
        
        result = await literature_agent.process_task(action)
        
        assert result.status == "completed"
        result_data = result.result
        
        # Should include multiple source types
        assert "web_search" in result_data
        assert "summary" in result_data
        
        # Verify summary statistics
        summary = result_data["summary"]
        assert "total_sources_searched" in summary
        assert "content_extracted" in summary
        assert "academic_search" in result_data
        assert "news_search" in result_data
        assert "summary" in result_data
        
        # Verify summary statistics
        summary = result_data["summary"]
        assert "total_sources_searched" in summary
        assert "high_quality_sources" in summary
    
    @pytest.mark.asyncio
    async def test_fact_verification_workflow(self, literature_agent):
        """Test fact verification workflow."""
        action = ResearchAction(
            task_id="test_verification",
            context_id="test_context",
            agent_type="Literature",
            action="fact_verification_workflow",
            payload={
                "claim": "The Earth orbits around the Sun",
                "require_academic": True
            }
        )
        
        result = await literature_agent.process_task(action)
        
        assert result.status == "completed"
        result_data = result.result
        
        # Should have verification components
        assert "verification_status" in result_data
        assert "academic_sources" in result_data
        assert "summary" in result_data
        
        # Verification status should be valid
        valid_statuses = ["highly_credible", "moderately_credible", "low_credibility", "unverified"]
        assert result_data["verification_status"] in valid_statuses
    
    @pytest.mark.asyncio
    async def test_content_extraction(self, literature_agent):
        """Test content extraction functionality."""
        action = ResearchAction(
            task_id="test_extraction",
            context_id="test_context",
            agent_type="Literature",
            action="extract_web_content",
            payload={
                "url": "https://www.python.org/about/"
            }
        )
        
        result = await literature_agent.process_task(action)
        
        assert result.status == "completed"
        assert "url" in result.result
        assert "content" in result.result
        assert "metadata" in result.result
        
        # Verify content structure
        content_data = result.result
        assert content_data["url"] == "https://www.python.org/about/"
        assert len(content_data["content"]) > 0
    
    @pytest.mark.asyncio
    async def test_error_handling(self, literature_agent):
        """Test error handling for invalid inputs."""
        # Test with invalid search engine
        action = ResearchAction(
            task_id="test_error",
            context_id="test_context",
            agent_type="Literature",
            action="search_information",
            payload={
                "query": "test query",
                "search_engines": ["invalid_engine"]
            }
        )
        
        result = await literature_agent.process_task(action)
        
        # Should handle gracefully, not crash
        assert result is not None
        # May have empty results but should not error
    
    @pytest.mark.asyncio
    async def test_capabilities_registration(self, literature_agent):
        """Test that all workflow capabilities are properly registered."""
        capabilities = literature_agent._get_capabilities()
        
        expected_capabilities = [
            "search_information",
            "extract_web_content", 
            "search_academic_papers",
            "academic_research_workflow",
            "multi_source_validation",
            "cost_optimized_search",
            "comprehensive_research_pipeline",
            "fact_verification_workflow"
        ]
        
        for capability in expected_capabilities:
            assert capability in capabilities, f"Missing capability: {capability}"


# Standalone execution for direct testing
async def run_standalone_tests():
    """Run tests directly without pytest."""
    print("🧪 Running Comprehensive LiteratureAgent Tests")
    print("=" * 60)
    
    # Initialize agent
    config_manager = ConfigManager()
    agent = LiteratureAgent(config_manager)
    
    try:
        await agent.initialize()
        print("✅ LiteratureAgent initialized successfully")
        
        # Create test instance
        test_suite = TestLiteratureAgent()
        
        # Run key tests
        test_methods = [
            ("Basic Search", test_suite.test_basic_search_functionality),
            ("Semantic Scholar", test_suite.test_semantic_scholar_integration),
            ("Academic Workflow", test_suite.test_academic_research_workflow),
            ("Cost Optimization", test_suite.test_cost_optimized_search),
            ("Capabilities", test_suite.test_capabilities_registration)
        ]
        
        passed = 0
        total = len(test_methods)
        
        for test_name, test_method in test_methods:
            print(f"\n🔍 Testing {test_name}...")
            try:
                await test_method(agent)
                print(f"✅ {test_name} test passed")
                passed += 1
            except Exception as e:
                print(f"❌ {test_name} test failed: {e}")
        
        print(f"\n📊 Test Summary: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed!")
            return 0
        else:
            print("⚠️  Some tests failed")
            return 1
            
    finally:
        await agent.stop()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--pytest":
        # Run with pytest
        pytest.main([__file__, "-v"])
    else:
        # Run standalone tests
        result = asyncio.run(run_standalone_tests())
        sys.exit(result)

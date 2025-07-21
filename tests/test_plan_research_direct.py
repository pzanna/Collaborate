"""
Direct test for PlanningAgent._plan_research function.

This script directly tests the _plan_research function without requiring pytest.
It can be run independently to validate the function's behavior.
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock
from typing import Dict, Any

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(src_path))

try:
    from src.agents.planning_agent import PlanningAgent
    from src.agents.base_agent import AgentStatus
    from src.config.config_manager import ConfigManager
    from src.models.data_models import Message
except ImportError:
    # Alternative import if src module not found
    sys.path.append(str(project_root / "src"))
    from agents.planning_agent import PlanningAgent
    from agents.base_agent import AgentStatus
    from config.config_manager import ConfigManager
    from models.data_models import Message


class DirectTestPlanResearch:
    """Direct test class for _plan_research function."""
    
    def __init__(self):
        """Initialize the test setup."""
        self.setup_mock_environment()
    
    def setup_mock_environment(self):
        """Set up mock configuration and AI client."""
        # Create mock config manager
        self.config_manager = MagicMock(spec=ConfigManager)
        self.config_manager.config = MagicMock()
        self.config_manager.config.ai_providers = {
            'openai': {
                'model': 'gpt-4o-mini',
                'temperature': 0.7,
                'max_tokens': 2000
            }
        }
        self.config_manager.get_api_key.return_value = "test-api-key"
        
        # Create mock AI client
        self.mock_ai_client = MagicMock()
        self.mock_ai_client.get_response.return_value = """
        Research Plan for Test Query:
        
        1. Research objectives:
        - Understand the core concepts and fundamentals
        - Identify key stakeholders and their roles
        - Analyze current trends and future directions
        - Evaluate potential challenges and opportunities
        
        2. Key areas to investigate:
        - Technical specifications and requirements
        - Market analysis and competitive landscape
        - Regulatory environment and compliance
        - Implementation strategies and best practices
        
        3. Specific questions to answer:
        - What are the main challenges in this domain?
        - How does this compare to existing alternatives?
        - What are the cost-benefit considerations?
        - What are the long-term sustainability prospects?
        
        4. Information sources to consult:
        - Peer-reviewed academic papers and journals
        - Industry reports and white papers
        - Expert interviews and surveys
        - Government publications and statistics
        - Professional conferences and workshops
        
        5. Expected outcomes:
        - Comprehensive understanding of the topic
        - Actionable insights and recommendations
        - Strategic planning framework
        - Risk assessment and mitigation strategies
        - Implementation roadmap and timeline
        """
    
    def create_planning_agent(self):
        """Create and configure a PlanningAgent for testing."""
        agent = PlanningAgent(self.config_manager)
        
        # Set up the mock AI client
        agent.ai_clients = {'openai': self.mock_ai_client}
        agent.default_client = self.mock_ai_client
        agent.status = AgentStatus.READY
        
        return agent
    
    async def test_basic_functionality(self):
        """Test basic research plan generation."""
        print("🧪 Testing basic functionality...")
        
        agent = self.create_planning_agent()
        
        payload = {
            'query': 'What are the benefits of artificial intelligence in healthcare?',
            'context': {
                'domain': 'healthcare',
                'focus': 'benefits',
                'stakeholders': ['patients', 'doctors', 'hospitals']
            }
        }
        
        result = await agent._plan_research(payload)
        
        # Validate the result
        assert 'query' in result, "Result must contain 'query'"
        assert 'plan' in result, "Result must contain 'plan'"
        assert 'raw_response' in result, "Result must contain 'raw_response'"
        assert 'planning_model' in result, "Result must contain 'planning_model'"
        
        # Validate the query preservation
        assert result['query'] == payload['query'], "Query should be preserved"
        
        # Validate the plan structure
        plan = result['plan']
        expected_keys = ['raw_plan', 'objectives', 'key_areas', 'questions', 'sources', 'outcomes']
        for key in expected_keys:
            assert key in plan, f"Plan must contain '{key}'"
        
        print("✅ Basic functionality test passed!")
        return result
    
    async def test_empty_query_handling(self):
        """Test handling of empty query."""
        print("🧪 Testing empty query handling...")
        
        agent = self.create_planning_agent()
        
        payload = {
            'query': '',
            'context': {}
        }
        
        try:
            await agent._plan_research(payload)
            print("❌ Expected ValueError for empty query!")
            return False
        except ValueError as e:
            if "Query is required for research planning" in str(e):
                print("✅ Empty query handling test passed!")
                return True
            else:
                print(f"❌ Unexpected error message: {e}")
                return False
    
    async def test_missing_query_handling(self):
        """Test handling of missing query."""
        print("🧪 Testing missing query handling...")
        
        agent = self.create_planning_agent()
        
        payload = {
            'context': {'some': 'data'}
        }
        
        try:
            await agent._plan_research(payload)
            print("❌ Expected ValueError for missing query!")
            return False
        except ValueError as e:
            if "Query is required for research planning" in str(e):
                print("✅ Missing query handling test passed!")
                return True
            else:
                print(f"❌ Unexpected error message: {e}")
                return False
    
    async def test_complex_context(self):
        """Test with complex context data."""
        print("🧪 Testing complex context handling...")
        
        agent = self.create_planning_agent()
        
        payload = {
            'query': 'Climate change impact on sustainable agriculture',
            'context': {
                'geographical_scope': ['North America', 'Europe', 'Asia'],
                'time_frame': '2024-2035',
                'stakeholders': {
                    'primary': ['farmers', 'agricultural_scientists'],
                    'secondary': ['policymakers', 'consumers', 'investors']
                },
                'priority_areas': {
                    'adaptation': ['crop_varieties', 'irrigation_systems'],
                    'mitigation': ['carbon_sequestration', 'renewable_energy'],
                    'sustainability': ['soil_health', 'biodiversity']
                },
                'constraints': {
                    'budget': '$10M',
                    'timeline': '18_months',
                    'regulatory': ['EU_regulations', 'US_EPA_guidelines']
                }
            }
        }
        
        result = await agent._plan_research(payload)
        
        # Validate basic structure
        assert result['query'] == payload['query']
        assert 'plan' in result
        
        # Check that AI client was called with the context
        call_args = self.mock_ai_client.get_response.call_args
        messages = call_args.kwargs['messages']
        prompt_content = messages[0].content
        
        # Verify context was included
        assert 'geographical_scope' in prompt_content
        assert 'stakeholders' in prompt_content
        assert 'priority_areas' in prompt_content
        
        print("✅ Complex context test passed!")
        return result
    
    async def test_ai_client_error_handling(self):
        """Test handling of AI client errors."""
        print("🧪 Testing AI client error handling...")
        
        agent = self.create_planning_agent()
        
        # Configure mock to raise an exception
        error_client = MagicMock()
        error_client.get_response.side_effect = Exception("Simulated API Error")
        agent.default_client = error_client
        
        payload = {
            'query': 'Test query for error handling',
            'context': {}
        }
        
        result = await agent._plan_research(payload)
        
        # Should handle error gracefully
        assert 'raw_response' in result
        assert 'Error generating response' in result['raw_response']
        
        print("✅ AI client error handling test passed!")
        return result
    
    async def test_no_ai_client(self):
        """Test behavior when no AI client is available."""
        print("🧪 Testing no AI client scenario...")
        
        agent = PlanningAgent(self.config_manager)
        agent.default_client = None
        agent.status = AgentStatus.READY
        
        payload = {
            'query': 'Test query with no AI client',
            'context': {}
        }
        
        try:
            result = await agent._plan_research(payload)
            print("❌ Expected RuntimeError for missing AI client!")
            return False
        except RuntimeError as e:
            if "No AI client available" in str(e):
                print("✅ No AI client test passed!")
                return True
            else:
                print(f"❌ Unexpected error message: {e}")
                return False
    
    async def test_prompt_structure(self):
        """Test the structure of the generated prompt."""
        print("🧪 Testing prompt structure...")
        
        agent = self.create_planning_agent()
        
        payload = {
            'query': 'Machine learning applications in financial services',
            'context': {
                'industry': 'finance',
                'use_cases': ['fraud_detection', 'risk_assessment', 'algorithmic_trading'],
                'compliance': ['GDPR', 'SOX', 'Basel_III']
            }
        }
        
        await agent._plan_research(payload)
        
        # Verify the prompt structure
        call_args = self.mock_ai_client.get_response.call_args
        messages = call_args.kwargs['messages']
        prompt_content = messages[0].content
        
        # Check required sections
        required_sections = [
            'comprehensive research plan',
            'Research objectives',
            'Key areas to investigate',
            'Specific questions to answer',
            'Information sources to consult',
            'Expected outcomes'
        ]
        
        for section in required_sections:
            assert section in prompt_content, f"Prompt must contain '{section}'"
        
        # Verify query and context are included
        assert payload['query'] in prompt_content
        assert json.dumps(payload['context'], indent=2) in prompt_content
        
        print("✅ Prompt structure test passed!")
        return True
    
    async def run_all_tests(self):
        """Run all tests and report results."""
        print("🚀 Starting comprehensive test suite for _plan_research function\n")
        
        tests = [
            self.test_basic_functionality,
            self.test_empty_query_handling,
            self.test_missing_query_handling,
            self.test_complex_context,
            self.test_ai_client_error_handling,
            self.test_no_ai_client,
            self.test_prompt_structure
        ]
        
        results = []
        
        for test in tests:
            try:
                result = await test()
                results.append((test.__name__, True, result))
                print()
            except Exception as e:
                print(f"❌ {test.__name__} failed with error: {e}")
                results.append((test.__name__, False, str(e)))
                print()
        
        # Report summary
        print("📊 TEST SUMMARY:")
        print("=" * 50)
        passed = sum(1 for _, success, _ in results if success)
        total = len(results)
        
        for test_name, success, result in results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status}: {test_name}")
        
        print("=" * 50)
        print(f"PASSED: {passed}/{total}")
        print(f"SUCCESS RATE: {passed/total*100:.1f}%")
        
        if passed == total:
            print("\n🎉 All tests passed! The _plan_research function is working correctly.")
        else:
            print(f"\n⚠️  {total-passed} test(s) failed. Please review the implementation.")
        
        return passed == total


async def main():
    """Main function to run the direct test."""
    print("Direct Test for PlanningAgent._plan_research Function")
    print("=" * 60)
    
    tester = DirectTestPlanResearch()
    success = await tester.run_all_tests()
    
    return success


if __name__ == "__main__":
    """
    Run the direct test when this file is executed.
    
    Usage:
        python test_plan_research_direct.py
    """
    try:
        success = asyncio.run(main())
        exit_code = 0 if success else 1
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Test failed with unexpected error: {e}")
        sys.exit(1)

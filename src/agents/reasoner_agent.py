"""
Reasoning Agent for research tasks.

This module provides the ReasonerAgent that handles analysis, reasoning,
and synthesis tasks for the research system.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
import json
import re

from .base_agent import BaseAgent, AgentStatus
from ..mcp.protocols import ResearchAction
from ..config.config_manager import ConfigManager
from ..ai_clients.openai_client import OpenAIClient
from ..ai_clients.xai_client import XAIClient


class ReasonerAgent(BaseAgent):
    """
    Reasoning Agent for analysis and synthesis tasks.
    
    This agent handles:
    - Information analysis
    - Research plan generation
    - Result synthesis
    - Chain of thought reasoning
    - Content summarization
    """
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the Reasoner Agent.
        
        Args:
            config_manager: Configuration manager instance
        """
        super().__init__("reasoner", config_manager)
        
        # AI clients
        self.ai_clients = {}
        
        # Reasoning configuration
        self.default_model = "gpt-4"
        self.max_context_length = 8000
        self.temperature = 0.7
        
        self.logger.info("ReasonerAgent initialized")
    
    def _get_capabilities(self) -> List[str]:
        """Get reasoner agent capabilities."""
        return [
            'plan_research',
            'analyze_information',
            'synthesize_results',
            'chain_of_thought',
            'summarize_content',
            'extract_insights',
            'compare_sources',
            'evaluate_credibility'
        ]
    
    async def _initialize_agent(self) -> None:
        """Initialize reasoner-specific resources."""
        # Initialize AI clients
        ai_providers = self.config.config.ai_providers
        
        # Initialize OpenAI client
        if 'openai' in ai_providers:
            api_key = self.config.get_api_key('openai')
            self.ai_clients['openai'] = OpenAIClient(api_key=api_key, config=ai_providers['openai'])
        
        # Initialize XAI client
        if 'xai' in ai_providers:
            api_key = self.config.get_api_key('xai')
            self.ai_clients['xai'] = XAIClient(api_key=api_key, config=ai_providers['xai'])
        
        # Set default client
        self.default_client = self.ai_clients.get('openai') or self.ai_clients.get('xai')
        
        if not self.default_client:
            raise RuntimeError("No AI client available for reasoning")
        
        self.logger.info(f"ReasonerAgent initialized with {len(self.ai_clients)} AI clients")
    
    async def _cleanup_agent(self) -> None:
        """Clean up reasoner-specific resources."""
        # Clean up AI clients if needed
        for client in self.ai_clients.values():
            if hasattr(client, 'close'):
                await client.close()
        
        self.ai_clients.clear()
        self.logger.info("ReasonerAgent cleanup completed")
    
    async def _process_task_impl(self, task: ResearchAction) -> Dict[str, Any]:
        """
        Process a reasoning task.
        
        Args:
            task: Research task to process
            
        Returns:
            Dict[str, Any]: Reasoning results
        """
        action = task.action
        payload = task.payload
        
        if action == 'plan_research':
            return await self._plan_research(payload)
        elif action == 'analyze_information':
            return await self._analyze_information(payload)
        elif action == 'synthesize_results':
            return await self._synthesize_results(payload)
        elif action == 'chain_of_thought':
            return await self._chain_of_thought(payload)
        elif action == 'summarize_content':
            return await self._summarize_content(payload)
        elif action == 'extract_insights':
            return await self._extract_insights(payload)
        elif action == 'compare_sources':
            return await self._compare_sources(payload)
        elif action == 'evaluate_credibility':
            return await self._evaluate_credibility(payload)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _plan_research(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a research plan.
        
        Args:
            payload: Research parameters
            
        Returns:
            Dict[str, Any]: Research plan
        """
        query = payload.get('query', '')
        context = payload.get('context', {})
        
        if not query:
            raise ValueError("Query is required for research planning")
        
        # Create research planning prompt
        prompt = f"""
        Please create a comprehensive research plan for the following query:
        
        Query: {query}
        
        Context: {json.dumps(context, indent=2)}
        
        Please provide:
        1. Research objectives
        2. Key areas to investigate
        3. Specific questions to answer
        4. Information sources to consult
        5. Expected outcomes
        
        Format your response as a structured plan.
        """
        
        # Get AI response
        response = await self._get_ai_response(prompt)
        
        # Parse the response into structured format
        plan = self._parse_research_plan(response)
        
        return {
            'query': query,
            'plan': plan,
            'raw_response': response,
            'planning_model': self.default_model
        }
    
    async def _analyze_information(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze information and provide insights.
        
        Args:
            payload: Analysis parameters
            
        Returns:
            Dict[str, Any]: Analysis results
        """
        query = payload.get('query', '')
        context = payload.get('context', {})
        search_results = context.get('search_results', [])
        
        if not search_results:
            raise ValueError("Search results are required for analysis")
        
        # Prepare content for analysis
        content = self._prepare_content_for_analysis(search_results)
        
        # Create analysis prompt
        prompt = f"""
        Please analyze the following information related to the query: {query}
        
        Content to analyze:
        {content}
        
        Please provide:
        1. Key findings and insights
        2. Main themes and patterns
        3. Important facts and statistics
        4. Contradictions or inconsistencies
        5. Gaps in information
        6. Reliability assessment
        
        Format your response as a structured analysis.
        """
        
        # Get AI response
        response = await self._get_ai_response(prompt)
        
        # Parse the response
        analysis = self._parse_analysis(response)
        
        return {
            'query': query,
            'analysis': analysis,
            'sources_analyzed': len(search_results),
            'raw_response': response,
            'analysis_model': self.default_model
        }
    
    async def _synthesize_results(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synthesize research results into a comprehensive response.
        
        Args:
            payload: Synthesis parameters
            
        Returns:
            Dict[str, Any]: Synthesized results
        """
        query = payload.get('query', '')
        context = payload.get('context', {})
        
        # Gather all available information
        search_results = context.get('search_results', [])
        reasoning_output = context.get('reasoning_output', '')
        execution_results = context.get('execution_results', [])
        
        # Prepare synthesis prompt
        prompt = f"""
        Please synthesize the following research information into a comprehensive response for the query: {query}
        
        Search Results:
        {self._prepare_content_for_analysis(search_results)}
        
        Previous Analysis:
        {reasoning_output}
        
        Execution Results:
        {json.dumps(execution_results, indent=2)}
        
        Please provide:
        1. A comprehensive answer to the original query
        2. Key supporting evidence
        3. Multiple perspectives on the topic
        4. Practical implications
        5. Recommendations for further research
        6. Source citations
        
        Format your response as a well-structured synthesis.
        """
        
        # Get AI response
        response = await self._get_ai_response(prompt)
        
        # Parse the response
        synthesis = self._parse_synthesis(response)
        
        return {
            'query': query,
            'synthesis': synthesis,
            'sources_used': len(search_results),
            'raw_response': response,
            'synthesis_model': self.default_model
        }
    
    async def _chain_of_thought(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform chain of thought reasoning.
        
        Args:
            payload: Reasoning parameters
            
        Returns:
            Dict[str, Any]: Reasoning chain
        """
        query = payload.get('query', '')
        context = payload.get('context', {})
        
        prompt = f"""
        Please think through this problem step by step using chain of thought reasoning:
        
        Query: {query}
        Context: {json.dumps(context, indent=2)}
        
        Please:
        1. Break down the problem into components
        2. Analyze each component systematically
        3. Draw logical connections
        4. Reach well-reasoned conclusions
        5. Identify assumptions and limitations
        
        Show your reasoning process clearly.
        """
        
        response = await self._get_ai_response(prompt)
        
        return {
            'query': query,
            'reasoning_chain': response,
            'reasoning_model': self.default_model
        }
    
    async def _summarize_content(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize content."""
        content = payload.get('content', '')
        max_length = payload.get('max_length', 500)
        
        if not content:
            raise ValueError("Content is required for summarization")
        
        prompt = f"""
        Please provide a concise summary of the following content (max {max_length} words):
        
        Content:
        {content}
        
        Summary:
        """
        
        response = await self._get_ai_response(prompt)
        
        return {
            'original_length': len(content),
            'summary': response,
            'summary_length': len(response),
            'compression_ratio': len(response) / len(content) if content else 0
        }
    
    async def _extract_insights(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key insights from content."""
        content = payload.get('content', '')
        
        prompt = f"""
        Please extract key insights from the following content:
        
        Content:
        {content}
        
        Provide:
        1. Top 5 key insights
        2. Important trends or patterns
        3. Surprising findings
        4. Actionable recommendations
        """
        
        response = await self._get_ai_response(prompt)
        
        return {
            'content_analyzed': len(content),
            'insights': response,
            'extraction_model': self.default_model
        }
    
    async def _compare_sources(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Compare multiple sources."""
        sources = payload.get('sources', [])
        
        if len(sources) < 2:
            raise ValueError("At least 2 sources are required for comparison")
        
        prompt = f"""
        Please compare the following sources:
        
        {json.dumps(sources, indent=2)}
        
        Provide:
        1. Agreements between sources
        2. Disagreements or contradictions
        3. Unique information from each source
        4. Credibility assessment
        5. Overall reliability ranking
        """
        
        response = await self._get_ai_response(prompt)
        
        return {
            'sources_compared': len(sources),
            'comparison': response,
            'comparison_model': self.default_model
        }
    
    async def _evaluate_credibility(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate source credibility."""
        sources = payload.get('sources', [])
        
        prompt = f"""
        Please evaluate the credibility of the following sources:
        
        {json.dumps(sources, indent=2)}
        
        For each source, assess:
        1. Authority and expertise
        2. Objectivity and bias
        3. Currency and timeliness
        4. Accuracy and reliability
        5. Overall credibility score (1-10)
        """
        
        response = await self._get_ai_response(prompt)
        
        return {
            'sources_evaluated': len(sources),
            'credibility_assessment': response,
            'evaluation_model': self.default_model
        }
    
    async def _get_ai_response(self, prompt: str) -> str:
        """
        Get response from AI client.
        
        Args:
            prompt: Input prompt
            
        Returns:
            str: AI response
        """
        if not self.default_client:
            raise RuntimeError("No AI client available")
        
        try:
            # Create a simple message format
            messages = [{"role": "user", "content": prompt}]
            
            # Get response (simplified - actual implementation depends on client interface)
            response = await self.default_client.generate_response(
                messages=messages,
                max_tokens=2000,
                temperature=self.temperature
            )
            
            return response.get('content', '') if isinstance(response, dict) else str(response)
            
        except Exception as e:
            self.logger.error(f"AI response generation failed: {e}")
            return f"Error generating response: {str(e)}"
    
    def _prepare_content_for_analysis(self, search_results: List[Dict[str, Any]]) -> str:
        """
        Prepare search results for analysis.
        
        Args:
            search_results: List of search results
            
        Returns:
            str: Formatted content
        """
        content_parts = []
        
        for i, result in enumerate(search_results[:10]):  # Limit to 10 results
            title = result.get('title', 'No title')
            url = result.get('url', '')
            content = result.get('content', '')
            source = result.get('source', 'Unknown')
            
            content_parts.append(f"""
            Result {i+1}:
            Title: {title}
            Source: {source}
            URL: {url}
            Content: {content[:500]}...
            """)
        
        return '\n'.join(content_parts)
    
    def _parse_research_plan(self, response: str) -> Dict[str, Any]:
        """Parse research plan from AI response."""
        # Simple parsing - in production, you'd use more sophisticated parsing
        return {
            'raw_plan': response,
            'objectives': self._extract_section(response, 'objectives'),
            'key_areas': self._extract_section(response, 'key areas'),
            'questions': self._extract_section(response, 'questions'),
            'sources': self._extract_section(response, 'sources'),
            'outcomes': self._extract_section(response, 'outcomes')
        }
    
    def _parse_analysis(self, response: str) -> Dict[str, Any]:
        """Parse analysis from AI response."""
        return {
            'raw_analysis': response,
            'key_findings': self._extract_section(response, 'findings'),
            'themes': self._extract_section(response, 'themes'),
            'facts': self._extract_section(response, 'facts'),
            'contradictions': self._extract_section(response, 'contradictions'),
            'gaps': self._extract_section(response, 'gaps'),
            'reliability': self._extract_section(response, 'reliability')
        }
    
    def _parse_synthesis(self, response: str) -> Dict[str, Any]:
        """Parse synthesis from AI response."""
        return {
            'raw_synthesis': response,
            'answer': self._extract_section(response, 'answer'),
            'evidence': self._extract_section(response, 'evidence'),
            'perspectives': self._extract_section(response, 'perspectives'),
            'implications': self._extract_section(response, 'implications'),
            'recommendations': self._extract_section(response, 'recommendations'),
            'citations': self._extract_section(response, 'citations')
        }
    
    def _extract_section(self, text: str, section_name: str) -> str:
        """Extract a section from structured text."""
        # Simple section extraction - in production, you'd use more sophisticated parsing
        pattern = rf'{section_name}[:\s]*\n(.*?)(?=\n\d+\.|$)'
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else ''

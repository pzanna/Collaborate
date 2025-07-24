"""
Planning Agent for research tasks.

This module provides the Planning Agent that handles planning, analysis, reasoning,
and synthesis tasks for the research system.
"""

import asyncio
import json
import re
from typing import Any, Dict, List

from ..ai_clients.openai_client import OpenAIClient
from ..ai_clients.xai_client import XAIClient
from ..config.config_manager import ConfigManager
from ..mcp.protocols import ResearchAction
from .base_agent import BaseAgent


class PlanningAgent(BaseAgent):
    """
    Planning Agent for planning, analysis and synthesis tasks.

    This agent handles:
    - Research planning and strategy
    - Information analysis
    - Research plan generation
    - Result synthesis
    - Chain of thought reasoning
    - Content summarization
    """

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the Planning Agent.

        Args:
            config_manager: Configuration manager instance
        """
        super().__init__("planning", config_manager)

        # AI clients
        self.ai_clients = {}

        # Planning and reasoning configuration
        self.default_model = "gpt - 4"
        self.max_context_length = 8000
        self.temperature = 0.7

        self.logger.info("PlanningAgent initialized")

    def _get_capabilities(self) -> List[str]:
        """Get planning agent capabilities."""
        return [
            "plan_research",
            "analyze_information",
            "synthesize_results",
            "chain_of_thought",
            "summarize_content",
            "extract_insights",
            "compare_sources",
            "evaluate_credibility",
        ]

    async def _initialize_agent(self) -> None:
        """Initialize planning - specific resources."""
        # Initialize AI clients
        ai_providers = self.config.config.ai_providers

        # Initialize OpenAI client
        if "openai" in ai_providers:
            api_key = self.config.get_api_key("openai")
            self.ai_clients["openai"] = OpenAIClient(
                api_key=api_key, config=ai_providers["openai"]
            )

        # Initialize XAI client
        if "xai" in ai_providers:
            api_key = self.config.get_api_key("xai")
            self.ai_clients["xai"] = XAIClient(
                api_key=api_key, config=ai_providers["xai"]
            )

        # Set default client
        self.default_client = self.ai_clients.get("openai") or self.ai_clients.get(
            "xai"
        )

        if not self.default_client:
            raise RuntimeError("No AI client available for planning")

        self.logger.info(
            f"Planning Agent initialized with {len(self.ai_clients)} AI clients"
        )

    async def _cleanup_agent(self) -> None:
        """Clean up planning - specific resources."""
        # Clean up AI clients if needed
        for client in self.ai_clients.values():
            if hasattr(client, "close"):
                await client.close()

        self.ai_clients.clear()
        self.logger.info("Planning Agent cleanup completed")

    async def _process_task_impl(self, task: ResearchAction) -> Dict[str, Any]:
        """
        Process a planning task.

        Args:
            task: Research task to process

        Returns:
            Dict[str, Any]: Planning results
        """
        action = task.action
        payload = task.payload

        if action == "plan_research":
            return await self._plan_research(payload)
        elif action == "analyze_information":
            return await self._analyze_information(payload)
        elif action == "synthesize_results":
            return await self._synthesize_results(payload)
        elif action == "chain_of_thought":
            return await self._chain_of_thought(payload)
        elif action == "summarize_content":
            return await self._summarize_content(payload)
        elif action == "extract_insights":
            return await self._extract_insights(payload)
        elif action == "compare_sources":
            return await self._compare_sources(payload)
        elif action == "evaluate_credibility":
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
        query = payload.get("query", "")
        context = payload.get("context", {})

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

        Format your response in JSON with the following structure:
        {{
            "objectives": ["Objective 1", "Objective 2"],
            "key_areas": ["Area 1", "Area 2"],
            "questions": ["Question 1", "Question 2"],
            "sources": ["Source 1", "Source 2"],
            "outcomes": ["Outcome 1", "Outcome 2"]
        }}
        Please be thorough and consider all relevant aspects of the research topic.
        If you need to make assumptions, please state them clearly.
        """

        # Get AI response
        response = await self._get_ai_response(prompt)

        # Parse the response into structured format
        plan = self._parse_research_plan(response)

        return {
            "query": query,
            "plan": plan,
            "raw_response": response,
            "planning_model": self.default_model,
        }

    async def _analyze_information(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze information and provide insights.

        Args:
            payload: Analysis parameters

        Returns:
            Dict[str, Any]: Analysis results
        """
        query = payload.get("query", "")
        context = payload.get("context", {})
        search_results = context.get("search_results", [])

        # If no search results available, provide analysis based on available context
        if not search_results:
            self.logger.info(
                "No search results available for analysis, proceeding with general knowledge"
            )
            # Use general knowledge to provide analysis
            prompt = f"""
            Please provide a comprehensive analysis of the topic: {query}

            Based on your knowledge, please provide:
            1. Key concepts and definitions
            2. Main aspects and considerations
            3. Important facts and background information
            4. Current trends and developments
            5. Potential challenges and opportunities
            6. Recommended areas for further research

            Please be thorough and provide actionable insights even without specific search results.
            """

            # Get AI response
            response = await self._get_ai_response(prompt)

            return {
                "query": query,
                "analysis": {
                    "type": "knowledge_based",
                    "findings": response,
                    "source": "general_knowledge",
                    "confidence": "medium",
                },
                "raw_response": response,
                "analysis_model": self.default_model,
            }

        # Prepare content for analysis with search results
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
            "query": query,
            "analysis": analysis,
            "sources_analyzed": len(search_results),
            "raw_response": response,
            "analysis_model": self.default_model,
        }

    async def _synthesize_results(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synthesize research results into a comprehensive response.

        Args:
            payload: Synthesis parameters

        Returns:
            Dict[str, Any]: Synthesized results
        """
        query = payload.get("query", "")
        context = payload.get("context", {})

        # Gather all available information
        search_results = context.get("search_results", [])
        reasoning_output = context.get("reasoning_output", "")
        execution_results = context.get("execution_results", [])

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

        Format your response as a well - structured synthesis.
        """

        # Get AI response
        response = await self._get_ai_response(prompt)

        # Parse the response
        synthesis = self._parse_synthesis(response)

        return {
            "query": query,
            "synthesis": synthesis,
            "sources_used": len(search_results),
            "raw_response": response,
            "synthesis_model": self.default_model,
        }

    async def _chain_of_thought(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform chain of thought reasoning.

        Args:
            payload: Reasoning parameters

        Returns:
            Dict[str, Any]: Reasoning chain
        """
        query = payload.get("query", "")
        context = payload.get("context", {})

        prompt = f"""
        Please think through this problem step by step using chain of thought reasoning:

        Query: {query}
        Context: {json.dumps(context, indent=2)}

        Please:
        1. Break down the problem into components
        2. Analyze each component systematically
        3. Draw logical connections
        4. Reach well - reasoned conclusions
        5. Identify assumptions and limitations

        Show your reasoning process clearly.
        """

        response = await self._get_ai_response(prompt)

        return {
            "query": query,
            "reasoning_chain": response,
            "reasoning_model": self.default_model,
        }

    async def _summarize_content(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize content."""
        content = payload.get("content", "")
        max_length = payload.get("max_length", 500)

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
            "original_length": len(content),
            "summary": response,
            "summary_length": len(response),
            "compression_ratio": len(response) / len(content) if content else 0,
        }

    async def _extract_insights(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key insights from content."""
        content = payload.get("content", "")

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
            "content_analyzed": len(content),
            "insights": response,
            "extraction_model": self.default_model,
        }

    async def _compare_sources(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Compare multiple sources."""
        sources = payload.get("sources", [])

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
            "sources_compared": len(sources),
            "comparison": response,
            "comparison_model": self.default_model,
        }

    async def _evaluate_credibility(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate source credibility."""
        sources = payload.get("sources", [])

        prompt = f"""
        Please evaluate the credibility of the following sources:

        {json.dumps(sources, indent=2)}

        For each source, assess:
        1. Authority and expertise
        2. Objectivity and bias
        3. Currency and timeliness
        4. Accuracy and reliability
        5. Overall credibility score (1 - 10)
        """

        response = await self._get_ai_response(prompt)

        return {
            "sources_evaluated": len(sources),
            "credibility_assessment": response,
            "evaluation_model": self.default_model,
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
            # Get response using the correct method name
            # The AI client expects string parameters, not Message objects
            # Use run_in_executor to handle the synchronous AI client call
            import asyncio

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: self.default_client.get_response(user_message=prompt)
            )

            return str(response)

        except Exception as e:
            self.logger.error(f"AI response generation failed: {e}")
            return f"Error generating response: {str(e)}"

    def _prepare_content_for_analysis(
        self, search_results: List[Dict[str, Any]]
    ) -> str:
        """
        Prepare search results for analysis.

        Args:
            search_results: List of search results

        Returns:
            str: Formatted content
        """
        content_parts = []

        for i, result in enumerate(search_results[:10]):  # Limit to 10 results
            title = result.get("title", "No title")
            url = result.get("url", "")
            content = result.get("content", "")
            source = result.get("source", "Unknown")

            content_parts.append(
                f"""
            Result {i + 1}:
            Title: {title}
            Source: {source}
            URL: {url}
            Content: {content[:500]}...
            """
            )

        return "\n".join(content_parts)

    def _parse_research_plan(self, response: str) -> Dict[str, Any]:
        """Parse research plan from AI response."""
        try:
            # Try to extract JSON from the response
            json_match = re.search(
                r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", response, re.DOTALL
            )
            if json_match:
                json_str = json_match.group(0)
                plan_json = json.loads(json_str)

                # Return the parsed JSON structure with the raw response
                return {
                    "raw_plan": response,
                    "objectives": plan_json.get("objectives", []),
                    "key_areas": plan_json.get("key_areas", []),
                    "questions": plan_json.get("questions", []),
                    "sources": plan_json.get("sources", []),
                    "outcomes": plan_json.get("outcomes", []),
                }
            else:
                # Fallback to text extraction if JSON parsing fails
                self.logger.warning(
                    "No JSON found in response, falling back to text extraction"
                )
                return {
                    "raw_plan": response,
                    "objectives": self._extract_section_as_list(response, "objectives"),
                    "key_areas": self._extract_section_as_list(response, "key areas"),
                    "questions": self._extract_section_as_list(response, "questions"),
                    "sources": self._extract_section_as_list(response, "sources"),
                    "outcomes": self._extract_section_as_list(response, "outcomes"),
                }
        except json.JSONDecodeError as e:
            self.logger.warning(
                f"JSON parsing failed: {e}, falling back to text extraction"
            )
            # Fallback to text extraction
            return {
                "raw_plan": response,
                "objectives": self._extract_section_as_list(response, "objectives"),
                "key_areas": self._extract_section_as_list(response, "key areas"),
                "questions": self._extract_section_as_list(response, "questions"),
                "sources": self._extract_section_as_list(response, "sources"),
                "outcomes": self._extract_section_as_list(response, "outcomes"),
            }
        except Exception as e:
            self.logger.error(f"Error parsing research plan: {e}")
            return {
                "raw_plan": response,
                "objectives": [],
                "key_areas": [],
                "questions": [],
                "sources": [],
                "outcomes": [],
            }

    def _parse_analysis(self, response: str) -> Dict[str, Any]:
        """Parse analysis from AI response."""
        return {
            "raw_analysis": response,
            "key_findings": self._extract_section(response, "findings"),
            "themes": self._extract_section(response, "themes"),
            "facts": self._extract_section(response, "facts"),
            "contradictions": self._extract_section(response, "contradictions"),
            "gaps": self._extract_section(response, "gaps"),
            "reliability": self._extract_section(response, "reliability"),
        }

    def _parse_synthesis(self, response: str) -> Dict[str, Any]:
        """Parse synthesis from AI response."""
        return {
            "raw_synthesis": response,
            "answer": self._extract_section(response, "answer"),
            "evidence": self._extract_section(response, "evidence"),
            "perspectives": self._extract_section(response, "perspectives"),
            "implications": self._extract_section(response, "implications"),
            "recommendations": self._extract_section(response, "recommendations"),
            "citations": self._extract_section(response, "citations"),
        }

    def _extract_section(self, text: str, section_name: str) -> str:
        """Extract a section from structured text."""
        # Handle different section formats
        patterns = [
            # Markdown headers with numbers: ### 1. Research Objectives
            rf"#{1,4}\s*\d+\.\s*{re.escape(section_name)}[^\n]*\n(.*?)(?=#{1,4}\s*\d+\.|$)",
            # Markdown headers without numbers: ### Research Objectives
            rf"#{1,4}\s*{re.escape(section_name)}[^\n]*\n(.*?)(?=#{1,4}\s*\w+|$)",
            # Colon format: Research Objectives:
            rf"{re.escape(section_name)}[:\s]*\n(.*?)(?=\n\d+\.|#{1,4}|$)",
            # Generic pattern
            rf"{re.escape(section_name)}[:\s]*\n(.*?)(?=\n[A - Z][^a - z]*[:|\n]|$)",
        ]

        # Map different variations of section names
        section_variations = {
            "objectives": ["objectives", "research objectives"],
            "key areas": ["key areas", "key areas to investigate"],
            "questions": [
                "questions",
                "specific questions",
                "specific questions to answer",
            ],
            "sources": [
                "sources",
                "information sources",
                "information sources to consult",
            ],
            "outcomes": ["outcomes", "expected outcomes"],
        }

        # Get all possible names for this section
        possible_names = section_variations.get(section_name.lower(), [section_name])

        for name in possible_names:
            for pattern in patterns:
                # Create the pattern with the current name variation
                current_pattern = pattern.replace(
                    re.escape(section_name), re.escape(name)
                )
                match = re.search(current_pattern, text, re.IGNORECASE | re.DOTALL)
                if match:
                    content = match.group(1).strip()
                    # Clean up the content
                    content = re.sub(
                        r"^-+$", "", content, flags=re.MULTILINE
                    )  # Remove separator lines
                    content = re.sub(
                        r"\n\s*\n\s*\n", "\n\n", content
                    )  # Remove excessive newlines
                    return content.strip()

        return ""

    def _extract_section_as_list(self, text: str, section_name: str) -> List[str]:
        """Extract a section from structured text and return as list."""
        content = self._extract_section(text, section_name)
        if not content:
            return []

        # Split content into items
        items = []
        lines = content.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Remove bullet points, numbers, dashes, etc.
            line = re.sub(r"^[-•*\d+\.)\s]+", "", line).strip()

            if line:
                items.append(line)

        return items


if __name__ == "__main__":
    import os
    import sys

    # Add the project root to the Python path
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    sys.path.insert(0, project_root)

    async def main():
        """Start the planning agent."""
        from ..config.config_manager import ConfigManager

        # Initialize config manager
        config_manager = ConfigManager()

        agent = PlanningAgent(config_manager)
        try:
            await agent.start()
            # Keep the agent running
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("Shutting down planning agent...")
        finally:
            await agent.stop()

    asyncio.run(main())

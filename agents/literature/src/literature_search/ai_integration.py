"""
AI integration module for search term extraction and optimization.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AIIntegration:
    """Handles AI-powered search term extraction and optimization."""
    
    def __init__(self, websocket, agent_id: str):
        """Initialize AI integration with MCP websocket connection."""
        self.websocket = websocket
        self.agent_id = agent_id
        self.pending_responses: Dict[str, asyncio.Future] = {}
    
    async def extract_search_terms_from_research_plan(self, research_plan) -> List[str]:
        """
        Extract optimized search terms from research plan using AI agent via MCP.
        
        Args:
            research_plan: AI-generated research plan with objectives, questions, etc. (can be dict or str)
            
        Returns:
            List of optimized search terms for academic databases
        """
        logger.info(f"Extracting search terms from research plan: {research_plan}")

        # Create research planning prompt
        prompt = (
            "You are a scientific search-strategy assistant. When given a research plan, "
            "reply ONLY with VALID JSON matching the schema in the instruction, "
            "containing highly targeted literature-search phrases ready for PubMed / "
            "Web of Science / Google Scholar. Do not add commentary or markdown.\n\n"
            f"Plan: {research_plan}\n\n"
            "Format your response in JSON with the following structure:\n"
            "{\n"
            '    "topic 1": ["Search String 1", "Search String 2", ...],\n'
            '    "topic 2": ["Search String 1", "Search String 2", ...],\n'
            '    "topic 3": ["Search String 1", "Search String 2", ...],\n'
            "    ...\n"
            "}\n"
            "Ensure the search strings are specific, relevant, and suitable for "
            "academic databases.\n"
        )

        # Send request to AI agent via MCP for search term optimization
        optimization_request = {
            "type": "research_action",
            "data": {
                "task_id": f"search_term_optimization_{uuid.uuid4().hex[:8]}",
                "context_id": f"literature_ai_optimization",
                "agent_type": "ai_service",  # Use correct agent type for AI service
                "action": "ai_chat_completion",  # Use the actual AI service action
                "payload": {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert research assistant specializing in academic literature search optimization. Extract 3-5 highly targeted search terms from the provided research plan that will be most effective for finding relevant academic papers in databases like PubMed, arXiv, Semantic Scholar, and CrossRef."
                        },
                        {
                            "role": "user", 
                            "content": prompt
                        }
                    ],
                    "max_tokens": 200,
                    "temperature": 0.3
                }
            },
            "client_id": self.agent_id,
            "timestamp": datetime.now().isoformat()
        }
        
        if not self.websocket:
            logger.warning("MCP connection not available, unable to perform a search")
            fallback_query = (research_plan[:100] if isinstance(research_plan, str) else str(research_plan)[:100])
            return [fallback_query]
        
        # Send the request
        task_id = optimization_request["data"]["task_id"]
        await self.websocket.send(json.dumps(optimization_request))
        logger.info("Search term optimization request sent to AI agent via MCP")
        
        # Wait for response using Future-based approach
        try:
            # Create future for this request
            future = asyncio.Future()
            self.pending_responses[task_id] = future
            
            # Wait for response with timeout
            response_data = await asyncio.wait_for(future, timeout=30.0)
            
            if (response_data.get("type") == "task_result" and 
                response_data.get("task_id") == task_id):
                
                if response_data.get("status") == "completed":
                    chat_response = response_data.get("result", {})
                    logger.info(f"Raw AI result received: {chat_response}")
                
                    if "choices" in chat_response and len(chat_response["choices"]) > 0:
                        choice = chat_response["choices"][0]

                        if "message" in choice and "content" in choice["message"]:
                            content = choice["message"]["content"]
                            logger.info(f"Search topics and terms extracted: {content}")
                            logger.info(f"Extracted content from OpenAI response: {len(content)} chars")
                            
                            # Parse the JSON response to extract search terms
                            try:
                                # Try to parse as JSON
                                search_topics_dict = json.loads(content)
                                logger.info(f"Parsed search topics: {search_topics_dict}")
                                
                                # Extract all search terms from the dictionary structure
                                search_terms = []
                                if search_topics_dict:
                                    for topic, terms in search_topics_dict.items():
                                        if isinstance(terms, list):
                                            search_terms.extend(terms)
                                        else:
                                            search_terms.append(str(terms))
                                
                                logger.info(f"Extracted {len(search_terms)} search terms: {search_terms}")
                                return search_terms
                                
                            except json.JSONDecodeError as e:
                                logger.warning(f"Failed to parse AI response as JSON: {e}")
                                # Return raw content as single search term
                                return [content.strip()]

            logger.warning("No valid search terms returned from AI agent")
            return []
            
        except asyncio.TimeoutError:
            logger.warning("Timeout waiting for AI agent response")
            return []
        except Exception as e:
            logger.error(f"Error extracting search terms from research plan: {e}")
            return []
        finally:
            # Clean up pending response
            self.pending_responses.pop(task_id, None)
            logger.info("Pending response cleaned up for search term optimization request")
    
    def handle_task_result(self, data: Dict[str, Any]) -> bool:
        """Handle task result responses for pending AI requests."""
        if data.get("type") == "task_result":
            task_id = data.get("task_id")
            if task_id in self.pending_responses:
                future = self.pending_responses.pop(task_id)
                if not future.done():
                    future.set_result(data)
                return True
        return False

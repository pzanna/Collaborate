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
    
    def __init__(self, websocket, agent_id: str, database_integration=None):
        """Initialize AI integration with MCP websocket connection."""
        self.websocket = websocket
        self.agent_id = agent_id
        self.pending_responses: Dict[str, asyncio.Future] = {}
        self.database_integration = database_integration
    
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
            "You are an expert scientific search-strategy assistant. "
            "When given a research plan in the variable `research_plan`, "
            "your task is to generate search strings for academic literature databases. "
            "Reply **only** with valid JSON in the following format:\n\n"

            "{\n"
            '  "Topic A": ["Search String 1", "Search String 2", ...],\n'
            '  "Topic B": ["Search String 1", "Search String 2", ...],\n'
            "  ...\n"
            "}\n\n"

            "Instructions:\n"
            "- For each high-level topic in the plan, generate 4-6 **concise**, **domain-specific** search queries.\n"
            "- Use terminology directly relevant to academic indexing in neuroscience, cell culture, or biomedical literature.\n"
            "- Prefer exact phrases in double quotes only when targeting specific concepts (e.g. `avian cerebral neurons`).\n"
            "- Avoid vague, overly generic, or blog-style terms such as `ingredient sourcing`, `budget constraints`, or `common household ingredients`.\n"
            "- Combine keywords intelligently using AND/OR when needed, but avoid overuse.\n"
            "- Ensure queries are optimised for scientific databases including PubMed, CORE, Semantic Scholar, CrossRef, and ArXiv.\n"
            "- Do not include any extra text, explanation, or markdown—only JSON.\n\n"

            "The generated queries should prioritise:\n"
            "- Scientific precision.\n"
            "- Methodological relevance.\n"
            "- Retrievability from academic databases.\n"
            "- Alignment with the goals and constraints of the research plan.\n\n"

            f"Plan: {research_plan}"
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
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert research assistant specializing in academic literature search optimization. Extract 3-4 highly targeted search terms from the provided research plan that will be most effective for finding relevant academic papers in databases like PubMed, arXiv, Semantic Scholar, and CrossRef. You have access to Google search to find recent research and validate terminology."
                        },
                        {
                            "role": "user", 
                            "content": prompt
                        }
                    ],
                    "tools": [
                        {
                            "type": "function",
                            "function": {
                                "name": "google_search",
                                "description": "Search the web using Google Custom Search to find recent research papers, validate scientific terminology, and discover current trends in research topics.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "query": {
                                            "type": "string",
                                            "description": "The search query to find relevant research and information"
                                        },
                                        "num_results": {
                                            "type": "integer",
                                            "description": "Number of search results to return (default: 10, max: 10)",
                                            "default": 10,
                                            "minimum": 1,
                                            "maximum": 10
                                        }
                                    },
                                    "required": ["query"]
                                }
                            }
                        }
                    ],
                    "tool_choice": "auto",
                    "max_tokens": 3000,
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
            response_data = await asyncio.wait_for(future, timeout=60.0)
            
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
    
    async def review_literature_results(self, plan, search_results) -> List[Dict[str, Any]]:
            """
            Review literature results using AI agent to filter and select most relevant papers.
            
            Args:
                plan: AI-generated research plan with objectives, questions, etc. (can be dict or str)
                search_results: List of literature records to review
                
            Returns:
                List of selected literature records in JSON format
            """
            logger.info(f"Review literature results: {search_results}")

            # Create research planning prompt
            prompt = (
                "I am conducting a literature review and have a structured research plan and a preliminary list of references.\n\n"

                "Your task is to act as a scientific research collaborator and perform a comprehensive expansion of the literature base.\n\n"

                "Input:\n"
                "1. A structured research plan (in JSON or plain text format), including:\n"
                "- Research questions and/or hypotheses\n"
                "- Research objectives and goals\n"
                "- Timeline or phases (if applicable)\n"
                "- Key thematic areas of investigation\n"
                "- Constraints (e.g., budget, data availability, species, technical limitations)\n"
                "2. A preliminary list of relevant literature I've already collected.\n\n"

                "Your responsibilities:\n\n"

                "Step 1: **Decompose the research plan**\n"
                "- Identify the major themes, variables, requirements, and outputs expected from the review.\n"
                "- Map each objective/question to the kind of literature or data needed to support it.\n\n"

                "Step 2: **Evaluate the preliminary literature**\n"
                "- Determine which parts of the research plan are already well-supported.\n"
                "- Identify missing or weakly supported areas where additional literature is needed.\n"
                "- Remove any literature that is not relevant or superfluous.\n"
                "- Note any methodological or domain-specific gaps (e.g., no functional validation, missing comparative analysis, outdated protocols, etc.)\n\n"

                "Step 3: **Expand the literature**\n"
                "- Find 10-15 additional highly relevant papers, protocols, or datasets.\n"
                "- Prioritise diversity: experimental methods, review articles, protocols, comparative studies, economic analyses, etc.\n"
                "- Ensure that every key area in the research plan is supported by at least one citation.\n"
                "- Include only credible and technically appropriate sources (e.g., PubMed, ArXiv, CORE, Springer, PLOS, major journals).\n\n"

                "Step 4: **Return outputs in the following format**\n"
                "1. An updated, unified list of papers in the same format as my original list (JSON only).\n"
                "- Add a 'discussion' field to the JSON response that includes:\n"
                "  - A summary of the key findings from the literature\n"
                "  - An analysis of how these findings relate to the research plan\n"
                "  - Any gaps that the original literature list did not address\n"
                "  - The items that you removed or added and the reasons why those changes were made.\n"
                "- Do not include any other commentary, just the JSON response.\n\n"

                "Instructions:\n"
                "- Be concise but technically detailed.\n"
                "- Use Markdown formatting, with tables and sections for clarity.\n"
                "- Assume the goal is to use this output directly in a PhD-level review or grant proposal.\n\n"

                f"Research Plan: {plan}\n\n"

                f"Literature: {search_results}\n\n"
            )


            # Send request to AI agent via MCP for search term optimization
            optimization_request = {
                "type": "research_action",
                "data": {
                    "task_id": f"literature_review_{uuid.uuid4().hex[:8]}",
                    "context_id": f"literature_ai_optimization",
                    "agent_type": "ai_service",  # Use correct agent type for AI service
                    "action": "ai_chat_completion",  # Use the actual AI service action
                    "payload": {
                        "provider": "openai",
                        "model": "gpt-4o-mini",
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are an expert research assistant specializing in academic literature review and analysis. You can search the web to find additional relevant papers, validate research gaps, and discover recent publications that complement the existing literature collection."
                            },
                            {
                                "role": "user", 
                                "content": prompt
                            }
                        ],
                        "tools": [
                            {
                                "type": "function",
                                "function": {
                                    "name": "google_search",
                                    "description": "Search the web using Google Custom Search to find recent research papers, discover additional relevant studies, and fill gaps in the literature collection.",
                                    "parameters": {
                                        "type": "object",
                                        "properties": {
                                            "query": {
                                                "type": "string",
                                                "description": "The search query to find relevant research papers and studies"
                                            },
                                            "num_results": {
                                                "type": "integer",
                                                "description": "Number of search results to return (default: 10, max: 10)",
                                                "default": 10,
                                                "minimum": 1,
                                                "maximum": 10
                                            }
                                        },
                                        "required": ["query"]
                                    }
                                }
                            }
                        ],
                        "tool_choice": "auto",
                        "max_tokens": 3000,
                        "temperature": 0.3
                    }
                },
                "client_id": self.agent_id,
                "timestamp": datetime.now().isoformat()
            }
            
            if not self.websocket:
                logger.warning("MCP connection not available, unable to perform a search")
                fallback_query = (search_results)
                return [fallback_query]
            
            # Send the request
            task_id = optimization_request["data"]["task_id"]
            await self.websocket.send(json.dumps(optimization_request))
            logger.info("Review literature request sent to AI agent via MCP")
            
            # Wait for response using Future-based approach
            try:
                # Create future for this request
                future = asyncio.Future()
                self.pending_responses[task_id] = future
                
                # Wait for response with timeout
                response_data = await asyncio.wait_for(future, timeout=60.0)
                
                if (response_data.get("type") == "task_result" and 
                    response_data.get("task_id") == task_id):
                    
                    if response_data.get("status") == "completed":
                        chat_response = response_data.get("result", {})
                        logger.info(f"Raw AI result received: {chat_response}")
                    
                        if "choices" in chat_response and len(chat_response["choices"]) > 0:
                            choice = chat_response["choices"][0]

                            if "message" in choice and "content" in choice["message"]:
                                content = choice["message"]["content"]
                                logger.info(f"Literature review response: {content[:500]}...")
                                
                                # Try to parse JSON response
                                try:
                                    # Look for JSON content in the response
                                    import re
                                    json_match = re.search(r'\[.*\]', content, re.DOTALL)
                                    if json_match:
                                        json_str = json_match.group(0)
                                        parsed_articles = json.loads(json_str)
                                        if isinstance(parsed_articles, list):
                                            logger.info(f"Successfully parsed {len(parsed_articles)} articles from AI response")
                                            return parsed_articles
                                    
                                    # If no JSON array found, try parsing the whole content
                                    parsed_articles = json.loads(content)
                                    if isinstance(parsed_articles, list):
                                        logger.info(f"Successfully parsed {len(parsed_articles)} articles from AI response")
                                        return parsed_articles
                                    
                                except json.JSONDecodeError as e:
                                    logger.warning(f"Failed to parse AI response as JSON: {e}")
                                    logger.debug(f"Raw content: {content}")
                                
                                # If JSON parsing fails, return the first 10 search results as fallback
                                logger.warning("Using fallback: returning first 10 search results")
                                return search_results[:10] if isinstance(search_results, list) else []
                                    

                logger.warning("No valid literature list returned from AI agent")
                return []
                
            except asyncio.TimeoutError:
                logger.warning("Timeout waiting for AI agent response")
                return []
            except Exception as e:
                logger.error(f"Error reviewing literature: {e}")
                return []
            finally:
                # Clean up pending response
                self.pending_responses.pop(task_id, None)
                logger.info("Pending response cleaned up for literature review request")


    def handle_task_result(self, data: Dict[str, Any]) -> bool:
        """Handle task result responses for pending AI requests."""
        logger.info(f"🤖 AI integration received task result: type={data.get('type')}, task_id={data.get('task_id')}")
        logger.info(f"   Pending responses: {list(self.pending_responses.keys())}")
        
        if data.get("type") == "task_result":
            task_id = data.get("task_id")
            # Only handle task results that we're actually waiting for
            if task_id in self.pending_responses:
                future = self.pending_responses.pop(task_id)
                if not future.done():
                    future.set_result(data)
                    logger.info(f"✅ Successfully resolved AI future for task_id: {task_id}")
                    return True
                else:
                    logger.warning(f"⚠️ AI future already done for task_id: {task_id}")
                    return True  # We handled it, even if already done
            else:
                logger.warning(f"❌ No pending AI response found for task_id: {task_id}")
                return False  # We didn't handle this task result
        else:
            logger.debug(f"🔍 Non-task_result AI message: {data.get('type')}")
            return False  # We didn't handle this message
        return False

   
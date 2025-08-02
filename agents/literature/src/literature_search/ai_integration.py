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
                    "max_tokens": 500,
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
    
    async def review_literature_results(self, research_plan, search_results, plan_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Review the list of search results using AI agent via MCP.
        
        Args:
            research_plan: AI-generated research plan with objectives, questions, etc. (can be dict or str)
            search_results: List of SIMPLIFIED search results (already containing only id, title, abstract)
            plan_id: Optional plan ID to store reviewed results in database
            
        Returns:
            List of reviewed search results in the format [{"id": "...", "title": "...", "abstract": "..."}]
        """
        logger.info(f"Reviewing literature results for research plan")

        # The search_results are now already simplified with only id, title, abstract
        # No need to create simplified_results here as this is handled earlier in the workflow
        simplified_results = search_results  # Input is already simplified
        logger.info(f"Received {len(simplified_results)} simplified records for AI review")
        
        # Create research planning prompt
        prompt = (
            "You are a scientific literature expert. When given a research plan and a list of search results, "
            "reply ONLY with VALID JSON matching the schema in the instruction, "
            "containing a list in the JSON schema in the instructions, but ONLY including the articles from the search results that are relevant to the research plan. "
            "Do not add commentary or markdown. ONLY include items that were on the original list with matching information.\n\n"
            f"Plan: {research_plan}\n\n"
            "Format your response as a JSON array with the following structure:\n"
            "[\n"
            "  {\n"
            '    "id": "<ID>",\n'
            '    "title": "<Title>",\n'
            '    "abstract": "<Abstract>"\n'
            "  },\n"
            "  ...\n"
            "]\n"
            "Ensure to only include articles that are relevant to the research plan and suitable for "
            "academic research. Each article must have all three fields: id, title, and abstract.\n\n"
            f"Search Results: {simplified_results}\n\n"
        )

        # This request will be sent to the AI agent to review the search results
        # and return only the relevant articles based on the research plan
        search_review_request = {
            "type": "research_action",
            "data": {
                "task_id": f"search_results_{uuid.uuid4().hex[:8]}",
                "context_id": f"literature_ai_optimization",
                "agent_type": "ai_service",  # Use correct agent type for AI service
                "action": "ai_chat_completion",  # Use the actual AI service action
                "payload": {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert research assistant specializing in academic literature reviews. Review the provided research plan and the search results and determine the most relevant articles."
                        },
                        {
                            "role": "user", 
                            "content": prompt
                        }
                    ],
                    "max_tokens": 2000,
                    "temperature": 0.3
                }
            },
            "client_id": self.agent_id,
            "timestamp": datetime.now().isoformat()
        }
        
        # Retrieve the JSON string out of the initial_literature_results column from the research plan table in the database via the MCP connection

        if not self.websocket:
            logger.warning("MCP connection not available, unable to perform a search")
            fallback_results = (search_results)
            return [fallback_results]
        
        # Send the request
        task_id = search_review_request["data"]["task_id"]
        await self.websocket.send(json.dumps(search_review_request))
        logger.info("Search review request sent to AI agent via MCP")
        
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

                    # Parse the AI response to extract reviewed literature results
                    if "choices" in chat_response and len(chat_response["choices"]) > 0:
                        choice = chat_response["choices"][0]
                        if "message" in choice and "content" in choice["message"]:
                            content = choice["message"]["content"]
                            logger.info(f"Literature review content received: {content}")
                            logger.info(f"Extracted content from OpenAI response: {len(content)} chars")
                            
                            # Parse the JSON response to extract reviewed articles
                            try:
                                # Handle both single article and array formats
                                if content.strip().startswith('['):
                                    # Multiple articles in array format
                                    reviewed_articles = json.loads(content)
                                elif content.strip().startswith('{'):
                                    # Single article in object format
                                    single_article = json.loads(content)
                                    reviewed_articles = [single_article]
                                else:
                                    # Try to extract JSON from text
                                    reviewed_articles = json.loads(content)
                                
                                logger.info(f"Parsed {len(reviewed_articles)} reviewed articles from AI response")
                                
                                # Validate that the articles have required fields
                                validated_articles = []
                                for article in reviewed_articles:
                                    if isinstance(article, dict) and all(key in article for key in ["id", "title", "abstract"]):
                                        validated_articles.append(article)
                                    else:
                                        logger.warning(f"Invalid article format in AI response: {article}")
                                
                                logger.info(f"Validated {len(validated_articles)} articles with required fields")
                                
                                # Store reviewed results in database if plan_id is provided and database integration is available
                                logger.info(f"📊 JSON STORAGE CHECK - Reviewed Literature Results:")
                                logger.info(f"  ├─ plan_id: {plan_id}")
                                logger.info(f"  ├─ database_integration: {'✅ Available' if self.database_integration else '❌ None'}")
                                logger.info(f"  ├─ validated_articles: {len(validated_articles)} articles")
                                logger.info(f"  └─ articles_sample: {[{k: v[:50] + '...' if len(str(v)) > 50 else v for k, v in validated_articles[0].items()} if validated_articles else 'No articles']}")
                                
                                if plan_id and self.database_integration and validated_articles:
                                    logger.info(f"📤 INITIATING REVIEWED RESULTS STORAGE: {len(validated_articles)} articles → plan_id={plan_id}")
                                    try:
                                        storage_success = await self.database_integration.store_reviewed_literature_results(
                                            plan_id, validated_articles
                                        )
                                        if storage_success:
                                            logger.info(f"🎉 JSON STORAGE SUCCESS: {len(validated_articles)} reviewed articles stored in database")
                                            logger.info(f"   └─ Storage location: research_plans.reviewed_literature_results (plan_id={plan_id})")
                                        else:
                                            logger.error("💥 JSON STORAGE FAILED: store_reviewed_literature_results returned False")
                                    except Exception as e:
                                        logger.error(f"💥 JSON STORAGE EXCEPTION: {type(e).__name__}: {e}")
                                        logger.error(f"   └─ Failed to store reviewed articles for plan_id={plan_id}")
                                else:
                                    missing_conditions = []
                                    if not plan_id:
                                        missing_conditions.append("no plan_id")
                                    if not self.database_integration:
                                        missing_conditions.append("no database_integration")
                                    if not validated_articles:
                                        missing_conditions.append("no validated_articles")
                                    logger.warning(f"⚠️ SKIPPING REVIEWED RESULTS STORAGE: {', '.join(missing_conditions)}")
                                
                                return validated_articles
                                
                            except json.JSONDecodeError as e:
                                logger.warning(f"Failed to parse AI response as JSON: {e}")
                                logger.warning(f"Raw content: {content}")
                                # Return empty list if parsing fails
                                return []
                    
                    logger.warning("No valid content found in AI response")
                    return []
                else:
                    logger.warning(f"AI task failed with status: {response_data.get('status')}")
                    return []
            else:
                logger.warning(f"Unexpected response format: {response_data}")
                return []

        except asyncio.TimeoutError:
            logger.warning("Timeout waiting for AI agent response")
            return []
        except Exception as e:
            logger.error(f"Error reviewing literature results: {e}")
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

    async def test_review_literature_results(self, test_research_plan: str, test_search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Test function to validate the review_literature_results functionality.
        
        Args:
            test_research_plan: Sample research plan for testing
            test_search_results: Sample search results for testing
            
        Returns:
            Dict with test results and validation info
        """
        logger.info("Starting test of review_literature_results function")
        
        try:
            # Call the review function
            start_time = datetime.now()
            reviewed_results = await self.review_literature_results(
                research_plan=test_research_plan,
                search_results=test_search_results,
                plan_id="test_plan_123"  # Use test plan ID
            )
            end_time = datetime.now()
            
            # Validate the results
            validation_results = {
                "test_status": "completed",
                "execution_time_seconds": (end_time - start_time).total_seconds(),
                "input_count": len(test_search_results),
                "output_count": len(reviewed_results) if reviewed_results else 0,
                "output_format_valid": True,
                "required_fields_present": True,
                "errors": []
            }
            
            # Validate format
            if not isinstance(reviewed_results, list):
                validation_results["output_format_valid"] = False
                validation_results["errors"].append("Output is not a list")
            
            # Validate each article has required fields
            for i, article in enumerate(reviewed_results or []):
                if not isinstance(article, dict):
                    validation_results["output_format_valid"] = False
                    validation_results["errors"].append(f"Article {i} is not a dictionary")
                    continue
                    
                required_fields = ["id", "title", "abstract"]
                missing_fields = [field for field in required_fields if field not in article]
                if missing_fields:
                    validation_results["required_fields_present"] = False
                    validation_results["errors"].append(f"Article {i} missing fields: {missing_fields}")
            
            # Overall test result
            validation_results["test_passed"] = (
                validation_results["output_format_valid"] and 
                validation_results["required_fields_present"] and
                len(validation_results["errors"]) == 0
            )
            
            logger.info(f"Test completed: {validation_results}")
            return validation_results
            
        except Exception as e:
            logger.error(f"Test failed with exception: {e}")
            return {
                "test_status": "failed",
                "error": str(e),
                "test_passed": False
            }

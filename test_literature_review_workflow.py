#!/usr/bin/env python3
"""
Literature Review Workflow Test Script

This script demonstrates the complete literature review process in Eunice,
showing how the Research Manager coordinates with the Literature Search Agent
through the MCP protocol to execute a comprehensive literature search.

Usage:
    python test_literature_review_workflow.py

Requirements:
    - MCP Server running on ws://localhost:9000
    - Literature Search Agent running
    - Research Manager Agent running
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List
import websockets

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class LiteratureReviewWorkflowDemo:
    """Demonstrates the literature review workflow."""
    
    def __init__(self):
        self.mcp_server_url = "ws://localhost:9000"
        self.websocket = None
        self.client_id = "workflow_demo"
        
    async def connect_to_mcp(self):
        """Connect to MCP server."""
        try:
            logger.info(f"Connecting to MCP server at {self.mcp_server_url}")
            self.websocket = await websockets.connect(self.mcp_server_url)
            
            # Register as a test client
            registration = {
                "type": "gateway_register",
                "client_id": self.client_id,
                "client_type": "workflow_test",
                "capabilities": ["test_workflow"],
                "timestamp": datetime.now().isoformat()
            }
            
            await self.websocket.send(json.dumps(registration))
            logger.info("Connected to MCP server")
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            raise
    
    async def disconnect_from_mcp(self):
        """Disconnect from MCP server."""
        if self.websocket:
            await self.websocket.close()
            logger.info("Disconnected from MCP server")
    
    async def demonstrate_literature_review_workflow(self):
        """Demonstrate the complete literature review workflow."""
        try:
            logger.info("🚀 Starting Literature Review Workflow Demonstration")
            
            # Step 1: Create research request
            research_request = await self._create_research_request()
            
            # Step 2: Send to Research Manager for coordination
            research_manager_response = await self._delegate_to_research_manager(research_request)
            
            # Step 3: Monitor workflow progress
            await self._monitor_workflow_progress(research_manager_response)
            
            logger.info("✅ Literature Review Workflow Demonstration Complete")
            
        except Exception as e:
            logger.error(f"❌ Workflow demonstration failed: {e}")
            raise
    
    async def _create_research_request(self) -> Dict[str, Any]:
        """Create a sample research request for literature review."""
        research_request = {
            "task_id": str(uuid.uuid4()),
            "user_id": "demo_researcher",
            "project_id": "demo_project_001",
            "query": "machine learning applications in medical diagnosis accuracy improvement",
            "research_type": "literature_review",
            "parameters": {
                "search_depth": "comprehensive",
                "max_results": 100,
                "sources": ["semantic_scholar", "pubmed", "arxiv", "crossref"],
                "filters": {
                    "year_min": 2020,
                    "year_max": 2024,
                    "publication_types": ["journal_article", "review", "conference_paper"],
                    "languages": ["en"],
                    "open_access_only": False
                },
                "quality_requirements": {
                    "min_citation_count": 5,
                    "require_abstract": True,
                    "peer_reviewed_only": True
                }
            },
            "cost_settings": {
                "auto_approve_under": 1.00,  # Auto-approve costs under $1.00
                "max_allowed_cost": 5.00     # Maximum allowed cost
            },
            "delivery_preferences": {
                "format": "structured_json",
                "include_abstracts": True,
                "include_full_citations": True,
                "group_by_themes": True
            }
        }
        
        logger.info(f"📋 Created research request: {research_request['query']}")
        logger.info(f"   - Sources: {', '.join(research_request['parameters']['sources'])}")
        logger.info(f"   - Date range: {research_request['parameters']['filters']['year_min']}-{research_request['parameters']['filters']['year_max']}")
        logger.info(f"   - Max results: {research_request['parameters']['max_results']}")
        
        return research_request
    
    async def _delegate_to_research_manager(self, research_request: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate the research request to the Research Manager."""
        logger.info("📤 Delegating research request to Research Manager")
        
        # Create MCP message for research coordination
        mcp_message = {
            "type": "research_action",
            "data": {
                "jsonrpc": "2.0",
                "method": "task/execute",
                "params": {
                    "task_type": "coordinate_research",
                    "data": {
                        "query": research_request["query"],
                        "user_id": research_request["user_id"],
                        "project_id": research_request["project_id"],
                        "single_agent_mode": False,
                        "parameters": research_request["parameters"],
                        "cost_settings": research_request["cost_settings"]
                    }
                },
                "id": f"research_{research_request['task_id']}"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # In demo mode, we'll simulate the MCP communication
        logger.info("   🎭 Simulating MCP message transmission...")
        logger.info(f"   📨 Message type: {mcp_message['type']}")
        logger.info(f"   🎯 Method: {mcp_message['data']['method']}")
        logger.info(f"   📋 Task type: {mcp_message['data']['params']['task_type']}")
        
        # Simulate network transmission delay
        await asyncio.sleep(0.5)
        logger.info("✅ Research request sent to Research Manager via MCP")
        
        # Wait for acknowledgment
        response = await self._wait_for_response(research_request['task_id'])
        return response
    
    async def _monitor_workflow_progress(self, initial_response: Dict[str, Any]):
        """Monitor the workflow progress through its stages."""
        logger.info("📊 Monitoring Literature Review Workflow Progress")
        
        task_id = initial_response.get('task_id')
        if not task_id:
            logger.error("No task ID received from Research Manager")
            return
        
        # Simulate monitoring the workflow stages
        stages = [
            "PLANNING",
            "COST_ESTIMATION", 
            "LITERATURE_REVIEW",
            "RESULT_PROCESSING",
            "SYNTHESIS",
            "COMPLETE"
        ]
        
        for i, stage in enumerate(stages):
            logger.info(f"📍 Stage {i+1}/{len(stages)}: {stage}")
            
            if stage == "COST_ESTIMATION":
                await self._demonstrate_cost_estimation(task_id)
            elif stage == "LITERATURE_REVIEW":
                await self._demonstrate_literature_search(task_id)
            elif stage == "RESULT_PROCESSING":
                await self._demonstrate_result_processing(task_id)
            elif stage == "SYNTHESIS":
                await self._demonstrate_synthesis(task_id)
            
            # Simulate processing time
            await asyncio.sleep(2)
            
        logger.info("🎉 Literature Review Workflow completed successfully!")
    
    async def _demonstrate_cost_estimation(self, task_id: str):
        """Demonstrate cost estimation for the literature search."""
        logger.info("💰 Research Manager estimating costs...")
        
        # Simulate cost calculation
        operations = [
            {"type": "literature_search", "source": "semantic_scholar", "estimated_requests": 2, "cost_per_request": 0.01},
            {"type": "literature_search", "source": "pubmed", "estimated_requests": 3, "cost_per_request": 0.005},
            {"type": "literature_search", "source": "arxiv", "estimated_requests": 2, "cost_per_request": 0.002},
            {"type": "literature_search", "source": "crossref", "estimated_requests": 2, "cost_per_request": 0.008},
            {"type": "normalization", "records": 100, "cost_per_record": 0.001},
            {"type": "deduplication", "records": 100, "cost_per_record": 0.0005},
            {"type": "synthesis", "tokens": 5000, "cost_per_token": 0.00001}
        ]
        
        total_cost = 0.0
        for op in operations:
            op_cost = 0.0
            if "estimated_requests" in op and "cost_per_request" in op:
                op_cost += op["estimated_requests"] * op["cost_per_request"]
            if "records" in op and "cost_per_record" in op:
                op_cost += op["records"] * op["cost_per_record"]
            if "tokens" in op and "cost_per_token" in op:
                op_cost += op["tokens"] * op["cost_per_token"]
            total_cost += op_cost
        
        logger.info(f"   💵 Estimated total cost: ${total_cost:.3f}")
        logger.info(f"   ✅ Cost approved (under $1.00 threshold)")
        
        # Log cost breakdown
        for op in operations:
            op_cost = 0.0
            if "estimated_requests" in op and "cost_per_request" in op:
                op_cost += op["estimated_requests"] * op["cost_per_request"]
            if "records" in op and "cost_per_record" in op:
                op_cost += op["records"] * op["cost_per_record"]
            if "tokens" in op and "cost_per_token" in op:
                op_cost += op["tokens"] * op["cost_per_token"]
            logger.info(f"     - {op['type']}: ${op_cost:.4f}")
    
    async def _demonstrate_literature_search(self, task_id: str):
        """Demonstrate the literature search execution."""
        logger.info("🔍 Research Manager delegating to Literature Search Agent...")
        
        # Simulate search delegation message
        search_delegation = {
            "target_agent": "literature_search",
            "action": "search_literature",
            "payload": {
                "lit_review_id": task_id,
                "query": "machine learning applications in medical diagnosis accuracy improvement",
                "sources": ["semantic_scholar", "pubmed", "arxiv", "crossref"],
                "max_results": 100,
                "filters": {
                    "year_min": 2020,
                    "year_max": 2024,
                    "publication_types": ["journal_article", "review"]
                }
            }
        }
        
        logger.info(f"   📤 Delegating search to Literature Agent")
        logger.info(f"   🎯 Target: {search_delegation['target_agent']}")
        logger.info(f"   🔎 Query: {search_delegation['payload']['query'][:50]}...")
        
        # Simulate literature search execution
        sources = search_delegation['payload']['sources']
        simulated_results = {}
        
        for source in sources:
            logger.info(f"   🌐 Searching {source}...")
            await asyncio.sleep(1)  # Simulate API call time
            
            # Simulate different result counts per source
            result_counts = {
                "semantic_scholar": 42,
                "pubmed": 28,
                "arxiv": 15,
                "crossref": 31
            }
            
            count = result_counts.get(source, 0)
            simulated_results[source] = count
            logger.info(f"     ✅ Found {count} records from {source}")
        
        total_found = sum(simulated_results.values())
        logger.info(f"   📊 Total records found: {total_found}")
        logger.info(f"   🔄 Starting normalization and deduplication...")
        
        # Simulate deduplication
        await asyncio.sleep(1)
        unique_count = int(total_found * 0.78)  # ~22% duplicates
        logger.info(f"   ✨ After deduplication: {unique_count} unique records")
    
    async def _demonstrate_result_processing(self, task_id: str):
        """Demonstrate result processing and quality filtering."""
        logger.info("⚙️ Literature Agent processing search results...")
        
        processing_steps = [
            ("Format normalization", "Standardizing record schemas across sources"),
            ("Author name disambiguation", "Resolving author name variations"),
            ("Citation extraction", "Extracting and validating citations"),
            ("Abstract quality assessment", "Evaluating abstract completeness"),
            ("Duplicate detection", "Advanced similarity matching"),
            ("Quality scoring", "Calculating relevance and quality scores"),
            ("Metadata enrichment", "Adding subject classifications")
        ]
        
        for step_name, step_description in processing_steps:
            logger.info(f"   🔧 {step_name}: {step_description}")
            await asyncio.sleep(0.5)  # Simulate processing time
        
        # Simulate quality filtering results
        quality_stats = {
            "total_processed": 94,
            "high_quality": 67,
            "medium_quality": 21,
            "low_quality": 6,
            "filtered_out": 6
        }
        
        logger.info(f"   📈 Quality Assessment Results:")
        for category, count in quality_stats.items():
            logger.info(f"     - {category.replace('_', ' ').title()}: {count}")
        
        final_count = quality_stats["high_quality"] + quality_stats["medium_quality"]
        logger.info(f"   ✅ Final curated dataset: {final_count} high-quality papers")
    
    async def _demonstrate_synthesis(self, task_id: str):
        """Demonstrate literature synthesis and report generation."""
        logger.info("📝 Research Manager generating literature review synthesis...")
        
        synthesis_components = [
            "Key themes identification",
            "Methodological analysis",
            "Temporal trend analysis", 
            "Geographic distribution analysis",
            "Citation network analysis",
            "Research gap identification",
            "Future directions synthesis"
        ]
        
        for component in synthesis_components:
            logger.info(f"   📊 Generating: {component}")
            await asyncio.sleep(0.7)
        
        # Simulate synthesis results
        synthesis_results = {
            "key_themes": [
                "Deep learning for medical imaging (34 papers)",
                "Clinical decision support systems (21 papers)", 
                "Diagnostic accuracy improvement (19 papers)",
                "Interpretability and explainability (14 papers)"
            ],
            "top_venues": [
                "Nature Medicine (8 papers)",
                "IEEE Transactions on Medical Imaging (6 papers)",
                "The Lancet Digital Health (5 papers)",
                "Medical Image Analysis (4 papers)"
            ],
            "temporal_trends": {
                "2020": 15,
                "2021": 22,
                "2022": 24,
                "2023": 19,
                "2024": 8
            },
            "research_gaps": [
                "Limited real-world deployment studies",
                "Insufficient diversity in training datasets",
                "Lack of standardized evaluation metrics",
                "Regulatory approval challenges"
            ]
        }
        
        logger.info(f"   🎯 Literature Review Synthesis Complete:")
        logger.info(f"     📚 Total papers analyzed: 88")
        logger.info(f"     🏷️ Key themes identified: {len(synthesis_results['key_themes'])}")
        logger.info(f"     📰 Top venues: {len(synthesis_results['top_venues'])}")
        logger.info(f"     🔍 Research gaps: {len(synthesis_results['research_gaps'])}")
    
    async def _wait_for_response(self, task_id: str, timeout: int = 30) -> Dict[str, Any]:
        """Wait for a response from MCP server."""
        try:
            # In a real implementation, this would listen for actual MCP responses
            # For demo purposes, we'll simulate a successful response
            await asyncio.sleep(1)
            
            simulated_response = {
                "status": "accepted",
                "task_id": task_id,
                "message": "Research coordination initiated",
                "estimated_duration": "45-60 seconds",
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"📥 Received response: {simulated_response['status']}")
            return simulated_response
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout waiting for response to task {task_id}")
            raise
        except Exception as e:
            logger.error(f"Error waiting for response: {e}")
            raise


async def main():
    """Main demonstration function."""
    demo = LiteratureReviewWorkflowDemo()
    
    try:
        # Connect to MCP (in real scenario)
        # await demo.connect_to_mcp()
        
        # For demo purposes, we'll simulate the workflow without actual MCP connection
        logger.info("🎬 Literature Review Workflow Demonstration")
        logger.info("📝 Note: This is a simulated demonstration of the workflow")
        logger.info("    In production, this would connect to actual MCP server and agents")
        logger.info("")
        
        # Demonstrate the workflow
        await demo.demonstrate_literature_review_workflow()
        
    except KeyboardInterrupt:
        logger.info("Demo interrupted by user")
    except Exception as e:
        logger.error(f"Demo failed: {e}")
    finally:
        # Cleanup
        # await demo.disconnect_from_mcp()
        logger.info("🏁 Demo completed")


if __name__ == "__main__":
    asyncio.run(main())

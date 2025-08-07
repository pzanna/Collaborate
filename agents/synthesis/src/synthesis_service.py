"""
Synthesis & Review Agent Service for Eunice Research Platform.

This module provides a containerized Synthesis & Review Agent that handles:
- Data extraction and evidence synthesis
- Meta-analysis and statistical aggregation 
- Evidence table generation and management
- Integration with research workflows
- Statistical analysis and reporting

ARCHITECTURE COMPLIANCE:
- ONLY exposes health check API endpoint (/health)
- ALL business operations via MCP protocol exclusively
- NO direct HTTP/REST endpoints for business logic
"""

import asyncio
import json
import logging
import uuid
import sys
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from statistics import mean, stdev

import uvicorn
import websockets
from fastapi import FastAPI
from websockets.exceptions import ConnectionClosed, WebSocketException

# Import the standardized health check service
sys.path.append(str(Path(__file__).parent.parent))
from health_check_service import create_health_check_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class OutcomeDatum:
    """Outcome data model for extracted study results."""
    record_id: str
    outcome_name: str
    group_labels: List[str]
    means: List[float]
    sds: List[float]
    ns: List[int]
    effect_size: Optional[float] = None
    confidence_interval: Optional[Tuple[float, float]] = None


@dataclass
class MetaAnalysisResult:
    """Meta-analysis result data model."""
    outcome_name: str
    pooled_effect: float
    ci: Tuple[float, float]
    heterogeneity_i2: float
    studies_included: int
    total_participants: int
    p_value: Optional[float] = None
    forest_plot_data: Optional[Dict[str, Any]] = None


@dataclass
class EvidenceTable:
    """Evidence table data model."""
    table_id: str
    lit_review_id: str
    studies: List[Dict[str, Any]]
    outcomes: List[OutcomeDatum]
    created_at: datetime = field(default_factory=datetime.now)
    summary_statistics: Optional[Dict[str, Any]] = None


class SynthesisReviewService:
    """
    Synthesis & Review Service for data extraction and meta-analysis.
    
    Handles evidence synthesis, statistical aggregation, and evidence table
    generation via MCP protocol.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Synthesis & Review Service."""
        self.config = config
        self.agent_id = "synthesis_review"
        self.agent_type = "synthesis_review"
        
        # Service configuration
        self.service_host = config.get("service_host", "0.0.0.0")
        self.service_port = config.get("service_port", 8005)
        self.mcp_server_url = config.get("mcp_server_url", "ws://mcp-server:9000")
        
        # Processing configuration
        self.min_studies_for_meta = config.get("min_studies_for_meta", 2)
        self.significance_level = config.get("significance_level", 0.05)
        self.heterogeneity_threshold = config.get("heterogeneity_threshold", 75.0)
        
        # MCP connection
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.mcp_connected = False
        self.should_run = True
        
        # Data storage
        self.evidence_tables: Dict[str, EvidenceTable] = {}
        self.meta_analyses: Dict[str, List[MetaAnalysisResult]] = {}
        self.synthesis_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Task processing queue
        self.task_queue = asyncio.Queue()
        
        # Start time for uptime tracking
        self.start_time = datetime.now()
        
        # Capabilities
        self.capabilities = [
            "extract_data",
            "synthesize_evidence",
            "perform_meta_analysis",
            "generate_evidence_tables",
            "calculate_effect_sizes",
            "assess_heterogeneity"
        ]
        
        logger.info(f"Synthesis & Review Service initialized on port {self.service_port}")
    
    async def start(self):
        """Start the Synthesis & Review Service."""
        try:
            # Connect to MCP server
            await self._connect_to_mcp_server()
            
            # Start task processing
            asyncio.create_task(self._process_task_queue())
            
            # Listen for MCP messages
            await self._listen_for_tasks()
            
            logger.info("Synthesis & Review Service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Synthesis & Review Service: {e}")
            raise
    
    async def stop(self):
        """Stop the Synthesis & Review Service."""
        try:
            self.should_run = False
            
            # Close MCP connection
            if self.websocket:
                await self.websocket.close()
            
            logger.info("Synthesis & Review Service stopped")
            
        except Exception as e:
            logger.error(f"Error stopping Synthesis & Review Service: {e}")
    
    async def _connect_to_mcp_server(self):
        """Connect to MCP server."""
        max_retries = 10
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Connecting to MCP server at {self.mcp_server_url} (attempt {attempt + 1})")
                
                self.websocket = await websockets.connect(
                    self.mcp_server_url,
                    ping_interval=30,
                    ping_timeout=10
                )
                
                # Register with MCP server
                await self._register_with_mcp_server()
                
                self.mcp_connected = True
                logger.info("Successfully connected to MCP server")
                return
                
            except Exception as e:
                logger.warning(f"Failed to connect to MCP server (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error("Failed to connect to MCP server after all retries")
                    raise
    
    async def _register_with_mcp_server(self):
        """Register this agent with the MCP server."""
        if not self.websocket:
            raise Exception("WebSocket connection not available")
            
        registration_message = {
            "type": "agent_register",
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": self.capabilities,
            "timestamp": datetime.now().isoformat(),
            "service_info": {
                    "host": self.service_host,
                    "port": self.service_port,
                    "health_endpoint": f"http://{self.service_host}:{self.service_port}/health"
                }
            
        }
        
        await self.websocket.send(json.dumps(registration_message))
        logger.info(f"Registered with MCP server: {len(self.capabilities)} capabilities")
    
    async def _listen_for_tasks(self):
        """Listen for tasks from MCP server."""
        try:
            if not self.websocket:
                logger.error("Cannot listen for tasks: no websocket connection")
                return
                
            logger.info("Starting to listen for tasks from MCP server")
            
            async for message in self.websocket:
                if not self.should_run:
                    break
                    
                try:
                    data = json.loads(message)
                    await self.task_queue.put(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse MCP message: {e}")
                except Exception as e:
                    logger.error(f"Error handling MCP message: {e}")
                    
        except ConnectionClosed:
            logger.warning("MCP server connection closed")
            self.mcp_connected = False
            # Attempt to reconnect
            asyncio.create_task(self._reconnect_to_mcp_server())
        except WebSocketException as e:
            logger.error(f"WebSocket error: {e}")
            self.mcp_connected = False
            # Attempt to reconnect
            asyncio.create_task(self._reconnect_to_mcp_server())
        except Exception as e:
            logger.error(f"Unexpected error in message listener: {e}")
            self.mcp_connected = False
    
    async def _reconnect_to_mcp_server(self):
        """Attempt to reconnect to MCP server after connection loss."""
        logger.info("Attempting to reconnect to MCP server...")
        max_retries = 5
        retry_delay = 3
        
        for attempt in range(max_retries):
            try:
                await asyncio.sleep(retry_delay)  # Wait before retry
                
                logger.info(f"Reconnection attempt {attempt + 1}/{max_retries}")
                
                # Close existing connection if any
                if self.websocket:
                    try:
                        await self.websocket.close()
                    except:
                        pass
                
                # Create new connection
                self.websocket = await websockets.connect(
                    self.mcp_server_url,
                    ping_interval=20,  # More frequent pings during long operations
                    ping_timeout=15    # Longer timeout for ping responses
                )
                
                # Re-register with MCP server
                await self._register_with_mcp_server()
                
                # Restart message handler
                asyncio.create_task(self._listen_for_tasks())
                
                self.mcp_connected = True
                logger.info("✅ Successfully reconnected to MCP server")
                
                return
                
            except Exception as e:
                logger.warning(f"Reconnection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    retry_delay = min(retry_delay * 2, 30)  # Exponential backoff, max 30s
                else:
                    logger.error("❌ Failed to reconnect to MCP server after all attempts")
                    self.mcp_connected = False
    
    async def _process_task_queue(self):
        """Process tasks from the MCP queue."""
        while self.should_run:
            try:
                # Get task from queue
                task_data = await self.task_queue.get()
                
                # Process the task
                result = await self._process_synthesis_task(task_data)
                
                # Send result back to MCP server
                if self.websocket and self.mcp_connected:
                    response = {
                        "jsonrpc": "2.0",
                        "id": task_data.get("id"),
                        "result": result
                    }
                    await self.websocket.send(json.dumps(response))
                
                # Mark task as done
                self.task_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error processing task: {e}")
                await asyncio.sleep(1)
    
    async def _process_synthesis_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a synthesis-related task."""
        try:
            method = task_data.get("method", "")
            params = task_data.get("params", {})
            
            # Route to appropriate handler
            if method == "task/execute":
                task_type = params.get("task_type", "")
                data = params.get("data", {})
                
                if task_type == "extract_data":
                    return await self._handle_extract_data(data)
                elif task_type == "synthesize_evidence":
                    return await self._handle_synthesize_evidence(data)
                elif task_type == "perform_meta_analysis":
                    return await self._handle_perform_meta_analysis(data)
                elif task_type == "generate_evidence_tables":
                    return await self._handle_generate_evidence_tables(data)
                elif task_type == "calculate_effect_sizes":
                    return await self._handle_calculate_effect_sizes(data)
                elif task_type == "assess_heterogeneity":
                    return await self._handle_assess_heterogeneity(data)
                else:
                    return {
                        "status": "failed",
                        "error": f"Unknown task type: {task_type}",
                        "timestamp": datetime.now().isoformat()
                    }
            elif method == "agent/ping":
                return {"status": "alive", "timestamp": datetime.now().isoformat()}
            elif method == "agent/status":
                return await self._get_agent_status()
            else:
                return {
                    "status": "failed",
                    "error": f"Unknown method: {method}",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error processing synthesis task: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_extract_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle data extraction request."""
        try:
            studies = data.get("studies", [])
            extraction_fields = data.get("extraction_fields", [])
            session_id = data.get("session_id", str(uuid.uuid4()))
            
            if not studies:
                return {
                    "status": "failed",
                    "error": "Studies are required for data extraction",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Extract data from studies
            extracted_data = await self._extract_study_data(studies, extraction_fields)
            
            # Store extraction session
            self.synthesis_sessions[session_id] = {
                "type": "data_extraction",
                "studies": studies,
                "extraction_fields": extraction_fields,
                "extracted_data": extracted_data,
                "created_at": datetime.now().isoformat()
            }
            
            return {
                "status": "completed",
                "session_id": session_id,
                "extracted_data": extracted_data,
                "studies_processed": len(studies),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to extract data: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_synthesize_evidence(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle evidence synthesis request."""
        try:
            studies = data.get("studies", [])
            outcomes = data.get("outcomes", [])
            synthesis_method = data.get("synthesis_method", "narrative")
            
            if not studies:
                return {
                    "status": "failed",
                    "error": "Studies are required for evidence synthesis",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Perform evidence synthesis
            synthesis_result = await self._synthesize_evidence(studies, outcomes, synthesis_method)
            
            return {
                "status": "completed",
                "synthesis_method": synthesis_method,
                "synthesis_result": synthesis_result,
                "studies_included": len(studies),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to synthesize evidence: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_perform_meta_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle meta-analysis request."""
        try:
            outcomes_data = data.get("outcomes_data", [])
            analysis_model = data.get("analysis_model", "random_effects")
            
            if not outcomes_data:
                return {
                    "status": "failed",
                    "error": "Outcomes data is required for meta-analysis",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Perform meta-analysis
            meta_results = await self._perform_meta_analysis(outcomes_data, analysis_model)
            
            return {
                "status": "completed",
                "analysis_model": analysis_model,
                "meta_analysis_results": [self._meta_result_to_dict(result) for result in meta_results],
                "outcomes_analyzed": len(meta_results),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to perform meta-analysis: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_generate_evidence_tables(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle evidence table generation request."""
        try:
            studies = data.get("studies", [])
            outcomes = data.get("outcomes", [])
            table_format = data.get("table_format", "standard")
            lit_review_id = data.get("lit_review_id", str(uuid.uuid4()))
            
            if not studies:
                return {
                    "status": "failed",
                    "error": "Studies are required for evidence table generation",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Generate evidence table
            evidence_table = await self._generate_evidence_table(studies, outcomes, lit_review_id, table_format)
            
            # Store evidence table
            self.evidence_tables[evidence_table.table_id] = evidence_table
            
            return {
                "status": "completed",
                "table_id": evidence_table.table_id,
                "lit_review_id": lit_review_id,
                "table_format": table_format,
                "studies_included": len(studies),
                "outcomes_included": len(outcomes),
                "evidence_table": self._evidence_table_to_dict(evidence_table),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate evidence tables: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_calculate_effect_sizes(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle effect size calculation request."""
        try:
            study_data = data.get("study_data", [])
            effect_size_type = data.get("effect_size_type", "cohens_d")
            
            if not study_data:
                return {
                    "status": "failed",
                    "error": "Study data is required for effect size calculation",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Calculate effect sizes
            effect_sizes = await self._calculate_effect_sizes(study_data, effect_size_type)
            
            return {
                "status": "completed",
                "effect_size_type": effect_size_type,
                "effect_sizes": effect_sizes,
                "studies_processed": len(study_data),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate effect sizes: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_assess_heterogeneity(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle heterogeneity assessment request."""
        try:
            effect_sizes = data.get("effect_sizes", [])
            assessment_method = data.get("assessment_method", "i_squared")
            
            if not effect_sizes:
                return {
                    "status": "failed",
                    "error": "Effect sizes are required for heterogeneity assessment",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Assess heterogeneity
            heterogeneity_result = await self._assess_heterogeneity(effect_sizes, assessment_method)
            
            return {
                "status": "completed",
                "assessment_method": assessment_method,
                "heterogeneity_result": heterogeneity_result,
                "effect_sizes_analyzed": len(effect_sizes),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to assess heterogeneity: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _extract_study_data(self, studies: List[Dict[str, Any]], 
                                 extraction_fields: List[str]) -> List[Dict[str, Any]]:
        """Extract data from studies based on specified fields."""
        extracted_data = []
        
        for study in studies:
            study_id = study.get("id", str(uuid.uuid4()))
            extracted_study = {"study_id": study_id}
            
            # Extract specified fields
            for field in extraction_fields:
                extracted_study[field] = study.get(field, "")
            
            # Extract common fields if not specified
            if "title" not in extraction_fields:
                extracted_study["title"] = study.get("title", "")
            if "authors" not in extraction_fields:
                extracted_study["authors"] = study.get("authors", [])
            if "year" not in extraction_fields:
                extracted_study["year"] = study.get("publication_year", study.get("year", ""))
            
            extracted_data.append(extracted_study)
        
        return extracted_data
    
    async def _synthesize_evidence(self, studies: List[Dict[str, Any]], outcomes: List[str], 
                                 synthesis_method: str) -> Dict[str, Any]:
        """Synthesize evidence from studies."""
        synthesis_result = {
            "method": synthesis_method,
            "studies_count": len(studies),
            "outcomes": outcomes,
            "synthesis": ""
        }
        
        if synthesis_method == "narrative":
            # Simple narrative synthesis
            synthesis_result["synthesis"] = await self._narrative_synthesis(studies, outcomes)
        elif synthesis_method == "vote_counting":
            # Vote counting synthesis
            synthesis_result["synthesis"] = await self._vote_counting_synthesis(studies, outcomes)
        else:
            synthesis_result["synthesis"] = f"Synthesis method '{synthesis_method}' not implemented"
        
        return synthesis_result
    
    async def _perform_meta_analysis(self, outcomes_data: List[Dict[str, Any]], 
                                   analysis_model: str) -> List[MetaAnalysisResult]:
        """Perform meta-analysis on outcomes data."""
        meta_results = []
        
        # Group outcomes by outcome name
        outcomes_by_name = {}
        for outcome in outcomes_data:
            name = outcome.get("outcome_name", "unknown")
            if name not in outcomes_by_name:
                outcomes_by_name[name] = []
            outcomes_by_name[name].append(outcome)
        
        # Perform meta-analysis for each outcome
        for outcome_name, outcome_list in outcomes_by_name.items():
            if len(outcome_list) >= self.min_studies_for_meta:
                meta_result = await self._calculate_pooled_effect(outcome_name, outcome_list, analysis_model)
                meta_results.append(meta_result)
        
        return meta_results
    
    async def _generate_evidence_table(self, studies: List[Dict[str, Any]], outcomes: List[Dict[str, Any]], 
                                     lit_review_id: str, table_format: str) -> EvidenceTable:
        """Generate an evidence table from studies and outcomes."""
        table_id = str(uuid.uuid4())
        
        # Convert outcomes to OutcomeDatum objects
        outcome_data = []
        for outcome in outcomes:
            datum = OutcomeDatum(
                record_id=outcome.get("record_id", ""),
                outcome_name=outcome.get("outcome_name", ""),
                group_labels=outcome.get("group_labels", []),
                means=outcome.get("means", []),
                sds=outcome.get("sds", []),
                ns=outcome.get("ns", [])
            )
            outcome_data.append(datum)
        
        # Calculate summary statistics
        summary_stats = await self._calculate_summary_statistics(studies, outcome_data)
        
        evidence_table = EvidenceTable(
            table_id=table_id,
            lit_review_id=lit_review_id,
            studies=studies,
            outcomes=outcome_data,
            summary_statistics=summary_stats
        )
        
        return evidence_table
    
    async def _calculate_effect_sizes(self, study_data: List[Dict[str, Any]], 
                                    effect_size_type: str) -> List[Dict[str, Any]]:
        """Calculate effect sizes for study data."""
        effect_sizes = []
        
        for study in study_data:
            study_id = study.get("id", str(uuid.uuid4()))
            
            # Extract numeric data for effect size calculation
            try:
                if effect_size_type == "cohens_d":
                    effect_size = await self._calculate_cohens_d(study)
                elif effect_size_type == "odds_ratio":
                    effect_size = await self._calculate_odds_ratio(study)
                elif effect_size_type == "mean_difference":
                    effect_size = await self._calculate_mean_difference(study)
                else:
                    effect_size = {"value": 0.0, "ci": [0.0, 0.0], "error": f"Unknown effect size type: {effect_size_type}"}
                
                effect_sizes.append({
                    "study_id": study_id,
                    "effect_size_type": effect_size_type,
                    "effect_size": effect_size["value"],
                    "confidence_interval": effect_size.get("ci", []),
                    "standard_error": effect_size.get("se", 0.0)
                })
                
            except Exception as e:
                logger.warning(f"Failed to calculate effect size for study {study_id}: {e}")
                effect_sizes.append({
                    "study_id": study_id,
                    "effect_size_type": effect_size_type,
                    "effect_size": 0.0,
                    "confidence_interval": [0.0, 0.0],
                    "standard_error": 0.0,
                    "error": str(e)
                })
        
        return effect_sizes
    
    async def _assess_heterogeneity(self, effect_sizes: List[float], 
                                  assessment_method: str) -> Dict[str, Any]:
        """Assess heterogeneity in effect sizes."""
        if len(effect_sizes) < 2:
            return {
                "heterogeneity": 0.0,
                "interpretation": "Cannot assess heterogeneity with less than 2 studies",
                "assessment_method": assessment_method
            }
        
        # Simple heterogeneity assessment using variance
        effect_variance = stdev(effect_sizes) ** 2 if len(effect_sizes) > 1 else 0.0
        
        # Calculate I² approximation
        if assessment_method == "i_squared":
            # Simplified I² calculation
            total_variance = effect_variance + (1.0 / len(effect_sizes))  # Add sampling variance approximation
            i_squared = max(0.0, (effect_variance / total_variance) * 100) if total_variance > 0 else 0.0
            
            # Interpret I²
            if i_squared < 25:
                interpretation = "Low heterogeneity"
            elif i_squared < 50:
                interpretation = "Moderate heterogeneity"
            elif i_squared < 75:
                interpretation = "Substantial heterogeneity"
            else:
                interpretation = "Considerable heterogeneity"
            
            return {
                "i_squared": i_squared,
                "interpretation": interpretation,
                "assessment_method": assessment_method,
                "effect_variance": effect_variance
            }
        
        return {
            "heterogeneity": effect_variance,
            "interpretation": "Basic variance assessment",
            "assessment_method": assessment_method
        }
    
    async def _narrative_synthesis(self, studies: List[Dict[str, Any]], outcomes: List[str]) -> str:
        """Perform narrative synthesis of studies."""
        if not studies:
            return "No studies available for synthesis."
        
        synthesis_parts = [
            f"Narrative synthesis of {len(studies)} studies investigating {', '.join(outcomes) if outcomes else 'various outcomes'}.",
            f"Studies ranged from {min(study.get('publication_year', 2000) for study in studies if study.get('publication_year'))} to {max(study.get('publication_year', 2023) for study in studies if study.get('publication_year'))}.",
            f"Sample sizes varied across studies (range: detailed analysis required).",
            "Key findings suggest further quantitative analysis is needed to draw definitive conclusions."
        ]
        
        return " ".join(synthesis_parts)
    
    async def _vote_counting_synthesis(self, studies: List[Dict[str, Any]], outcomes: List[str]) -> str:
        """Perform vote counting synthesis."""
        # Simple vote counting - would need more sophisticated implementation
        positive_studies = len([s for s in studies if s.get("effect_direction", "") == "positive"])
        negative_studies = len([s for s in studies if s.get("effect_direction", "") == "negative"])
        no_effect_studies = len(studies) - positive_studies - negative_studies
        
        return f"Vote counting synthesis: {positive_studies} studies showed positive effects, {negative_studies} showed negative effects, and {no_effect_studies} showed no clear effect."
    
    async def _calculate_pooled_effect(self, outcome_name: str, outcome_list: List[Dict[str, Any]], 
                                     analysis_model: str) -> MetaAnalysisResult:
        """Calculate pooled effect for meta-analysis."""
        # Simple pooled effect calculation (would need more sophisticated implementation)
        effect_sizes = [outcome.get("effect_size", 0.0) for outcome in outcome_list if outcome.get("effect_size")]
        
        if not effect_sizes:
            pooled_effect = 0.0
            ci = (0.0, 0.0)
            heterogeneity_i2 = 0.0
        else:
            pooled_effect = mean(effect_sizes)
            # Simplified confidence interval
            se = stdev(effect_sizes) / (len(effect_sizes) ** 0.5) if len(effect_sizes) > 1 else 0.1
            ci = (pooled_effect - 1.96 * se, pooled_effect + 1.96 * se)
            # Simplified heterogeneity
            heterogeneity_i2 = min(100.0, (stdev(effect_sizes) ** 2) * 100) if len(effect_sizes) > 1 else 0.0
        
        total_participants = sum(outcome.get("total_n", 0) for outcome in outcome_list)
        
        return MetaAnalysisResult(
            outcome_name=outcome_name,
            pooled_effect=pooled_effect,
            ci=ci,
            heterogeneity_i2=heterogeneity_i2,
            studies_included=len(outcome_list),
            total_participants=total_participants
        )
    
    async def _calculate_summary_statistics(self, studies: List[Dict[str, Any]], 
                                          outcomes: List[OutcomeDatum]) -> Dict[str, Any]:
        """Calculate summary statistics for evidence table."""
        return {
            "total_studies": len(studies),
            "total_outcomes": len(outcomes),
            "date_range": {
                "earliest": min(study.get("publication_year", 2000) for study in studies if study.get("publication_year")),
                "latest": max(study.get("publication_year", 2023) for study in studies if study.get("publication_year"))
            },
            "sample_size_range": {
                "min": min(study.get("sample_size", 0) for study in studies if study.get("sample_size")),
                "max": max(study.get("sample_size", 0) for study in studies if study.get("sample_size"))
            }
        }
    
    async def _calculate_cohens_d(self, study: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate Cohen's d effect size."""
        # Simplified Cohen's d calculation
        try:
            mean1 = float(study.get("mean_group1", 0))
            mean2 = float(study.get("mean_group2", 0))
            sd1 = float(study.get("sd_group1", 1))
            sd2 = float(study.get("sd_group2", 1))
            n1 = int(study.get("n_group1", 10))
            n2 = int(study.get("n_group2", 10))
            
            # Pooled standard deviation
            pooled_sd = ((((n1 - 1) * sd1**2) + ((n2 - 1) * sd2**2)) / (n1 + n2 - 2)) ** 0.5
            
            # Cohen's d
            cohens_d = (mean1 - mean2) / pooled_sd if pooled_sd > 0 else 0.0
            
            # Simplified standard error and CI
            se = ((n1 + n2) / (n1 * n2) + (cohens_d**2) / (2 * (n1 + n2))) ** 0.5
            ci = [cohens_d - 1.96 * se, cohens_d + 1.96 * se]
            
            return {"value": cohens_d, "se": se, "ci": ci}
            
        except (ValueError, ZeroDivisionError) as e:
            return {"value": 0.0, "se": 0.0, "ci": [0.0, 0.0], "error": str(e)}
    
    async def _calculate_odds_ratio(self, study: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate odds ratio effect size."""
        # Simplified odds ratio calculation
        try:
            a = int(study.get("events_group1", 1))
            b = int(study.get("non_events_group1", 1))
            c = int(study.get("events_group2", 1))
            d = int(study.get("non_events_group2", 1))
            
            odds_ratio = (a * d) / (b * c) if (b * c) > 0 else 1.0
            log_or = float('inf') if odds_ratio <= 0 else (odds_ratio ** 0.5)  # Simplified
            
            # Simplified standard error and CI
            se = (1/a + 1/b + 1/c + 1/d) ** 0.5 if all(x > 0 for x in [a, b, c, d]) else 1.0
            ci = [max(0.01, odds_ratio * ((1.96 * se) ** -1)), odds_ratio * (1.96 * se)]
            
            return {"value": odds_ratio, "se": se, "ci": ci}
            
        except (ValueError, ZeroDivisionError) as e:
            return {"value": 1.0, "se": 0.0, "ci": [1.0, 1.0], "error": str(e)}
    
    async def _calculate_mean_difference(self, study: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate mean difference effect size."""
        try:
            mean1 = float(study.get("mean_group1", 0))
            mean2 = float(study.get("mean_group2", 0))
            sd1 = float(study.get("sd_group1", 1))
            sd2 = float(study.get("sd_group2", 1))
            n1 = int(study.get("n_group1", 10))
            n2 = int(study.get("n_group2", 10))
            
            mean_diff = mean1 - mean2
            
            # Standard error of mean difference
            se = ((sd1**2 / n1) + (sd2**2 / n2)) ** 0.5
            ci = [mean_diff - 1.96 * se, mean_diff + 1.96 * se]
            
            return {"value": mean_diff, "se": se, "ci": ci}
            
        except (ValueError, ZeroDivisionError) as e:
            return {"value": 0.0, "se": 0.0, "ci": [0.0, 0.0], "error": str(e)}
    
    def _meta_result_to_dict(self, result: MetaAnalysisResult) -> Dict[str, Any]:
        """Convert MetaAnalysisResult to dictionary."""
        return {
            "outcome_name": result.outcome_name,
            "pooled_effect": result.pooled_effect,
            "confidence_interval": list(result.ci),
            "heterogeneity_i2": result.heterogeneity_i2,
            "studies_included": result.studies_included,
            "total_participants": result.total_participants,
            "p_value": result.p_value
        }
    
    def _evidence_table_to_dict(self, table: EvidenceTable) -> Dict[str, Any]:
        """Convert EvidenceTable to dictionary."""
        return {
            "table_id": table.table_id,
            "lit_review_id": table.lit_review_id,
            "studies_count": len(table.studies),
            "outcomes_count": len(table.outcomes),
            "created_at": table.created_at.isoformat(),
            "summary_statistics": table.summary_statistics
        }
    
    async def _get_agent_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "status": "ready" if self.mcp_connected else "disconnected",
            "capabilities": self.capabilities,
            "timestamp": datetime.now().isoformat(),
            "mcp_connected": self.mcp_connected,
            "evidence_tables": len(self.evidence_tables),
            "synthesis_sessions": len(self.synthesis_sessions),
            "meta_analyses": len(self.meta_analyses),
            "uptime_seconds": uptime,
            "timestamp": datetime.now().isoformat()
        }


# Global service instance
synthesis_service: Optional[SynthesisReviewService] = None


def get_mcp_status() -> Dict[str, Any]:
    """Get MCP connection status for health check."""
    if synthesis_service:
        return {
            "connected": synthesis_service.mcp_connected,
            "last_heartbeat": datetime.now().isoformat()
        }
    return {"connected": False, "last_heartbeat": "never"}


def get_additional_metadata() -> Dict[str, Any]:
    """Get additional metadata for health check."""
    if synthesis_service:
        return {
            "capabilities": synthesis_service.capabilities,
            "evidence_tables": len(synthesis_service.evidence_tables),
            "synthesis_sessions": len(synthesis_service.synthesis_sessions),
            "agent_id": synthesis_service.agent_id
        }
    return {}


# Create health check only FastAPI application
app = create_health_check_app(
    agent_type="synthesis_review",
    agent_id="synthesis-review-agent",
    version="1.0.0",
    get_mcp_status=get_mcp_status,
    get_additional_metadata=get_additional_metadata
)


async def main():
    """Main entry point for the synthesis & review agent service."""
    global synthesis_service
    
    try:
        # Load configuration
        config_path = Path("/app/config/config.json")
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
        else:
            config = {
                "service_host": "0.0.0.0",
                "service_port": 8005,
                "mcp_server_url": "ws://mcp-server:9000",
                "min_studies_for_meta": 2,
                "significance_level": 0.05,
                "heterogeneity_threshold": 75.0
            }
        
        # Initialize service
        synthesis_service = SynthesisReviewService(config)
        
        # Start FastAPI health check server in background
        config_uvicorn = uvicorn.Config(
            app,
            host=config["service_host"],
            port=config["service_port"],
            log_level="info"
        )
        server = uvicorn.Server(config_uvicorn)
        
        logger.info("🚨 ARCHITECTURE COMPLIANCE: Synthesis & Review Agent")
        logger.info("✅ ONLY health check API exposed")
        logger.info("✅ All business operations via MCP protocol exclusively")
        
        # Start server and MCP service concurrently
        await asyncio.gather(
            server.serve(),
            synthesis_service.start()
        )
        
    except KeyboardInterrupt:
        logger.info("Synthesis & review agent shutdown requested")
    except Exception as e:
        logger.error(f"Synthesis & review agent failed: {e}")
        sys.exit(1)
    finally:
        if synthesis_service:
            await synthesis_service.stop()


if __name__ == "__main__":
    asyncio.run(main())

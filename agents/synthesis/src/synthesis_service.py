"""
Synthesis & Review Agent Service for Eunice Research Platform.

This module provides a containerized Synthesis & Review Agent that specializes in:
- Data extraction and evidence synthesis
- Meta-analysis and statistical aggregation 
- Evidence table generation and management
- Integration with MCP protocol for task coordination
"""

import asyncio
import hashlib
import json
import logging
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from statistics import mean, stdev

import aiohttp
import uvicorn
import websockets
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

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
    generation with integration to MCP protocol.
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
        self.websocket = None
        self.mcp_connected = False
        
        # HTTP session for API calls
        self.session = None
        
        # Task processing queue
        self.task_queue = asyncio.Queue()
        
        logger.info(f"Synthesis & Review Service initialized on port {self.service_port}")
    
    async def start(self):
        """Start the Synthesis & Review Service."""
        try:
            # Initialize HTTP session
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={'User-Agent': 'Eunice-Research-Platform/1.0'}
            )
            
            # Connect to MCP server
            await self._connect_to_mcp_server()
            
            # Start task processing
            asyncio.create_task(self._process_task_queue())
            
            logger.info("Synthesis & Review Service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Synthesis & Review Service: {e}")
            raise
    
    async def stop(self):
        """Stop the Synthesis & Review Service."""
        try:
            # Close HTTP session
            if self.session:
                await self.session.close()
            
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
                
                # Start message handler
                asyncio.create_task(self._handle_mcp_messages())
                
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
        capabilities = [
            "data_extraction",
            "evidence_synthesis",
            "meta_analysis",
            "statistical_aggregation",
            "evidence_table_generation",
            "outcome_extraction",
            "forest_plot_generation",
            "heterogeneity_assessment"
        ]
        
        registration_message = {
            "type": "register",
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": capabilities,
            "service_info": {
                "host": self.service_host,
                "port": self.service_port,
                "health_endpoint": f"http://{self.service_host}:{self.service_port}/health"
            }
        }
        
        if self.websocket:
            await self.websocket.send(json.dumps(registration_message))
        logger.info(f"Registered with MCP server: {len(capabilities)} capabilities")
    
    async def _handle_mcp_messages(self):
        """Handle incoming MCP messages."""
        try:
            while self.websocket:
                message = await self.websocket.recv()
                data = json.loads(message)
                
                if data.get("type") == "task":
                    await self.task_queue.put(data)
                elif data.get("type") == "ping":
                    await self.websocket.send(json.dumps({"type": "pong"}))
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("MCP server connection closed")
            self.mcp_connected = False
        except Exception as e:
            logger.error(f"Error handling MCP messages: {e}")
            self.mcp_connected = False
    
    async def _process_task_queue(self):
        """Process tasks from the MCP queue."""
        while True:
            try:
                # Get task from queue
                task_data = await self.task_queue.get()
                
                # Process the task
                result = await self._process_synthesis_task(task_data)
                
                # Send result back to MCP server
                if self.websocket and self.mcp_connected:
                    response = {
                        "type": "task_result",
                        "task_id": task_data.get("task_id"),
                        "agent_id": self.agent_id,
                        "result": result
                    }
                    await self.websocket.send(json.dumps(response))
                
                # Mark task as done
                self.task_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error processing task: {e}")
                await asyncio.sleep(1)
    
    async def _process_synthesis_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a synthesis task."""
        try:
            action = task_data.get("action", "")
            payload = task_data.get("payload", {})
            
            # Route to appropriate handler
            if action == "extract_data":
                return await self._handle_extract_data(payload)
            elif action == "synthesize_evidence":
                return await self._handle_synthesize_evidence(payload)
            elif action == "perform_meta_analysis":
                return await self._handle_perform_meta_analysis(payload)
            elif action == "generate_evidence_table":
                return await self._handle_generate_evidence_table(payload)
            else:
                return {
                    "status": "failed",
                    "error": f"Unknown action: {action}",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error processing synthesis task: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_extract_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle data extraction request."""
        try:
            studies = payload.get("studies", [])
            extraction_template = payload.get("extraction_template", {})
            
            if not studies:
                return {
                    "status": "failed",
                    "error": "Studies data is required",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Extract data from studies
            extracted_data = []
            for study in studies:
                extracted_study = await self._extract_study_data(study, extraction_template)
                extracted_data.append(extracted_study)
            
            return {
                "status": "completed",
                "extracted_data": extracted_data,
                "studies_processed": len(extracted_data),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to handle extract data: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_synthesize_evidence(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle evidence synthesis request."""
        try:
            studies = payload.get("studies", [])
            synthesis_type = payload.get("synthesis_type", "narrative")
            
            if not studies:
                return {
                    "status": "failed",
                    "error": "Studies data is required",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Perform evidence synthesis
            synthesis_result = await self._synthesize_evidence(studies, synthesis_type)
            
            return {
                "status": "completed",
                "synthesis_result": synthesis_result,
                "studies_included": len(studies),
                "synthesis_type": synthesis_type,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to handle synthesize evidence: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_perform_meta_analysis(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle meta-analysis request."""
        try:
            outcome_data = payload.get("outcome_data", [])
            outcome_name = payload.get("outcome_name", "")
            analysis_model = payload.get("analysis_model", "fixed")
            
            if not outcome_data:
                return {
                    "status": "failed",
                    "error": "Outcome data is required",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Perform meta-analysis
            meta_result = await self._perform_meta_analysis(outcome_data, outcome_name, analysis_model)
            
            return {
                "status": "completed",
                "meta_analysis_result": {
                    "outcome_name": meta_result.outcome_name,
                    "pooled_effect": meta_result.pooled_effect,
                    "confidence_interval": meta_result.ci,
                    "heterogeneity_i2": meta_result.heterogeneity_i2,
                    "studies_included": meta_result.studies_included,
                    "total_participants": meta_result.total_participants,
                    "p_value": meta_result.p_value,
                    "forest_plot_data": meta_result.forest_plot_data
                },
                "analysis_model": analysis_model,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to handle perform meta-analysis: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_generate_evidence_table(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle evidence table generation request."""
        try:
            lit_review_id = payload.get("lit_review_id", str(uuid.uuid4()))
            studies = payload.get("studies", [])
            outcomes = payload.get("outcomes", [])
            
            if not studies:
                return {
                    "status": "failed",
                    "error": "Studies data is required",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Generate evidence table
            evidence_table = await self._generate_evidence_table(lit_review_id, studies, outcomes)
            
            return {
                "status": "completed",
                "evidence_table": {
                    "table_id": evidence_table.table_id,
                    "lit_review_id": evidence_table.lit_review_id,
                    "studies": evidence_table.studies,
                    "outcomes": [
                        {
                            "record_id": o.record_id,
                            "outcome_name": o.outcome_name,
                            "group_labels": o.group_labels,
                            "means": o.means,
                            "sds": o.sds,
                            "ns": o.ns,
                            "effect_size": o.effect_size,
                            "confidence_interval": o.confidence_interval
                        } for o in evidence_table.outcomes
                    ],
                    "summary_statistics": evidence_table.summary_statistics,
                    "created_at": evidence_table.created_at.isoformat()
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to handle generate evidence table: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _extract_study_data(self, study: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured data from a study."""
        try:
            extracted = {
                "study_id": study.get("id", str(uuid.uuid4())),
                "title": study.get("title", ""),
                "authors": study.get("authors", []),
                "year": study.get("year"),
                "sample_size": study.get("sample_size"),
                "study_design": study.get("study_design", ""),
                "intervention": study.get("intervention", ""),
                "control": study.get("control", ""),
                "outcomes": study.get("outcomes", []),
                "risk_of_bias": study.get("risk_of_bias", {}),
                "extraction_timestamp": datetime.now().isoformat()
            }
            
            # Apply extraction template if provided
            if template:
                for field, extractor in template.items():
                    if isinstance(extractor, dict) and "path" in extractor:
                        # Extract nested field
                        value = study
                        for path_part in extractor["path"].split("."):
                            if isinstance(value, dict) and path_part in value:
                                value = value[path_part]
                            else:
                                value = None
                                break
                        extracted[field] = value
            
            return extracted
            
        except Exception as e:
            logger.error(f"Error extracting study data: {e}")
            return {"error": str(e), "study_id": study.get("id", "unknown")}
    
    async def _synthesize_evidence(self, studies: List[Dict[str, Any]], synthesis_type: str) -> Dict[str, Any]:
        """Synthesize evidence from multiple studies."""
        try:
            synthesis_result = {
                "synthesis_type": synthesis_type,
                "studies_count": len(studies),
                "summary": {},
                "themes": [],
                "gaps": [],
                "recommendations": []
            }
            
            if synthesis_type == "narrative":
                # Narrative synthesis
                synthesis_result["summary"] = await self._narrative_synthesis(studies)
            elif synthesis_type == "thematic":
                # Thematic synthesis
                synthesis_result["themes"] = await self._thematic_synthesis(studies)
            elif synthesis_type == "framework":
                # Framework synthesis
                synthesis_result["framework"] = await self._framework_synthesis(studies)
            
            # Identify research gaps
            synthesis_result["gaps"] = await self._identify_research_gaps(studies)
            
            # Generate recommendations
            synthesis_result["recommendations"] = await self._generate_recommendations(studies)
            
            return synthesis_result
            
        except Exception as e:
            logger.error(f"Error synthesizing evidence: {e}")
            return {"error": str(e)}
    
    async def _narrative_synthesis(self, studies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform narrative synthesis."""
        try:
            summary = {
                "total_studies": len(studies),
                "study_designs": {},
                "population_characteristics": {},
                "intervention_types": {},
                "outcome_measures": {},
                "quality_assessment": {}
            }
            
            # Analyze study characteristics
            for study in studies:
                # Study design distribution
                design = study.get("study_design", "unknown")
                summary["study_designs"][design] = summary["study_designs"].get(design, 0) + 1
                
                # Population characteristics
                sample_size = study.get("sample_size")
                if sample_size:
                    if "sample_sizes" not in summary["population_characteristics"]:
                        summary["population_characteristics"]["sample_sizes"] = []
                    summary["population_characteristics"]["sample_sizes"].append(sample_size)
                
                # Intervention types
                intervention = study.get("intervention", "")
                if intervention:
                    summary["intervention_types"][intervention] = summary["intervention_types"].get(intervention, 0) + 1
            
            # Calculate summary statistics
            if summary["population_characteristics"].get("sample_sizes"):
                sizes = summary["population_characteristics"]["sample_sizes"]
                summary["population_characteristics"]["total_participants"] = sum(sizes)
                summary["population_characteristics"]["mean_sample_size"] = mean(sizes)
                summary["population_characteristics"]["median_sample_size"] = sorted(sizes)[len(sizes)//2]
            
            return summary
            
        except Exception as e:
            logger.error(f"Error in narrative synthesis: {e}")
            return {"error": str(e)}
    
    async def _thematic_synthesis(self, studies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Perform thematic synthesis."""
        try:
            themes = []
            
            # Extract themes from study outcomes and conclusions
            outcome_themes = {}
            
            for study in studies:
                outcomes = study.get("outcomes", [])
                for outcome in outcomes:
                    if isinstance(outcome, dict):
                        outcome_name = outcome.get("name", "")
                        if outcome_name:
                            if outcome_name not in outcome_themes:
                                outcome_themes[outcome_name] = {
                                    "theme": outcome_name,
                                    "studies": [],
                                    "frequency": 0
                                }
                            outcome_themes[outcome_name]["studies"].append(study.get("id", ""))
                            outcome_themes[outcome_name]["frequency"] += 1
            
            # Convert to list and sort by frequency
            themes = list(outcome_themes.values())
            themes.sort(key=lambda x: x["frequency"], reverse=True)
            
            return themes
            
        except Exception as e:
            logger.error(f"Error in thematic synthesis: {e}")
            return []
    
    async def _framework_synthesis(self, studies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform framework-based synthesis."""
        try:
            framework = {
                "intervention_components": {},
                "mechanism_of_action": {},
                "contextual_factors": {},
                "outcomes_pathway": {}
            }
            
            # Analyze intervention components
            for study in studies:
                intervention = study.get("intervention", "")
                if intervention:
                    components = intervention.split(",")  # Simple parsing
                    for component in components:
                        component = component.strip()
                        if component:
                            framework["intervention_components"][component] = \
                                framework["intervention_components"].get(component, 0) + 1
            
            return framework
            
        except Exception as e:
            logger.error(f"Error in framework synthesis: {e}")
            return {"error": str(e)}
    
    async def _identify_research_gaps(self, studies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify research gaps."""
        try:
            gaps = []
            
            # Analyze study designs
            designs = {}
            for study in studies:
                design = study.get("study_design", "unknown")
                designs[design] = designs.get(design, 0) + 1
            
            # Identify methodological gaps
            if designs.get("randomized_controlled_trial", 0) < len(studies) * 0.5:
                gaps.append({
                    "type": "methodological",
                    "gap": "Limited randomized controlled trials",
                    "recommendation": "More RCTs needed for stronger evidence"
                })
            
            # Identify population gaps
            total_participants = sum(s.get("sample_size", 0) for s in studies if s.get("sample_size"))
            if total_participants < 1000:
                gaps.append({
                    "type": "population",
                    "gap": "Small total sample size",
                    "recommendation": "Larger studies needed for adequate power"
                })
            
            return gaps
            
        except Exception as e:
            logger.error(f"Error identifying research gaps: {e}")
            return []
    
    async def _generate_recommendations(self, studies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate evidence-based recommendations."""
        try:
            recommendations = []
            
            # Quality of evidence assessment
            high_quality_studies = [s for s in studies if s.get("risk_of_bias", {}).get("overall", "") == "low"]
            
            if len(high_quality_studies) > len(studies) * 0.6:
                recommendations.append({
                    "type": "clinical",
                    "strength": "strong",
                    "recommendation": "High-quality evidence supports intervention effectiveness",
                    "confidence": "high"
                })
            else:
                recommendations.append({
                    "type": "research",
                    "strength": "conditional",
                    "recommendation": "More high-quality studies needed before clinical recommendations",
                    "confidence": "low"
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return []
    
    async def _perform_meta_analysis(self, outcome_data: List[Dict[str, Any]], outcome_name: str, model: str) -> MetaAnalysisResult:
        """Perform meta-analysis on outcome data."""
        try:
            if len(outcome_data) < self.min_studies_for_meta:
                raise ValueError(f"Minimum {self.min_studies_for_meta} studies required for meta-analysis")
            
            # Extract effect sizes and variances
            effect_sizes = []
            variances = []
            sample_sizes = []
            
            for data in outcome_data:
                # Calculate effect size (Cohen's d for continuous outcomes)
                if "mean_intervention" in data and "mean_control" in data:
                    mean_int = data["mean_intervention"]
                    mean_ctrl = data["mean_control"]
                    sd_int = data.get("sd_intervention", 1.0)
                    sd_ctrl = data.get("sd_control", 1.0)
                    n_int = data.get("n_intervention", 10)
                    n_ctrl = data.get("n_control", 10)
                    
                    # Pooled standard deviation
                    pooled_sd = ((n_int - 1) * sd_int**2 + (n_ctrl - 1) * sd_ctrl**2) / (n_int + n_ctrl - 2)
                    pooled_sd = pooled_sd**0.5
                    
                    # Cohen's d
                    cohens_d = (mean_int - mean_ctrl) / pooled_sd if pooled_sd > 0 else 0
                    
                    # Variance of Cohen's d
                    variance = ((n_int + n_ctrl) / (n_int * n_ctrl)) + (cohens_d**2) / (2 * (n_int + n_ctrl))
                    
                    effect_sizes.append(cohens_d)
                    variances.append(variance)
                    sample_sizes.append(n_int + n_ctrl)
            
            if not effect_sizes:
                raise ValueError("No valid effect sizes could be calculated")
            
            # Perform fixed or random effects meta-analysis
            weights = [1/v for v in variances]
            if model == "fixed":
                # Fixed effects model
                weighted_sum = sum(e * w for e, w in zip(effect_sizes, weights))
                sum_weights = sum(weights)
                pooled_effect = weighted_sum / sum_weights
                
                # Confidence interval
                pooled_variance = 1 / sum_weights
                se = pooled_variance**0.5
                ci_lower = pooled_effect - 1.96 * se
                ci_upper = pooled_effect + 1.96 * se
                
            else:
                # Random effects model (simplified)
                pooled_effect = mean(effect_sizes)
                se = stdev(effect_sizes) / (len(effect_sizes)**0.5) if len(effect_sizes) > 1 else 0
                ci_lower = pooled_effect - 1.96 * se
                ci_upper = pooled_effect + 1.96 * se
            
            # Calculate heterogeneity (I²)
            if len(effect_sizes) > 1:
                Q = sum(w * (e - pooled_effect)**2 for e, w in zip(effect_sizes, weights))
                df = len(effect_sizes) - 1
                I2 = max(0, (Q - df) / Q * 100) if Q > 0 else 0
            else:
                I2 = 0
            
            # P-value (simplified)
            z_score = pooled_effect / se if se > 0 else 0
            p_value = 2 * (1 - abs(z_score) / 1.96) if abs(z_score) <= 1.96 else 0.05
            
            # Create forest plot data
            forest_plot_data = {
                "studies": [
                    {
                        "study_id": f"Study_{i+1}",
                        "effect_size": effect_sizes[i],
                        "ci_lower": effect_sizes[i] - 1.96 * (variances[i]**0.5),
                        "ci_upper": effect_sizes[i] + 1.96 * (variances[i]**0.5),
                        "weight": weights[i] / sum(weights) * 100
                    }
                    for i in range(len(effect_sizes))
                ],
                "pooled_effect": pooled_effect,
                "pooled_ci_lower": ci_lower,
                "pooled_ci_upper": ci_upper
            }
            
            return MetaAnalysisResult(
                outcome_name=outcome_name,
                pooled_effect=pooled_effect,
                ci=(ci_lower, ci_upper),
                heterogeneity_i2=I2,
                studies_included=len(effect_sizes),
                total_participants=sum(sample_sizes),
                p_value=p_value,
                forest_plot_data=forest_plot_data
            )
            
        except Exception as e:
            logger.error(f"Error performing meta-analysis: {e}")
            raise
    
    async def _generate_evidence_table(self, lit_review_id: str, studies: List[Dict[str, Any]], outcomes: List[Dict[str, Any]]) -> EvidenceTable:
        """Generate structured evidence table."""
        try:
            table_id = str(uuid.uuid4())
            
            # Process outcomes data
            outcome_data = []
            for outcome in outcomes:
                outcome_datum = OutcomeDatum(
                    record_id=outcome.get("record_id", str(uuid.uuid4())),
                    outcome_name=outcome.get("outcome_name", ""),
                    group_labels=outcome.get("group_labels", []),
                    means=outcome.get("means", []),
                    sds=outcome.get("sds", []),
                    ns=outcome.get("ns", [])
                )
                outcome_data.append(outcome_datum)
            
            # Generate summary statistics
            summary_stats = {
                "total_studies": len(studies),
                "total_participants": sum(s.get("sample_size", 0) for s in studies if s.get("sample_size")),
                "study_designs": {},
                "outcome_measures": len(outcome_data),
                "risk_of_bias_summary": {}
            }
            
            # Study design distribution
            for study in studies:
                design = study.get("study_design", "unknown")
                summary_stats["study_designs"][design] = summary_stats["study_designs"].get(design, 0) + 1
            
            # Risk of bias summary
            rob_categories = ["low", "unclear", "high"]
            for category in rob_categories:
                count = sum(1 for s in studies if s.get("risk_of_bias", {}).get("overall") == category)
                summary_stats["risk_of_bias_summary"][category] = count
            
            return EvidenceTable(
                table_id=table_id,
                lit_review_id=lit_review_id,
                studies=studies,
                outcomes=outcome_data,
                summary_statistics=summary_stats
            )
            
        except Exception as e:
            logger.error(f"Error generating evidence table: {e}")
            raise


# Request/Response models for FastAPI
class DataExtractionRequest(BaseModel):
    studies: List[Dict[str, Any]] = Field(description="Studies to extract data from")
    extraction_template: Dict[str, Any] = Field(default_factory=dict, description="Data extraction template")


class EvidenceSynthesisRequest(BaseModel):
    studies: List[Dict[str, Any]] = Field(description="Studies to synthesize")
    synthesis_type: str = Field(default="narrative", description="Type of synthesis: narrative, thematic, framework")


class MetaAnalysisRequest(BaseModel):
    outcome_data: List[Dict[str, Any]] = Field(description="Outcome data for meta-analysis")
    outcome_name: str = Field(description="Name of the outcome measure")
    analysis_model: str = Field(default="fixed", description="Analysis model: fixed or random")


class EvidenceTableRequest(BaseModel):
    lit_review_id: str = Field(description="Literature review ID")
    studies: List[Dict[str, Any]] = Field(description="Studies for evidence table")
    outcomes: List[Dict[str, Any]] = Field(default_factory=list, description="Outcome data")


class TaskRequest(BaseModel):
    action: str
    payload: Dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    agent_type: str
    mcp_connected: bool
    capabilities: List[str]
    processing_capabilities: List[str]


# Global service instance
synthesis_service: Optional[SynthesisReviewService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global synthesis_service
    
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
    
    # Start service
    synthesis_service = SynthesisReviewService(config)
    await synthesis_service.start()
    
    try:
        yield
    finally:
        # Cleanup
        if synthesis_service:
            await synthesis_service.stop()


# FastAPI application
app = FastAPI(
    title="Synthesis & Review Service",
    description="Synthesis & Review Agent for data extraction and meta-analysis",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    if not synthesis_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    capabilities = [
        "data_extraction",
        "evidence_synthesis",
        "meta_analysis",
        "statistical_aggregation",
        "evidence_table_generation",
        "outcome_extraction"
    ]
    
    processing_capabilities = [
        "narrative_synthesis",
        "thematic_synthesis", 
        "framework_synthesis",
        "forest_plot_generation",
        "heterogeneity_assessment"
    ]
    
    return HealthResponse(
        status="healthy",
        agent_type="synthesis_review",
        mcp_connected=synthesis_service.mcp_connected,
        capabilities=capabilities,
        processing_capabilities=processing_capabilities
    )


@app.post("/extract")
async def extract_data(request: DataExtractionRequest):
    """Extract data from studies."""
    if not synthesis_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        result = await synthesis_service._handle_extract_data({
            "studies": request.studies,
            "extraction_template": request.extraction_template
        })
        return result
    except Exception as e:
        logger.error(f"Error extracting data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/synthesize")
async def synthesize_evidence(request: EvidenceSynthesisRequest):
    """Synthesize evidence from studies."""
    if not synthesis_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        result = await synthesis_service._handle_synthesize_evidence({
            "studies": request.studies,
            "synthesis_type": request.synthesis_type
        })
        return result
    except Exception as e:
        logger.error(f"Error synthesizing evidence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/meta-analysis")
async def perform_meta_analysis(request: MetaAnalysisRequest):
    """Perform meta-analysis."""
    if not synthesis_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        result = await synthesis_service._handle_perform_meta_analysis({
            "outcome_data": request.outcome_data,
            "outcome_name": request.outcome_name,
            "analysis_model": request.analysis_model
        })
        return result
    except Exception as e:
        logger.error(f"Error performing meta-analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/evidence-table")
async def generate_evidence_table(request: EvidenceTableRequest):
    """Generate evidence table."""
    if not synthesis_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        result = await synthesis_service._handle_generate_evidence_table({
            "lit_review_id": request.lit_review_id,
            "studies": request.studies,
            "outcomes": request.outcomes
        })
        return result
    except Exception as e:
        logger.error(f"Error generating evidence table: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/task")
async def process_task(request: TaskRequest):
    """Process a synthesis task directly (for testing)."""
    if not synthesis_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        result = await synthesis_service._process_synthesis_task({
            "action": request.action,
            "payload": request.payload
        })
        return result
    except Exception as e:
        logger.error(f"Error processing task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "synthesis_service:app",
        host="0.0.0.0",
        port=8005,
        log_level="info"
    )

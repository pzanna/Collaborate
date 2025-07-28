"""
Synthesis Agent - Pure MCP Client Implementation

Architecture-compliant synthesis agent that specializes in:
- Data extraction and evidence synthesis
- Meta-analysis and statistical aggregation
- Evidence table generation and management
- Pure MCP protocol communication only
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import sys
from statistics import mean, stdev
from dataclasses import dataclass, field

# Import base MCP agent
sys.path.append('/app')
from base_mcp_agent import BaseMCPAgent, create_agent_main

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


class SynthesisAgent(BaseMCPAgent):
    """
    Synthesis Agent - Pure MCP Client
    
    Handles evidence synthesis, meta-analysis, and statistical aggregation
    through MCP protocol only.
    """
    
    def __init__(self, agent_type: str, config: Dict[str, Any]):
        """Initialize Synthesis Agent."""
        super().__init__(agent_type, config)
        
        # Synthesis-specific configuration
        self.min_studies_for_meta = config.get("min_studies_for_meta", 2)
        self.significance_level = config.get("significance_level", 0.05)
        self.heterogeneity_threshold = config.get("heterogeneity_threshold", 75.0)
        
        self.logger.info("Synthesis Agent initialized with MCP client")
    
    def get_capabilities(self) -> List[str]:
        """Return synthesis agent capabilities."""
        return [
            "data_extraction",
            "evidence_synthesis",
            "meta_analysis", 
            "statistical_aggregation",
            "evidence_table_generation",
            "outcome_extraction",
            "forest_plot_generation",
            "heterogeneity_assessment",
            "narrative_synthesis",
            "thematic_synthesis",
            "framework_synthesis"
        ]
    
    def setup_task_handlers(self) -> Dict[str, Any]:
        """Setup task handlers for synthesis operations."""
        return {
            "extract_data": self._handle_extract_data,
            "synthesize_evidence": self._handle_synthesize_evidence,
            "perform_meta_analysis": self._handle_perform_meta_analysis,
            "generate_evidence_table": self._handle_generate_evidence_table,
            "narrative_synthesis": self._handle_narrative_synthesis,
            "thematic_synthesis": self._handle_thematic_synthesis,
            "framework_synthesis": self._handle_framework_synthesis,
            "assess_heterogeneity": self._handle_assess_heterogeneity
        }
    
    # Task Handlers
    
    async def _handle_extract_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle data extraction from studies."""
        try:
            studies = data.get("studies", [])
            extraction_template = data.get("extraction_template", {})
            
            if not studies:
                raise ValueError("Studies data is required")
            
            self.logger.info(f"Extracting data from {len(studies)} studies")
            
            # Process studies
            extracted_data = []
            for study in studies:
                extracted_study = await self._extract_study_data(study, extraction_template)
                extracted_data.append(extracted_study)
            
            return {
                "extracted_data": extracted_data,
                "studies_processed": len(extracted_data),
                "extraction_template_applied": bool(extraction_template),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error in data extraction: {e}")
            raise
    
    async def _handle_synthesize_evidence(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle evidence synthesis."""
        try:
            studies = data.get("studies", [])
            synthesis_type = data.get("synthesis_type", "narrative")
            
            if not studies:
                raise ValueError("Studies data is required")
            
            self.logger.info(f"Synthesizing evidence from {len(studies)} studies using {synthesis_type} approach")
            
            # Perform synthesis based on type
            if synthesis_type == "narrative":
                synthesis_data = await self._narrative_synthesis(studies)
            elif synthesis_type == "thematic":
                themes = await self._thematic_synthesis(studies)
                synthesis_data = {"themes": themes}
            elif synthesis_type == "framework":
                synthesis_data = await self._framework_synthesis(studies)
            else:
                raise ValueError(f"Unknown synthesis type: {synthesis_type}")
            
            # Identify research gaps
            gaps = await self._identify_research_gaps(studies)
            
            # Generate recommendations  
            recommendations = await self._generate_recommendations(studies)
            
            # Combine all results
            synthesis_result = {
                "synthesis_type": synthesis_type,
                "studies_count": len(studies),
                "synthesis_data": synthesis_data,
                "gaps": gaps,
                "recommendations": recommendations,
                "timestamp": datetime.now().isoformat()
            }
            
            return synthesis_result
            
        except Exception as e:
            self.logger.error(f"Error in evidence synthesis: {e}")
            raise
    
    async def _handle_perform_meta_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle meta-analysis execution."""
        try:
            outcome_data = data.get("outcome_data", [])
            outcome_name = data.get("outcome_name", "")
            analysis_model = data.get("analysis_model", "fixed")
            
            if len(outcome_data) < self.min_studies_for_meta:
                raise ValueError(f"Minimum {self.min_studies_for_meta} studies required for meta-analysis")
            
            self.logger.info(f"Performing {analysis_model} effects meta-analysis on {outcome_name}")
            
            # Perform meta-analysis
            meta_result = await self._perform_meta_analysis(outcome_data, outcome_name, analysis_model)
            
            return {
                "outcome_name": meta_result.outcome_name,
                "pooled_effect": meta_result.pooled_effect,
                "confidence_interval": list(meta_result.ci),
                "heterogeneity_i2": meta_result.heterogeneity_i2,
                "studies_included": meta_result.studies_included,
                "total_participants": meta_result.total_participants,
                "p_value": meta_result.p_value,
                "forest_plot_data": meta_result.forest_plot_data,
                "analysis_model": analysis_model,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error in meta-analysis: {e}")
            raise
    
    async def _handle_generate_evidence_table(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle evidence table generation."""
        try:
            lit_review_id = data.get("lit_review_id", str(uuid.uuid4()))
            studies = data.get("studies", [])
            outcomes = data.get("outcomes", [])
            
            if not studies:
                raise ValueError("Studies data is required")
            
            self.logger.info(f"Generating evidence table for {len(studies)} studies")
            
            # Generate evidence table
            evidence_table = await self._generate_evidence_table(lit_review_id, studies, outcomes)
            
            return {
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
                "created_at": evidence_table.created_at.isoformat(),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error generating evidence table: {e}")
            raise
    
    async def _handle_narrative_synthesis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle narrative synthesis specifically."""
        studies = data.get("studies", [])
        return await self._narrative_synthesis(studies)
    
    async def _handle_thematic_synthesis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle thematic synthesis specifically."""
        studies = data.get("studies", [])
        themes = await self._thematic_synthesis(studies)
        return {"themes": themes}
    
    async def _handle_framework_synthesis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle framework synthesis specifically."""
        studies = data.get("studies", [])
        return await self._framework_synthesis(studies)
    
    async def _handle_assess_heterogeneity(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle heterogeneity assessment."""
        try:
            outcome_data = data.get("outcome_data", [])
            
            if len(outcome_data) < 2:
                raise ValueError("Minimum 2 studies required for heterogeneity assessment")
            
            # Calculate I² statistic (simplified)
            effect_sizes = [d.get("effect_size", 0) for d in outcome_data if d.get("effect_size") is not None]
            
            if len(effect_sizes) < 2:
                i2 = 0
                interpretation = "Cannot assess - insufficient effect sizes"
            else:
                # Simplified I² calculation
                mean_effect = mean(effect_sizes)
                q_statistic = sum((es - mean_effect) ** 2 for es in effect_sizes)
                df = len(effect_sizes) - 1
                i2 = max(0, (q_statistic - df) / q_statistic * 100) if q_statistic > 0 else 0
                
                # Interpret I²
                if i2 < 25:
                    interpretation = "Low heterogeneity"
                elif i2 < 50:
                    interpretation = "Moderate heterogeneity" 
                elif i2 < 75:
                    interpretation = "Substantial heterogeneity"
                else:
                    interpretation = "Considerable heterogeneity"
            
            return {
                "i2_statistic": i2,
                "interpretation": interpretation,
                "studies_analyzed": len(effect_sizes),
                "heterogeneity_threshold": self.heterogeneity_threshold,
                "exceeds_threshold": i2 > self.heterogeneity_threshold,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error in heterogeneity assessment: {e}")
            raise
    
    # Business Logic Methods
    
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
            self.logger.error(f"Error extracting study data: {e}")
            return {"error": str(e), "study_id": study.get("id", "unknown")}
    
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
            sample_sizes = []
            for study in studies:
                # Study design distribution
                design = study.get("study_design", "unknown")
                summary["study_designs"][design] = summary["study_designs"].get(design, 0) + 1
                
                # Population characteristics
                sample_size = study.get("sample_size")
                if sample_size and isinstance(sample_size, (int, float)):
                    sample_sizes.append(sample_size)
                
                # Intervention types
                intervention = study.get("intervention", "")
                if intervention:
                    summary["intervention_types"][intervention] = summary["intervention_types"].get(intervention, 0) + 1
            
            # Calculate summary statistics
            if sample_sizes:
                summary["population_characteristics"]["total_participants"] = sum(sample_sizes)
                summary["population_characteristics"]["mean_sample_size"] = round(mean(sample_sizes), 2)
                summary["population_characteristics"]["median_sample_size"] = sorted(sample_sizes)[len(sample_sizes)//2]
                if len(sample_sizes) > 1:
                    summary["population_characteristics"]["sample_size_range"] = [min(sample_sizes), max(sample_sizes)]
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error in narrative synthesis: {e}")
            return {"error": str(e)}
    
    async def _thematic_synthesis(self, studies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Perform thematic synthesis."""
        try:
            themes = []
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
                                    "frequency": 0,
                                    "description": outcome.get("description", "")
                                }
                            outcome_themes[outcome_name]["studies"].append(study.get("id", ""))
                            outcome_themes[outcome_name]["frequency"] += 1
            
            # Convert to list and sort by frequency
            themes = list(outcome_themes.values())
            themes.sort(key=lambda x: x["frequency"], reverse=True)
            
            return themes
            
        except Exception as e:
            self.logger.error(f"Error in thematic synthesis: {e}")
            return []
    
    async def _framework_synthesis(self, studies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform framework-based synthesis."""
        try:
            framework = {
                "intervention_components": {},
                "mechanism_of_action": {},
                "contextual_factors": {},
                "outcomes_pathway": {},
                "theoretical_framework": "Evidence-based practice framework"
            }
            
            # Analyze intervention components
            for study in studies:
                intervention = study.get("intervention", "")
                if intervention:
                    # Simple component parsing
                    components = [comp.strip() for comp in intervention.split(",")]
                    for component in components:
                        if component:
                            framework["intervention_components"][component] = \
                                framework["intervention_components"].get(component, 0) + 1
                
                # Extract contextual factors
                setting = study.get("setting", "")
                if setting:
                    framework["contextual_factors"][setting] = \
                        framework["contextual_factors"].get(setting, 0) + 1
            
            return framework
            
        except Exception as e:
            self.logger.error(f"Error in framework synthesis: {e}")
            return {"error": str(e)}
    
    async def _identify_research_gaps(self, studies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify research gaps from studies."""
        try:
            gaps = []
            
            # Analyze study designs
            designs = {}
            for study in studies:
                design = study.get("study_design", "unknown")
                designs[design] = designs.get(design, 0) + 1
            
            # Methodological gaps
            rct_count = designs.get("randomized_controlled_trial", 0) + designs.get("RCT", 0)
            if rct_count < len(studies) * 0.5:
                gaps.append({
                    "type": "methodological",
                    "gap": "Limited randomized controlled trials",
                    "recommendation": "More RCTs needed for stronger evidence",
                    "priority": "high"
                })
            
            # Population gaps
            sample_sizes = [s.get("sample_size", 0) for s in studies if s.get("sample_size")]
            total_participants = sum(sample_sizes)
            if total_participants < 1000:
                gaps.append({
                    "type": "population",
                    "gap": "Small total sample size",
                    "recommendation": "Larger studies needed for adequate power",
                    "priority": "medium"
                })
            
            # Duration gaps
            long_term_studies = sum(1 for s in studies if s.get("follow_up_duration", 0) > 12)
            if long_term_studies < len(studies) * 0.3:
                gaps.append({
                    "type": "temporal",
                    "gap": "Limited long-term follow-up studies",
                    "recommendation": "Need studies with longer follow-up periods",
                    "priority": "medium"
                })
            
            return gaps
            
        except Exception as e:
            self.logger.error(f"Error identifying research gaps: {e}")
            return []
    
    async def _generate_recommendations(self, studies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate evidence-based recommendations."""
        try:
            recommendations = []
            
            # Quality assessment
            high_quality_studies = [
                s for s in studies 
                if s.get("risk_of_bias", {}).get("overall", "") in ["low", "Low"]
            ]
            
            quality_ratio = len(high_quality_studies) / len(studies) if studies else 0
            
            if quality_ratio > 0.6:
                recommendations.append({
                    "type": "clinical",
                    "strength": "strong",
                    "recommendation": "High-quality evidence supports intervention effectiveness",
                    "confidence": "high",
                    "quality_ratio": round(quality_ratio, 2)
                })
            else:
                recommendations.append({
                    "type": "research",
                    "strength": "conditional",
                    "recommendation": "More high-quality studies needed before clinical recommendations",
                    "confidence": "low",
                    "quality_ratio": round(quality_ratio, 2)
                })
            
            # Sample size recommendations
            total_participants = sum(s.get("sample_size", 0) for s in studies if s.get("sample_size"))
            if total_participants > 2000:
                recommendations.append({
                    "type": "statistical",
                    "strength": "strong", 
                    "recommendation": "Adequate sample size for reliable effect estimates",
                    "confidence": "high",
                    "total_participants": total_participants
                })
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
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
            
            # Perform meta-analysis
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
            p_value = 2 * (1 - min(abs(z_score) / 1.96, 1)) if abs(z_score) <= 1.96 else 0.001
            
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
            self.logger.error(f"Error performing meta-analysis: {e}")
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
                "risk_of_bias_summary": {},
                "publication_years": []
            }
            
            # Study design distribution
            for study in studies:
                design = study.get("study_design", "unknown")
                summary_stats["study_designs"][design] = summary_stats["study_designs"].get(design, 0) + 1
                
                # Publication years
                year = study.get("year")
                if year:
                    summary_stats["publication_years"].append(year)
            
            # Risk of bias summary
            rob_categories = ["low", "unclear", "high"]
            for category in rob_categories:
                count = sum(1 for s in studies if s.get("risk_of_bias", {}).get("overall") == category)
                summary_stats["risk_of_bias_summary"][category] = count
            
            # Year range
            if summary_stats["publication_years"]:
                summary_stats["year_range"] = [
                    min(summary_stats["publication_years"]),
                    max(summary_stats["publication_years"])
                ]
            
            return EvidenceTable(
                table_id=table_id,
                lit_review_id=lit_review_id,
                studies=studies,
                outcomes=outcome_data,
                summary_statistics=summary_stats
            )
            
        except Exception as e:
            self.logger.error(f"Error generating evidence table: {e}")
            raise


# Create main entry point
main = create_agent_main(SynthesisAgent, "synthesis")

if __name__ == "__main__":
    asyncio.run(main())

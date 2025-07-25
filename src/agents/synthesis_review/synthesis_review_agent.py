"""
Synthesis & Review Agent (SRA) for the Eunice Research Platform.

This agent analyzes included studies, extracts key data, and synthesizes findings
into structured summaries and meta-analysis outputs.

Based on the Literature Review Agents Design Specification.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field
from ..base_agent import BaseAgent
from ...config.config_manager import ConfigManager


class OutcomeDatum(BaseModel):
    """Outcome data model for extracted study results."""
    record_id: str = Field(description="Record identifier")
    outcome_name: str = Field(description="Outcome measure name")
    group_labels: List[str] = Field(description="Study group labels")
    means: List[float] = Field(description="Group means")
    sds: List[float] = Field(description="Standard deviations")
    ns: List[int] = Field(description="Sample sizes")


class MetaAnalysisResult(BaseModel):
    """Meta-analysis result data model."""
    outcome_name: str = Field(description="Outcome measure name")
    pooled_effect: float = Field(description="Pooled effect size")
    ci: Tuple[float, float] = Field(description="Confidence interval")
    heterogeneity_i2: float = Field(description="I² heterogeneity statistic")
    studies_included: int = Field(description="Number of studies included")
    total_participants: int = Field(description="Total number of participants")


class EvidenceTable(BaseModel):
    """Evidence table data model."""
    table_id: str = Field(description="Table identifier")
    lit_review_id: str = Field(description="Literature review identifier")
    studies: List[Dict[str, Any]] = Field(description="Study data")
    outcomes: List[OutcomeDatum] = Field(description="Extracted outcomes")
    created_at: datetime = Field(default_factory=datetime.now)


class SynthesisReviewAgent(BaseAgent):
    """
    Synthesis & Review Agent for data extraction and meta-analysis.
    
    Core Responsibilities:
    - Extract structured data from full-text studies
    - Aggregate findings to perform meta-analysis
    - Generate evidence tables and quality assessments
    - Create narrative synthesis summaries
    """

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the Synthesis & Review Agent.

        Args:
            config_manager: Configuration manager instance
        """
        super().__init__("synthesis_review", config_manager)
        self.logger = logging.getLogger(__name__)
        
        # Initialize storage
        self.evidence_tables: Dict[str, EvidenceTable] = {}
        self.meta_analyses: Dict[str, List[MetaAnalysisResult]] = {}

    async def extract_outcomes(
        self, 
        lit_review_id: str, 
        studies: List[Dict[str, Any]]
    ) -> List[OutcomeDatum]:
        """
        Extract outcome data from included studies.
        
        Args:
            lit_review_id: Literature review identifier
            studies: List of included studies
            
        Returns:
            List of extracted outcome data
        """
        self.logger.info(f"Extracting outcomes from {len(studies)} studies for review {lit_review_id}")
        
        all_outcomes = []
        
        for study in studies:
            try:
                study_id = study.get('id', study.get('record_id', f"study_{datetime.now().timestamp()}"))
                
                # Extract outcomes from PDF or structured content
                outcomes = await self._extract_study_outcomes(study_id, study)
                all_outcomes.extend(outcomes)
                
            except Exception as e:
                self.logger.error(f"Error extracting outcomes from study {study.get('id', 'unknown')}: {str(e)}")
                continue
        
        self.logger.info(f"Extracted {len(all_outcomes)} outcome measures")
        return all_outcomes

    async def _extract_study_outcomes(
        self, 
        study_id: str, 
        study: Dict[str, Any]
    ) -> List[OutcomeDatum]:
        """
        Extract outcomes from a single study.
        
        Args:
            study_id: Study identifier
            study: Study data
            
        Returns:
            List of outcome data for the study
        """
        outcomes = []
        
        # Simple extraction - in production this would use NLP/AI models
        # to parse PDFs and extract structured data
        
        # Look for structured outcome data
        if 'outcomes' in study:
            for outcome_data in study['outcomes']:
                try:
                    outcome = OutcomeDatum(
                        record_id=study_id,
                        outcome_name=outcome_data.get('name', 'Unknown'),
                        group_labels=outcome_data.get('groups', ['Control', 'Treatment']),
                        means=outcome_data.get('means', [0.0, 0.0]),
                        sds=outcome_data.get('sds', [1.0, 1.0]),
                        ns=outcome_data.get('ns', [10, 10])
                    )
                    outcomes.append(outcome)
                except Exception as e:
                    self.logger.warning(f"Error parsing outcome data: {str(e)}")
                    continue
        
        # Extract from abstract or results text (simplified)
        elif 'abstract' in study or 'results' in study:
            # This is a placeholder - real implementation would use NLP
            # to extract numerical data from text
            outcome = OutcomeDatum(
                record_id=study_id,
                outcome_name="Primary Outcome",
                group_labels=["Control", "Treatment"],
                means=[0.0, 0.0],  # Would be extracted from text
                sds=[1.0, 1.0],
                ns=[10, 10]
            )
            outcomes.append(outcome)
        
        return outcomes

    async def perform_meta_analysis(
        self, 
        lit_review_id: str, 
        outcomes: List[OutcomeDatum]
    ) -> List[MetaAnalysisResult]:
        """
        Perform meta-analysis on extracted outcomes.
        
        Args:
            lit_review_id: Literature review identifier
            outcomes: Extracted outcome data
            
        Returns:
            List of meta-analysis results
        """
        self.logger.info(f"Performing meta-analysis for review {lit_review_id}")
        
        # Group outcomes by outcome name
        outcome_groups = {}
        for outcome in outcomes:
            if outcome.outcome_name not in outcome_groups:
                outcome_groups[outcome.outcome_name] = []
            outcome_groups[outcome.outcome_name].append(outcome)
        
        meta_results = []
        
        for outcome_name, outcome_list in outcome_groups.items():
            try:
                # Perform meta-analysis for this outcome
                result = await self._calculate_pooled_effect(outcome_name, outcome_list)
                meta_results.append(result)
                
            except Exception as e:
                self.logger.error(f"Error in meta-analysis for {outcome_name}: {str(e)}")
                continue
        
        # Store results
        self.meta_analyses[lit_review_id] = meta_results
        
        self.logger.info(f"Completed meta-analysis: {len(meta_results)} outcomes analyzed")
        return meta_results

    async def _calculate_pooled_effect(
        self, 
        outcome_name: str, 
        outcomes: List[OutcomeDatum]
    ) -> MetaAnalysisResult:
        """
        Calculate pooled effect size for an outcome.
        
        Args:
            outcome_name: Name of the outcome
            outcomes: List of outcome data for this measure
            
        Returns:
            Meta-analysis result
        """
        if not outcomes:
            raise ValueError(f"No outcomes provided for {outcome_name}")
        
        # Simple fixed-effects meta-analysis (placeholder)
        # Real implementation would use proper statistical methods
        
        total_studies = len(outcomes)
        total_participants = sum(sum(outcome.ns) for outcome in outcomes)
        
        # Calculate weighted mean difference (simplified)
        weighted_effects = []
        weights = []
        
        for outcome in outcomes:
            if len(outcome.means) >= 2 and len(outcome.sds) >= 2 and len(outcome.ns) >= 2:
                # Calculate effect size (mean difference)
                effect = outcome.means[1] - outcome.means[0]
                
                # Calculate weight (inverse variance, simplified)
                pooled_sd = (outcome.sds[0] + outcome.sds[1]) / 2
                weight = sum(outcome.ns) / (pooled_sd ** 2) if pooled_sd > 0 else 1.0
                
                weighted_effects.append(effect * weight)
                weights.append(weight)
        
        if not weights:
            raise ValueError(f"No valid effect sizes for {outcome_name}")
        
        # Calculate pooled effect
        total_weight = sum(weights)
        pooled_effect = sum(weighted_effects) / total_weight if total_weight > 0 else 0.0
        
        # Calculate confidence interval (simplified)
        se = (1.0 / total_weight) ** 0.5 if total_weight > 0 else 1.0
        ci_lower = pooled_effect - 1.96 * se
        ci_upper = pooled_effect + 1.96 * se
        
        # Calculate I² heterogeneity (simplified)
        heterogeneity_i2 = 0.0  # Would be calculated properly in real implementation
        
        return MetaAnalysisResult(
            outcome_name=outcome_name,
            pooled_effect=pooled_effect,
            ci=(ci_lower, ci_upper),
            heterogeneity_i2=heterogeneity_i2,
            studies_included=total_studies,
            total_participants=total_participants
        )

    async def generate_evidence_table(
        self, 
        lit_review_id: str, 
        studies: List[Dict[str, Any]], 
        outcomes: List[OutcomeDatum]
    ) -> EvidenceTable:
        """
        Generate evidence table from studies and outcomes.
        
        Args:
            lit_review_id: Literature review identifier
            studies: Included studies
            outcomes: Extracted outcomes
            
        Returns:
            Evidence table
        """
        table_id = f"evidence_{lit_review_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        evidence_table = EvidenceTable(
            table_id=table_id,
            lit_review_id=lit_review_id,
            studies=studies,
            outcomes=outcomes
        )
        
        # Store evidence table
        self.evidence_tables[table_id] = evidence_table
        
        self.logger.info(f"Generated evidence table {table_id} with {len(studies)} studies")
        
        return evidence_table

    async def create_narrative_synthesis(
        self, 
        lit_review_id: str, 
        studies: List[Dict[str, Any]], 
        meta_results: List[MetaAnalysisResult]
    ) -> str:
        """
        Create narrative synthesis of findings.
        
        Args:
            lit_review_id: Literature review identifier
            studies: Included studies
            meta_results: Meta-analysis results
            
        Returns:
            Narrative synthesis text
        """
        self.logger.info(f"Creating narrative synthesis for review {lit_review_id}")
        
        synthesis_parts = []
        
        # Overview
        synthesis_parts.append(f"## Narrative Synthesis\n")
        synthesis_parts.append(f"This synthesis includes {len(studies)} studies with analysis of {len(meta_results)} outcomes.\n")
        
        # Study characteristics
        synthesis_parts.append("### Study Characteristics\n")
        
        # Extract years for range
        years = []
        for study in studies:
            year = study.get('year')
            if year:
                years.append(int(year))
        
        if years:
            synthesis_parts.append(f"Studies were published between {min(years)} and {max(years)}.\n")
        
        # Meta-analysis results
        if meta_results:
            synthesis_parts.append("### Meta-Analysis Results\n")
            for result in meta_results:
                synthesis_parts.append(
                    f"- **{result.outcome_name}**: Pooled effect = {result.pooled_effect:.2f} "
                    f"(95% CI: {result.ci[0]:.2f} to {result.ci[1]:.2f}), "
                    f"I² = {result.heterogeneity_i2:.1f}%, "
                    f"{result.studies_included} studies, "
                    f"{result.total_participants} participants\n"
                )
        
        # Conclusions
        synthesis_parts.append("### Conclusions\n")
        synthesis_parts.append("The evidence suggests... [This would be generated based on results]\n")
        
        synthesis_text = "".join(synthesis_parts)
        
        self.logger.info("Completed narrative synthesis")
        return synthesis_text

    async def handle_action(self, action) -> Dict[str, Any]:
        """
        Handle research actions for synthesis and review.
        
        Args:
            action: Research action to handle
            
        Returns:
            Action result
        """
        try:
            action_type = getattr(action, 'action_type', getattr(action, 'type', 'unknown'))
            parameters = getattr(action, 'parameters', getattr(action, 'data', {}))
            
            if action_type == "extract_outcomes":
                outcomes = await self.extract_outcomes(
                    parameters.get('lit_review_id', ''),
                    parameters.get('studies', [])
                )
                return {
                    'status': 'success',
                    'agent': self.agent_id,
                    'action_type': action_type,
                    'result': [o.dict() for o in outcomes],
                    'timestamp': datetime.now().isoformat()
                }
            
            elif action_type == "perform_meta_analysis":
                # Parse outcomes from parameters
                outcome_data = parameters.get('outcomes', [])
                outcomes = [OutcomeDatum(**od) for od in outcome_data]
                
                results = await self.perform_meta_analysis(
                    parameters.get('lit_review_id', ''),
                    outcomes
                )
                return {
                    'status': 'success',
                    'agent': self.agent_id,
                    'action_type': action_type,
                    'result': [r.dict() for r in results],
                    'timestamp': datetime.now().isoformat()
                }
            
            elif action_type == "generate_evidence_table":
                outcome_data = parameters.get('outcomes', [])
                outcomes = [OutcomeDatum(**od) for od in outcome_data]
                
                evidence_table = await self.generate_evidence_table(
                    parameters.get('lit_review_id', ''),
                    parameters.get('studies', []),
                    outcomes
                )
                return {
                    'status': 'success',
                    'agent': self.agent_id,
                    'action_type': action_type,
                    'result': evidence_table.dict(),
                    'timestamp': datetime.now().isoformat()
                }
            
            else:
                return {
                    'status': 'error',
                    'agent': self.agent_id,
                    'action_type': action_type,
                    'error': f"Unsupported action type: {action_type}",
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Error handling action: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'agent': self.agent_id,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    async def get_health_status(self) -> Dict[str, Any]:
        """Get agent health status."""
        return {
            'agent': self.agent_id,
            'status': 'healthy',
            'evidence_tables': len(self.evidence_tables),
            'meta_analyses': len(self.meta_analyses),
            'timestamp': datetime.now().isoformat()
        }

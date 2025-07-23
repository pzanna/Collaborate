"""
Quality appraisal plugin architecture for systematic reviews.

This module provides a flexible plugin system for quality assessment tools including:
- ROBINS-I for non-randomized studies
- RoB 2 for randomized controlled trials  
- Custom assessment tools
- Inter-rater reliability metrics
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import json
from datetime import datetime

try:
    from ..utils.error_handler import handle_errors, ValidationError
    from ..utils.id_utils import generate_timestamped_id
    from ..storage.systematic_review_database import SystematicReviewDatabase
    from ..ai_clients.openai_client import OpenAIClient
except ImportError:
    # For testing or standalone use
    from utils.error_handler import handle_errors, ValidationError
    from utils.id_utils import generate_timestamped_id
    from storage.systematic_review_database import SystematicReviewDatabase
    from ai_clients.openai_client import OpenAIClient


class BiasLevel(Enum):
    """Bias assessment levels."""
    LOW = "low"
    MODERATE = "moderate"  
    SERIOUS = "serious"
    CRITICAL = "critical"
    NO_INFORMATION = "no_information"


class AssessmentDomain(Enum):
    """Quality assessment domains."""
    # ROBINS-I domains
    CONFOUNDING = "confounding"
    SELECTION = "selection"
    CLASSIFICATION_INTERVENTION = "classification_intervention"
    DEVIATION_INTERVENTION = "deviation_intervention"
    MISSING_DATA = "missing_data"
    MEASUREMENT_OUTCOME = "measurement_outcome"
    SELECTION_REPORTED_RESULT = "selection_reported_result"
    
    # RoB 2 domains
    RANDOMIZATION = "randomization"
    DEVIATION_INTENDED = "deviation_intended"
    MISSING_OUTCOME_DATA = "missing_outcome_data"
    MEASUREMENT_OUTCOME_ROB2 = "measurement_outcome_rob2"
    SELECTION_REPORTED_ROB2 = "selection_reported_rob2"


@dataclass
class DomainAssessment:
    """Assessment for a single domain."""
    domain: AssessmentDomain
    bias_level: BiasLevel
    rationale: str
    supporting_evidence: List[str]
    confidence: float
    reviewer: str
    timestamp: datetime


@dataclass
class QualityAssessment:
    """Complete quality assessment for a study."""
    study_id: str
    tool_id: str
    overall_bias: BiasLevel
    domain_assessments: List[DomainAssessment]
    overall_rationale: str
    assessor: str
    model_id: Optional[str] = None
    assessment_time: Optional[float] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class QualityAppraisalPlugin(ABC):
    """Abstract base class for quality appraisal plugins."""
    
    @property
    @abstractmethod
    def tool_id(self) -> str:
        """Unique identifier for the assessment tool."""
        pass
    
    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Human-readable name for the assessment tool."""
        pass
    
    @property
    @abstractmethod
    def applicable_study_types(self) -> List[str]:
        """List of study types this tool can assess."""
        pass
    
    @property
    @abstractmethod
    def assessment_domains(self) -> List[AssessmentDomain]:
        """List of domains this tool assesses."""
        pass
    
    @abstractmethod
    async def assess_study(
        self, 
        study: Dict[str, Any], 
        criteria: Dict[str, Any]
    ) -> QualityAssessment:
        """
        Conduct quality assessment for a study.
        
        Args:
            study: Study data including full text
            criteria: Assessment criteria and parameters
            
        Returns:
            Complete quality assessment
        """
        pass
    
    @abstractmethod
    def validate_assessment(self, assessment: QualityAssessment) -> List[str]:
        """
        Validate a quality assessment.
        
        Args:
            assessment: Quality assessment to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        pass


class QualityAppraisalManager:
    """Manager for quality appraisal plugins and assessments."""
    
    def __init__(self, database: SystematicReviewDatabase, ai_client: OpenAIClient):
        """
        Initialize quality appraisal manager.
        
        Args:
            database: Systematic review database instance
            ai_client: AI client for LLM assistance
        """
        self.database = database
        self.ai_client = ai_client
        self.plugins: Dict[str, QualityAppraisalPlugin] = {}
        self.default_assessor = "ai"
        
    def register_plugin(self, plugin: QualityAppraisalPlugin) -> None:
        """
        Register a quality appraisal plugin.
        
        Args:
            plugin: Plugin to register
        """
        self.plugins[plugin.tool_id] = plugin
        
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        Get list of available assessment tools.
        
        Returns:
            List of available tools with metadata
        """
        tools = []
        for plugin in self.plugins.values():
            tools.append({
                'tool_id': plugin.tool_id,
                'tool_name': plugin.tool_name,
                'applicable_study_types': plugin.applicable_study_types,
                'assessment_domains': [domain.value for domain in plugin.assessment_domains]
            })
        return tools
    
    def get_recommended_tool(self, study: Dict[str, Any]) -> Optional[str]:
        """
        Get recommended assessment tool for a study.
        
        Args:
            study: Study data
            
        Returns:
            Recommended tool ID or None
        """
        study_type = study.get('metadata', {}).get('study_type', '').lower()
        
        # Simple recommendation logic
        if 'randomized' in study_type or 'rct' in study_type:
            return 'rob2'  # RoB 2 for randomized trials
        elif any(word in study_type for word in ['cohort', 'case-control', 'cross-sectional']):
            return 'robins-i'  # ROBINS-I for non-randomized studies
        
        # Default to ROBINS-I for most studies
        return 'robins-i'
    
    @handle_errors(context="quality_assessment")
    async def assess_studies(
        self, 
        studies: List[Dict[str, Any]], 
        tool_id: Optional[str] = None,
        criteria: Optional[Dict[str, Any]] = None
    ) -> List[QualityAssessment]:
        """
        Assess quality for multiple studies.
        
        Args:
            studies: List of studies to assess
            tool_id: Specific tool to use (if None, auto-recommend)
            criteria: Assessment criteria
            
        Returns:
            List of quality assessments
        """
        assessments = []
        
        for study in studies:
            # Determine tool to use
            assessment_tool_id = tool_id or self.get_recommended_tool(study)
            
            if assessment_tool_id not in self.plugins:
                raise ValidationError(f"Assessment tool not available: {assessment_tool_id}")
            
            plugin = self.plugins[assessment_tool_id]
            
            # Conduct assessment
            assessment = await plugin.assess_study(study, criteria or {})
            assessments.append(assessment)
            
            # Save to database
            self._save_assessment(assessment)
        
        return assessments
    
    def _save_assessment(self, assessment: QualityAssessment) -> None:
        """Save quality assessment to database."""
        assessment_data = {
            'record_id': assessment.study_id,
            'tool_id': assessment.tool_id,
            'scores': json.dumps({
                'overall_bias': assessment.overall_bias.value,
                'domain_assessments': [
                    {
                        'domain': da.domain.value,
                        'bias_level': da.bias_level.value,
                        'rationale': da.rationale,
                        'supporting_evidence': da.supporting_evidence,
                        'confidence': da.confidence,
                        'reviewer': da.reviewer,
                        'timestamp': da.timestamp.isoformat()
                    }
                    for da in assessment.domain_assessments
                ]
            }),
            'justification': assessment.overall_rationale,
            'assessor': assessment.assessor,
            'model_id': assessment.model_id
        }
        
        self.database.create_bias_assessment(assessment_data)
    
    def get_assessments_by_study(self, study_id: str) -> List[QualityAssessment]:
        """
        Get all quality assessments for a study.
        
        Args:
            study_id: Study identifier
            
        Returns:
            List of quality assessments
        """
        with self.database.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM bias_assessments 
                WHERE record_id = ?
                ORDER BY timestamp DESC
            """, (study_id,))
            
            assessments = []
            for row in cursor.fetchall():
                assessment_data = json.loads(row['scores'])
                
                domain_assessments = []
                for da_data in assessment_data['domain_assessments']:
                    domain_assessments.append(DomainAssessment(
                        domain=AssessmentDomain(da_data['domain']),
                        bias_level=BiasLevel(da_data['bias_level']),
                        rationale=da_data['rationale'],
                        supporting_evidence=da_data['supporting_evidence'],
                        confidence=da_data['confidence'],
                        reviewer=da_data['reviewer'],
                        timestamp=datetime.fromisoformat(da_data['timestamp'])
                    ))
                
                assessments.append(QualityAssessment(
                    study_id=row['record_id'],
                    tool_id=row['tool_id'],
                    overall_bias=BiasLevel(assessment_data['overall_bias']),
                    domain_assessments=domain_assessments,
                    overall_rationale=row['justification'],
                    assessor=row['assessor'],
                    model_id=row['model_id'],
                    created_at=datetime.fromisoformat(row['timestamp'])
                ))
            
            return assessments
    
    def calculate_inter_rater_reliability(
        self, 
        study_ids: List[str], 
        tool_id: str
    ) -> Dict[str, Any]:
        """
        Calculate inter-rater reliability metrics.
        
        Args:
            study_ids: List of study IDs to analyze
            tool_id: Assessment tool to analyze
            
        Returns:
            Dictionary of reliability metrics
        """
        # Get assessments for specified studies and tool
        assessments_by_study = {}
        
        for study_id in study_ids:
            assessments = self.get_assessments_by_study(study_id)
            tool_assessments = [a for a in assessments if a.tool_id == tool_id]
            if len(tool_assessments) >= 2:  # Need at least 2 assessors
                assessments_by_study[study_id] = tool_assessments
        
        if not assessments_by_study:
            return {'error': 'Insufficient data for reliability analysis'}
        
        # Calculate agreement metrics
        domain_agreements = {}
        overall_agreements = []
        
        for study_id, assessments in assessments_by_study.items():
            # Overall bias agreement
            overall_bias_levels = [a.overall_bias for a in assessments]
            if len(set(overall_bias_levels)) == 1:
                overall_agreements.append(1.0)  # Perfect agreement
            else:
                overall_agreements.append(0.0)  # Disagreement
            
            # Domain-level agreement
            for domain in AssessmentDomain:
                if domain.value not in domain_agreements:
                    domain_agreements[domain.value] = []
                
                domain_bias_levels = []
                for assessment in assessments:
                    domain_assessment = next(
                        (da for da in assessment.domain_assessments if da.domain == domain), 
                        None
                    )
                    if domain_assessment:
                        domain_bias_levels.append(domain_assessment.bias_level)
                
                if len(domain_bias_levels) >= 2:
                    if len(set(domain_bias_levels)) == 1:
                        domain_agreements[domain.value].append(1.0)
                    else:
                        domain_agreements[domain.value].append(0.0)
        
        # Calculate summary statistics
        overall_agreement = sum(overall_agreements) / len(overall_agreements) if overall_agreements else 0.0
        
        domain_agreement_summary = {}
        for domain, agreements in domain_agreements.items():
            if agreements:
                domain_agreement_summary[domain] = sum(agreements) / len(agreements)
        
        return {
            'overall_agreement': overall_agreement,
            'domain_agreements': domain_agreement_summary,
            'studies_analyzed': len(assessments_by_study),
            'total_assessments': sum(len(assessments) for assessments in assessments_by_study.values())
        }


class BaseAIQualityPlugin(QualityAppraisalPlugin):
    """Base class for AI-assisted quality appraisal plugins."""
    
    def __init__(self, ai_client: OpenAIClient, assessor: str = "ai"):
        """
        Initialize AI quality plugin.
        
        Args:
            ai_client: AI client for LLM interactions
            assessor: Identifier for the assessor
        """
        self.ai_client = ai_client
        self.assessor = assessor
    
    async def assess_study(
        self, 
        study: Dict[str, Any], 
        criteria: Dict[str, Any]
    ) -> QualityAssessment:
        """Conduct AI-assisted quality assessment."""
        start_time = datetime.now()
        
        # Build assessment prompt
        prompt = self._build_assessment_prompt(study, criteria)
        
        # Get AI assessment
        try:
            response = self.ai_client.get_response(
                user_message=prompt,
                system_prompt=self._get_system_prompt()
            )
            
            # Parse assessment response
            assessment_data = self._parse_assessment_response(response)
            
            # Build domain assessments
            domain_assessments = []
            for domain_data in assessment_data['domains']:
                domain_assessments.append(DomainAssessment(
                    domain=AssessmentDomain(domain_data['domain']),
                    bias_level=BiasLevel(domain_data['bias_level']),
                    rationale=domain_data['rationale'],
                    supporting_evidence=domain_data.get('supporting_evidence', []),
                    confidence=domain_data.get('confidence', 0.8),
                    reviewer=self.assessor,
                    timestamp=datetime.now()
                ))
            
            # Calculate assessment time
            assessment_time = (datetime.now() - start_time).total_seconds()
            
            return QualityAssessment(
                study_id=study['id'],
                tool_id=self.tool_id,
                overall_bias=BiasLevel(assessment_data['overall_bias']),
                domain_assessments=domain_assessments,
                overall_rationale=assessment_data['overall_rationale'],
                assessor=self.assessor,
                model_id=self.ai_client.config.model,
                assessment_time=assessment_time
            )
            
        except Exception as e:
            # Return minimal assessment on failure
            return QualityAssessment(
                study_id=study['id'],
                tool_id=self.tool_id,
                overall_bias=BiasLevel.NO_INFORMATION,
                domain_assessments=[],
                overall_rationale=f"Assessment failed: {str(e)}",
                assessor=self.assessor
            )
    
    @abstractmethod
    def _build_assessment_prompt(self, study: Dict[str, Any], criteria: Dict[str, Any]) -> str:
        """Build assessment prompt for the specific tool."""
        pass
    
    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Get system prompt for the assessment tool."""
        pass
    
    def _parse_assessment_response(self, response: str) -> Dict[str, Any]:
        """
        Parse AI assessment response.
        
        Args:
            response: JSON response from AI
            
        Returns:
            Parsed assessment data
        """
        try:
            # Clean response and parse JSON
            cleaned_response = response.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
            
            assessment_data = json.loads(cleaned_response)
            
            # Validate required fields
            required_fields = ['overall_bias', 'domains', 'overall_rationale']
            for field in required_fields:
                if field not in assessment_data:
                    raise ValidationError(f"Missing required field: {field}")
            
            return assessment_data
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            raise ValidationError(f"Failed to parse assessment response: {str(e)}")
    
    def validate_assessment(self, assessment: QualityAssessment) -> List[str]:
        """Validate quality assessment."""
        errors = []
        
        # Check that all required domains are assessed
        assessed_domains = {da.domain for da in assessment.domain_assessments}
        required_domains = set(self.assessment_domains)
        
        missing_domains = required_domains - assessed_domains
        if missing_domains:
            errors.append(f"Missing assessments for domains: {[d.value for d in missing_domains]}")
        
        # Check overall bias consistency with domain assessments
        domain_bias_levels = [da.bias_level for da in assessment.domain_assessments]
        if domain_bias_levels:
            max_domain_bias = max(domain_bias_levels, key=lambda x: ['low', 'moderate', 'serious', 'critical', 'no_information'].index(x.value))
            
            overall_severity = ['low', 'moderate', 'serious', 'critical', 'no_information'].index(assessment.overall_bias.value)
            max_domain_severity = ['low', 'moderate', 'serious', 'critical', 'no_information'].index(max_domain_bias.value)
            
            if overall_severity < max_domain_severity:
                errors.append("Overall bias rating is less severe than worst domain rating")
        
        return errors

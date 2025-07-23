"""
Enhanced two-stage screening workflow for systematic reviews.

This module provides improved screening capabilities with:
- Enhanced confidence scoring algorithms
- Contextual decision explanations  
- Human-AI collaboration interfaces
- Batch processing optimization
- Conflict resolution workflows
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

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


class ScreeningStage(Enum):
    """Screening stages in systematic review."""
    TITLE_ABSTRACT = "title_abstract"
    FULL_TEXT = "full_text"


class ScreeningDecision(Enum):
    """Possible screening decisions."""
    INCLUDE = "include"
    EXCLUDE = "exclude"
    UNCERTAIN = "uncertain"
    HUMAN_REQUIRED = "human_required"


class ExclusionReason(Enum):
    """Standardized exclusion reason codes."""
    WRONG_POPULATION = "WRONG_POPULATION"
    WRONG_INTERVENTION = "WRONG_INTERVENTION"
    WRONG_COMPARISON = "WRONG_COMPARISON"
    WRONG_OUTCOME = "WRONG_OUTCOME"
    WRONG_STUDY_DESIGN = "WRONG_STUDY_DESIGN"
    NOT_PEER_REVIEWED = "NOT_PEER_REVIEWED"
    DUPLICATE = "DUPLICATE"
    LANGUAGE_BARRIER = "LANGUAGE_BARRIER"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    RETRACTED = "RETRACTED"
    OTHER = "OTHER"


@dataclass
class ScreeningResult:
    """Result of screening decision."""
    study_id: str
    decision: ScreeningDecision
    confidence_score: float
    rationale: str
    exclusion_reason: Optional[ExclusionReason] = None
    model_id: Optional[str] = None
    prompt_hash: Optional[str] = None
    processing_time: Optional[float] = None
    human_review_required: bool = False


@dataclass
class ScreeningBatch:
    """Batch of studies for screening."""
    batch_id: str
    studies: List[Dict[str, Any]]
    criteria: Dict[str, Any]
    stage: ScreeningStage
    created_at: datetime
    completed_at: Optional[datetime] = None
    results: Optional[List[ScreeningResult]] = None


class EnhancedScreeningWorkflow:
    """Enhanced screening workflow with improved AI assistance."""
    
    def __init__(self, database: SystematicReviewDatabase, ai_client: OpenAIClient):
        """
        Initialize enhanced screening workflow.
        
        Args:
            database: Systematic review database instance
            ai_client: AI client for LLM interactions
        """
        self.database = database
        self.ai_client = ai_client
        self.confidence_threshold = 0.8
        self.batch_size = 10
        
    @handle_errors(context="enhanced_screening_setup")
    def configure_screening(self, config: Dict[str, Any]) -> None:
        """
        Configure screening parameters.
        
        Args:
            config: Screening configuration including thresholds and settings
        """
        self.confidence_threshold = config.get('confidence_threshold', 0.8)
        self.batch_size = config.get('batch_size', 10)
        self.require_human_review = config.get('require_human_review', True)
        self.exclusion_reasons = [
            ExclusionReason(reason) for reason in config.get('exclusion_reasons', [])
        ]
        
    @handle_errors(context="title_abstract_screening")
    async def title_abstract_screening(
        self, 
        studies: List[Dict[str, Any]], 
        criteria: Dict[str, Any],
        task_id: str
    ) -> Dict[str, Any]:
        """
        Enhanced title/abstract screening with improved AI assistance.
        
        Args:
            studies: List of studies to screen
            criteria: Inclusion/exclusion criteria
            task_id: Task identifier
            
        Returns:
            Screening results with decisions and rationales
        """
        screening_results = []
        human_review_queue = []
        
        # Process in batches for efficiency
        for i in range(0, len(studies), self.batch_size):
            batch_studies = studies[i:i + self.batch_size]
            batch_id = generate_timestamped_id("batch")
            
            batch = ScreeningBatch(
                batch_id=batch_id,
                studies=batch_studies,
                criteria=criteria,
                stage=ScreeningStage.TITLE_ABSTRACT,
                created_at=datetime.now()
            )
            
            # Process batch
            batch_results = await self._process_screening_batch(batch, task_id)
            screening_results.extend(batch_results)
            
            # Identify studies requiring human review
            for result in batch_results:
                if result.human_review_required or result.confidence_score < self.confidence_threshold:
                    human_review_queue.append(result)
        
        # Save screening decisions to database
        for result in screening_results:
            decision_data = {
                'record_id': result.study_id,
                'stage': ScreeningStage.TITLE_ABSTRACT.value,
                'decision': result.decision.value,
                'reason_code': result.exclusion_reason.value if result.exclusion_reason else None,
                'actor': 'human_required' if result.human_review_required else 'ai',
                'confidence_score': result.confidence_score,
                'rationale': result.rationale,
                'model_id': result.model_id,
                'prompt_hash': result.prompt_hash
            }
            self.database.create_screening_decision(decision_data)
        
        return {
            'total_screened': len(studies),
            'included': len([r for r in screening_results if r.decision == ScreeningDecision.INCLUDE]),
            'excluded': len([r for r in screening_results if r.decision == ScreeningDecision.EXCLUDE]),
            'uncertain': len([r for r in screening_results if r.decision == ScreeningDecision.UNCERTAIN]),
            'human_review_required': len(human_review_queue),
            'screening_results': screening_results,
            'human_review_queue': human_review_queue
        }
    
    @handle_errors(context="full_text_screening")
    async def full_text_screening(
        self,
        studies: List[Dict[str, Any]], 
        criteria: Dict[str, Any],
        task_id: str
    ) -> Dict[str, Any]:
        """
        Enhanced full-text screening with detailed analysis.
        
        Args:
            studies: List of studies that passed title/abstract screening
            criteria: Detailed inclusion/exclusion criteria
            task_id: Task identifier
            
        Returns:
            Full-text screening results with detailed assessments
        """
        screening_results = []
        
        for study in studies:
            result = await self._screen_full_text_study(study, criteria, task_id)
            screening_results.append(result)
            
            # Save to database
            decision_data = {
                'record_id': study['id'],
                'stage': ScreeningStage.FULL_TEXT.value,
                'decision': result.decision.value,
                'reason_code': result.exclusion_reason.value if result.exclusion_reason else None,
                'actor': 'human_required' if result.human_review_required else 'ai',
                'confidence_score': result.confidence_score,
                'rationale': result.rationale,
                'model_id': result.model_id,
                'prompt_hash': result.prompt_hash
            }
            self.database.create_screening_decision(decision_data)
        
        return {
            'total_screened': len(studies),
            'included': len([r for r in screening_results if r.decision == ScreeningDecision.INCLUDE]),
            'excluded': len([r for r in screening_results if r.decision == ScreeningDecision.EXCLUDE]),
            'screening_results': screening_results
        }
    
    async def _process_screening_batch(
        self, 
        batch: ScreeningBatch, 
        task_id: str
    ) -> List[ScreeningResult]:
        """
        Process a batch of studies for screening.
        
        Args:
            batch: Batch of studies to process
            task_id: Task identifier
            
        Returns:
            List of screening results
        """
        results = []
        
        for study in batch.studies:
            result = await self._screen_title_abstract_study(study, batch.criteria, task_id)
            results.append(result)
        
        batch.results = results
        batch.completed_at = datetime.now()
        
        return results
    
    async def _screen_title_abstract_study(
        self, 
        study: Dict[str, Any], 
        criteria: Dict[str, Any],
        task_id: str
    ) -> ScreeningResult:
        """
        Screen individual study at title/abstract level.
        
        Args:
            study: Study to screen
            criteria: Screening criteria
            task_id: Task identifier
            
        Returns:
            Screening result with decision and rationale
        """
        start_time = datetime.now()
        
        # Construct screening prompt
        prompt = self._build_title_abstract_prompt(study, criteria)
        prompt_hash = self._hash_prompt(prompt)
        
        # Get AI screening decision
        try:
            response = self.ai_client.get_response(
                user_message=prompt,
                system_prompt=self._get_screening_system_prompt()
            )
            
            # Parse AI response
            decision_data = self._parse_screening_response(response)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Determine if human review is required
            human_review_required = (
                decision_data['confidence'] < self.confidence_threshold or
                decision_data['decision'] == 'uncertain' or
                self.require_human_review and decision_data['decision'] == 'exclude'
            )
            
            return ScreeningResult(
                study_id=study['id'],
                decision=ScreeningDecision(decision_data['decision']),
                confidence_score=decision_data['confidence'],
                rationale=decision_data['rationale'],
                exclusion_reason=ExclusionReason(decision_data['exclusion_reason']) if decision_data.get('exclusion_reason') else None,
                model_id=self.ai_client.config.model,
                prompt_hash=prompt_hash,
                processing_time=processing_time,
                human_review_required=human_review_required
            )
            
        except Exception as e:
            # Fallback to human review on AI failure
            return ScreeningResult(
                study_id=study['id'],
                decision=ScreeningDecision.HUMAN_REQUIRED,
                confidence_score=0.0,
                rationale=f"AI screening failed: {str(e)}",
                human_review_required=True
            )
    
    async def _screen_full_text_study(
        self, 
        study: Dict[str, Any], 
        criteria: Dict[str, Any],
        task_id: str
    ) -> ScreeningResult:
        """
        Screen individual study at full-text level.
        
        Args:
            study: Study to screen
            criteria: Detailed screening criteria
            task_id: Task identifier
            
        Returns:
            Screening result with detailed assessment
        """
        start_time = datetime.now()
        
        # Construct full-text screening prompt
        prompt = self._build_full_text_prompt(study, criteria)
        prompt_hash = self._hash_prompt(prompt)
        
        try:
            response = self.ai_client.get_response(
                user_message=prompt,
                system_prompt=self._get_full_text_screening_system_prompt()
            )
            
            # Parse AI response
            decision_data = self._parse_screening_response(response)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Full-text screening generally requires higher confidence
            human_review_required = decision_data['confidence'] < 0.9
            
            return ScreeningResult(
                study_id=study['id'],
                decision=ScreeningDecision(decision_data['decision']),
                confidence_score=decision_data['confidence'],
                rationale=decision_data['rationale'],
                exclusion_reason=ExclusionReason(decision_data['exclusion_reason']) if decision_data.get('exclusion_reason') else None,
                model_id=self.ai_client.config.model,
                prompt_hash=prompt_hash,
                processing_time=processing_time,
                human_review_required=human_review_required
            )
            
        except Exception as e:
            return ScreeningResult(
                study_id=study['id'],
                decision=ScreeningDecision.HUMAN_REQUIRED,
                confidence_score=0.0,
                rationale=f"Full-text screening failed: {str(e)}",
                human_review_required=True
            )
    
    def _build_title_abstract_prompt(self, study: Dict[str, Any], criteria: Dict[str, Any]) -> str:
        """Build prompt for title/abstract screening."""
        return f"""
Please screen this study for a systematic review based on the title and abstract.

STUDY INFORMATION:
Title: {study.get('title', 'No title available')}
Authors: {', '.join(study.get('authors', []))}
Year: {study.get('year', 'Unknown')}
Abstract: {study.get('abstract', 'No abstract available')}

INCLUSION CRITERIA:
Population: {criteria.get('population', 'Not specified')}
Intervention: {criteria.get('intervention', 'Not specified')}
Comparison: {criteria.get('comparison', 'Not specified')}
Outcomes: {', '.join(criteria.get('outcomes', []))}
Study Types: {', '.join(criteria.get('inclusion_criteria', {}).get('study_types', []))}

EXCLUSION CRITERIA:
{self._format_exclusion_criteria(criteria.get('exclusion_criteria', {}))}

Please provide your screening decision in JSON format:
{{
    "decision": "include|exclude|uncertain",
    "confidence": 0.0-1.0,
    "rationale": "Clear explanation of decision",
    "exclusion_reason": "reason_code_if_excluded"
}}
"""
    
    def _build_full_text_prompt(self, study: Dict[str, Any], criteria: Dict[str, Any]) -> str:
        """Build prompt for full-text screening."""
        return f"""
Please conduct detailed full-text screening for this study.

STUDY INFORMATION:
Title: {study.get('title', 'No title available')}
Authors: {', '.join(study.get('authors', []))}
Year: {study.get('year', 'Unknown')}
Journal: {study.get('metadata', {}).get('journal', 'Unknown')}
DOI: {study.get('doi', 'No DOI')}
Full Text: {study.get('full_text', 'Full text not available - assess based on available information')}

DETAILED INCLUSION CRITERIA:
{self._format_detailed_criteria(criteria)}

EXCLUSION CRITERIA:
{self._format_exclusion_criteria(criteria.get('exclusion_criteria', {}))}

Please provide your detailed screening decision in JSON format:
{{
    "decision": "include|exclude",
    "confidence": 0.0-1.0,
    "rationale": "Detailed explanation with specific references to criteria",
    "exclusion_reason": "reason_code_if_excluded",
    "data_extraction_notes": "Notes for evidence synthesis if included"
}}
"""
    
    def _get_screening_system_prompt(self) -> str:
        """Get system prompt for title/abstract screening."""
        return """
You are an expert research assistant conducting systematic literature review screening.
Your task is to evaluate studies for inclusion based on specific criteria.

Guidelines:
1. Be conservative - when in doubt, include for full-text review
2. Only exclude if clearly outside scope
3. Provide clear, evidence-based rationales
4. Use standardized exclusion reason codes
5. Assign confidence scores based on clarity of decision

Response must be valid JSON format only.
"""
    
    def _get_full_text_screening_system_prompt(self) -> str:
        """Get system prompt for full-text screening."""
        return """
You are an expert research assistant conducting detailed full-text screening for systematic reviews.
Your task is to make final inclusion/exclusion decisions based on complete study information.

Guidelines:
1. Thoroughly evaluate all inclusion/exclusion criteria
2. Provide detailed rationales with specific evidence
3. Be precise - this is the final inclusion decision
4. Note any data extraction points for included studies
5. Higher confidence required for final decisions

Response must be valid JSON format only.
"""
    
    def _format_exclusion_criteria(self, exclusion_criteria: Dict[str, Any]) -> str:
        """Format exclusion criteria for prompt."""
        criteria_text = []
        for key, value in exclusion_criteria.items():
            if value:
                criteria_text.append(f"- {key.replace('_', ' ').title()}: {value}")
        return '\n'.join(criteria_text) if criteria_text else "No specific exclusion criteria"
    
    def _format_detailed_criteria(self, criteria: Dict[str, Any]) -> str:
        """Format detailed criteria for full-text screening."""
        return f"""
Population: {criteria.get('population', 'Not specified')}
Intervention: {criteria.get('intervention', 'Not specified')}
Comparison: {criteria.get('comparison', 'Not specified')}  
Outcomes: {', '.join(criteria.get('outcomes', []))}
Study Design: {', '.join(criteria.get('inclusion_criteria', {}).get('study_types', []))}
Language: {', '.join(criteria.get('inclusion_criteria', {}).get('languages', []))}
Publication Type: {'Peer-reviewed only' if criteria.get('inclusion_criteria', {}).get('peer_reviewed') else 'All publication types'}
Time Frame: {criteria.get('timeframe', 'Not specified')}
"""
    
    def _parse_screening_response(self, response: str) -> Dict[str, Any]:
        """
        Parse AI screening response.
        
        Args:
            response: JSON response from AI
            
        Returns:
            Parsed decision data
        """
        try:
            # Clean response and parse JSON
            cleaned_response = response.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
            
            decision_data = json.loads(cleaned_response)
            
            # Validate required fields
            required_fields = ['decision', 'confidence', 'rationale']
            for field in required_fields:
                if field not in decision_data:
                    raise ValidationError(f"Missing required field: {field}")
            
            # Validate decision value
            valid_decisions = ['include', 'exclude', 'uncertain']
            if decision_data['decision'] not in valid_decisions:
                raise ValidationError(f"Invalid decision: {decision_data['decision']}")
            
            # Validate confidence score
            confidence = float(decision_data['confidence'])
            if not 0.0 <= confidence <= 1.0:
                raise ValidationError(f"Invalid confidence score: {confidence}")
            
            decision_data['confidence'] = confidence
            return decision_data
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            raise ValidationError(f"Failed to parse screening response: {str(e)}")
    
    def _hash_prompt(self, prompt: str) -> str:
        """Generate hash for prompt for caching/tracking."""
        import hashlib
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]


class ScreeningConflictResolver:
    """Resolve conflicts between multiple screening decisions."""
    
    def __init__(self, database: SystematicReviewDatabase):
        """
        Initialize conflict resolver.
        
        Args:
            database: Systematic review database instance
        """
        self.database = database
    
    @handle_errors(context="conflict_resolution")
    def resolve_conflicts(
        self, 
        task_id: str, 
        resolution_strategy: str = 'consensus'
    ) -> Dict[str, Any]:
        """
        Resolve screening conflicts for a task.
        
        Args:
            task_id: Task identifier
            resolution_strategy: Strategy for conflict resolution
            
        Returns:
            Conflict resolution results
        """
        # Get all screening decisions for task
        decisions = self._get_screening_decisions_by_task(task_id)
        
        # Group decisions by study and stage
        conflicts = self._identify_conflicts(decisions)
        
        # Resolve conflicts based on strategy
        if resolution_strategy == 'consensus':
            resolved = self._resolve_by_consensus(conflicts)
        elif resolution_strategy == 'highest_confidence':
            resolved = self._resolve_by_highest_confidence(conflicts)
        elif resolution_strategy == 'most_inclusive':
            resolved = self._resolve_by_most_inclusive(conflicts)
        else:
            raise ValidationError(f"Unknown resolution strategy: {resolution_strategy}")
        
        return {
            'conflicts_found': len(conflicts),
            'conflicts_resolved': len(resolved),
            'resolution_strategy': resolution_strategy,
            'resolved_decisions': resolved
        }
    
    def _identify_conflicts(self, decisions: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Identify conflicting decisions."""
        # Group decisions by study and stage
        grouped = {}
        for decision in decisions:
            key = f"{decision['record_id']}_{decision['stage']}"
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(decision)
        
        # Identify conflicts (multiple different decisions for same study/stage)
        conflicts = {}
        for key, decision_group in grouped.items():
            if len(decision_group) > 1:
                unique_decisions = set(d['decision'] for d in decision_group)
                if len(unique_decisions) > 1:
                    conflicts[key] = decision_group
        
        return conflicts
    
    def _resolve_by_consensus(self, conflicts: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Resolve conflicts by consensus (majority vote)."""
        resolved = []
        for key, decision_group in conflicts.items():
            decision_counts = {}
            for decision in decision_group:
                dec = decision['decision']
                if dec not in decision_counts:
                    decision_counts[dec] = []
                decision_counts[dec].append(decision)
            
            # Find majority decision
            majority_decision = max(decision_counts.keys(), key=lambda k: len(decision_counts[k]))
            majority_group = decision_counts[majority_decision]
            
            # Use highest confidence from majority group
            best_decision = max(majority_group, key=lambda d: d.get('confidence_score', 0))
            
            resolved.append({
                'study_id': best_decision['record_id'],
                'stage': best_decision['stage'],
                'final_decision': majority_decision,
                'resolution_method': 'consensus',
                'confidence': best_decision.get('confidence_score', 0),
                'rationale': f"Consensus decision from {len(majority_group)} reviewers"
            })
        
        return resolved
    
    def _resolve_by_highest_confidence(self, conflicts: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Resolve conflicts by selecting highest confidence decision."""
        resolved = []
        for key, decision_group in conflicts.items():
            best_decision = max(decision_group, key=lambda d: d.get('confidence_score', 0))
            
            resolved.append({
                'study_id': best_decision['record_id'],
                'stage': best_decision['stage'],
                'final_decision': best_decision['decision'],
                'resolution_method': 'highest_confidence',
                'confidence': best_decision.get('confidence_score', 0),
                'rationale': f"Highest confidence decision (score: {best_decision.get('confidence_score', 0):.2f})"
            })
        
        return resolved
    
    def _resolve_by_most_inclusive(self, conflicts: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Resolve conflicts by being most inclusive (prefer include over exclude)."""
        resolved = []
        for key, decision_group in conflicts.items():
            decisions = [d['decision'] for d in decision_group]
            
            # Preference order: include > uncertain > exclude
            if 'include' in decisions:
                final_decision = 'include'
                best_decision = next(d for d in decision_group if d['decision'] == 'include')
            elif 'uncertain' in decisions:
                final_decision = 'uncertain'
                best_decision = next(d for d in decision_group if d['decision'] == 'uncertain')
            else:
                final_decision = 'exclude'
                best_decision = max(decision_group, key=lambda d: d.get('confidence_score', 0))
            
            resolved.append({
                'study_id': best_decision['record_id'],
                'stage': best_decision['stage'],
                'final_decision': final_decision,
                'resolution_method': 'most_inclusive',
                'confidence': best_decision.get('confidence_score', 0),
                'rationale': f"Most inclusive decision from conflict resolution"
            })
        
        return resolved
    
    def _get_screening_decisions_by_task(self, task_id: str) -> List[Dict[str, Any]]:
        """Get all screening decisions for a task."""
        # Query the database for all screening decisions related to this task
        with self.database.get_connection() as conn:
            cursor = conn.execute("""
                SELECT sd.*, sr.task_id 
                FROM screening_decisions sd
                JOIN study_records sr ON sd.record_id = sr.id
                WHERE sr.task_id = ?
                ORDER BY sd.timestamp DESC
            """, (task_id,))
            
            decisions = []
            for row in cursor.fetchall():
                decisions.append(dict(row))
            
            return decisions

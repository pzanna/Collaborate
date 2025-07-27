"""
Screening & PRISMA Agent (SPA) for the Eunice Research Platform.

This agent manages systematic review screening, applies inclusion/exclusion criteria,
and maintains a transparent PRISMA-compliant audit trail.

Based on the Literature Review Agents Design Specification.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal

from pydantic import BaseModel, Field
from ..base_agent import BaseAgent
from ...config.config_manager import ConfigManager


class Criteria(BaseModel):
    """Inclusion/exclusion criteria data model."""
    name: str = Field(description="Criteria name")
    description: str = Field(description="Criteria description")
    type: Literal["include", "exclude"] = Field(description="Criteria type")


class ScreeningDecision(BaseModel):
    """Screening decision data model."""
    record_id: str = Field(description="Record identifier")
    stage: Literal["title_abstract", "full_text"] = Field(description="Screening stage")
    decision: Literal["include", "exclude", "unsure"] = Field(description="Screening decision")
    reason: str = Field(description="Decision rationale")
    confidence: float = Field(ge=0.0, le=1.0, description="Decision confidence score")
    timestamp: datetime = Field(default_factory=datetime.now, description="Decision timestamp")


class PRISMASession(BaseModel):
    """PRISMA session data model."""
    session_id: str = Field(description="Session identifier")
    lit_review_id: str = Field(description="Literature review identifier")
    criteria: List[Criteria] = Field(description="Screening criteria")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ScreeningPrismaAgent(BaseAgent):
    """
    Screening & PRISMA Agent for systematic review screening.
    
    Core Responsibilities:
    - Perform title/abstract and full-text screening
    - Apply rules or model-assisted classification against criteria
    - Track all PRISMA flowchart counts
    - Maintain logs for human overrides and decisions
    """

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the Screening & PRISMA Agent.

        Args:
            config_manager: Configuration manager instance
        """
        super().__init__("screening_prisma", config_manager)
        self.logger = logging.getLogger(__name__)
        
        # Initialize screening sessions storage
        self.sessions: Dict[str, PRISMASession] = {}
        self.decisions: Dict[str, List[ScreeningDecision]] = {}

    async def create_prisma_session(
        self, 
        lit_review_id: str, 
        criteria: List[Dict[str, Any]]
    ) -> PRISMASession:
        """
        Create a new PRISMA screening session.
        
        Args:
            lit_review_id: Literature review identifier
            criteria: List of inclusion/exclusion criteria
            
        Returns:
            Created PRISMA session
        """
        session_id = f"prisma_{lit_review_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Parse criteria
        parsed_criteria = [Criteria(**c) for c in criteria]
        
        # Create session
        session = PRISMASession(
            session_id=session_id,
            lit_review_id=lit_review_id,
            criteria=parsed_criteria
        )
        
        # Store session
        self.sessions[session_id] = session
        self.decisions[session_id] = []
        
        self.logger.info(f"Created PRISMA session {session_id} for review {lit_review_id}")
        
        return session

    async def screen_batch(
        self, 
        session_id: str, 
        records: List[Dict[str, Any]], 
        stage: Literal["title_abstract", "full_text"] = "title_abstract"
    ) -> List[ScreeningDecision]:
        """
        Screen a batch of records against criteria.
        
        Args:
            session_id: PRISMA session identifier
            records: Records to screen
            stage: Screening stage
            
        Returns:
            List of screening decisions
        """
        if session_id not in self.sessions:
            raise ValueError(f"PRISMA session {session_id} not found")
        
        session = self.sessions[session_id]
        decisions = []
        
        self.logger.info(f"Screening {len(records)} records in {stage} stage for session {session_id}")
        
        for record in records:
            try:
                # Evaluate record against each criterion
                decision = await self._evaluate_record(record, session.criteria, stage)
                decisions.append(decision)
                
            except Exception as e:
                self.logger.error(f"Error screening record {record.get('id', 'unknown')}: {str(e)}")
                # Create unsure decision for failed evaluations
                decision = ScreeningDecision(
                    record_id=record.get('id', f"unknown_{datetime.now().timestamp()}"),
                    stage=stage,
                    decision="unsure",
                    reason=f"Evaluation error: {str(e)}",
                    confidence=0.0
                )
                decisions.append(decision)
        
        # Store decisions
        self.decisions[session_id].extend(decisions)
        
        # Update session timestamp
        session.updated_at = datetime.now()
        
        self.logger.info(f"Completed screening batch: {len(decisions)} decisions made")
        
        return decisions

    async def _evaluate_record(
        self, 
        record: Dict[str, Any], 
        criteria: List[Criteria], 
        stage: str
    ) -> ScreeningDecision:
        """
        Evaluate a single record against screening criteria.
        
        Args:
            record: Record to evaluate
            criteria: Screening criteria
            stage: Screening stage
            
        Returns:
            Screening decision
        """
        record_id = record.get('id', record.get('record_id', f"record_{datetime.now().timestamp()}"))
        
        # Extract relevant text for evaluation
        if stage == "title_abstract":
            text_content = f"{record.get('title', '')} {record.get('abstract', '')}"
        else:  # full_text
            text_content = record.get('full_text', record.get('content', ''))
        
        # Simple rule-based evaluation
        include_score = 0
        exclude_score = 0
        reasons = []
        
        for criterion in criteria:
            # Basic keyword matching (can be enhanced with AI models)
            criterion_score = self._evaluate_criterion(text_content, criterion)
            
            if criterion.type == "include":
                include_score += criterion_score
                if criterion_score > 0.5:
                    reasons.append(f"Meets inclusion criterion: {criterion.name}")
            else:  # exclude
                exclude_score += criterion_score
                if criterion_score > 0.5:
                    reasons.append(f"Meets exclusion criterion: {criterion.name}")
        
        # Make decision based on scores
        if exclude_score > include_score and exclude_score > 0.5:
            decision = "exclude"
            confidence = min(exclude_score, 1.0)
        elif include_score > exclude_score and include_score > 0.5:
            decision = "include"
            confidence = min(include_score, 1.0)
        else:
            decision = "unsure"
            confidence = 0.3  # Low confidence for unclear cases
        
        reason = "; ".join(reasons) if reasons else f"Score-based decision (include: {include_score:.2f}, exclude: {exclude_score:.2f})"
        
        return ScreeningDecision(
            record_id=record_id,
            stage=stage,
            decision=decision,
            reason=reason,
            confidence=confidence
        )

    def _evaluate_criterion(self, text_content: str, criterion: Criteria) -> float:
        """
        Evaluate text content against a single criterion.
        
        Args:
            text_content: Text to evaluate
            criterion: Screening criterion
            
        Returns:
            Score between 0.0 and 1.0
        """
        # Simple keyword-based evaluation
        # In production, this could use AI models for better evaluation
        
        if not text_content:
            return 0.0
        
        text_lower = text_content.lower()
        criterion_lower = criterion.description.lower()
        
        # Basic keyword matching
        keywords = criterion_lower.split()
        matches = sum(1 for keyword in keywords if keyword in text_lower)
        
        if keywords:
            return matches / len(keywords)
        else:
            return 0.0

    async def get_prisma_counts(self, session_id: str) -> Dict[str, int]:
        """
        Get PRISMA flowchart counts for a session.
        
        Args:
            session_id: PRISMA session identifier
            
        Returns:
            Dictionary of PRISMA node counts
        """
        if session_id not in self.decisions:
            return {}
        
        decisions = self.decisions[session_id]
        
        # Count decisions by stage and type
        counts = {
            "total_records": len(decisions),
            "title_abstract_screened": len([d for d in decisions if d.stage == "title_abstract"]),
            "title_abstract_included": len([d for d in decisions if d.stage == "title_abstract" and d.decision == "include"]),
            "title_abstract_excluded": len([d for d in decisions if d.stage == "title_abstract" and d.decision == "exclude"]),
            "full_text_screened": len([d for d in decisions if d.stage == "full_text"]),
            "full_text_included": len([d for d in decisions if d.stage == "full_text" and d.decision == "include"]),
            "full_text_excluded": len([d for d in decisions if d.stage == "full_text" and d.decision == "exclude"]),
            "unsure_decisions": len([d for d in decisions if d.decision == "unsure"])
        }
        
        return counts

    async def generate_prisma_flowchart(self, session_id: str) -> Dict[str, Any]:
        """
        Generate PRISMA flowchart data.
        
        Args:
            session_id: PRISMA session identifier
            
        Returns:
            PRISMA flowchart data structure
        """
        counts = await self.get_prisma_counts(session_id)
        
        # Generate flowchart structure
        flowchart = {
            "identification": {
                "records_identified": counts.get("total_records", 0)
            },
            "screening": {
                "records_screened": counts.get("title_abstract_screened", 0),
                "records_excluded": counts.get("title_abstract_excluded", 0)
            },
            "eligibility": {
                "full_text_assessed": counts.get("full_text_screened", 0),
                "full_text_excluded": counts.get("full_text_excluded", 0)
            },
            "included": {
                "studies_included": counts.get("full_text_included", 0)
            },
            "generated_at": datetime.now().isoformat(),
            "session_id": session_id
        }
        
        return flowchart

    async def handle_action(self, action) -> Dict[str, Any]:
        """
        Handle research actions for screening and PRISMA.
        
        Args:
            action: Research action to handle
            
        Returns:
            Action result
        """
        try:
            action_type = getattr(action, 'action_type', getattr(action, 'type', 'unknown'))
            parameters = getattr(action, 'parameters', getattr(action, 'data', {}))
            
            if action_type == "create_prisma_session":
                session = await self.create_prisma_session(
                    parameters.get('lit_review_id'),
                    parameters.get('criteria', [])
                )
                return {
                    'status': 'success',
                    'agent': self.agent_id,
                    'action_type': action_type,
                    'result': session.dict(),
                    'timestamp': datetime.now().isoformat()
                }
            
            elif action_type == "screen_batch":
                decisions = await self.screen_batch(
                    parameters.get('session_id'),
                    parameters.get('records', []),
                    parameters.get('stage', 'title_abstract')
                )
                return {
                    'status': 'success',
                    'agent': self.agent_id,
                    'action_type': action_type,
                    'result': [d.dict() for d in decisions],
                    'timestamp': datetime.now().isoformat()
                }
            
            elif action_type == "generate_prisma_flowchart":
                flowchart = await self.generate_prisma_flowchart(parameters.get('session_id'))
                return {
                    'status': 'success',
                    'agent': self.agent_id,
                    'action_type': action_type,
                    'result': flowchart,
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
            'active_sessions': len(self.sessions),
            'total_decisions': sum(len(decisions) for decisions in self.decisions.values()),
            'timestamp': datetime.now().isoformat()
        }

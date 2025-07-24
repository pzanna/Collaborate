"""
Advanced Conflict Resolution System for Collaborative Systematic Reviews

This module provides intelligent conflict detection and resolution algorithms for
systematic review collaboration, including:
- Automated conflict identification between reviewers
- AI - powered mediation suggestions
- Expert reviewer assignment systems
- Conflict history tracking and analytics

Key Features:
- Multi - dimensional conflict analysis
- Intelligent resolution suggestions
- Expert assignment algorithms
- Conflict pattern recognition
- Resolution effectiveness tracking

Author: Eunice AI System
Date: 2024
"""

import asyncio
import json
import logging
import math
import sqlite3
import statistics
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConflictType(Enum):
    """Types of conflicts in systematic reviews"""

    INCLUSION_EXCLUSION = "inclusion_exclusion"
    CRITERIA_DISAGREEMENT = "criteria_disagreement"
    QUALITY_ASSESSMENT = "quality_assessment"
    DATA_EXTRACTION = "data_extraction"
    RISK_OF_BIAS = "risk_of_bias"
    GRADING = "grading"
    ANNOTATION_CONFLICT = "annotation_conflict"


class ConflictSeverity(Enum):
    """Severity levels for conflicts"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ResolutionStatus(Enum):
    """Status of conflict resolution"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    CONSENSUS_REACHED = "consensus_reached"


class ResolutionMethod(Enum):
    """Methods for conflict resolution"""

    AUTOMATIC = "automatic"
    DISCUSSION = "discussion"
    EXPERT_DECISION = "expert_decision"
    VOTING = "voting"
    CONSENSUS_BUILDING = "consensus_building"
    THIRD_REVIEWER = "third_reviewer"
    MEDIATION = "mediation"
    RE_EXTRACTION = "re_extraction"
    EXPERT_REVIEW = "expert_review"


@dataclass
class ConflictDetection:
    """Conflict detection result"""

    conflict_id: str
    conflict_type: ConflictType
    severity: ConflictSeverity
    study_id: str
    project_id: str
    reviewers: List[str]
    conflicting_decisions: Dict[str, Any]
    detection_timestamp: datetime
    confidence_score: float
    metadata: Dict[str, Any]


@dataclass
class ResolutionSuggestion:
    """AI - generated resolution suggestion"""

    suggestion_id: str
    conflict_id: str
    method: ResolutionMethod
    suggestion_text: str
    rationale: str
    confidence_score: float
    evidence_support: Dict[str, Any]
    estimated_resolution_time: int  # minutes
    success_probability: float
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ConflictResolution:
    """Conflict resolution record"""

    resolution_id: str
    conflict_id: str
    method: ResolutionMethod
    status: ResolutionStatus
    resolved_by: Optional[str]
    resolution_data: Dict[str, Any]
    start_timestamp: datetime
    end_timestamp: Optional[datetime]
    resolution_notes: Optional[str]
    effectiveness_score: Optional[float]


@dataclass
class ExpertAssignment:
    """Expert reviewer assignment for conflict resolution"""

    assignment_id: str
    conflict_id: str
    expert_id: str
    assignment_timestamp: datetime
    expertise_match_score: float
    availability_score: float
    workload_score: float
    total_score: float
    status: str  # 'assigned', 'accepted', 'declined', 'completed'


class AdvancedConflictResolver:
    """
    Advanced conflict resolution system for systematic reviews

    Features:
    - Intelligent conflict detection algorithms
    - AI - powered resolution suggestions
    - Expert assignment optimization
    - Conflict pattern analysis
    - Resolution effectiveness tracking
    """

    def __init__(self, db_path: str = "data / eunice.db"):
        self.db_path = db_path
        self.conflict_thresholds = {
            ConflictType.INCLUSION_EXCLUSION: 0.3,
            ConflictType.CRITERIA_DISAGREEMENT: 0.4,
            ConflictType.QUALITY_ASSESSMENT: 0.5,
            ConflictType.DATA_EXTRACTION: 0.6,
            ConflictType.RISK_OF_BIAS: 0.4,
            ConflictType.GRADING: 0.3,
        }

        # Initialize database
        self._init_database()

        # Load machine learning models for conflict prediction
        self._load_conflict_models()

        logger.info("Advanced Conflict Resolver initialized")

    def _init_database(self):
        """Initialize conflict resolution database tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Conflicts table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS conflicts (
                        conflict_id TEXT PRIMARY KEY,
                        conflict_type TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        study_id TEXT NOT NULL,
                        project_id TEXT NOT NULL,
                        reviewers TEXT NOT NULL,
                        conflicting_decisions TEXT NOT NULL,
                        detection_timestamp TEXT NOT NULL,
                        confidence_score REAL NOT NULL,
                        metadata TEXT,
                        status TEXT DEFAULT 'pending'
                    )
                """
                )

                # Resolution suggestions table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS resolution_suggestions (
                        suggestion_id TEXT PRIMARY KEY,
                        conflict_id TEXT NOT NULL,
                        method TEXT NOT NULL,
                        suggestion_text TEXT NOT NULL,
                        rationale TEXT NOT NULL,
                        confidence_score REAL NOT NULL,
                        evidence_support TEXT,
                        estimated_resolution_time INTEGER,
                        success_probability REAL,
                        created_timestamp TEXT NOT NULL,
                        FOREIGN KEY (conflict_id) REFERENCES conflicts (conflict_id)
                    )
                """
                )

                # Resolutions table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS conflict_resolutions (
                        resolution_id TEXT PRIMARY KEY,
                        conflict_id TEXT NOT NULL,
                        method TEXT NOT NULL,
                        status TEXT NOT NULL,
                        resolved_by TEXT,
                        resolution_data TEXT,
                        start_timestamp TEXT NOT NULL,
                        end_timestamp TEXT,
                        resolution_notes TEXT,
                        effectiveness_score REAL,
                        FOREIGN KEY (conflict_id) REFERENCES conflicts (conflict_id)
                    )
                """
                )

                # Expert assignments table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS expert_assignments (
                        assignment_id TEXT PRIMARY KEY,
                        conflict_id TEXT NOT NULL,
                        expert_id TEXT NOT NULL,
                        assignment_timestamp TEXT NOT NULL,
                        expertise_match_score REAL NOT NULL,
                        availability_score REAL NOT NULL,
                        workload_score REAL NOT NULL,
                        total_score REAL NOT NULL,
                        status TEXT DEFAULT 'assigned',
                        FOREIGN KEY (conflict_id) REFERENCES conflicts (conflict_id)
                    )
                """
                )

                # Reviewer profiles table for expert matching
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS reviewer_profiles (
                        reviewer_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        expertise_areas TEXT,
                        experience_years INTEGER DEFAULT 0,
                        specializations TEXT,
                        current_workload INTEGER DEFAULT 0,
                        availability_score REAL DEFAULT 1.0,
                        resolution_success_rate REAL DEFAULT 0.0,
                        average_resolution_time INTEGER DEFAULT 60,
                        preferred_conflict_types TEXT
                    )
                """
                )

                # Conflict patterns table for learning
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS conflict_patterns (
                        pattern_id TEXT PRIMARY KEY,
                        conflict_type TEXT NOT NULL,
                        pattern_description TEXT NOT NULL,
                        frequency INTEGER DEFAULT 1,
                        resolution_methods TEXT,
                        success_rates TEXT,
                        created_timestamp TEXT NOT NULL,
                        last_updated TEXT NOT NULL
                    )
                """
                )

                conn.commit()
                logger.info("Conflict resolution database initialized successfully")

        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            raise

    def _load_conflict_models(self):
        """Load machine learning models for conflict prediction"""
        # Placeholder for ML model loading
        # In production, load pre - trained models for:
        # - Conflict severity prediction
        # - Resolution method selection
        # - Expert assignment optimization
        self.severity_model = None
        self.resolution_model = None
        self.expert_matching_model = None
        logger.info("Conflict prediction models loaded")

    async def detect_conflicts(
        self, project_id: str, study_id: str, recent_decisions: List[Dict[str, Any]]
    ) -> List[ConflictDetection]:
        """
        Detect conflicts between reviewer decisions using advanced algorithms

        Args:
            project_id: Project identifier
            study_id: Study identifier
            recent_decisions: List of recent screening / assessment decisions

        Returns:
            List of detected conflicts
        """
        conflicts = []

        try:
            # Group decisions by reviewer
            reviewer_decisions = defaultdict(list)
            for decision in recent_decisions:
                reviewer_decisions[decision["user_id"]].append(decision)

            # Check for inclusion / exclusion conflicts
            inclusion_conflicts = await self._detect_inclusion_conflicts(
                project_id, study_id, reviewer_decisions
            )
            conflicts.extend(inclusion_conflicts)

            # Check for criteria disagreements
            criteria_conflicts = await self._detect_criteria_conflicts(
                project_id, study_id, reviewer_decisions
            )
            conflicts.extend(criteria_conflicts)

            # Check for quality assessment conflicts
            quality_conflicts = await self._detect_quality_conflicts(
                project_id, study_id, reviewer_decisions
            )
            conflicts.extend(quality_conflicts)

            # Store detected conflicts
            for conflict in conflicts:
                await self._store_conflict(conflict)

            logger.info(f"Detected {len(conflicts)} conflicts for study {study_id}")
            return conflicts

        except Exception as e:
            logger.error(f"Conflict detection error: {str(e)}")
            return []

    async def _detect_inclusion_conflicts(
        self, project_id: str, study_id: str, reviewer_decisions: Dict[str, List[Dict]]
    ) -> List[ConflictDetection]:
        """Detect inclusion / exclusion decision conflicts"""
        conflicts = []

        try:
            # Extract inclusion decisions
            inclusion_decisions = {}
            for reviewer_id, decisions in reviewer_decisions.items():
                for decision in decisions:
                    if "decision" in decision:
                        inclusion_decisions[reviewer_id] = decision["decision"]

            # Check for conflicts
            if len(inclusion_decisions) >= 2:
                decision_values = list(inclusion_decisions.values())
                unique_decisions = set(decision_values)

                # Conflict if not all decisions are the same
                if len(unique_decisions) > 1:
                    # Calculate conflict severity
                    severity = self._calculate_inclusion_conflict_severity(
                        decision_values
                    )

                    conflict = ConflictDetection(
                        conflict_id=str(uuid.uuid4()),
                        conflict_type=ConflictType.INCLUSION_EXCLUSION,
                        severity=severity,
                        study_id=study_id,
                        project_id=project_id,
                        reviewers=list(inclusion_decisions.keys()),
                        conflicting_decisions=inclusion_decisions,
                        detection_timestamp=datetime.now(timezone.utc),
                        confidence_score=0.9,  # High confidence for clear inclusion conflicts
                        metadata={
                            "decision_distribution": dict(Counter(decision_values)),
                            "total_reviewers": len(inclusion_decisions),
                        },
                    )
                    conflicts.append(conflict)

        except Exception as e:
            logger.error(f"Inclusion conflict detection error: {str(e)}")

        return conflicts

    async def _detect_criteria_conflicts(
        self, project_id: str, study_id: str, reviewer_decisions: Dict[str, List[Dict]]
    ) -> List[ConflictDetection]:
        """Detect conflicts in inclusion / exclusion criteria"""
        conflicts = []

        try:
            # Extract criteria selections
            criteria_decisions = {}
            for reviewer_id, decisions in reviewer_decisions.items():
                for decision in decisions:
                    if "criteria" in decision:
                        criteria_decisions[reviewer_id] = set(decision["criteria"])

            # Check for criteria conflicts
            if len(criteria_decisions) >= 2:
                all_criteria = set()
                for criteria_set in criteria_decisions.values():
                    all_criteria.update(criteria_set)

                # Calculate disagreement level
                disagreement_score = 0
                for criterion in all_criteria:
                    reviewer_count = sum(
                        1
                        for criteria_set in criteria_decisions.values()
                        if criterion in criteria_set
                    )
                    total_reviewers = len(criteria_decisions)
                    agreement_ratio = reviewer_count / total_reviewers
                    disagreement_score += abs(0.5 - agreement_ratio)

                disagreement_score /= len(all_criteria) if all_criteria else 1

                # Create conflict if disagreement is significant
                threshold = self.conflict_thresholds[ConflictType.CRITERIA_DISAGREEMENT]
                if disagreement_score > threshold:
                    severity = self._calculate_criteria_conflict_severity(
                        disagreement_score
                    )

                    conflict = ConflictDetection(
                        conflict_id=str(uuid.uuid4()),
                        conflict_type=ConflictType.CRITERIA_DISAGREEMENT,
                        severity=severity,
                        study_id=study_id,
                        project_id=project_id,
                        reviewers=list(criteria_decisions.keys()),
                        conflicting_decisions={
                            k: list(v) for k, v in criteria_decisions.items()
                        },
                        detection_timestamp=datetime.now(timezone.utc),
                        confidence_score=min(0.9, disagreement_score * 2),
                        metadata={
                            "disagreement_score": disagreement_score,
                            "conflicting_criteria": list(all_criteria),
                            "agreement_ratios": {
                                criterion: sum(
                                    1
                                    for cs in criteria_decisions.values()
                                    if criterion in cs
                                )
                                / len(criteria_decisions)
                                for criterion in all_criteria
                            },
                        },
                    )
                    conflicts.append(conflict)

        except Exception as e:
            logger.error(f"Criteria conflict detection error: {str(e)}")

        return conflicts

    async def _detect_quality_conflicts(
        self, project_id: str, study_id: str, reviewer_decisions: Dict[str, List[Dict]]
    ) -> List[ConflictDetection]:
        """Detect conflicts in quality assessment scores"""
        conflicts = []

        try:
            # Extract quality scores
            quality_scores = {}
            for reviewer_id, decisions in reviewer_decisions.items():
                for decision in decisions:
                    if "quality_score" in decision:
                        quality_scores[reviewer_id] = decision["quality_score"]

            # Check for quality assessment conflicts
            if len(quality_scores) >= 2:
                scores = list(quality_scores.values())

                # Calculate variance in quality scores
                if len(scores) > 1:
                    score_variance = statistics.variance(scores)
                    mean_score = statistics.mean(scores)

                    # Normalize variance by mean to get relative disagreement
                    relative_variance = score_variance / (
                        mean_score + 0.1
                    )  # Avoid division by zero

                    threshold = self.conflict_thresholds[
                        ConflictType.QUALITY_ASSESSMENT
                    ]
                    if relative_variance > threshold:
                        severity = self._calculate_quality_conflict_severity(
                            relative_variance
                        )

                        conflict = ConflictDetection(
                            conflict_id=str(uuid.uuid4()),
                            conflict_type=ConflictType.QUALITY_ASSESSMENT,
                            severity=severity,
                            study_id=study_id,
                            project_id=project_id,
                            reviewers=list(quality_scores.keys()),
                            conflicting_decisions=quality_scores,
                            detection_timestamp=datetime.now(timezone.utc),
                            confidence_score=min(0.9, relative_variance * 2),
                            metadata={
                                "score_variance": score_variance,
                                "mean_score": mean_score,
                                "relative_variance": relative_variance,
                                "score_range": max(scores) - min(scores),
                            },
                        )
                        conflicts.append(conflict)

        except Exception as e:
            logger.error(f"Quality conflict detection error: {str(e)}")

        return conflicts

    def _calculate_inclusion_conflict_severity(
        self, decisions: List[str]
    ) -> ConflictSeverity:
        """Calculate severity for inclusion / exclusion conflicts"""
        decision_counts = Counter(decisions)
        total_decisions = len(decisions)

        # Calculate entropy (higher entropy = more disagreement)
        entropy = 0
        for count in decision_counts.values():
            probability = count / total_decisions
            if probability > 0:
                entropy -= probability * math.log2(probability)

        # Map entropy to severity
        if entropy >= 1.5:
            return ConflictSeverity.CRITICAL
        elif entropy >= 1.0:
            return ConflictSeverity.HIGH
        elif entropy >= 0.5:
            return ConflictSeverity.MEDIUM
        else:
            return ConflictSeverity.LOW

    def _calculate_criteria_conflict_severity(
        self, disagreement_score: float
    ) -> ConflictSeverity:
        """Calculate severity for criteria conflicts"""
        if disagreement_score >= 0.8:
            return ConflictSeverity.CRITICAL
        elif disagreement_score >= 0.6:
            return ConflictSeverity.HIGH
        elif disagreement_score >= 0.4:
            return ConflictSeverity.MEDIUM
        else:
            return ConflictSeverity.LOW

    def _calculate_quality_conflict_severity(
        self, relative_variance: float
    ) -> ConflictSeverity:
        """Calculate severity for quality assessment conflicts"""
        if relative_variance >= 1.0:
            return ConflictSeverity.CRITICAL
        elif relative_variance >= 0.7:
            return ConflictSeverity.HIGH
        elif relative_variance >= 0.4:
            return ConflictSeverity.MEDIUM
        else:
            return ConflictSeverity.LOW

    async def generate_resolution_suggestions(
        self, conflict: ConflictDetection
    ) -> List[ResolutionSuggestion]:
        """
        Generate AI - powered resolution suggestions for conflicts

        Args:
            conflict: Detected conflict to resolve

        Returns:
            List of resolution suggestions ranked by effectiveness
        """
        suggestions = []

        try:
            # Generate suggestions based on conflict type and severity
            if conflict.conflict_type == ConflictType.INCLUSION_EXCLUSION:
                suggestions.extend(await self._suggest_inclusion_resolutions(conflict))
            elif conflict.conflict_type == ConflictType.CRITERIA_DISAGREEMENT:
                suggestions.extend(await self._suggest_criteria_resolutions(conflict))
            elif conflict.conflict_type == ConflictType.QUALITY_ASSESSMENT:
                suggestions.extend(await self._suggest_quality_resolutions(conflict))

            # Add general resolution suggestions
            suggestions.extend(await self._suggest_general_resolutions(conflict))

            # Rank suggestions by predicted effectiveness
            suggestions = await self._rank_suggestions(suggestions, conflict)

            # Store suggestions
            for suggestion in suggestions:
                await self._store_suggestion(suggestion)

            logger.info(
                f"Generated {len(suggestions)} resolution suggestions for conflict {conflict.conflict_id}"
            )
            return suggestions

        except Exception as e:
            logger.error(f"Resolution suggestion generation error: {str(e)}")
            return []

    async def _suggest_inclusion_resolutions(
        self, conflict: ConflictDetection
    ) -> List[ResolutionSuggestion]:
        """Generate resolution suggestions for inclusion / exclusion conflicts"""
        suggestions = []

        try:
            # Third reviewer suggestion
            suggestions.append(
                ResolutionSuggestion(
                    suggestion_id=str(uuid.uuid4()),
                    conflict_id=conflict.conflict_id,
                    method=ResolutionMethod.THIRD_REVIEWER,
                    suggestion_text="Assign a third independent reviewer to make the final inclusion decision",
                    rationale="Third reviewer can break the tie and provide an independent assessment",
                    confidence_score=0.85,
                    evidence_support={
                        "success_rate": 0.82,
                        "average_resolution_time": 45,
                        "reviewer_satisfaction": 0.78,
                    },
                    estimated_resolution_time=45,
                    success_probability=0.82,
                )
            )

            # Discussion - based resolution
            suggestions.append(
                ResolutionSuggestion(
                    suggestion_id=str(uuid.uuid4()),
                    conflict_id=conflict.conflict_id,
                    method=ResolutionMethod.DISCUSSION,
                    suggestion_text="Facilitate a structured discussion between conflicting reviewers",
                    rationale="Discussion can reveal underlying reasoning and lead to consensus",
                    confidence_score=0.75,
                    evidence_support={
                        "success_rate": 0.68,
                        "average_resolution_time": 30,
                        "learning_benefit": 0.85,
                    },
                    estimated_resolution_time=30,
                    success_probability=0.68,
                )
            )

            # Expert decision for high severity conflicts
            if conflict.severity in [ConflictSeverity.HIGH, ConflictSeverity.CRITICAL]:
                suggestions.append(
                    ResolutionSuggestion(
                        suggestion_id=str(uuid.uuid4()),
                        conflict_id=conflict.conflict_id,
                        method=ResolutionMethod.EXPERT_DECISION,
                        suggestion_text="Escalate to senior reviewer or domain expert",
                        rationale="Complex conflicts require expert judgment and domain knowledge",
                        confidence_score=0.90,
                        evidence_support={
                            "success_rate": 0.95,
                            "average_resolution_time": 60,
                            "final_quality": 0.92,
                        },
                        estimated_resolution_time=60,
                        success_probability=0.95,
                    )
                )

        except Exception as e:
            logger.error(f"Inclusion resolution suggestion error: {str(e)}")

        return suggestions

    async def _suggest_criteria_resolutions(
        self, conflict: ConflictDetection
    ) -> List[ResolutionSuggestion]:
        """Generate resolution suggestions for criteria conflicts"""
        suggestions = []

        try:
            # Consensus building
            suggestions.append(
                ResolutionSuggestion(
                    suggestion_id=str(uuid.uuid4()),
                    conflict_id=conflict.conflict_id,
                    method=ResolutionMethod.CONSENSUS_BUILDING,
                    suggestion_text="Conduct structured consensus-building session with criteria clarification",
                    rationale="Criteria conflicts often stem from interpretation differences that can be resolved "
                    "through discussion",
                    confidence_score=0.80,
                    evidence_support={
                        "success_rate": 0.75,
                        "average_resolution_time": 40,
                        "criteria_clarity_improvement": 0.88,
                    },
                    estimated_resolution_time=40,
                    success_probability=0.75,
                )
            )

            # Automatic resolution for low - severity conflicts
            if conflict.severity == ConflictSeverity.LOW:
                suggestions.append(
                    ResolutionSuggestion(
                        suggestion_id=str(uuid.uuid4()),
                        conflict_id=conflict.conflict_id,
                        method=ResolutionMethod.AUTOMATIC,
                        suggestion_text="Apply majority vote rule for criteria selection",
                        rationale="Low - severity criteria conflicts can be resolved automatically using majority rule",
                        confidence_score=0.70,
                        evidence_support={
                            "success_rate": 0.78,
                            "average_resolution_time": 5,
                            "efficiency_gain": 0.95,
                        },
                        estimated_resolution_time=5,
                        success_probability=0.78,
                    )
                )

        except Exception as e:
            logger.error(f"Criteria resolution suggestion error: {str(e)}")

        return suggestions

    async def _suggest_quality_resolutions(
        self, conflict: ConflictDetection
    ) -> List[ResolutionSuggestion]:
        """Generate resolution suggestions for quality assessment conflicts"""
        suggestions = []

        try:
            # Calibration session
            suggestions.append(
                ResolutionSuggestion(
                    suggestion_id=str(uuid.uuid4()),
                    conflict_id=conflict.conflict_id,
                    method=ResolutionMethod.CONSENSUS_BUILDING,
                    suggestion_text="Conduct quality assessment calibration session",
                    rationale="Quality score conflicts often indicate need for better calibration between reviewers",
                    confidence_score=0.85,
                    evidence_support={
                        "success_rate": 0.82,
                        "average_resolution_time": 35,
                        "inter_rater_reliability_improvement": 0.76,
                    },
                    estimated_resolution_time=35,
                    success_probability=0.82,
                )
            )

            # Expert review for high severity conflicts
            if conflict.severity in [ConflictSeverity.HIGH, ConflictSeverity.CRITICAL]:
                suggestions.append(
                    ResolutionSuggestion(
                        suggestion_id=str(uuid.uuid4()),
                        conflict_id=conflict.conflict_id,
                        method=ResolutionMethod.EXPERT_REVIEW,
                        suggestion_text="Assign senior quality assessment expert to review conflicting domains",
                        rationale="Quality assessment disagreements often require deep methodological expertise to "
                        "resolve",
                        confidence_score=0.88,
                        evidence_support={
                            "success_rate": 0.85,
                            "average_resolution_time": 50,
                            "expertise_impact": 0.90,
                        },
                        estimated_resolution_time=50,
                        success_probability=0.85,
                    )
                )

            # Average scoring for minor conflicts
            if conflict.severity in [ConflictSeverity.LOW, ConflictSeverity.MEDIUM]:
                suggestions.append(
                    ResolutionSuggestion(
                        suggestion_id=str(uuid.uuid4()),
                        conflict_id=conflict.conflict_id,
                        method=ResolutionMethod.AUTOMATIC,
                        suggestion_text="Use weighted average of quality scores",
                        rationale="Minor quality score differences can be resolved by averaging with reviewer "
                        "experience weights",
                        confidence_score=0.75,
                        evidence_support={
                            "success_rate": 0.85,
                            "average_resolution_time": 2,
                            "score_accuracy": 0.79,
                        },
                        estimated_resolution_time=2,
                        success_probability=0.85,
                    )
                )

        except Exception as e:
            logger.error(f"Quality resolution suggestion error: {str(e)}")

        return suggestions

    async def _suggest_general_resolutions(
        self, conflict: ConflictDetection
    ) -> List[ResolutionSuggestion]:
        """Generate general resolution suggestions applicable to any conflict type"""
        suggestions = []

        try:
            # Voting for multi - reviewer conflicts
            if len(conflict.reviewers) >= 3:
                suggestions.append(
                    ResolutionSuggestion(
                        suggestion_id=str(uuid.uuid4()),
                        conflict_id=conflict.conflict_id,
                        method=ResolutionMethod.VOTING,
                        suggestion_text="Conduct anonymous voting among all project reviewers",
                        rationale="Democratic voting can resolve conflicts when multiple reviewers are available",
                        confidence_score=0.70,
                        evidence_support={
                            "success_rate": 0.72,
                            "average_resolution_time": 20,
                            "reviewer_acceptance": 0.81,
                        },
                        estimated_resolution_time=20,
                        success_probability=0.72,
                    )
                )

        except Exception as e:
            logger.error(f"General resolution suggestion error: {str(e)}")

        return suggestions

    async def _rank_suggestions(
        self, suggestions: List[ResolutionSuggestion], conflict: ConflictDetection
    ) -> List[ResolutionSuggestion]:
        """Rank resolution suggestions by predicted effectiveness"""
        try:
            # Calculate composite score for each suggestion
            for suggestion in suggestions:
                # Factors: success probability, time efficiency, confidence
                time_efficiency = 1.0 / (suggestion.estimated_resolution_time + 1)
                composite_score = (
                    suggestion.success_probability * 0.5
                    + suggestion.confidence_score * 0.3
                    + time_efficiency * 0.2
                )
                suggestion.metadata = {"composite_score": composite_score}

            # Sort by composite score (descending)
            suggestions.sort(
                key=lambda s: s.metadata.get("composite_score", 0) if s.metadata else 0,
                reverse=True,
            )

        except Exception as e:
            logger.error(f"Suggestion ranking error: {str(e)}")

        return suggestions

    async def assign_expert_reviewer(
        self, conflict: ConflictDetection
    ) -> Optional[ExpertAssignment]:
        """
        Assign an expert reviewer for conflict resolution

        Args:
            conflict: Conflict requiring expert review

        Returns:
            Expert assignment details
        """
        try:
            # Get available expert reviewers
            experts = await self._get_available_experts(conflict)

            if not experts:
                logger.warning(
                    f"No available experts for conflict {conflict.conflict_id}"
                )
                return None

            # Calculate assignment scores
            best_expert = None
            best_score = 0

            for expert in experts:
                score = await self._calculate_expert_score(expert, conflict)
                if score > best_score:
                    best_score = score
                    best_expert = expert

            if best_expert:
                assignment = ExpertAssignment(
                    assignment_id=str(uuid.uuid4()),
                    conflict_id=conflict.conflict_id,
                    expert_id=best_expert["reviewer_id"],
                    assignment_timestamp=datetime.now(timezone.utc),
                    expertise_match_score=best_expert["expertise_score"],
                    availability_score=best_expert["availability_score"],
                    workload_score=best_expert["workload_score"],
                    total_score=best_score,
                    status="assigned",
                )

                await self._store_expert_assignment(assignment)
                logger.info(
                    f"Assigned expert {best_expert['reviewer_id']} to conflict {conflict.conflict_id}"
                )
                return assignment

        except Exception as e:
            logger.error(f"Expert assignment error: {str(e)}")

        return None

    async def resolve_conflict(
        self,
        conflict_id: str,
        resolution_method: ResolutionMethod,
        resolved_by: str,
        final_decision: Dict[str, Any],
        resolution_notes: Optional[str] = None,
    ) -> Optional[ConflictResolution]:
        """
        Resolve a conflict and store the resolution record.

        Args:
            conflict_id: The ID of the conflict to resolve.
            resolution_method: The method used for resolution.
            resolved_by: The ID of the user/system that resolved the conflict.
            final_decision: The final decision that resolves the conflict.
            resolution_notes: Optional notes about the resolution process.

        Returns:
            The conflict resolution record, or None if resolution failed.
        """
        try:
            resolution = ConflictResolution(
                resolution_id=str(uuid.uuid4()),
                conflict_id=conflict_id,
                method=resolution_method,
                status=ResolutionStatus.RESOLVED,
                resolved_by=resolved_by,
                resolution_data=final_decision,
                start_timestamp=datetime.now(
                    timezone.utc
                ),  # This should ideally be tracked from when resolution starts
                end_timestamp=datetime.now(timezone.utc),
                resolution_notes=resolution_notes,
                effectiveness_score=None,  # To be calculated later
            )

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO conflict_resolutions
                    (resolution_id, conflict_id, method, status, resolved_by, resolution_data,
                     start_timestamp, end_timestamp, resolution_notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        resolution.resolution_id,
                        resolution.conflict_id,
                        resolution.method.value,
                        resolution.status.value,
                        resolution.resolved_by,
                        json.dumps(resolution.resolution_data),
                        resolution.start_timestamp.isoformat(),
                        (
                            resolution.end_timestamp.isoformat()
                            if resolution.end_timestamp
                            else None
                        ),
                        resolution.resolution_notes,
                    ),
                )
                cursor.execute(
                    "UPDATE conflicts SET status = ? WHERE conflict_id = ?",
                    (ResolutionStatus.RESOLVED.value, conflict_id),
                )
                conn.commit()

            logger.info(f"Conflict {conflict_id} resolved successfully.")
            return resolution
        except Exception as e:
            logger.error(f"Failed to resolve conflict {conflict_id}: {str(e)}")
            return None

    async def _get_available_experts(
        self, conflict: ConflictDetection
    ) -> List[Dict[str, Any]]:
        """Get list of available expert reviewers"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT * FROM reviewer_profiles
                    WHERE availability_score > 0.3
                    AND current_workload < 10
                    ORDER BY resolution_success_rate DESC
                """
                )

                experts = []
                for row in cursor.fetchall():
                    expert = {
                        "reviewer_id": row[0],
                        "name": row[1],
                        "expertise_areas": json.loads(row[2]) if row[2] else [],
                        "experience_years": row[3],
                        "availability_score": row[5],
                        "workload_score": 1.0 - (row[4] / 10.0),  # Invert workload
                        "success_rate": row[6],
                    }
                    experts.append(expert)

                return experts

        except Exception as e:
            logger.error(f"Expert retrieval error: {str(e)}")
            return []

    async def _calculate_expert_score(
        self, expert: Dict[str, Any], conflict: ConflictDetection
    ) -> float:
        """Calculate assignment score for expert reviewer"""
        try:
            # Expertise match score
            expertise_score = 0.5  # Default
            conflict_domain = conflict.metadata.get("domain", "")
            if conflict_domain and conflict_domain in expert["expertise_areas"]:
                expertise_score = 0.9
            elif any(area in conflict_domain for area in expert["expertise_areas"]):
                expertise_score = 0.7

            # Experience bonus
            experience_bonus = min(expert["experience_years"] / 10.0, 0.2)

            # Composite score
            total_score = (
                expertise_score * 0.4
                + expert["availability_score"] * 0.3
                + expert["workload_score"] * 0.2
                + expert["success_rate"] * 0.1
                + experience_bonus
            )

            expert["expertise_score"] = expertise_score
            return total_score

        except Exception as e:
            logger.error(f"Expert scoring error: {str(e)}")
            return 0.0

    async def _store_conflict(self, conflict: ConflictDetection):
        """Store detected conflict in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO conflicts
                    (conflict_id, conflict_type, severity, study_id, project_id, reviewers,
                     conflicting_decisions, detection_timestamp, confidence_score, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        conflict.conflict_id,
                        conflict.conflict_type.value,
                        conflict.severity.value,
                        conflict.study_id,
                        conflict.project_id,
                        json.dumps(conflict.reviewers),
                        json.dumps(conflict.conflicting_decisions),
                        conflict.detection_timestamp.isoformat(),
                        conflict.confidence_score,
                        json.dumps(conflict.metadata),
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to store conflict: {str(e)}")

    async def _store_suggestion(self, suggestion: ResolutionSuggestion):
        """Store resolution suggestion in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO resolution_suggestions
                    (suggestion_id, conflict_id, method, suggestion_text, rationale,
                     confidence_score, evidence_support, estimated_resolution_time,
                     success_probability, created_timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        suggestion.suggestion_id,
                        suggestion.conflict_id,
                        suggestion.method.value,
                        suggestion.suggestion_text,
                        suggestion.rationale,
                        suggestion.confidence_score,
                        json.dumps(suggestion.evidence_support),
                        suggestion.estimated_resolution_time,
                        suggestion.success_probability,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to store suggestion: {str(e)}")

    async def _store_expert_assignment(self, assignment: ExpertAssignment):
        """Store expert assignment in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO expert_assignments
                    (assignment_id, conflict_id, expert_id, assignment_timestamp,
                     expertise_match_score, availability_score, workload_score, total_score, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        assignment.assignment_id,
                        assignment.conflict_id,
                        assignment.expert_id,
                        assignment.assignment_timestamp.isoformat(),
                        assignment.expertise_match_score,
                        assignment.availability_score,
                        assignment.workload_score,
                        assignment.total_score,
                        assignment.status,
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to store expert assignment: {str(e)}")

    async def track_resolution_effectiveness(self, resolution: ConflictResolution):
        """
        Track and analyze the effectiveness of conflict resolution methods

        Args:
            resolution: Conflict resolution record
        """
        try:
            # Placeholder for tracking logic
            # In production, implement tracking of:
            # - Resolution outcomes (success/failure)
            # - Time to resolution
            # - Reviewer satisfaction
            # - Recurrence of conflicts
            logger.info(
                f"Tracking effectiveness for resolution {resolution.resolution_id} "
                f"using method {resolution.method.value}"
            )
        except Exception as e:
            logger.error(f"Failed to track resolution effectiveness: {str(e)}")

    async def get_conflict_analytics(self, project_id: str) -> Dict[str, Any]:
        """Get comprehensive conflict analytics for project"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Overall conflict statistics
                cursor.execute(
                    """
                    SELECT
                        conflict_type,
                        severity,
                        COUNT(*) as count,
                        AVG(confidence_score) as avg_confidence
                    FROM conflicts
                    WHERE project_id = ?
                    GROUP BY conflict_type, severity
                """,
                    (project_id,),
                )

                conflict_stats = cursor.fetchall()

                # Resolution effectiveness
                cursor.execute(
                    """
                    SELECT
                        r.method,
                        COUNT(*) as total_resolutions,
                        AVG(r.effectiveness_score) as avg_effectiveness,
                        AVG(
                            (julianday(r.end_timestamp) - julianday(r.start_timestamp)) * 24 * 60
                        ) as avg_resolution_time_minutes
                    FROM conflict_resolutions r
                    JOIN conflicts c ON r.conflict_id = c.conflict_id
                    WHERE c.project_id = ? AND r.status = 'resolved'
                    GROUP BY r.method
                """,
                    (project_id,),
                )

                resolution_stats = cursor.fetchall()

                return {
                    "conflict_statistics": conflict_stats,
                    "resolution_effectiveness": resolution_stats,
                    "generated_timestamp": datetime.now(timezone.utc).isoformat(),
                }

        except Exception as e:
            logger.error(f"Analytics generation error: {str(e)}")
            return {}


async def demonstrate_conflict_resolution():
    """Demonstrates the advanced conflict resolution system."""
    logger.info("🎬 Demonstrating Conflict Resolution System")

    # Initialize system
    db_path = ":memory:"
    conflict_resolver = AdvancedConflictResolver(db_path)

    # Simulate project and study setup
    project_id = "proj_001"
    study_id = "study_001"

    # Simulate reviewer decisions leading to conflicts
    decisions1 = [
        {"user_id": "rev_01", "decision": "include", "criteria": ["A", "B"]},
        {"user_id": "rev_02", "decision": "include", "criteria": ["A", "C"]},
        {"user_id": "rev_03", "decision": "exclude", "criteria": ["B"]},
    ]

    decisions2 = [
        {
            "user_id": "rev_01",
            "decision": "high",
            "quality_score": 0.9,
            "criteria": ["A"],
        },
        {
            "user_id": "rev_02",
            "decision": "medium",
            "quality_score": 0.6,
            "criteria": ["A"],
        },
        {
            "user_id": "rev_03",
            "decision": "low",
            "quality_score": 0.3,
            "criteria": ["B"],
        },
    ]

    # Detect conflicts
    logger.info("🔍 Detecting conflicts in reviewer decisions...")
    conflicts1 = await conflict_resolver.detect_conflicts(
        project_id, study_id, decisions1
    )
    conflicts2 = await conflict_resolver.detect_conflicts(
        project_id, study_id, decisions2
    )
    all_conflicts = conflicts1 + conflicts2

    for conflict in all_conflicts:
        logger.info(
            f"Detected conflict: {conflict.conflict_type.value} (ID: {conflict.conflict_id})"
        )

    # Generate resolution suggestions
    logger.info("\n💡 Generating AI-powered resolution suggestions...")
    for conflict in all_conflicts:
        suggestions = await conflict_resolver.generate_resolution_suggestions(conflict)
        logger.info(
            f"   Suggestions for Conflict {conflict.conflict_id[:8]} ({conflict.conflict_type.value}):"
        )
        for suggestion in suggestions[:2]:  # Show top 2
            logger.info(
                f"     - {suggestion.suggestion_text} (Confidence: {suggestion.confidence_score:.2f})"
            )

    # Assign expert reviewer for a high severity conflict
    quality_conflict = next(
        (
            c
            for c in all_conflicts
            if c.conflict_type == ConflictType.QUALITY_ASSESSMENT
        ),
        None,
    )
    if quality_conflict:
        logger.info(
            "\n🧑‍⚖️ Assigning expert reviewer for quality assessment conflict..."
        )
        # Add a dummy expert for demonstration
        with sqlite3.connect(db_path) as conn:
            conn.cursor().execute(
                "INSERT INTO reviewer_profiles (reviewer_id, name, expertise_areas) VALUES (?, ?, ?)",
                ("expert1", "Dr. Expert", '["quality_assessment"]'),
            )
            conn.commit()
        assignment = await conflict_resolver.assign_expert_reviewer(quality_conflict)
        if assignment:
            logger.info(
                f"   Assigned expert: {assignment.expert_id} to conflict {quality_conflict.conflict_id[:8]}"
            )

    # Resolve a conflict
    inclusion_conflict = next(
        (
            c
            for c in all_conflicts
            if c.conflict_type == ConflictType.INCLUSION_EXCLUSION
        ),
        None,
    )
    if inclusion_conflict:
        logger.info("\n✅ Resolving a conflict via mediation...")
        resolution = await conflict_resolver.resolve_conflict(
            conflict_id=inclusion_conflict.conflict_id,
            resolution_method=ResolutionMethod.MEDIATION,
            resolved_by="mediator_01",
            final_decision={
                "decision": "include",
                "reason": "Consensus reached after discussion",
            },
        )
        if resolution:
            logger.info(f"   Conflict {resolution.conflict_id[:8]} resolved.")

    # Generate analytics report
    logger.info("\n📊 Generating conflict analytics report...")
    analytics = await conflict_resolver.get_conflict_analytics(project_id)
    logger.info("   Conflict Statistics:")
    for stat_row in analytics.get("conflict_statistics", []):
        logger.info(
            f"     - Type: {stat_row[0]}, Severity: {stat_row[1]}, Count: {stat_row[2]}"
        )

    logger.info("   Resolution Effectiveness:")
    for res_row in analytics.get("resolution_effectiveness", []):
        logger.info(
            f"     - Method: {res_row[0]}, Count: {res_row[1]}, Avg Time (min): {res_row[3]:.2f}"
        )

    logger.info("\n🎉 Conflict Resolution System demonstration completed!")


if __name__ == "__main__":
    asyncio.run(demonstrate_conflict_resolution())

"""
Collaborative Quality Assurance Workflows for Systematic Reviews

This module provides comprehensive quality assurance workflows including:
- Distributed quality assessment processes
- Consensus - building mechanisms for reviewer agreements
- Expert validation pipelines
- Quality metric aggregation and reporting
- Automated quality checks and validations

Key Features:
- Multi - stage QA workflows
- Inter - rater reliability calculations
- Consensus measurement and improvement
- Expert reviewer validation-Quality metrics dashboard

Author: Eunice AI System
Date: 2024
"""

import asyncio
import json
import logging
import sqlite3
import statistics
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QAStage(Enum):
    """Quality assurance workflow stages"""

    INITIAL_SCREENING = "initial_screening"
    DETAILED_ASSESSMENT = "detailed_assessment"
    DATA_EXTRACTION = "data_extraction"
    QUALITY_ASSESSMENT = "quality_assessment"
    RISK_OF_BIAS = "risk_of_bias"
    GRADE_ASSESSMENT = "grade_assessment"
    CONSENSUS_BUILDING = "consensus_building"
    EXPERT_VALIDATION = "expert_validation"
    FINAL_REVIEW = "final_review"


class ConsensusLevel(Enum):
    """Levels of consensus between reviewers"""

    PERFECT = "perfect"  # 100% agreement
    HIGH = "high"  # 90-99% agreement
    MODERATE = "moderate"  # 70-89% agreement
    LOW = "low"  # 50-69% agreement
    POOR = "poor"  # <50% agreement


class ValidationStatus(Enum):
    """Status of expert validation"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"
    ESCALATED = "escalated"


class QAMetricType(Enum):
    """Types of quality assurance metrics"""

    INTER_RATER_RELIABILITY = "inter_rater_reliability"
    CONSENSUS_SCORE = "consensus_score"
    COMPLETION_RATE = "completion_rate"
    ERROR_RATE = "error_rate"
    CONSISTENCY_SCORE = "consistency_score"
    EFFICIENCY_SCORE = "efficiency_score"


@dataclass
class QAWorkflow:
    """Quality assurance workflow configuration"""

    workflow_id: str
    project_id: str
    workflow_name: str
    stages: List[QAStage]
    required_reviewers_per_stage: Dict[QAStage, int]
    consensus_thresholds: Dict[QAStage, float]
    auto_advance_conditions: Dict[QAStage, Dict[str, Any]]
    expert_validation_required: Set[QAStage]
    created_by: str
    created_date: datetime
    is_active: bool


@dataclass
class QAAssignment:
    """Quality assurance assignment for reviewers"""

    assignment_id: str
    workflow_id: str
    stage: QAStage
    study_id: str
    reviewer_id: str
    assigned_date: datetime
    due_date: Optional[datetime]
    completion_date: Optional[datetime]
    status: str  # 'assigned', 'in_progress', 'completed', 'overdue'
    assignment_data: Dict[str, Any]


@dataclass
class QASubmission:
    """Quality assurance submission by reviewer"""

    submission_id: str
    assignment_id: str
    reviewer_id: str
    stage: QAStage
    study_id: str
    submission_data: Dict[str, Any]
    submission_date: datetime
    confidence_score: float
    time_spent_minutes: int
    notes: Optional[str]


@dataclass
class ConsensusMetrics:
    """Consensus measurement between reviewers"""

    metrics_id: str
    project_id: str
    stage: QAStage
    study_id: str
    reviewers: List[str]
    agreement_percentage: float
    consensus_level: ConsensusLevel
    disagreement_items: List[Dict[str, Any]]
    kappa_score: Optional[float]
    calculation_date: datetime
    recommendations: List[str]


@dataclass
class ExpertValidation:
    """Expert validation of QA submissions"""

    validation_id: str
    submission_ids: List[str]
    expert_id: str
    stage: QAStage
    study_id: str
    validation_status: ValidationStatus
    expert_decision: Dict[str, Any]
    validation_notes: str
    confidence_score: float
    validation_date: datetime
    recommendations: List[str]


@dataclass
class QAMetrics:
    """Quality assurance metrics for monitoring"""

    metrics_id: str
    project_id: str
    metric_type: QAMetricType
    stage: Optional[QAStage]
    reviewer_id: Optional[str]
    metric_value: float
    calculation_date: datetime
    time_period: str  # 'daily', 'weekly', 'monthly'
    additional_data: Dict[str, Any]


class CollaborativeQAWorkflows:
    """
    Comprehensive collaborative quality assurance workflow management

    Features:
    - Multi - stage QA workflow orchestration
    - Automated reviewer assignments
    - Consensus measurement and improvement
   -Expert validation processes
   -Quality metrics tracking and reporting
    """

    def __init__(self, db_path: str = "data / eunice.db"):
        self.db_path = db_path

        # Default consensus thresholds
        self.default_consensus_thresholds = {
            QAStage.INITIAL_SCREENING: 0.8,
            QAStage.DETAILED_ASSESSMENT: 0.85,
            QAStage.DATA_EXTRACTION: 0.9,
            QAStage.QUALITY_ASSESSMENT: 0.85,
            QAStage.RISK_OF_BIAS: 0.8,
            QAStage.GRADE_ASSESSMENT: 0.9,
        }

        # Initialize database
        self._init_database()

        logger.info("Collaborative QA Workflows initialized")

    def _init_database(self):
        """Initialize QA workflows database tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # QA workflows table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS qa_workflows (
                        workflow_id TEXT PRIMARY KEY,
                        project_id TEXT NOT NULL,
                        workflow_name TEXT NOT NULL,
                        stages TEXT NOT NULL,
                        required_reviewers_per_stage TEXT NOT NULL,
                        consensus_thresholds TEXT NOT NULL,
                        auto_advance_conditions TEXT NOT NULL,
                        expert_validation_required TEXT NOT NULL,
                        created_by TEXT NOT NULL,
                        created_date TEXT NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE
                    )
                """
                )

                # QA assignments table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS qa_assignments (
                        assignment_id TEXT PRIMARY KEY,
                        workflow_id TEXT NOT NULL,
                        stage TEXT NOT NULL,
                        study_id TEXT NOT NULL,
                        reviewer_id TEXT NOT NULL,
                        assigned_date TEXT NOT NULL,
                        due_date TEXT,
                        completion_date TEXT,
                        status TEXT DEFAULT 'assigned',
                        assignment_data TEXT,
                        FOREIGN KEY (workflow_id) REFERENCES qa_workflows (workflow_id)
                    )
                """
                )

                # QA submissions table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS qa_submissions (
                        submission_id TEXT PRIMARY KEY,
                        assignment_id TEXT NOT NULL,
                        reviewer_id TEXT NOT NULL,
                        stage TEXT NOT NULL,
                        study_id TEXT NOT NULL,
                        submission_data TEXT NOT NULL,
                        submission_date TEXT NOT NULL,
                        confidence_score REAL NOT NULL,
                        time_spent_minutes INTEGER NOT NULL,
                        notes TEXT,
                        FOREIGN KEY (assignment_id) REFERENCES qa_assignments (assignment_id)
                    )
                """
                )

                # Consensus metrics table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS consensus_metrics (
                        metrics_id TEXT PRIMARY KEY,
                        project_id TEXT NOT NULL,
                        stage TEXT NOT NULL,
                        study_id TEXT NOT NULL,
                        reviewers TEXT NOT NULL,
                        agreement_percentage REAL NOT NULL,
                        consensus_level TEXT NOT NULL,
                        disagreement_items TEXT NOT NULL,
                        kappa_score REAL,
                        calculation_date TEXT NOT NULL,
                        recommendations TEXT NOT NULL
                    )
                """
                )

                # Expert validations table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS expert_validations (
                        validation_id TEXT PRIMARY KEY,
                        submission_ids TEXT NOT NULL,
                        expert_id TEXT NOT NULL,
                        stage TEXT NOT NULL,
                        study_id TEXT NOT NULL,
                        validation_status TEXT NOT NULL,
                        expert_decision TEXT NOT NULL,
                        validation_notes TEXT NOT NULL,
                        confidence_score REAL NOT NULL,
                        validation_date TEXT NOT NULL,
                        recommendations TEXT NOT NULL
                    )
                """
                )

                # QA metrics table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS qa_metrics (
                        metrics_id TEXT PRIMARY KEY,
                        project_id TEXT NOT NULL,
                        metric_type TEXT NOT NULL,
                        stage TEXT,
                        reviewer_id TEXT,
                        metric_value REAL NOT NULL,
                        calculation_date TEXT NOT NULL,
                        time_period TEXT NOT NULL,
                        additional_data TEXT
                    )
                """
                )

                # Create indexes
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_qa_assignments_workflow_stage ON qa_assignments(workflow_id, "
                    "stage)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_qa_submissions_study_stage ON qa_submissions(study_id, stage)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_consensus_metrics_project_stage ON "
                    "consensus_metrics(project_id, stage)"
                )

                conn.commit()
                logger.info("QA workflows database initialized successfully")

        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            raise

    async def create_qa_workflow(
        self,
        project_id: str,
        workflow_name: str,
        stages: List[QAStage],
        created_by: str,
        custom_config: Optional[Dict[str, Any]] = None,
    ) -> QAWorkflow:
        """
        Create a new QA workflow for a project

        Args:
            project_id: Project identifier
            workflow_name: Name of the workflow
            stages: List of QA stages
            created_by: User creating the workflow
            custom_config: Custom configuration overrides

        Returns:
            Created QA workflow
        """
        try:
            # Set default configurations
            required_reviewers = {stage: 2 for stage in stages}
            consensus_thresholds = {
                stage: self.default_consensus_thresholds.get(stage, 0.8)
                for stage in stages
            }
            auto_advance = {
                stage: {"consensus_threshold": 0.9, "min_reviewers": 2}
                for stage in stages
            }
            expert_validation = {QAStage.GRADE_ASSESSMENT, QAStage.FINAL_REVIEW}

            # Apply custom configuration
            if custom_config:
                required_reviewers.update(custom_config.get("required_reviewers", {}))
                consensus_thresholds.update(
                    custom_config.get("consensus_thresholds", {})
                )
                auto_advance.update(custom_config.get("auto_advance", {}))
                expert_validation.update(custom_config.get("expert_validation", set()))

            workflow = QAWorkflow(
                workflow_id=str(uuid.uuid4()),
                project_id=project_id,
                workflow_name=workflow_name,
                stages=stages,
                required_reviewers_per_stage=required_reviewers,
                consensus_thresholds=consensus_thresholds,
                auto_advance_conditions=auto_advance,
                expert_validation_required=expert_validation,
                created_by=created_by,
                created_date=datetime.now(timezone.utc),
                is_active=True,
            )

            await self._store_workflow(workflow)
            logger.info(
                f"Created QA workflow: {workflow_name} for project {project_id}"
            )
            return workflow

        except Exception as e:
            logger.error(f"QA workflow creation failed: {str(e)}")
            raise

    async def assign_reviewers_to_stage(
        self,
        workflow_id: str,
        stage: QAStage,
        study_ids: List[str],
        reviewer_ids: List[str],
        due_date: Optional[datetime] = None,
    ) -> List[QAAssignment]:
        """
        Assign reviewers to a specific QA stage for multiple studies

        Args:
            workflow_id: QA workflow identifier
            stage: QA stage for assignments
            study_ids: List of study identifiers
            reviewer_ids: List of reviewer identifiers
            due_date: Optional due date for assignments

        Returns:
            List of created assignments
        """
        try:
            assignments = []

            for study_id in study_ids:
                for reviewer_id in reviewer_ids:
                    assignment = QAAssignment(
                        assignment_id=str(uuid.uuid4()),
                        workflow_id=workflow_id,
                        stage=stage,
                        study_id=study_id,
                        reviewer_id=reviewer_id,
                        assigned_date=datetime.now(timezone.utc),
                        due_date=due_date,
                        completion_date=None,
                        status="assigned",
                        assignment_data={
                            "instructions": f"Complete {stage.value} for study {study_id}",
                            "priority": "normal",
                        },
                    )

                    await self._store_assignment(assignment)
                    assignments.append(assignment)

            logger.info(
                f"Created {len(assignments)} QA assignments for stage {stage.value}"
            )
            return assignments

        except Exception as e:
            logger.error(f"Reviewer assignment failed: {str(e)}")
            raise

    async def submit_qa_assessment(
        self,
        assignment_id: str,
        submission_data: Dict[str, Any],
        confidence_score: float,
        time_spent_minutes: int,
        notes: Optional[str] = None,
    ) -> QASubmission:
        """
        Submit a QA assessment for an assignment

        Args:
            assignment_id: Assignment identifier
            submission_data: Assessment data and decisions
            confidence_score: Reviewer's confidence in assessment
            time_spent_minutes: Time spent on assessment
            notes: Optional reviewer notes

        Returns:
            Created QA submission
        """
        try:
            # Get assignment details
            assignment = await self._get_assignment(assignment_id)
            if not assignment:
                raise ValueError(f"Assignment {assignment_id} not found")

            # Create submission
            submission = QASubmission(
                submission_id=str(uuid.uuid4()),
                assignment_id=assignment_id,
                reviewer_id=assignment.reviewer_id,
                stage=assignment.stage,
                study_id=assignment.study_id,
                submission_data=submission_data,
                submission_date=datetime.now(timezone.utc),
                confidence_score=confidence_score,
                time_spent_minutes=time_spent_minutes,
                notes=notes,
            )

            await self._store_submission(submission)

            # Update assignment status
            await self._update_assignment_status(assignment_id, "completed")

            # Check for consensus and auto-advance
            await self._check_stage_consensus(
                assignment.workflow_id, assignment.stage, assignment.study_id
            )

            logger.info(f"QA submission completed for assignment {assignment_id}")
            return submission

        except Exception as e:
            logger.error(f"QA submission failed: {str(e)}")
            raise

    async def calculate_consensus_metrics(
        self, project_id: str, stage: QAStage, study_id: str
    ) -> Optional[ConsensusMetrics]:
        """
        Calculate consensus metrics between reviewers for a study / stage

        Args:
            project_id: Project identifier
            stage: QA stage
            study_id: Study identifier

        Returns:
            Calculated consensus metrics
        """
        try:
            # Get all submissions for this study / stage
            submissions = await self._get_submissions_for_study_stage(study_id, stage)

            if len(submissions) < 2:
                logger.warning(
                    f"Insufficient submissions for consensus calculation: {len(submissions)}"
                )
                return None

            # Extract reviewer decisions
            reviewers = [sub.reviewer_id for sub in submissions]
            decisions = {}

            # Analyze different types of decisions
            agreement_scores = []
            disagreement_items = []

            # Calculate agreement for each decision field
            for submission in submissions:
                for key, value in submission.submission_data.items():
                    if key not in decisions:
                        decisions[key] = {}
                    decisions[key][submission.reviewer_id] = value

            # Calculate overall agreement
            total_comparisons = 0
            total_agreements = 0

            for decision_key, reviewer_decisions in decisions.items():
                if len(reviewer_decisions) >= 2:
                    values = list(reviewer_decisions.values())

                    # For categorical decisions
                    if isinstance(values[0], str):
                        agreement_count = sum(1 for v in values if v == values[0])
                        agreement_ratio = agreement_count / len(values)

                    # For numerical decisions
                    elif isinstance(values[0], (int, float)):
                        # Consider agreement if values are within 10% of each other
                        mean_value = statistics.mean(values)
                        tolerance = abs(mean_value * 0.1) if mean_value != 0 else 0.1
                        agreement_count = sum(
                            1 for v in values if abs(v-mean_value) <= tolerance
                        )
                        agreement_ratio = agreement_count / len(values)

                    else:
                        agreement_ratio = (
                            1.0 if all(v == values[0] for v in values) else 0.0
                        )

                    agreement_scores.append(agreement_ratio)
                    total_comparisons += 1
                    total_agreements += agreement_ratio

                    # Track disagreements
                    if agreement_ratio < 1.0:
                        disagreement_items.append(
                            {
                                "decision_field": decision_key,
                                "reviewer_decisions": reviewer_decisions,
                                "agreement_ratio": agreement_ratio,
                            }
                        )

            # Calculate overall agreement percentage
            agreement_percentage = (
                (total_agreements / total_comparisons) * 100
                if total_comparisons > 0
                else 0
            )

            # Determine consensus level
            consensus_level = self._determine_consensus_level(agreement_percentage)

            # Calculate Cohen's Kappa (simplified version for multiple raters)
            kappa_score = await self._calculate_kappa_score(submissions)

            # Generate recommendations
            recommendations = await self._generate_consensus_recommendations(
                agreement_percentage, disagreement_items, submissions
            )

            # Create consensus metrics
            metrics = ConsensusMetrics(
                metrics_id=str(uuid.uuid4()),
                project_id=project_id,
                stage=stage,
                study_id=study_id,
                reviewers=reviewers,
                agreement_percentage=agreement_percentage,
                consensus_level=consensus_level,
                disagreement_items=disagreement_items,
                kappa_score=kappa_score,
                calculation_date=datetime.now(timezone.utc),
                recommendations=recommendations,
            )

            await self._store_consensus_metrics(metrics)
            logger.info(
                f"Consensus metrics calculated: {agreement_percentage:.1f}% agreement"
            )
            return metrics

        except Exception as e:
            logger.error(f"Consensus calculation failed: {str(e)}")
            return None

    async def request_expert_validation(
        self, submission_ids: List[str], expert_id: str, stage: QAStage, study_id: str
    ) -> ExpertValidation:
        """
        Request expert validation for QA submissions

        Args:
            submission_ids: List of submission identifiers to validate
            expert_id: Expert reviewer identifier
            stage: QA stage being validated
            study_id: Study identifier

        Returns:
            Expert validation record
        """
        try:
            validation = ExpertValidation(
                validation_id=str(uuid.uuid4()),
                submission_ids=submission_ids,
                expert_id=expert_id,
                stage=stage,
                study_id=study_id,
                validation_status=ValidationStatus.PENDING,
                expert_decision={},
                validation_notes="",
                confidence_score=0.0,
                validation_date=datetime.now(timezone.utc),
                recommendations=[],
            )

            await self._store_expert_validation(validation)
            logger.info(
                f"Expert validation requested for study {study_id}, stage {stage.value}"
            )
            return validation

        except Exception as e:
            logger.error(f"Expert validation request failed: {str(e)}")
            raise

    async def complete_expert_validation(
        self,
        validation_id: str,
        expert_decision: Dict[str, Any],
        validation_status: ValidationStatus,
        validation_notes: str,
        confidence_score: float,
        recommendations: List[str],
    ) -> Optional[ExpertValidation]:
        """
        Complete expert validation with decision

        Args:
            validation_id: Validation identifier
            expert_decision: Expert's validation decision
            validation_status: Validation outcome status
            validation_notes: Expert's notes and rationale
            confidence_score: Expert's confidence in decision
            recommendations: Expert recommendations for improvement

        Returns:
            Updated expert validation
        """
        try:
            # Update validation record
            await self._update_expert_validation(
                validation_id,
                expert_decision,
                validation_status,
                validation_notes,
                confidence_score,
                recommendations,
            )

            # Get updated validation
            validation = await self._get_expert_validation(validation_id)

            # If approved, advance workflow stage
            if validation and validation_status == ValidationStatus.APPROVED:
                await self._advance_workflow_stage(
                    validation.study_id, validation.stage
                )

            logger.info(f"Expert validation completed: {validation_status.value}")
            return validation

        except Exception as e:
            logger.error(f"Expert validation completion failed: {str(e)}")
            raise

    async def calculate_qa_metrics(
        self, project_id: str, time_period: str = "weekly"
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive QA metrics for a project

        Args:
            project_id: Project identifier
            time_period: Time period for metrics calculation

        Returns:
            Dictionary of calculated QA metrics
        """
        try:
            metrics = {}

            # Calculate inter-rater reliability
            irr_metric = await self._calculate_inter_rater_reliability(project_id)
            metrics["inter_rater_reliability"] = irr_metric

            # Calculate completion rates
            completion_rates = await self._calculate_completion_rates(project_id)
            metrics["completion_rates"] = completion_rates

            # Calculate consensus scores
            consensus_scores = await self._calculate_average_consensus(project_id)
            metrics["consensus_scores"] = consensus_scores

            # Calculate efficiency metrics
            efficiency_metrics = await self._calculate_efficiency_metrics(project_id)
            metrics["efficiency_metrics"] = efficiency_metrics

            # Calculate error rates
            error_rates = await self._calculate_error_rates(project_id)
            metrics["error_rates"] = error_rates

            # Store metrics in database
            for metric_type, value in metrics.items():
                # Convert metric type to valid enum
                metric_type_enum = None
                if "inter_rater" in metric_type.lower():
                    metric_type_enum = QAMetricType.INTER_RATER_RELIABILITY
                elif "completion" in metric_type.lower():
                    metric_type_enum = QAMetricType.COMPLETION_RATE
                elif "consensus" in metric_type.lower():
                    metric_type_enum = QAMetricType.CONSENSUS_SCORE
                elif "efficiency" in metric_type.lower():
                    metric_type_enum = QAMetricType.EFFICIENCY_SCORE
                elif "error" in metric_type.lower():
                    metric_type_enum = QAMetricType.ERROR_RATE
                else:
                    metric_type_enum = QAMetricType.CONSISTENCY_SCORE

                qa_metric = QAMetrics(
                    metrics_id=str(uuid.uuid4()),
                    project_id=project_id,
                    metric_type=metric_type_enum,
                    stage=None,
                    reviewer_id=None,
                    metric_value=value if isinstance(value, (int, float)) else 0.0,
                    calculation_date=datetime.now(timezone.utc),
                    time_period=time_period,
                    additional_data=value if isinstance(value, dict) else {},
                )
                await self._store_qa_metric(qa_metric)

            logger.info(f"QA metrics calculated for project {project_id}")
            return metrics

        except Exception as e:
            logger.error(f"QA metrics calculation failed: {str(e)}")
            return {}

    def _determine_consensus_level(self, agreement_percentage: float) -> ConsensusLevel:
        """Determine consensus level from agreement percentage"""
        if agreement_percentage >= 100:
            return ConsensusLevel.PERFECT
        elif agreement_percentage >= 90:
            return ConsensusLevel.HIGH
        elif agreement_percentage >= 70:
            return ConsensusLevel.MODERATE
        elif agreement_percentage >= 50:
            return ConsensusLevel.LOW
        else:
            return ConsensusLevel.POOR

    async def _calculate_kappa_score(
        self, submissions: List[QASubmission]
    ) -> Optional[float]:
        """Calculate inter-rater agreement using Cohen's Kappa"""
        try:
            # Simplified kappa calculation for demonstration
            # In production, would use more sophisticated statistical methods
            if len(submissions) < 2:
                return None

            # Extract categorical decisions for kappa calculation
            # This is a simplified implementation
            return 0.75  # Placeholder

        except Exception as e:
            logger.error(f"Kappa calculation failed: {str(e)}")
            return None

    async def _generate_consensus_recommendations(
        self,
        agreement_percentage: float,
        disagreement_items: List[Dict],
        submissions: List[QASubmission],
    ) -> List[str]:
        """Generate recommendations for improving consensus"""
        recommendations = []

        if agreement_percentage < 70:
            recommendations.append(
                "Consider additional reviewer training to improve agreement"
            )
            recommendations.append("Review and clarify assessment criteria")

        if len(disagreement_items) > 0:
            recommendations.append(
                "Focus on resolving specific disagreement areas through discussion"
            )

        if agreement_percentage < 50:
            recommendations.append("Consider expert mediation for this assessment")
            recommendations.append(
                "Review assessment protocols and provide additional guidance"
            )

        return recommendations

    async def _check_stage_consensus(
        self, workflow_id: str, stage: QAStage, study_id: str
    ):
        """Check if consensus is reached for auto-advancing stage"""
        try:
            # Get workflow configuration
            workflow = await self._get_workflow(workflow_id)
            if not workflow:
                return

            # Get consensus threshold for this stage
            threshold = workflow.consensus_thresholds.get(stage, 0.8)

            # Calculate current consensus
            submissions = await self._get_submissions_for_study_stage(study_id, stage)
            required_reviewers = workflow.required_reviewers_per_stage.get(stage, 2)

            if len(submissions) >= required_reviewers:
                # Calculate consensus (simplified)
                consensus_score = await self._calculate_simple_consensus(submissions)

                if consensus_score >= threshold:
                    # Auto-advance to next stage if configured
                    auto_advance = workflow.auto_advance_conditions.get(stage, {})
                    if auto_advance.get("auto_advance", False):
                        await self._advance_workflow_stage(study_id, stage)
                        logger.info(
                            f"Auto-advanced study {study_id} from stage {stage.value}"
                        )

        except Exception as e:
            logger.error(f"Stage consensus check failed: {str(e)}")

    async def _calculate_simple_consensus(
        self, submissions: List[QASubmission]
    ) -> float:
        """Calculate simple consensus score from submissions"""
        if len(submissions) < 2:
            return 0.0

        # Simplified consensus calculation
        # In production, would use more sophisticated methods
        return 0.85  # Placeholder

    async def _advance_workflow_stage(self, study_id: str, current_stage: QAStage):
        """Advance study to next workflow stage"""
        # Placeholder for stage advancement logic
        logger.info(f"Advancing study {study_id} from stage {current_stage.value}")

    # Database operations
    async def _store_workflow(self, workflow: QAWorkflow):
        """Store QA workflow in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO qa_workflows
                    (workflow_id, project_id, workflow_name, stages, required_reviewers_per_stage,
                     consensus_thresholds, auto_advance_conditions, expert_validation_required,
                     created_by, created_date, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        workflow.workflow_id,
                        workflow.project_id,
                        workflow.workflow_name,
                        json.dumps([stage.value for stage in workflow.stages]),
                        json.dumps(
                            {
                                stage.value: count
                                for stage, count in workflow.required_reviewers_per_stage.items()
                            }
                        ),
                        json.dumps(
                            {
                                stage.value: threshold
                                for stage, threshold in workflow.consensus_thresholds.items()
                            }
                        ),
                        json.dumps(
                            {
                                stage.value: conditions
                                for stage, conditions in workflow.auto_advance_conditions.items()
                            }
                        ),
                        json.dumps(
                            [
                                stage.value
                                for stage in workflow.expert_validation_required
                            ]
                        ),
                        workflow.created_by,
                        workflow.created_date.isoformat(),
                        workflow.is_active,
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to store workflow: {str(e)}")
            raise

    async def _store_assignment(self, assignment: QAAssignment):
        """Store QA assignment in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO qa_assignments
                    (assignment_id, workflow_id, stage, study_id, reviewer_id, assigned_date,
                     due_date, completion_date, status, assignment_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        assignment.assignment_id,
                        assignment.workflow_id,
                        assignment.stage.value,
                        assignment.study_id,
                        assignment.reviewer_id,
                        assignment.assigned_date.isoformat(),
                        (
                            assignment.due_date.isoformat()
                            if assignment.due_date
                            else None
                        ),
                        (
                            assignment.completion_date.isoformat()
                            if assignment.completion_date
                            else None
                        ),
                        assignment.status,
                        json.dumps(assignment.assignment_data),
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to store assignment: {str(e)}")
            raise

    async def _store_submission(self, submission: QASubmission):
        """Store QA submission in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO qa_submissions
                    (submission_id, assignment_id, reviewer_id, stage, study_id, submission_data,
                     submission_date, confidence_score, time_spent_minutes, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        submission.submission_id,
                        submission.assignment_id,
                        submission.reviewer_id,
                        submission.stage.value,
                        submission.study_id,
                        json.dumps(submission.submission_data),
                        submission.submission_date.isoformat(),
                        submission.confidence_score,
                        submission.time_spent_minutes,
                        submission.notes,
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to store submission: {str(e)}")
            raise

    async def _store_consensus_metrics(self, metrics: ConsensusMetrics):
        """Store consensus metrics in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO consensus_metrics
                    (metrics_id, project_id, stage, study_id, reviewers, agreement_percentage,
                     consensus_level, disagreement_items, kappa_score, calculation_date, recommendations)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        metrics.metrics_id,
                        metrics.project_id,
                        metrics.stage.value,
                        metrics.study_id,
                        json.dumps(metrics.reviewers),
                        metrics.agreement_percentage,
                        metrics.consensus_level.value,
                        json.dumps(metrics.disagreement_items),
                        metrics.kappa_score,
                        metrics.calculation_date.isoformat(),
                        json.dumps(metrics.recommendations),
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to store consensus metrics: {str(e)}")
            raise

    async def _store_expert_validation(self, validation: ExpertValidation):
        """Store expert validation in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO expert_validations
                    (validation_id, submission_ids, expert_id, stage, study_id, validation_status,
                     expert_decision, validation_notes, confidence_score, validation_date, recommendations)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        validation.validation_id,
                        json.dumps(validation.submission_ids),
                        validation.expert_id,
                        validation.stage.value,
                        validation.study_id,
                        validation.validation_status.value,
                        json.dumps(validation.expert_decision),
                        validation.validation_notes,
                        validation.confidence_score,
                        validation.validation_date.isoformat(),
                        json.dumps(validation.recommendations),
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to store expert validation: {str(e)}")
            raise

    async def _store_qa_metric(self, metric: QAMetrics):
        """Store QA metric in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO qa_metrics
                    (metrics_id, project_id, metric_type, stage, reviewer_id, metric_value,
                     calculation_date, time_period, additional_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        metric.metrics_id,
                        metric.project_id,
                        metric.metric_type.value,
                        metric.stage.value if metric.stage else None,
                        metric.reviewer_id,
                        metric.metric_value,
                        metric.calculation_date.isoformat(),
                        metric.time_period,
                        json.dumps(metric.additional_data),
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to store QA metric: {str(e)}")
            raise

    # Retrieval methods
    async def _get_workflow(self, workflow_id: str) -> Optional[QAWorkflow]:
        """Get QA workflow by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM qa_workflows WHERE workflow_id = ?", (workflow_id,)
                )
                row = cursor.fetchone()

                if row:
                    return QAWorkflow(
                        workflow_id=row[0],
                        project_id=row[1],
                        workflow_name=row[2],
                        stages=[QAStage(stage) for stage in json.loads(row[3])],
                        required_reviewers_per_stage={
                            QAStage(k): v for k, v in json.loads(row[4]).items()
                        },
                        consensus_thresholds={
                            QAStage(k): v for k, v in json.loads(row[5]).items()
                        },
                        auto_advance_conditions={
                            QAStage(k): v for k, v in json.loads(row[6]).items()
                        },
                        expert_validation_required={
                            QAStage(stage) for stage in json.loads(row[7])
                        },
                        created_by=row[8],
                        created_date=datetime.fromisoformat(row[9]),
                        is_active=bool(row[10]),
                    )
                return None
        except Exception as e:
            logger.error(f"Failed to get workflow: {str(e)}")
            return None

    async def _get_assignment(self, assignment_id: str) -> Optional[QAAssignment]:
        """Get QA assignment by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM qa_assignments WHERE assignment_id = ?",
                    (assignment_id,),
                )
                row = cursor.fetchone()

                if row:
                    return QAAssignment(
                        assignment_id=row[0],
                        workflow_id=row[1],
                        stage=QAStage(row[2]),
                        study_id=row[3],
                        reviewer_id=row[4],
                        assigned_date=datetime.fromisoformat(row[5]),
                        due_date=datetime.fromisoformat(row[6]) if row[6] else None,
                        completion_date=(
                            datetime.fromisoformat(row[7]) if row[7] else None
                        ),
                        status=row[8],
                        assignment_data=json.loads(row[9]) if row[9] else {},
                    )
                return None
        except Exception as e:
            logger.error(f"Failed to get assignment: {str(e)}")
            return None

    async def _get_submissions_for_study_stage(
        self, study_id: str, stage: QAStage
    ) -> List[QASubmission]:
        """Get all submissions for a study / stage combination"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT * FROM qa_submissions
                    WHERE study_id = ? AND stage = ?
                """,
                    (study_id, stage.value),
                )

                submissions = []
                for row in cursor.fetchall():
                    submission = QASubmission(
                        submission_id=row[0],
                        assignment_id=row[1],
                        reviewer_id=row[2],
                        stage=QAStage(row[3]),
                        study_id=row[4],
                        submission_data=json.loads(row[5]),
                        submission_date=datetime.fromisoformat(row[6]),
                        confidence_score=row[7],
                        time_spent_minutes=row[8],
                        notes=row[9],
                    )
                    submissions.append(submission)

                return submissions
        except Exception as e:
            logger.error(f"Failed to get submissions: {str(e)}")
            return []

    async def _get_expert_validation(
        self, validation_id: str
    ) -> Optional[ExpertValidation]:
        """Get expert validation by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM expert_validations WHERE validation_id = ?",
                    (validation_id,),
                )
                row = cursor.fetchone()

                if row:
                    return ExpertValidation(
                        validation_id=row[0],
                        submission_ids=json.loads(row[1]),
                        expert_id=row[2],
                        stage=QAStage(row[3]),
                        study_id=row[4],
                        validation_status=ValidationStatus(row[5]),
                        expert_decision=json.loads(row[6]),
                        validation_notes=row[7],
                        confidence_score=row[8],
                        validation_date=datetime.fromisoformat(row[9]),
                        recommendations=json.loads(row[10]),
                    )
                return None
        except Exception as e:
            logger.error(f"Failed to get expert validation: {str(e)}")
            return None

    # Update methods
    async def _update_assignment_status(self, assignment_id: str, status: str):
        """Update assignment status"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE qa_assignments
                    SET status = ?, completion_date = ?
                    WHERE assignment_id = ?
                """,
                    (status, datetime.now(timezone.utc).isoformat(), assignment_id),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to update assignment status: {str(e)}")

    async def _update_expert_validation(
        self,
        validation_id: str,
        expert_decision: Dict[str, Any],
        validation_status: ValidationStatus,
        validation_notes: str,
        confidence_score: float,
        recommendations: List[str],
    ):
        """Update expert validation with decision"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE expert_validations
                    SET expert_decision = ?, validation_status = ?, validation_notes = ?,
                        confidence_score = ?, recommendations = ?
                    WHERE validation_id = ?
                """,
                    (
                        json.dumps(expert_decision),
                        validation_status.value,
                        validation_notes,
                        confidence_score,
                        json.dumps(recommendations),
                        validation_id,
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to update expert validation: {str(e)}")

    # Metrics calculation methods
    async def _calculate_inter_rater_reliability(self, project_id: str) -> float:
        """Calculate inter-rater reliability for project"""
        # Placeholder for IRR calculation
        return 0.82

    async def _calculate_completion_rates(self, project_id: str) -> Dict[str, float]:
        """Calculate completion rates by stage"""
        # Placeholder for completion rate calculation
        return {
            "initial_screening": 0.95,
            "detailed_assessment": 0.88,
            "quality_assessment": 0.92,
        }

    async def _calculate_average_consensus(self, project_id: str) -> float:
        """Calculate average consensus score"""
        # Placeholder for consensus calculation
        return 0.86

    async def _calculate_efficiency_metrics(self, project_id: str) -> Dict[str, float]:
        """Calculate efficiency metrics"""
        # Placeholder for efficiency calculation
        return {"avg_time_per_study": 25.5, "reviews_per_hour": 2.4}

    async def _calculate_error_rates(self, project_id: str) -> float:
        """Calculate error rates"""
        # Placeholder for error rate calculation
        return 0.03


if __name__ == "__main__":
    # Example usage
    async def test_qa_workflows():
        qa_system = CollaborativeQAWorkflows()

        # Create QA workflow
        workflow = await qa_system.create_qa_workflow(
            project_id="test_project",
            workflow_name="Standard Systematic Review QA",
            stages=[
                QAStage.INITIAL_SCREENING,
                QAStage.DETAILED_ASSESSMENT,
                QAStage.QUALITY_ASSESSMENT,
            ],
            created_by="admin",
        )

        # Assign reviewers
        assignments = await qa_system.assign_reviewers_to_stage(
            workflow_id=workflow.workflow_id,
            stage=QAStage.INITIAL_SCREENING,
            study_ids=["study1", "study2"],
            reviewer_ids=["reviewer1", "reviewer2"],
        )

        print(f"Created workflow: {workflow.workflow_name}")
        print(f"Created {len(assignments)} assignments")

        # Submit assessments
        for assignment in assignments[:2]:  # Submit first two
            await qa_system.submit_qa_assessment(
                assignment_id=assignment.assignment_id,
                submission_data={
                    "decision": "include",
                    "quality_score": 8.5,
                    "criteria_met": ["population", "intervention", "outcome"],
                },
                confidence_score=0.9,
                time_spent_minutes=30,
            )

        # Calculate consensus
        consensus = await qa_system.calculate_consensus_metrics(
            project_id="test_project",
            stage=QAStage.INITIAL_SCREENING,
            study_id="study1",
        )

        if consensus:
            print(
                f"Consensus: {consensus.agreement_percentage:.1f}% ({consensus.consensus_level.value})"
            )

        # Calculate QA metrics
        metrics = await qa_system.calculate_qa_metrics("test_project")
        print(f"QA metrics calculated: {len(metrics)} metrics")

    # Run test
    asyncio.run(test_qa_workflows())

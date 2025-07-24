"""
GRADE Automation System
======================

Automated GRADE (Grading of Recommendations Assessment, Development and Evaluation)
assessment system for systematic reviews.

This module provides:
- Automated GRADE scoring based on study characteristics
- Evidence certainty determination
- Explanation generation for GRADE decisions
- Integration with evidence synthesis results

Author: Eunice AI System
Date: July 2025
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# Configure logging
logger = logging.getLogger(__name__)


class GRADELevel(Enum):
    """GRADE certainty levels"""

    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class GRADECriteria(Enum):
    """GRADE assessment criteria"""

    RISK_OF_BIAS = "risk_of_bias"
    INCONSISTENCY = "inconsistency"
    INDIRECTNESS = "indirectness"
    IMPRECISION = "imprecision"
    PUBLICATION_BIAS = "publication_bias"
    LARGE_EFFECT = "large_effect"
    DOSE_RESPONSE = "dose_response"
    CONFOUNDERS = "confounders"


class StudyDesign(Enum):
    """Study design types for GRADE assessment"""

    RANDOMIZED_TRIAL = "randomized_controlled_trial"
    OBSERVATIONAL = "observational_study"
    CASE_CONTROL = "case_control"
    COHORT = "cohort_study"
    CROSS_SECTIONAL = "cross_sectional"
    CASE_SERIES = "case_series"


@dataclass
class EvidenceProfile:
    """Evidence profile for GRADE assessment"""

    outcome: str
    studies: List[Dict[str, Any]]
    study_design: StudyDesign
    participants: int
    effect_estimate: Optional[float] = None
    confidence_interval: Optional[Tuple[float, float]] = None
    heterogeneity_i2: Optional[float] = None
    risk_of_bias_concerns: List[str] = field(default_factory=list)
    indirectness_concerns: List[str] = field(default_factory=list)
    imprecision_concerns: List[str] = field(default_factory=list)
    publication_bias_detected: bool = False
    large_effect_size: bool = False
    dose_response_gradient: bool = False
    confounders_reduce_effect: bool = False


@dataclass
class GRADEAssessment:
    """Complete GRADE assessment result"""

    outcome: str
    initial_certainty: GRADELevel
    final_certainty: GRADELevel
    downgrades: Dict[GRADECriteria, int] = field(default_factory=dict)
    upgrades: Dict[GRADECriteria, int] = field(default_factory=dict)
    rationale: Dict[str, str] = field(default_factory=dict)
    evidence_profile: Optional[EvidenceProfile] = None
    assessment_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confidence_score: float = 0.0


@dataclass
class GRADERecommendation:
    """GRADE recommendation based on assessment"""

    strength: str  # "strong" or "conditional"
    direction: str  # "for" or "against"
    certainty: GRADELevel
    rationale: str
    considerations: List[str] = field(default_factory=list)


class GRADEAutomation:
    """
    Automated GRADE assessment system

    Provides intelligent GRADE scoring based on study characteristics,
    automated certainty determination, and explanation generation.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize GRADE automation system

        Args:
            config: Configuration dictionary for GRADE parameters
        """
        self.config = config or self._get_default_config()
        self.assessment_history: List[GRADEAssessment] = []

        # Initialize assessment criteria weights
        self.criteria_weights = self.config.get(
            "criteria_weights",
            {
                GRADECriteria.RISK_OF_BIAS: 1.0,
                GRADECriteria.INCONSISTENCY: 1.0,
                GRADECriteria.INDIRECTNESS: 0.8,
                GRADECriteria.IMPRECISION: 0.9,
                GRADECriteria.PUBLICATION_BIAS: 0.7,
            },
        )

        logger.info("GRADE automation system initialized")

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default GRADE configuration"""
        return {
            "criteria_weights": {
                GRADECriteria.RISK_OF_BIAS: 1.0,
                GRADECriteria.INCONSISTENCY: 1.0,
                GRADECriteria.INDIRECTNESS: 0.8,
                GRADECriteria.IMPRECISION: 0.9,
                GRADECriteria.PUBLICATION_BIAS: 0.7,
            },
            "thresholds": {
                "high_risk_of_bias": 0.3,
                "high_inconsistency": 0.5,
                "imprecision_threshold": 0.4,
                "large_effect_threshold": 2.0,
                "very_large_effect_threshold": 5.0,
            },
            "confidence_thresholds": {"high_confidence": 0.8, "moderate_confidence": 0.6, "low_confidence": 0.4},
        }

    async def assess_evidence(self, evidence_profile: EvidenceProfile) -> GRADEAssessment:
        """
        Perform automated GRADE assessment

        Args:
            evidence_profile: Evidence profile to assess

        Returns:
            Complete GRADE assessment
        """
        logger.info(f"Starting GRADE assessment for outcome: {evidence_profile.outcome}")

        # Determine initial certainty based on study design
        initial_certainty = self._determine_initial_certainty(evidence_profile.study_design)

        # Assess downgrading factors
        downgrades = await self._assess_downgrades(evidence_profile)

        # Assess upgrading factors
        upgrades = await self._assess_upgrades(evidence_profile)

        # Calculate final certainty
        final_certainty = self._calculate_final_certainty(initial_certainty, downgrades, upgrades)

        # Generate rationale
        rationale = await self._generate_rationale(evidence_profile, downgrades, upgrades)

        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(evidence_profile, downgrades, upgrades)

        assessment = GRADEAssessment(
            outcome=evidence_profile.outcome,
            initial_certainty=initial_certainty,
            final_certainty=final_certainty,
            downgrades=downgrades,
            upgrades=upgrades,
            rationale=rationale,
            evidence_profile=evidence_profile,
            confidence_score=confidence_score,
        )

        self.assessment_history.append(assessment)

        logger.info(f"GRADE assessment completed: {final_certainty.value} certainty")
        return assessment

    def _determine_initial_certainty(self, study_design: StudyDesign) -> GRADELevel:
        """Determine initial certainty based on study design"""
        design_certainty_map = {
            StudyDesign.RANDOMIZED_TRIAL: GRADELevel.HIGH,
            StudyDesign.OBSERVATIONAL: GRADELevel.LOW,
            StudyDesign.COHORT: GRADELevel.LOW,
            StudyDesign.CASE_CONTROL: GRADELevel.LOW,
            StudyDesign.CROSS_SECTIONAL: GRADELevel.VERY_LOW,
            StudyDesign.CASE_SERIES: GRADELevel.VERY_LOW,
        }

        return design_certainty_map.get(study_design, GRADELevel.VERY_LOW)

    async def _assess_downgrades(self, evidence_profile: EvidenceProfile) -> Dict[GRADECriteria, int]:
        """Assess factors that downgrade evidence certainty"""
        downgrades = {}

        # Risk of bias
        if evidence_profile.risk_of_bias_concerns:
            risk_score = len(evidence_profile.risk_of_bias_concerns) / len(evidence_profile.studies)
            if risk_score >= self.config["thresholds"]["high_risk_of_bias"]:
                downgrades[GRADECriteria.RISK_OF_BIAS] = 2 if risk_score > 0.6 else 1

        # Inconsistency (based on I² statistic)
        if evidence_profile.heterogeneity_i2 is not None:
            if evidence_profile.heterogeneity_i2 >= 75:
                downgrades[GRADECriteria.INCONSISTENCY] = 2
            elif evidence_profile.heterogeneity_i2 >= 50:
                downgrades[GRADECriteria.INCONSISTENCY] = 1

        # Indirectness
        if evidence_profile.indirectness_concerns:
            concern_severity = len(evidence_profile.indirectness_concerns)
            downgrades[GRADECriteria.INDIRECTNESS] = min(2, concern_severity)

        # Imprecision
        if evidence_profile.imprecision_concerns:
            imprecision_score = len(evidence_profile.imprecision_concerns) / 3  # Normalize
            if imprecision_score >= self.config["thresholds"]["imprecision_threshold"]:
                downgrades[GRADECriteria.IMPRECISION] = 2 if imprecision_score > 0.7 else 1

        # Publication bias
        if evidence_profile.publication_bias_detected:
            downgrades[GRADECriteria.PUBLICATION_BIAS] = 1

        return downgrades

    async def _assess_upgrades(self, evidence_profile: EvidenceProfile) -> Dict[GRADECriteria, int]:
        """Assess factors that upgrade evidence certainty"""
        upgrades = {}

        # Large effect size
        if evidence_profile.large_effect_size and evidence_profile.effect_estimate:
            effect_magnitude = abs(evidence_profile.effect_estimate)
            if effect_magnitude >= self.config["thresholds"]["very_large_effect_threshold"]:
                upgrades[GRADECriteria.LARGE_EFFECT] = 2
            elif effect_magnitude >= self.config["thresholds"]["large_effect_threshold"]:
                upgrades[GRADECriteria.LARGE_EFFECT] = 1

        # Dose - response gradient
        if evidence_profile.dose_response_gradient:
            upgrades[GRADECriteria.DOSE_RESPONSE] = 1

        # All plausible confounders would reduce effect
        if evidence_profile.confounders_reduce_effect:
            upgrades[GRADECriteria.CONFOUNDERS] = 1

        return upgrades

    def _calculate_final_certainty(
        self, initial: GRADELevel, downgrades: Dict[GRADECriteria, int], upgrades: Dict[GRADECriteria, int]
    ) -> GRADELevel:
        """Calculate final certainty level"""
        # Convert to numeric scale
        certainty_scale = {GRADELevel.VERY_LOW: 0, GRADELevel.LOW: 1, GRADELevel.MODERATE: 2, GRADELevel.HIGH: 3}

        reverse_scale = {v: k for k, v in certainty_scale.items()}

        current_level = certainty_scale[initial]

        # Apply downgrades
        total_downgrades = sum(downgrades.values())
        current_level -= total_downgrades

        # Apply upgrades (only for observational studies)
        if initial in [GRADELevel.LOW, GRADELevel.VERY_LOW]:
            total_upgrades = sum(upgrades.values())
            current_level += total_upgrades

        # Ensure within bounds
        current_level = max(0, min(3, current_level))

        return reverse_scale[current_level]

    async def _generate_rationale(
        self,
        evidence_profile: EvidenceProfile,
        downgrades: Dict[GRADECriteria, int],
        upgrades: Dict[GRADECriteria, int],
    ) -> Dict[str, str]:
        """Generate rationale for GRADE decisions"""
        rationale = {}

        # Downgrade rationales
        for criteria, level in downgrades.items():
            if criteria == GRADECriteria.RISK_OF_BIAS:
                rationale[criteria.value] = (
                    f"Downgraded {level} level(s) due to risk of bias concerns: "
                    f"{', '.join(evidence_profile.risk_of_bias_concerns[:3])}"
                )
            elif criteria == GRADECriteria.INCONSISTENCY:
                rationale[criteria.value] = (
                    f"Downgraded {level} level(s) due to substantial heterogeneity "
                    f"(I² = {evidence_profile.heterogeneity_i2}%)"
                )
            elif criteria == GRADECriteria.INDIRECTNESS:
                rationale[criteria.value] = (
                    f"Downgraded {level} level(s) due to indirectness: "
                    f"{', '.join(evidence_profile.indirectness_concerns[:2])}"
                )
            elif criteria == GRADECriteria.IMPRECISION:
                rationale[criteria.value] = f"Downgraded {level} level(s) due to imprecision in results"
            elif criteria == GRADECriteria.PUBLICATION_BIAS:
                rationale[criteria.value] = f"Downgraded {level} level(s) due to suspected publication bias"

        # Upgrade rationales
        for criteria, level in upgrades.items():
            if criteria == GRADECriteria.LARGE_EFFECT:
                rationale[criteria.value] = (
                    f"Upgraded {level} level(s) due to large effect size "
                    f"(effect estimate: {evidence_profile.effect_estimate})"
                )
            elif criteria == GRADECriteria.DOSE_RESPONSE:
                rationale[criteria.value] = f"Upgraded {level} level(s) due to dose - response gradient"
            elif criteria == GRADECriteria.CONFOUNDERS:
                rationale[criteria.value] = f"Upgraded {level} level(s) as confounders would reduce the effect"

        return rationale

    def _calculate_confidence_score(
        self,
        evidence_profile: EvidenceProfile,
        downgrades: Dict[GRADECriteria, int],
        upgrades: Dict[GRADECriteria, int],
    ) -> float:
        """Calculate confidence score for the assessment"""
        base_score = 0.7  # Base confidence

        # Adjust based on number of studies
        study_factor = min(1.0, len(evidence_profile.studies) / 10)

        # Adjust based on sample size
        sample_factor = min(1.0, evidence_profile.participants / 1000)

        # Adjust based on downgrades / upgrades certainty
        downgrade_penalty = sum(downgrades.values()) * 0.1
        upgrade_bonus = sum(upgrades.values()) * 0.05

        confidence = base_score + study_factor * 0.2 + sample_factor * 0.1 - downgrade_penalty + upgrade_bonus

        return max(0.0, min(1.0, confidence))

    async def generate_recommendation(
        self, assessment: GRADEAssessment, context: Dict[str, Any]
    ) -> GRADERecommendation:
        """
        Generate GRADE recommendation based on assessment

        Args:
            assessment: GRADE assessment result
            context: Additional context for recommendation

        Returns:
            GRADE recommendation
        """
        # Determine recommendation strength
        strength = "strong" if assessment.final_certainty in [GRADELevel.HIGH, GRADELevel.MODERATE] else "conditional"

        # Determine direction based on effect estimate
        direction = "for"
        if assessment.evidence_profile and assessment.evidence_profile.effect_estimate:
            direction = "for" if assessment.evidence_profile.effect_estimate > 0 else "against"

        # Generate rationale
        rationale = self._generate_recommendation_rationale(assessment, context)

        # Generate considerations
        considerations = self._generate_considerations(assessment, context)

        return GRADERecommendation(
            strength=strength,
            direction=direction,
            certainty=assessment.final_certainty,
            rationale=rationale,
            considerations=considerations,
        )

    def _generate_recommendation_rationale(self, assessment: GRADEAssessment, context: Dict[str, Any]) -> str:
        """Generate rationale for recommendation"""
        certainty_text = assessment.final_certainty.value.replace("_", " ")

        rationale = (
            f"Based on {certainty_text} certainty evidence from "
            f"{len(assessment.evidence_profile.studies) if assessment.evidence_profile else 'multiple'} studies"
        )

        if assessment.evidence_profile and assessment.evidence_profile.participants:
            rationale += f" involving {assessment.evidence_profile.participants} participants"

        # Add key concerns
        if assessment.downgrades:
            major_concerns = [k.value.replace("_", " ") for k, v in assessment.downgrades.items() if v >= 2]
            if major_concerns:
                rationale += f". Major concerns include {', '.join(major_concerns)}"

        return rationale + "."

    def _generate_considerations(self, assessment: GRADEAssessment, context: Dict[str, Any]) -> List[str]:
        """Generate additional considerations"""
        considerations = []

        # Add context - specific considerations
        if context.get("population_specific"):
            considerations.append("Consider population - specific factors")

        if context.get("resource_implications"):
            considerations.append("Evaluate resource requirements and feasibility")

        if assessment.final_certainty in [GRADELevel.LOW, GRADELevel.VERY_LOW]:
            considerations.append("Additional high - quality research may change this recommendation")

        # Add assessment - specific considerations
        if GRADECriteria.INDIRECTNESS in assessment.downgrades:
            considerations.append("Direct evidence in target population may be limited")

        if GRADECriteria.IMPRECISION in assessment.downgrades:
            considerations.append("Confidence intervals include both beneficial and harmful effects")

        return considerations

    def get_assessment_summary(self, task_id: str) -> Dict[str, Any]:
        """
        Get summary of all GRADE assessments for a task

        Args:
            task_id: Task identifier

        Returns:
            Assessment summary
        """
        task_assessments = [
            a
            for a in self.assessment_history
            if (a.evidence_profile and getattr(a.evidence_profile, "task_id", None) == task_id)
        ]

        if not task_assessments:
            return {"assessments": [], "summary": "No GRADE assessments found"}

        # Calculate summary statistics
        certainty_distribution = {}
        for level in GRADELevel:
            certainty_distribution[level.value] = sum(1 for a in task_assessments if a.final_certainty == level)

        avg_confidence = sum(a.confidence_score for a in task_assessments) / len(task_assessments)

        return {
            "total_assessments": len(task_assessments),
            "certainty_distribution": certainty_distribution,
            "average_confidence": round(avg_confidence, 3),
            "assessments": [
                {
                    "outcome": a.outcome,
                    "final_certainty": a.final_certainty.value,
                    "confidence_score": a.confidence_score,
                    "assessment_date": a.assessment_date.isoformat(),
                }
                for a in task_assessments
            ],
        }

    async def export_assessment(self, assessment: GRADEAssessment, format_type: str = "json") -> str:
        """
        Export GRADE assessment in specified format

        Args:
            assessment: Assessment to export
            format_type: Export format (json, yaml, xml)

        Returns:
            Formatted assessment string
        """
        if format_type.lower() == "json":
            return json.dumps(
                {
                    "outcome": assessment.outcome,
                    "initial_certainty": assessment.initial_certainty.value,
                    "final_certainty": assessment.final_certainty.value,
                    "downgrades": {k.value: v for k, v in assessment.downgrades.items()},
                    "upgrades": {k.value: v for k, v in assessment.upgrades.items()},
                    "rationale": assessment.rationale,
                    "confidence_score": assessment.confidence_score,
                    "assessment_date": assessment.assessment_date.isoformat(),
                },
                indent=2,
            )

        # Add other formats as needed
        return str(assessment)


# Example usage and testing functions
async def demo_grade_automation():
    """Demonstrate GRADE automation capabilities"""
    print("🎯 GRADE Automation Demo")
    print("=" * 50)

    # Initialize GRADE automation
    grade = GRADEAutomation()

    # Create example evidence profile
    evidence_profile = EvidenceProfile(
        outcome="Mortality reduction",
        studies=[
            {"id": "study_1", "design": "RCT", "participants": 500},
            {"id": "study_2", "design": "RCT", "participants": 300},
            {"id": "study_3", "design": "RCT", "participants": 400},
        ],
        study_design=StudyDesign.RANDOMIZED_TRIAL,
        participants=1200,
        effect_estimate=0.75,  # Risk ratio
        confidence_interval=(0.60, 0.95),
        heterogeneity_i2=30.0,
        risk_of_bias_concerns=["allocation_concealment", "blinding"],
        imprecision_concerns=["wide_confidence_interval"],
    )

    # Perform assessment
    assessment = await grade.assess_evidence(evidence_profile)

    print(f"✅ GRADE Assessment completed:")
    print(f"   Outcome: {assessment.outcome}")
    print(f"   Initial certainty: {assessment.initial_certainty.value}")
    print(f"   Final certainty: {assessment.final_certainty.value}")
    print(f"   Confidence score: {assessment.confidence_score:.2f}")

    # Generate recommendation
    context = {"population_specific": True, "resource_implications": False}
    recommendation = await grade.generate_recommendation(assessment, context)

    print(f"\n🎯 Recommendation:")
    print(f"   Strength: {recommendation.strength}")
    print(f"   Direction: {recommendation.direction}")
    print(f"   Rationale: {recommendation.rationale}")

    return grade


if __name__ == "__main__":
    asyncio.run(demo_grade_automation())

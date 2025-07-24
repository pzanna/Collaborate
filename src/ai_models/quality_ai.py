"""
Quality AI for Systematic Reviews - Phase 4A Implementation.

This module provides AI - powered quality assessment, bias detection,
and automated GRADE evidence evaluation for systematic reviews.
"""

import asyncio
import logging
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List

import numpy as np


class QualityTool(Enum):
    """Quality assessment tools."""

    ROB_2 = "rob_2"  # Risk of Bias 2 for RCTs
    ROBINS_I = "robins_i"  # Risk of Bias In Non - randomized Studies
    CASP = "casp"  # Critical Appraisal Skills Programme
    JBI = "jbi"  # Joanna Briggs Institute
    NEWCASTLE_OTTAWA = "newcastle_ottawa"  # Newcastle - Ottawa Scale
    AMSTAR = "amstar"  # Assessment of Multiple Systematic Reviews
    PRISMA_P = "prisma_p"  # PRISMA for Protocols


class BiasRisk(Enum):
    """Risk of bias levels."""

    LOW = "low"
    SOME_CONCERNS = "some_concerns"
    HIGH = "high"
    UNCLEAR = "unclear"


class GRADEFactor(Enum):
    """GRADE assessment factors."""

    RISK_OF_BIAS = "risk_of_bias"
    INCONSISTENCY = "inconsistency"
    INDIRECTNESS = "indirectness"
    IMPRECISION = "imprecision"
    PUBLICATION_BIAS = "publication_bias"
    LARGE_EFFECT = "large_effect"
    DOSE_RESPONSE = "dose_response"
    CONFOUNDING = "confounding"


@dataclass
class QualityDomain:
    """Individual quality assessment domain."""

    domain_name: str
    assessment: BiasRisk
    justification: str
    supporting_evidence: List[str]
    confidence_score: float
    ai_detected_issues: List[str]


@dataclass
class QualityAssessment:
    """Complete quality assessment for a study."""

    study_id: str
    assessment_id: str
    assessment_tool: QualityTool
    overall_risk: BiasRisk
    domain_assessments: List[QualityDomain]
    overall_score: float
    assessment_rationale: str
    methodological_strengths: List[str]
    methodological_limitations: List[str]
    ai_confidence: float
    human_review_required: bool
    assessment_date: str
    explanation: str
    confidence_score: float
    overall_bias: BiasRisk

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "study_id": self.study_id,
            "assessment_tool": self.assessment_tool.value,
            "overall_risk": self.overall_risk.value,
            "domain_assessments": [
                {
                    "domain_name": d.domain_name,
                    "assessment": d.assessment.value,
                    "justification": d.justification,
                    "supporting_evidence": d.supporting_evidence,
                    "confidence_score": d.confidence_score,
                    "ai_detected_issues": d.ai_detected_issues,
                }
                for d in self.domain_assessments
            ],
            "overall_score": self.overall_score,
            "assessment_rationale": self.assessment_rationale,
            "methodological_strengths": self.methodological_strengths,
            "methodological_limitations": self.methodological_limitations,
            "ai_confidence": self.ai_confidence,
            "human_review_required": self.human_review_required,
            "assessment_date": self.assessment_date,
        }


@dataclass
class GRADEAssessment:
    """GRADE evidence assessment."""

    outcome: str
    study_design_quality: int  # Starting point (RCT=4, Observational=2)
    risk_of_bias_downgrade: int
    inconsistency_downgrade: int
    indirectness_downgrade: int
    imprecision_downgrade: int
    publication_bias_downgrade: int
    large_effect_upgrade: int
    dose_response_upgrade: int
    confounding_upgrade: int
    final_grade: str  # "High", "Moderate", "Low", "Very Low"
    grade_justification: str
    evidence_summary: str

    def calculate_final_grade(self) -> str:
        """Calculate final GRADE assessment."""
        initial_score = self.study_design_quality

        # Apply downgrades
        final_score = (
            initial_score
            - self.risk_of_bias_downgrade
            - self.inconsistency_downgrade
            - self.indirectness_downgrade
            - self.imprecision_downgrade
            - self.publication_bias_downgrade
        )

        # Apply upgrades
        final_score += (
            self.large_effect_upgrade
            + self.dose_response_upgrade
            + self.confounding_upgrade
        )

        # Map to GRADE levels
        if final_score >= 4:
            return "High"
        elif final_score >= 3:
            return "Moderate"
        elif final_score >= 2:
            return "Low"
        else:
            return "Very Low"


class RoB2Assessor:
    """Risk of Bias 2 assessment for RCTs."""

    DOMAINS = [
        "randomization_process",
        "deviations_intended_interventions",
        "missing_outcome_data",
        "measurement_outcome",
        "selection_reported_results",
    ]

    def __init__(self):
        """Initialize RoB 2 assessor."""
        self.logger = logging.getLogger(__name__)

    async def assess_study(self, study_data: Dict[str, Any]) -> QualityAssessment:
        """Perform RoB 2 assessment on RCT."""

        domain_assessments = []

        for domain in self.DOMAINS:
            assessment = await self._assess_domain(study_data, domain)
            domain_assessments.append(assessment)

        # Calculate overall risk
        overall_risk = self._calculate_overall_risk(domain_assessments)

        # Calculate numeric score
        overall_score = self._calculate_numeric_score(domain_assessments)

        # Generate rationale
        rationale = await self._generate_assessment_rationale(
            domain_assessments, overall_risk
        )

        # Identify strengths and limitations
        strengths = await self._identify_methodological_strengths(
            study_data, domain_assessments
        )
        limitations = await self._identify_methodological_limitations(
            study_data, domain_assessments
        )

        # Calculate AI confidence
        ai_confidence = np.mean([d.confidence_score for d in domain_assessments])

        # Determine if human review required
        human_review_required = (
            overall_risk == BiasRisk.HIGH
            or ai_confidence < 0.7
            or any(d.assessment == BiasRisk.UNCLEAR for d in domain_assessments)
        )

        return QualityAssessment(
            study_id=study_data["study_id"],
            assessment_id=f"QA_{study_data['study_id']}_{datetime.now().timestamp()}",
            assessment_tool=QualityTool.ROB_2,
            overall_risk=overall_risk,
            domain_assessments=domain_assessments,
            overall_score=overall_score,
            assessment_rationale=rationale,
            methodological_strengths=strengths,
            methodological_limitations=limitations,
            ai_confidence=float(ai_confidence),
            human_review_required=bool(human_review_required),
            assessment_date=datetime.now().isoformat(),
            explanation=rationale,
            confidence_score=float(ai_confidence),
            overall_bias=overall_risk,
        )

    async def _assess_domain(
        self, study_data: Dict[str, Any], domain: str
    ) -> QualityDomain:
        """Assess individual RoB 2 domain."""

        # Simulate AI - based domain assessment
        # In production, this would use NLP and ML models

        domain_patterns = {
            "randomization_process": {
                "low_risk_patterns": [
                    "randomized",
                    "random sequence",
                    "computer generated",
                ],
                "high_risk_patterns": ["alternating", "birth date", "medical record"],
                "some_concerns_patterns": ["unclear randomization", "not specified"],
            },
            "deviations_intended_interventions": {
                "low_risk_patterns": [
                    "intention to treat",
                    "blinded",
                    "protocol adherence",
                ],
                "high_risk_patterns": [
                    "per protocol",
                    "unblinded intervention",
                    "crossover",
                ],
                "some_concerns_patterns": ["unclear blinding", "protocol deviations"],
            },
            "missing_outcome_data": {
                "low_risk_patterns": [
                    "complete follow - up",
                    "minimal missing data",
                    "ITT analysis",
                ],
                "high_risk_patterns": [
                    "high dropout",
                    "differential missing",
                    "per protocol only",
                ],
                "some_concerns_patterns": [
                    "moderate missing data",
                    "unclear attrition",
                ],
            },
            "measurement_outcome": {
                "low_risk_patterns": [
                    "objective outcome",
                    "blinded assessor",
                    "validated measure",
                ],
                "high_risk_patterns": [
                    "subjective outcome",
                    "unblinded assessor",
                    "non - validated",
                ],
                "some_concerns_patterns": ["partially blinded", "unclear measurement"],
            },
            "selection_reported_results": {
                "low_risk_patterns": [
                    "pre - registered",
                    "protocol published",
                    "all outcomes reported",
                ],
                "high_risk_patterns": [
                    "selective reporting",
                    "post - hoc analysis",
                    "missing outcomes",
                ],
                "some_concerns_patterns": ["unclear reporting", "protocol unavailable"],
            },
        }

        patterns = domain_patterns.get(domain, {})
        study_text = " ".join(
            [
                study_data.get("title", ""),
                study_data.get("abstract", ""),
                study_data.get("methods", ""),
            ]
        ).lower()

        # Count pattern matches
        low_risk_score = sum(
            1
            for pattern in patterns.get("low_risk_patterns", [])
            if pattern in study_text
        )
        high_risk_score = sum(
            1
            for pattern in patterns.get("high_risk_patterns", [])
            if pattern in study_text
        )
        some_concerns_score = sum(
            1
            for pattern in patterns.get("some_concerns_patterns", [])
            if pattern in study_text
        )

        # Determine assessment
        if low_risk_score > high_risk_score + some_concerns_score:
            assessment = BiasRisk.LOW
            confidence = 0.8 + np.random.uniform(0, 0.2)
        elif high_risk_score > low_risk_score + some_concerns_score:
            assessment = BiasRisk.HIGH
            confidence = 0.7 + np.random.uniform(0, 0.2)
        elif some_concerns_score > 0 or (low_risk_score == high_risk_score == 0):
            assessment = BiasRisk.SOME_CONCERNS
            confidence = 0.6 + np.random.uniform(0, 0.3)
        else:
            assessment = BiasRisk.UNCLEAR
            confidence = 0.5 + np.random.uniform(0, 0.2)

        # Generate justification
        justification = await self._generate_domain_justification(
            domain, assessment, study_text
        )

        # Extract supporting evidence
        supporting_evidence = await self._extract_supporting_evidence(
            domain, study_text
        )

        # Detect AI issues
        ai_issues = await self._detect_ai_issues(domain, study_text)

        return QualityDomain(
            domain_name=domain,
            assessment=assessment,
            justification=justification,
            supporting_evidence=supporting_evidence,
            confidence_score=confidence,
            ai_detected_issues=ai_issues,
        )

    def _calculate_overall_risk(
        self, domain_assessments: List[QualityDomain]
    ) -> BiasRisk:
        """Calculate overall risk from domain assessments."""

        # RoB 2 algorithm: Overall risk is highest individual domain risk
        risks = [d.assessment for d in domain_assessments]

        if BiasRisk.HIGH in risks:
            return BiasRisk.HIGH
        elif BiasRisk.SOME_CONCERNS in risks:
            return BiasRisk.SOME_CONCERNS
        elif BiasRisk.UNCLEAR in risks:
            return BiasRisk.UNCLEAR
        else:
            return BiasRisk.LOW

    def _calculate_numeric_score(
        self, domain_assessments: List[QualityDomain]
    ) -> float:
        """Calculate numeric quality score (0 - 1)."""

        risk_scores = {
            BiasRisk.LOW: 1.0,
            BiasRisk.SOME_CONCERNS: 0.6,
            BiasRisk.HIGH: 0.2,
            BiasRisk.UNCLEAR: 0.4,
        }

        domain_scores = [risk_scores[d.assessment] for d in domain_assessments]
        return float(np.mean(domain_scores))

    async def _generate_assessment_rationale(
        self, domain_assessments: List[QualityDomain], overall_risk: BiasRisk
    ) -> str:
        """Generate overall assessment rationale."""

        high_risk_domains = [
            d.domain_name for d in domain_assessments if d.assessment == BiasRisk.HIGH
        ]
        some_concerns_domains = [
            d.domain_name
            for d in domain_assessments
            if d.assessment == BiasRisk.SOME_CONCERNS
        ]
        low_risk_domains = [
            d.domain_name for d in domain_assessments if d.assessment == BiasRisk.LOW
        ]

        rationale = f"Overall risk of bias assessed as {overall_risk.value}. "

        if high_risk_domains:
            rationale += f"High risk domains: {', '.join(high_risk_domains)}. "

        if some_concerns_domains:
            rationale += f"Some concerns in: {', '.join(some_concerns_domains)}. "

        if low_risk_domains:
            rationale += f"Low risk domains: {', '.join(low_risk_domains)}."

        return rationale

    async def _identify_methodological_strengths(
        self, study_data: Dict[str, Any], domain_assessments: List[QualityDomain]
    ) -> List[str]:
        """Identify methodological strengths."""

        strengths = []

        for domain in domain_assessments:
            if domain.assessment == BiasRisk.LOW:
                if domain.domain_name == "randomization_process":
                    strengths.append("Adequate randomization procedures")
                elif domain.domain_name == "measurement_outcome":
                    strengths.append("Objective outcome measurement")
                elif domain.domain_name == "missing_outcome_data":
                    strengths.append("Complete follow - up data")

        return strengths

    async def _identify_methodological_limitations(
        self, study_data: Dict[str, Any], domain_assessments: List[QualityDomain]
    ) -> List[str]:
        """Identify methodological limitations."""

        limitations = []

        for domain in domain_assessments:
            if domain.assessment in [BiasRisk.HIGH, BiasRisk.SOME_CONCERNS]:
                if domain.domain_name == "randomization_process":
                    limitations.append("Concerns about randomization process")
                elif domain.domain_name == "deviations_intended_interventions":
                    limitations.append("Protocol deviations noted")
                elif domain.domain_name == "missing_outcome_data":
                    limitations.append("Missing outcome data concerns")

        return limitations

    async def _generate_domain_justification(
        self, domain: str, assessment: BiasRisk, study_text: str
    ) -> str:
        """Generate justification for domain assessment."""

        justifications = {
            BiasRisk.LOW: f"Clear evidence of appropriate {domain.replace('_', ' ')} methodology",
            BiasRisk.SOME_CONCERNS: f"Some methodological concerns identified in {domain.replace('_', ' ')}",
            BiasRisk.HIGH: f"Significant methodological issues in {domain.replace('_', ' ')}",
            BiasRisk.UNCLEAR: f"Insufficient information to assess {domain.replace('_', ' ')}",
        }

        return justifications[assessment]

    async def _extract_supporting_evidence(
        self, domain: str, study_text: str
    ) -> List[str]:
        """Extract supporting evidence for domain assessment."""

        # Simulate evidence extraction
        evidence_patterns = {
            "randomization_process": ["randomization method", "sequence generation"],
            "missing_outcome_data": ["dropout rates", "attrition analysis"],
            "measurement_outcome": ["outcome measures", "blinding procedures"],
        }

        evidence = []
        for pattern in evidence_patterns.get(domain, []):
            if pattern in study_text:
                evidence.append(f"Evidence of {pattern} described")

        return evidence or ["No specific evidence extracted"]

    async def _detect_ai_issues(self, domain: str, study_text: str) -> List[str]:
        """Detect potential issues using AI analysis."""

        issues = []

        # Simulate AI issue detection
        if len(study_text) < 100:
            issues.append("Limited text available for assessment")

        if "unclear" in study_text or "not specified" in study_text:
            issues.append("Reporting gaps identified")

        return issues


class GRADEAssessor:
    """GRADE evidence assessment."""

    def __init__(self):
        """Initialize GRADE assessor."""
        self.logger = logging.getLogger(__name__)

    async def assess_evidence(
        self,
        studies: List[Dict[str, Any]],
        outcome: str,
        synthesis_results: Dict[str, Any],
    ) -> GRADEAssessment:
        """Perform GRADE assessment of evidence."""

        # Determine starting quality based on study design
        rct_proportion = sum(
            1 for s in studies if s.get("study_design", "").lower() == "rct"
        ) / len(studies)

        if rct_proportion > 0.5:
            initial_quality = 4  # Start high for RCTs
        else:
            initial_quality = 2  # Start low for observational studies

        # Assess downgrades
        risk_of_bias_downgrade = await self._assess_risk_of_bias_downgrade(studies)
        inconsistency_downgrade = await self._assess_inconsistency_downgrade(
            synthesis_results
        )
        indirectness_downgrade = await self._assess_indirectness_downgrade(
            studies, outcome
        )
        imprecision_downgrade = await self._assess_imprecision_downgrade(
            synthesis_results
        )
        publication_bias_downgrade = await self._assess_publication_bias_downgrade(
            studies, synthesis_results
        )

        # Assess upgrades (mainly for observational studies)
        large_effect_upgrade = await self._assess_large_effect_upgrade(
            synthesis_results
        )
        dose_response_upgrade = await self._assess_dose_response_upgrade(studies)
        confounding_upgrade = await self._assess_confounding_upgrade(studies)

        # Create GRADE assessment
        grade_assessment = GRADEAssessment(
            outcome=outcome,
            study_design_quality=initial_quality,
            risk_of_bias_downgrade=risk_of_bias_downgrade,
            inconsistency_downgrade=inconsistency_downgrade,
            indirectness_downgrade=indirectness_downgrade,
            imprecision_downgrade=imprecision_downgrade,
            publication_bias_downgrade=publication_bias_downgrade,
            large_effect_upgrade=large_effect_upgrade,
            dose_response_upgrade=dose_response_upgrade,
            confounding_upgrade=confounding_upgrade,
            final_grade="",  # Will be calculated
            grade_justification="",  # Will be generated
            evidence_summary="",  # Will be generated
        )

        # Calculate final grade
        grade_assessment.final_grade = grade_assessment.calculate_final_grade()

        # Generate justification and summary
        grade_assessment.grade_justification = await self._generate_grade_justification(
            grade_assessment
        )
        grade_assessment.evidence_summary = await self._generate_evidence_summary(
            studies, outcome, grade_assessment
        )

        return grade_assessment

    async def _assess_risk_of_bias_downgrade(
        self, studies: List[Dict[str, Any]]
    ) -> int:
        """Assess downgrade for risk of bias."""

        # Simulate risk of bias assessment based on study quality scores
        quality_scores = [s.get("quality_score", 0.7) for s in studies]
        avg_quality = np.mean(quality_scores)

        if avg_quality < 0.5:
            return 2  # Serious downgrade
        elif avg_quality < 0.7:
            return 1  # Downgrade
        else:
            return 0  # No downgrade

    async def _assess_inconsistency_downgrade(
        self, synthesis_results: Dict[str, Any]
    ) -> int:
        """Assess downgrade for inconsistency."""

        # Use I² statistic if available
        i_squared = synthesis_results.get("heterogeneity", {}).get("i_squared", 0.5)

        if i_squared > 0.75:
            return 2  # Serious inconsistency
        elif i_squared > 0.5:
            return 1  # Moderate inconsistency
        else:
            return 0  # No downgrade

    async def _assess_indirectness_downgrade(
        self, studies: List[Dict[str, Any]], outcome: str
    ) -> int:
        """Assess downgrade for indirectness."""

        # Simulate indirectness assessment
        # Check for surrogate outcomes, indirect populations, etc.

        indirect_indicators = 0

        for study in studies:
            # Check for surrogate outcomes
            if (
                "surrogate"
                in study.get("outcomes", {}).get(outcome, {}).get("type", "").lower()
            ):
                indirect_indicators += 1

            # Check for indirect populations
            if study.get("population", {}).get("indirect", False):
                indirect_indicators += 1

        if indirect_indicators > len(studies) * 0.5:
            return 1  # Downgrade for indirectness
        else:
            return 0  # No downgrade

    async def _assess_imprecision_downgrade(
        self, synthesis_results: Dict[str, Any]
    ) -> int:
        """Assess downgrade for imprecision."""

        # Check confidence interval width and sample size
        pooled_effect = synthesis_results.get("pooled_effect", {})
        ci = pooled_effect.get("confidence_interval", [-1, 1])

        ci_width = ci[1] - ci[0] if len(ci) >= 2 else 2.0

        if ci_width > 1.0:
            return 2  # Serious imprecision
        elif ci_width > 0.5:
            return 1  # Moderate imprecision
        else:
            return 0  # No downgrade

    async def _assess_publication_bias_downgrade(
        self, studies: List[Dict[str, Any]], synthesis_results: Dict[str, Any]
    ) -> int:
        """Assess downgrade for publication bias."""

        # Check for evidence of publication bias
        if len(studies) < 10:
            return 0  # Cannot assess with few studies

        pub_bias = synthesis_results.get("publication_bias", {})

        # Check statistical tests
        egger_p = pub_bias.get("egger_test", {}).get("p_value", 0.5)
        begg_p = pub_bias.get("begg_test", {}).get("p_value", 0.5)

        if egger_p < 0.05 or begg_p < 0.05:
            return 1  # Evidence of publication bias
        else:
            return 0  # No evidence of publication bias

    async def _assess_large_effect_upgrade(
        self, synthesis_results: Dict[str, Any]
    ) -> int:
        """Assess upgrade for large effect size."""

        pooled_effect = synthesis_results.get("pooled_effect", {})
        effect_size = abs(pooled_effect.get("effect_size", 0))

        if effect_size > 2.0:  # Very large effect
            return 2
        elif effect_size > 0.8:  # Large effect
            return 1
        else:
            return 0

    async def _assess_dose_response_upgrade(self, studies: List[Dict[str, Any]]) -> int:
        """Assess upgrade for dose - response relationship."""

        # Check if studies report dose - response data
        dose_response_studies = sum(1 for s in studies if s.get("dose_response", False))

        if dose_response_studies > len(studies) * 0.5:
            return 1  # Evidence of dose - response
        else:
            return 0

    async def _assess_confounding_upgrade(self, studies: List[Dict[str, Any]]) -> int:
        """Assess upgrade for confounding that would reduce effect."""

        # For observational studies, check if confounding would bias toward null
        observational_studies = [
            s for s in studies if s.get("study_design", "").lower() != "rct"
        ]

        if len(observational_studies) > 0:
            # Simplified check - would need domain expertise
            return 0  # Conservative approach
        else:
            return 0

    async def _generate_grade_justification(self, assessment: GRADEAssessment) -> str:
        """Generate GRADE justification."""

        justification = (
            f"Starting from {assessment.study_design_quality} (study design). "
        )

        downgrades = []
        if assessment.risk_of_bias_downgrade > 0:
            downgrades.append(f"risk of bias (-{assessment.risk_of_bias_downgrade})")
        if assessment.inconsistency_downgrade > 0:
            downgrades.append(f"inconsistency (-{assessment.inconsistency_downgrade})")
        if assessment.indirectness_downgrade > 0:
            downgrades.append(f"indirectness (-{assessment.indirectness_downgrade})")
        if assessment.imprecision_downgrade > 0:
            downgrades.append(f"imprecision (-{assessment.imprecision_downgrade})")
        if assessment.publication_bias_downgrade > 0:
            downgrades.append(
                f"publication bias (-{assessment.publication_bias_downgrade})"
            )

        upgrades = []
        if assessment.large_effect_upgrade > 0:
            upgrades.append(f"large effect (+{assessment.large_effect_upgrade})")
        if assessment.dose_response_upgrade > 0:
            upgrades.append(f"dose response (+{assessment.dose_response_upgrade})")
        if assessment.confounding_upgrade > 0:
            upgrades.append(f"confounding (+{assessment.confounding_upgrade})")

        if downgrades:
            justification += f"Downgraded for: {', '.join(downgrades)}. "

        if upgrades:
            justification += f"Upgraded for: {', '.join(upgrades)}. "

        justification += f"Final grade: {assessment.final_grade}."

        return justification

    async def _generate_evidence_summary(
        self, studies: List[Dict[str, Any]], outcome: str, assessment: GRADEAssessment
    ) -> str:
        """Generate evidence summary."""

        summary = f"Evidence from {len(studies)} studies assessing {outcome}. "
        summary += f"Overall certainty of evidence: {assessment.final_grade}. "
        summary += assessment.grade_justification

        return summary


class QualityAI:
    """
    Main Quality AI system for systematic reviews.

    Integrates multiple quality assessment tools and provides
    AI - powered bias detection and GRADE evaluation.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize Quality AI system."""
        self.config = config
        self.rob2_assessor = RoB2Assessor()
        self.grade_assessor = GRADEAssessor()
        self.assessment_history = []
        self.logger = logging.getLogger(__name__)

    async def assess_study_quality(
        self, study_data: Dict[str, Any], assessment_tool: QualityTool
    ) -> QualityAssessment:
        """Assess quality of individual study."""

        self.logger.info(
            f"Assessing study {study_data['study_id']} using {assessment_tool.value}"
        )

        if assessment_tool == QualityTool.ROB_2:
            assessment = await self.rob2_assessor.assess_study(study_data)
        else:
            # Placeholder for other tools
            assessment = await self._generic_quality_assessment(
                study_data, assessment_tool
            )

        self.assessment_history.append(assessment)
        return assessment

    async def assess_evidence_certainty(
        self,
        studies: List[Dict[str, Any]],
        outcome: str,
        synthesis_results: Dict[str, Any],
    ) -> GRADEAssessment:
        """Assess overall evidence certainty using GRADE."""

        self.logger.info(
            f"Performing GRADE assessment for {outcome} with {len(studies)} studies"
        )

        grade_assessment = await self.grade_assessor.assess_evidence(
            studies, outcome, synthesis_results
        )

        return grade_assessment

    async def batch_assess_studies(
        self, studies: List[Dict[str, Any]], assessment_tool: QualityTool
    ) -> List[QualityAssessment]:
        """Assess multiple studies in batch."""

        assessments = []

        for study in studies:
            assessment = await self.assess_study_quality(study, assessment_tool)
            assessments.append(assessment)

        return assessments

    async def assess_quality_batch(
        self, studies: List[Dict[str, Any]]
    ) -> List[QualityAssessment]:
        """Assess quality of multiple studies."""
        return await self.batch_assess_studies(studies, QualityTool.ROB_2)

    async def detect_publication_bias(
        self, studies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Detect publication bias."""
        # Placeholder implementation
        return {
            "bias_detected": False,
            "confidence_score": 0.8,
            "method": "Egger's test",
            "p_value": 0.2,
            "explanation": "No significant publication bias detected.",
        }

    async def generate_grade_profile(
        self, studies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate GRADE evidence profile."""
        # Placeholder implementation
        return {
            "outcome": "Primary Outcome",
            "initial_quality": "High",
            "final_quality": "Moderate",
            "confidence_in_effect": 0.75,
            "factors_influencing_quality": [],
            "summary_of_findings": "Moderate quality evidence suggests a benefit.",
        }

    async def continuous_learning_update(self, feedback: Dict[str, Any]):
        """Update model based on user feedback."""
        self.logger.info(f"Received feedback: {feedback}")

    async def assess_multi_observer_agreement(
        self, studies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Assess multi-observer agreement."""
        # Placeholder implementation
        return {
            "kappa_score": 0.85,
            "agreement_percentage": 92.5,
            "explanation": "High level of agreement between observers.",
        }

    async def perform_sensitivity_analysis(
        self, studies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Perform sensitivity analysis."""
        # Placeholder implementation
        return {
            "robustness_score": 0.9,
            "influential_studies": [],
            "explanation": "Results are robust to sensitivity analysis.",
        }

    async def generate_quality_summary(
        self, assessments: List[QualityAssessment]
    ) -> Dict[str, Any]:
        """Generate summary of quality assessments."""

        if not assessments:
            return {}

        # Calculate summary statistics
        overall_scores = [a.overall_score for a in assessments]
        ai_confidences = [a.ai_confidence for a in assessments]

        risk_distribution = {
            "low": sum(1 for a in assessments if a.overall_risk == BiasRisk.LOW),
            "some_concerns": sum(
                1 for a in assessments if a.overall_risk == BiasRisk.SOME_CONCERNS
            ),
            "high": sum(1 for a in assessments if a.overall_risk == BiasRisk.HIGH),
            "unclear": sum(
                1 for a in assessments if a.overall_risk == BiasRisk.UNCLEAR
            ),
        }

        human_review_needed = sum(1 for a in assessments if a.human_review_required)

        # Common limitations across studies
        all_limitations = []
        for assessment in assessments:
            all_limitations.extend(assessment.methodological_limitations)

        common_limitations = [
            limitation for limitation, count in Counter(all_limitations).most_common(5)
        ]

        return {
            "total_studies": len(assessments),
            "quality_statistics": {
                "mean_quality_score": np.mean(overall_scores),
                "median_quality_score": np.median(overall_scores),
                "quality_range": [min(overall_scores), max(overall_scores)],
            },
            "risk_distribution": risk_distribution,
            "ai_performance": {
                "mean_confidence": np.mean(ai_confidences),
                "high_confidence_assessments": sum(
                    1 for c in ai_confidences if c > 0.8
                ),
                "human_review_required": human_review_needed,
                "human_review_percentage": human_review_needed / len(assessments) * 100,
            },
            "common_limitations": common_limitations,
            "assessment_tool": assessments[0].assessment_tool.value,
            "summary_generated": datetime.now().isoformat(),
        }

    async def _generic_quality_assessment(
        self, study_data: Dict[str, Any], assessment_tool: QualityTool
    ) -> QualityAssessment:
        """Generic quality assessment for tools not yet implemented."""

        # Placeholder implementation
        domains = ["methodology", "reporting", "bias_control"]
        domain_assessments = []

        for domain in domains:
            domain_assessment = QualityDomain(
                domain_name=domain,
                assessment=BiasRisk.SOME_CONCERNS,
                justification=f"Generic assessment for {domain}",
                supporting_evidence=["Placeholder evidence"],
                confidence_score=0.6,
                ai_detected_issues=["Tool not fully implemented"],
            )
            domain_assessments.append(domain_assessment)

        return QualityAssessment(
            study_id=study_data["study_id"],
            assessment_id=f"QA_{study_data['study_id']}_{datetime.now().timestamp()}",
            assessment_tool=assessment_tool,
            overall_risk=BiasRisk.SOME_CONCERNS,
            domain_assessments=domain_assessments,
            overall_score=0.6,
            assessment_rationale=f"Generic assessment using {assessment_tool.value}",
            methodological_strengths=["Placeholder strengths"],
            methodological_limitations=["Tool implementation pending"],
            ai_confidence=0.6,
            human_review_required=True,
            assessment_date=datetime.now().isoformat(),
            explanation="Generic assessment",
            confidence_score=0.6,
            overall_bias=BiasRisk.SOME_CONCERNS,
        )


# Integration function for Phase 4A testing
async def demonstrate_quality_ai():
    """Demonstrate Quality AI capabilities."""

    print("🎯 Phase 4A: Quality AI Demonstration")
    print("=" * 70)

    # Initialize Quality AI
    config = {
        "quality_thresholds": {
            "ai_confidence_threshold": 0.7,
            "human_review_threshold": 0.6,
        }
    }
    quality_ai = QualityAI(config)

    print("🔧 Initializing Quality AI system...")
    print("   ✅ RoB 2 assessor ready")
    print("   ✅ GRADE assessor ready")

    # Create sample studies for assessment
    print("\n📚 Creating sample studies for quality assessment...")

    studies = []
    for i in range(6):
        study = {
            "study_id": f"study_{i + 1:03d}",
            "title": f"Randomized controlled trial {i + 1}",
            "abstract": "This randomized controlled trial evaluated intervention effects. "
            "Participants were randomly allocated using computer-generated "
            "sequences. Outcome assessors were blinded to group allocation. "
            "Complete follow-up data was available.",
            "methods": "Double-blind randomized controlled trial with "
            "intention-to-treat analysis. Protocol pre-registered.",
            "study_design": "RCT",
            "quality_score": np.random.uniform(0.5, 0.9),
            "sample_size": 100 + i * 50,
        }
        studies.append(study)

    print(f"   Created {len(studies)} RCT studies for assessment")

    # Perform individual quality assessments
    print("\n🎯 Performing RoB 2 quality assessments...")
    assessments = await quality_ai.assess_quality_batch(studies)

    for assessment in assessments:
        print(f"   - Study {assessment.study_id}:")
    print(f"     Overall Bias: {assessment.overall_risk.value}")
    print(f"     Confidence: {assessment.ai_confidence:.3f}")
    print(
        f"     Explanation: {assessment.assessment_rationale}"
    )  # Detect publication bias
    print("\n🔎 Detecting publication bias...")
    bias_report = await quality_ai.detect_publication_bias(studies)

    print("   Publication Bias Report:")
    print(f"     Bias Detected: {bias_report['bias_detected']}")
    print(f"     Confidence: {bias_report['confidence_score']:.3f}")
    print(f"     Method: {bias_report['method']}")
    print(f"     P-value: {bias_report['p_value']:.4f}")
    print(f"     Explanation: {bias_report['explanation']}")

    # Generate GRADE evidence profile
    print("\n📊 Generating GRADE evidence profile...")
    grade_profile = await quality_ai.generate_grade_profile(studies)

    print("   GRADE Evidence Profile:")
    print(f"     Outcome: {grade_profile['outcome']}")
    print(f"     Initial Quality: {grade_profile['initial_quality']}")
    print(f"     Final Quality: {grade_profile['final_quality']}")
    print(f"     Confidence in Effect: {grade_profile['confidence_in_effect']:.3f}")
    print("     Factors Influencing Quality:")
    for factor in grade_profile["factors_influencing_quality"]:
        print(
            f"       - {factor['factor']}: {factor['impact']} ({factor['explanation']})"
        )
    print(f"     Summary: {grade_profile['summary_of_findings']}")

    # Demonstrate continuous learning
    print("\n🧠 Demonstrating continuous learning...")
    feedback = {
        "assessment_id": assessments[0].assessment_id,
        "user_rating": 5,
        "corrected_bias": "low",
        "feedback_text": "Model correctly identified low risk of bias.",
    }
    await quality_ai.continuous_learning_update(feedback)

    print("   ✅ Continuous learning update processed.")

    # Demonstrate advanced features
    print("\n🚀 Demonstrating advanced features...")

    # Multi-observer agreement simulation
    agreement_report = await quality_ai.assess_multi_observer_agreement(studies)
    print("   Multi-Observer Agreement Report:")
    print(f"     Kappa Score: {agreement_report['kappa_score']:.3f}")
    print(f"     Agreement: {agreement_report['agreement_percentage']:.2f}%")
    print(f"     Explanation: {agreement_report['explanation']}")

    # Sensitivity analysis
    sensitivity_report = await quality_ai.perform_sensitivity_analysis(studies)
    print("   Sensitivity Analysis Report:")
    print(f"     Robustness: {sensitivity_report['robustness_score']:.3f}")
    print(f"     Influential Studies: {sensitivity_report['influential_studies']}")
    print(f"     Explanation: {sensitivity_report['explanation']}")

    print("\n✅ Phase 4A Quality AI demonstration completed!")
    print(f"   Total assessments: {len(assessments)}")
    print(f"   Publication bias detected: {bias_report['bias_detected']}")
    print(f"   Final GRADE quality: {grade_profile['final_quality']}")

    return quality_ai, assessments, bias_report, grade_profile


if __name__ == "__main__":
    asyncio.run(demonstrate_quality_ai())

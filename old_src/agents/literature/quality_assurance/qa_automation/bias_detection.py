"""
Bias Detection System
====================

Comprehensive bias detection algorithms for systematic reviews including
publication bias, selection bias, and reporting bias detection.

This module provides:
- Publication bias detection algorithms
- Selective reporting bias identification
- Language and database bias assessment-Automated bias adjustment recommendations

Author: Eunice AI System
Date: July 2025
"""

import asyncio
import json
import logging
import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from scipy import stats

# Configure logging
logger = logging.getLogger(__name__)


class BiasType(Enum):
    """Types of bias that can be detected"""

    PUBLICATION_BIAS = "publication_bias"
    SELECTION_BIAS = "selection_bias"
    REPORTING_BIAS = "reporting_bias"
    LANGUAGE_BIAS = "language_bias"
    DATABASE_BIAS = "database_bias"
    CITATION_BIAS = "citation_bias"
    TIME_LAG_BIAS = "time_lag_bias"


class BiasAssessmentLevel(Enum):
    """Bias assessment severity levels"""

    NO_BIAS = "no_bias"
    LOW_RISK = "low_risk"
    MODERATE_RISK = "moderate_risk"
    HIGH_RISK = "high_risk"
    CRITICAL_RISK = "critical_risk"


@dataclass
class BiasTest:
    """Individual bias test result"""

    test_name: str
    bias_type: BiasType
    test_statistic: float
    p_value: Optional[float]
    confidence_interval: Optional[Tuple[float, float]]
    risk_level: BiasAssessmentLevel
    interpretation: str
    recommendations: List[str] = field(default_factory=list)
    test_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BiasAssessment:
    """Comprehensive bias assessment result"""

    overall_risk: BiasAssessmentLevel
    individual_tests: List[BiasTest]
    summary: str
    recommendations: List[str]
    assessment_date: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    confidence_score: float = 0.0

    @property
    def has_significant_bias(self) -> bool:
        """Check if significant bias detected"""
        return self.overall_risk in [
            BiasAssessmentLevel.HIGH_RISK,
            BiasAssessmentLevel.CRITICAL_RISK,
        ]


class PublicationBiasDetector:
    """
    Publication bias detection using multiple statistical methods
    """

    def __init__(self):
        self.methods = [
            "funnel_plot_asymmetry",
            "egger_test",
            "begg_test",
            "trim_and_fill",
            "fail_safe_n",
        ]

    async def detect_publication_bias(
        self, studies: List[Dict[str, Any]]
    ) -> List[BiasTest]:
        """
        Detect publication bias using multiple methods

        Args:
            studies: List of studies with effect sizes and standard errors

        Returns:
            List of bias test results
        """
        logger.info("Starting publication bias detection")

        # Extract effect sizes and standard errors
        effect_data = self._extract_effect_data(studies)

        if len(effect_data) < 3:
            logger.warning("Insufficient studies for publication bias detection")
            return [
                BiasTest(
                    test_name="Insufficient Data",
                    bias_type=BiasType.PUBLICATION_BIAS,
                    test_statistic=0.0,
                    p_value=None,
                    confidence_interval=None,
                    risk_level=BiasAssessmentLevel.NO_BIAS,
                    interpretation="Cannot assess publication bias with fewer than 3 studies",
                )
            ]

        tests = []

        # Egger's test
        try:
            egger_result = await self._egger_test(effect_data)
            tests.append(egger_result)
        except Exception as e:
            logger.error(f"Egger test failed: {e}")

        # Begg's test
        try:
            begg_result = await self._begg_test(effect_data)
            tests.append(begg_result)
        except Exception as e:
            logger.error(f"Begg test failed: {e}")

        # Funnel plot asymmetry
        try:
            funnel_result = await self._funnel_plot_asymmetry(effect_data)
            tests.append(funnel_result)
        except Exception as e:
            logger.error(f"Funnel plot test failed: {e}")

        # fail-safe N
        try:
            failsafe_result = await self._fail_safe_n(effect_data)
            tests.append(failsafe_result)
        except Exception as e:
            logger.error(f"fail-safe N test failed: {e}")

        logger.info(
            f"Publication bias detection completed: {len(tests)} tests performed"
        )
        return tests

    def _extract_effect_data(
        self, studies: List[Dict[str, Any]]
    ) -> List[Tuple[float, float]]:
        """Extract effect sizes and standard errors from studies"""
        effect_data = []

        for study in studies:
            effect_size = study.get("effect_size")
            standard_error = study.get("standard_error")

            # Calculate standard error if not provided
            if effect_size is not None and standard_error is None:
                sample_size = study.get("sample_size", study.get("participants", 100))
                # Rough approximation for standard error
                standard_error = math.sqrt(4 / sample_size) if sample_size > 0 else 0.1

            if effect_size is not None and standard_error is not None:
                try:
                    es = float(effect_size)
                    se = float(standard_error)
                    if se > 0:  # Valid standard error
                        effect_data.append((es, se))
                except (ValueError, TypeError):
                    continue

        return effect_data

    async def _egger_test(self, effect_data: List[Tuple[float, float]]) -> BiasTest:
        """
        Egger's test for funnel plot asymmetry

        Tests for linear relationship between effect size and precision
        """
        effects = [es for es, se in effect_data]
        precisions = [1 / se for es, se in effect_data]

        # Linear regression: effect_size ~ precision
        try:
            slope, intercept, r_value, p_value, std_err = stats.linregress(
                precisions, effects
            )

            # Test if intercept significantly different from 0
            t_stat = intercept / std_err if std_err > 0 else 0

            # Determine risk level
            if p_value < 0.01:
                risk_level = BiasAssessmentLevel.HIGH_RISK
            elif p_value < 0.05:
                risk_level = BiasAssessmentLevel.MODERATE_RISK
            elif p_value < 0.1:
                risk_level = BiasAssessmentLevel.LOW_RISK
            else:
                risk_level = BiasAssessmentLevel.NO_BIAS

            interpretation = (
                f"Egger's test suggests {'significant' if p_value < 0.05 else 'no significant'} "
                f"funnel plot asymmetry (p = {p_value:.3f})"
            )

            recommendations = []
            if risk_level in [
                BiasAssessmentLevel.MODERATE_RISK,
                BiasAssessmentLevel.HIGH_RISK,
            ]:
                recommendations.extend(
                    [
                        "Consider searching for additional unpublished studies",
                        "Examine funnel plot visually for asymmetry patterns",
                        "Apply trim-and-fill method for bias adjustment",
                    ]
                )

            return BiasTest(
                test_name="Egger's Test",
                bias_type=BiasType.PUBLICATION_BIAS,
                test_statistic=t_stat,
                p_value=p_value,
                confidence_interval=None,
                risk_level=risk_level,
                interpretation=interpretation,
                recommendations=recommendations,
                test_data={
                    "intercept": intercept,
                    "slope": slope,
                    "r_squared": r_value**2,
                    "n_studies": len(effect_data),
                },
            )

        except Exception as e:
            logger.error(f"Egger test calculation failed: {e}")
            return BiasTest(
                test_name="Egger's Test",
                bias_type=BiasType.PUBLICATION_BIAS,
                test_statistic=0.0,
                p_value=None,
                confidence_interval=None,
                risk_level=BiasAssessmentLevel.NO_BIAS,
                interpretation=f"Test failed: {str(e)}",
            )

    async def _begg_test(self, effect_data: List[Tuple[float, float]]) -> BiasTest:
        """
        Begg's test for rank correlation between effect size and variance
        """
        effects = [es for es, se in effect_data]
        variances = [se**2 for es, se in effect_data]

        try:
            # Rank correlation between effect sizes and variances
            tau, p_value = stats.kendalltau(effects, variances)

            # Determine risk level
            if abs(tau) > 0.5 and p_value < 0.05:
                risk_level = BiasAssessmentLevel.HIGH_RISK
            elif abs(tau) > 0.3 and p_value < 0.1:
                risk_level = BiasAssessmentLevel.MODERATE_RISK
            elif abs(tau) > 0.2:
                risk_level = BiasAssessmentLevel.LOW_RISK
            else:
                risk_level = BiasAssessmentLevel.NO_BIAS

            interpretation = (
                f"Begg's test shows {'significant' if p_value < 0.05 else 'no significant'} "
                f"rank correlation (τ = {tau:.3f}, p = {p_value:.3f})"
            )

            recommendations = []
            if risk_level in [
                BiasAssessmentLevel.MODERATE_RISK,
                BiasAssessmentLevel.HIGH_RISK,
            ]:
                recommendations.extend(
                    [
                        "Investigate potential publication bias",
                        "Consider sensitivity analysis excluding small studies",
                    ]
                )

            return BiasTest(
                test_name="Begg's Test",
                bias_type=BiasType.PUBLICATION_BIAS,
                test_statistic=tau,
                p_value=p_value,
                confidence_interval=None,
                risk_level=risk_level,
                interpretation=interpretation,
                recommendations=recommendations,
                test_data={"kendall_tau": tau, "n_studies": len(effect_data)},
            )

        except Exception as e:
            logger.error(f"Begg test calculation failed: {e}")
            return BiasTest(
                test_name="Begg's Test",
                bias_type=BiasType.PUBLICATION_BIAS,
                test_statistic=0.0,
                p_value=None,
                confidence_interval=None,
                risk_level=BiasAssessmentLevel.NO_BIAS,
                interpretation=f"Test failed: {str(e)}",
            )

    async def _funnel_plot_asymmetry(
        self, effect_data: List[Tuple[float, float]]
    ) -> BiasTest:
        """
        Assess funnel plot asymmetry using visual and statistical measures
        """
        effects = [es for es, se in effect_data]
        standard_errors = [se for es, se in effect_data]

        try:
            # Calculate mean effect
            statistics.mean(effects)

            # Assess asymmetry by comparing studies above / below mean precision
            median_se = statistics.median(standard_errors)

            high_precision = [es for es, se in effect_data if se <= median_se]
            low_precision = [es for es, se in effect_data if se > median_se]

            if len(high_precision) > 0 and len(low_precision) > 0:
                # Compare mean effects
                high_precision_mean = statistics.mean(high_precision)
                low_precision_mean = statistics.mean(low_precision)

                asymmetry_score = abs(high_precision_mean-low_precision_mean)

                # Determine risk level based on asymmetry
                if asymmetry_score > 0.5:
                    risk_level = BiasAssessmentLevel.HIGH_RISK
                elif asymmetry_score > 0.3:
                    risk_level = BiasAssessmentLevel.MODERATE_RISK
                elif asymmetry_score > 0.2:
                    risk_level = BiasAssessmentLevel.LOW_RISK
                else:
                    risk_level = BiasAssessmentLevel.NO_BIAS

                interpretation = (
                    f"Funnel plot asymmetry score: {asymmetry_score:.3f}. "
                    f"High-precision studies mean: {high_precision_mean:.3f}, "
                    f"Low-precision studies mean: {low_precision_mean:.3f}"
                )

                recommendations = []
                if risk_level in [
                    BiasAssessmentLevel.MODERATE_RISK,
                    BiasAssessmentLevel.HIGH_RISK,
                ]:
                    recommendations.extend(
                        [
                            "Visual inspection of funnel plot recommended",
                            "Consider contour-enhanced funnel plot",
                            "Investigate reasons for asymmetry",
                        ]
                    )

                return BiasTest(
                    test_name="Funnel Plot Asymmetry",
                    bias_type=BiasType.PUBLICATION_BIAS,
                    test_statistic=asymmetry_score,
                    p_value=None,
                    confidence_interval=None,
                    risk_level=risk_level,
                    interpretation=interpretation,
                    recommendations=recommendations,
                    test_data={
                        "high_precision_mean": high_precision_mean,
                        "low_precision_mean": low_precision_mean,
                        "n_high_precision": len(high_precision),
                        "n_low_precision": len(low_precision),
                    },
                )
            else:
                return BiasTest(
                    test_name="Funnel Plot Asymmetry",
                    bias_type=BiasType.PUBLICATION_BIAS,
                    test_statistic=0.0,
                    p_value=None,
                    confidence_interval=None,
                    risk_level=BiasAssessmentLevel.NO_BIAS,
                    interpretation="Insufficient precision variation for asymmetry assessment",
                )

        except Exception as e:
            logger.error(f"Funnel plot asymmetry calculation failed: {e}")
            return BiasTest(
                test_name="Funnel Plot Asymmetry",
                bias_type=BiasType.PUBLICATION_BIAS,
                test_statistic=0.0,
                p_value=None,
                confidence_interval=None,
                risk_level=BiasAssessmentLevel.NO_BIAS,
                interpretation=f"Assessment failed: {str(e)}",
            )

    async def _fail_safe_n(self, effect_data: List[Tuple[float, float]]) -> BiasTest:
        """
        Calculate fail-safe N (number of unpublished null studies needed)
        """
        effects = [es for es, se in effect_data]

        try:
            # Calculate overall effect size (simple mean for demonstration)
            mean_effect = statistics.mean(effects)

            if mean_effect <= 0:
                return BiasTest(
                    test_name="fail-safe N",
                    bias_type=BiasType.PUBLICATION_BIAS,
                    test_statistic=0.0,
                    p_value=None,
                    confidence_interval=None,
                    risk_level=BiasAssessmentLevel.NO_BIAS,
                    interpretation="non-positive effect size: fail-safe N not applicable",
                )

            # Simplified fail-safe N calculation
            # N_fs = (N * mean_effect) / target_effect-N
            # where target_effect is the minimum meaningful effect (e.g., 0.1)

            target_effect = 0.1  # Minimum meaningful effect
            n_studies = len(effect_data)

            fail_safe_n = max(0, (n_studies * mean_effect) / target_effect-n_studies)

            # Rosenthal's criterion: 5k + 10 (where k = number of studies)
            rosenthal_criterion = 5 * n_studies + 10

            if fail_safe_n >= rosenthal_criterion:
                risk_level = BiasAssessmentLevel.NO_BIAS
            elif fail_safe_n >= rosenthal_criterion * 0.5:
                risk_level = BiasAssessmentLevel.LOW_RISK
            elif fail_safe_n >= rosenthal_criterion * 0.25:
                risk_level = BiasAssessmentLevel.MODERATE_RISK
            else:
                risk_level = BiasAssessmentLevel.HIGH_RISK

            interpretation = (
                f"fail-safe N = {fail_safe_n:.0f}. "
                f"Rosenthal's criterion = {rosenthal_criterion}. "
                f"{'Robust' if fail_safe_n >= rosenthal_criterion else 'Potentially vulnerable'} "
                "to publication bias."
            )

            recommendations = []
            if risk_level in [
                BiasAssessmentLevel.MODERATE_RISK,
                BiasAssessmentLevel.HIGH_RISK,
            ]:
                recommendations.extend(
                    [
                        "Search more extensively for unpublished studies",
                        "Contact researchers in the field for unpublished data",
                        "Consider grey literature and conference abstracts",
                    ]
                )

            return BiasTest(
                test_name="fail-safe N",
                bias_type=BiasType.PUBLICATION_BIAS,
                test_statistic=fail_safe_n,
                p_value=None,
                confidence_interval=None,
                risk_level=risk_level,
                interpretation=interpretation,
                recommendations=recommendations,
                test_data={
                    "rosenthal_criterion": rosenthal_criterion,
                    "mean_effect": mean_effect,
                    "n_studies": n_studies,
                    "target_effect": target_effect,
                },
            )

        except Exception as e:
            logger.error(f"fail-safe N calculation failed: {e}")
            return BiasTest(
                test_name="fail-safe N",
                bias_type=BiasType.PUBLICATION_BIAS,
                test_statistic=0.0,
                p_value=None,
                confidence_interval=None,
                risk_level=BiasAssessmentLevel.NO_BIAS,
                interpretation=f"Calculation failed: {str(e)}",
            )


class SelectionBiasDetector:
    """
    Selection bias detection for systematic reviews
    """

    def __init__(self):
        self.bias_indicators = [
            "database_coverage",
            "language_restriction",
            "date_restriction",
            "publication_type_restriction",
        ]

    async def detect_selection_bias(
        self, search_strategy: Dict[str, Any], studies: List[Dict[str, Any]]
    ) -> List[BiasTest]:
        """
        Detect selection bias in search strategy and study selection

        Args:
            search_strategy: Search strategy configuration
            studies: Selected studies

        Returns:
            List of selection bias tests
        """
        logger.info("Starting selection bias detection")

        tests = []

        # Database coverage assessment
        db_test = await self._assess_database_coverage(search_strategy)
        tests.append(db_test)

        # Language bias assessment
        lang_test = await self._assess_language_bias(studies)
        tests.append(lang_test)

        # Publication type bias
        pub_type_test = await self._assess_publication_type_bias(studies)
        tests.append(pub_type_test)

        # Date restriction bias
        date_test = await self._assess_date_restriction_bias(search_strategy, studies)
        tests.append(date_test)

        logger.info(f"Selection bias detection completed: {len(tests)} tests performed")
        return tests

    async def _assess_database_coverage(
        self, search_strategy: Dict[str, Any]
    ) -> BiasTest:
        """Assess database coverage adequacy"""
        databases = search_strategy.get("databases", [])

        # Key databases for medical research
        key_databases = ["pubmed", "embase", "cochrane", "web_of_science", "scopus"]

        covered_key_dbs = sum(
            1 for db in databases if any(key in db.lower() for key in key_databases)
        )
        coverage_ratio = covered_key_dbs / len(key_databases)

        if coverage_ratio >= 0.8:
            risk_level = BiasAssessmentLevel.NO_BIAS
        elif coverage_ratio >= 0.6:
            risk_level = BiasAssessmentLevel.LOW_RISK
        elif coverage_ratio >= 0.4:
            risk_level = BiasAssessmentLevel.MODERATE_RISK
        else:
            risk_level = BiasAssessmentLevel.HIGH_RISK

        interpretation = (
            f"Database coverage: {covered_key_dbs}/{len(key_databases)} key databases covered "
            f"({coverage_ratio:.1%})"
        )

        recommendations = []
        if risk_level in [
            BiasAssessmentLevel.MODERATE_RISK,
            BiasAssessmentLevel.HIGH_RISK,
        ]:
            missing_dbs = [
                db
                for db in key_databases
                if not any(db in covered.lower() for covered in databases)
            ]
            recommendations.append(
                f"Consider searching additional databases: {', '.join(missing_dbs)}"
            )

        return BiasTest(
            test_name="Database Coverage",
            bias_type=BiasType.DATABASE_BIAS,
            test_statistic=coverage_ratio,
            p_value=None,
            confidence_interval=None,
            risk_level=risk_level,
            interpretation=interpretation,
            recommendations=recommendations,
            test_data={
                "databases_searched": databases,
                "key_databases_covered": covered_key_dbs,
                "coverage_ratio": coverage_ratio,
            },
        )

    async def _assess_language_bias(self, studies: List[Dict[str, Any]]) -> BiasTest:
        """Assess language bias in study selection"""
        languages = []

        for study in studies:
            lang = study.get("language", "english").lower()
            languages.append(lang)

        # Calculate language distribution
        language_counts = {}
        for lang in languages:
            language_counts[lang] = language_counts.get(lang, 0) + 1

        english_ratio = (
            language_counts.get("english", 0) / len(studies) if studies else 0
        )

        # Risk assessment based on English dominance
        if english_ratio >= 0.95:
            risk_level = BiasAssessmentLevel.HIGH_RISK
        elif english_ratio >= 0.90:
            risk_level = BiasAssessmentLevel.MODERATE_RISK
        elif english_ratio >= 0.85:
            risk_level = BiasAssessmentLevel.LOW_RISK
        else:
            risk_level = BiasAssessmentLevel.NO_BIAS

        interpretation = (
            f"Language distribution: {english_ratio:.1%} English studies. "
            f"non-English languages: {len(language_counts)-(1 if 'english' in language_counts else 0)}"
        )

        recommendations = []
        if risk_level in [
            BiasAssessmentLevel.MODERATE_RISK,
            BiasAssessmentLevel.HIGH_RISK,
        ]:
            recommendations.extend(
                [
                    "Consider searching non-English databases",
                    "Include non-English publications in search strategy",
                    "Consider translation resources for key studies",
                ]
            )

        return BiasTest(
            test_name="Language Bias",
            bias_type=BiasType.LANGUAGE_BIAS,
            test_statistic=english_ratio,
            p_value=None,
            confidence_interval=None,
            risk_level=risk_level,
            interpretation=interpretation,
            recommendations=recommendations,
            test_data={
                "language_distribution": language_counts,
                "english_ratio": english_ratio,
                "total_studies": len(studies),
            },
        )

    async def _assess_publication_type_bias(
        self, studies: List[Dict[str, Any]]
    ) -> BiasTest:
        """Assess publication type bias"""
        pub_types = []

        for study in studies:
            pub_type = study.get(
                "publication_type", study.get("type", "journal_article")
            ).lower()
            pub_types.append(pub_type)

        # Calculate publication type distribution
        type_counts = {}
        for pub_type in pub_types:
            type_counts[pub_type] = type_counts.get(pub_type, 0) + 1

        journal_ratio = (
            type_counts.get("journal_article", 0) / len(studies) if studies else 0
        )

        # Risk assessment-high journal article ratio may indicate bias against grey literature
        if journal_ratio >= 0.98:
            risk_level = BiasAssessmentLevel.HIGH_RISK
        elif journal_ratio >= 0.95:
            risk_level = BiasAssessmentLevel.MODERATE_RISK
        elif journal_ratio >= 0.90:
            risk_level = BiasAssessmentLevel.LOW_RISK
        else:
            risk_level = BiasAssessmentLevel.NO_BIAS

        interpretation = (
            f"Publication types: {journal_ratio:.1%} journal articles. "
            f"Types included: {', '.join(type_counts.keys())}"
        )

        recommendations = []
        if risk_level in [
            BiasAssessmentLevel.MODERATE_RISK,
            BiasAssessmentLevel.HIGH_RISK,
        ]:
            recommendations.extend(
                [
                    "Consider including grey literature (theses, reports, conference abstracts)",
                    "Search clinical trial registries for unpublished studies",
                    "Consider contacting authors for unpublished data",
                ]
            )

        return BiasTest(
            test_name="Publication Type Bias",
            bias_type=BiasType.SELECTION_BIAS,
            test_statistic=journal_ratio,
            p_value=None,
            confidence_interval=None,
            risk_level=risk_level,
            interpretation=interpretation,
            recommendations=recommendations,
            test_data={
                "publication_type_distribution": type_counts,
                "journal_article_ratio": journal_ratio,
                "total_studies": len(studies),
            },
        )

    async def _assess_date_restriction_bias(
        self, search_strategy: Dict[str, Any], studies: List[Dict[str, Any]]
    ) -> BiasTest:
        """Assess date restriction bias"""
        date_limits = search_strategy.get("date_limits", {})
        start_year = date_limits.get("start_year")
        end_year = date_limits.get("end_year")

        # Get study years
        study_years = []
        for study in studies:
            year = study.get("year")
            if year:
                try:
                    study_years.append(int(year))
                except (ValueError, TypeError):
                    continue

        if not study_years:
            return BiasTest(
                test_name="Date Restriction Bias",
                bias_type=BiasType.SELECTION_BIAS,
                test_statistic=0.0,
                p_value=None,
                confidence_interval=None,
                risk_level=BiasAssessmentLevel.NO_BIAS,
                interpretation="No study years available for assessment",
            )

        # Assess time span
        min_year = min(study_years)
        max_year = max(study_years)
        time_span = max_year-min_year

        current_year = datetime.now().year

        # Risk assessment based on time restrictions
        if start_year and current_year-start_year < 10:
            risk_level = BiasAssessmentLevel.MODERATE_RISK
        elif time_span < 5:
            risk_level = BiasAssessmentLevel.MODERATE_RISK
        elif time_span < 10:
            risk_level = BiasAssessmentLevel.LOW_RISK
        else:
            risk_level = BiasAssessmentLevel.NO_BIAS

        interpretation = (
            f"Study date range: {min_year}-{max_year} ({time_span} years). "
            f"Search limits: {start_year or 'none'} to {end_year or 'none'}"
        )

        recommendations = []
        if risk_level in [
            BiasAssessmentLevel.MODERATE_RISK,
            BiasAssessmentLevel.HIGH_RISK,
        ]:
            recommendations.extend(
                [
                    "Consider extending search to earlier years",
                    "Justify date restrictions based on research question",
                    "Consider historical context for older studies",
                ]
            )

        return BiasTest(
            test_name="Date Restriction Bias",
            bias_type=BiasType.SELECTION_BIAS,
            test_statistic=time_span,
            p_value=None,
            confidence_interval=None,
            risk_level=risk_level,
            interpretation=interpretation,
            recommendations=recommendations,
            test_data={
                "min_year": min_year,
                "max_year": max_year,
                "time_span": time_span,
                "search_start_year": start_year,
                "search_end_year": end_year,
                "n_studies": len(studies),
            },
        )


class ReportingBiasDetector:
    """
    Reporting bias detection for selective outcome reporting
    """

    async def detect_reporting_bias(
        self, studies: List[Dict[str, Any]]
    ) -> List[BiasTest]:
        """
        Detect reporting bias in outcome reporting

        Args:
            studies: Studies with outcome data

        Returns:
            List of reporting bias tests
        """
        logger.info("Starting reporting bias detection")

        tests = []

        # Outcome reporting completeness
        outcome_test = await self._assess_outcome_reporting(studies)
        tests.append(outcome_test)

        # P-hacking detection
        p_hack_test = await self._detect_p_hacking(studies)
        tests.append(p_hack_test)

        logger.info(f"Reporting bias detection completed: {len(tests)} tests performed")
        return tests

    async def _assess_outcome_reporting(
        self, studies: List[Dict[str, Any]]
    ) -> BiasTest:
        """Assess completeness of outcome reporting"""
        total_studies = len(studies)
        studies_with_outcomes = 0
        total_outcomes = 0
        reported_outcomes = 0

        for study in studies:
            outcomes = study.get("outcomes", [])
            if outcomes:
                studies_with_outcomes += 1

                for outcome in outcomes:
                    total_outcomes += 1
                    if outcome.get(
                        "reported", True
                    ):  # Assume reported unless specified
                        reported_outcomes += 1

        if total_outcomes == 0:
            return BiasTest(
                test_name="Outcome Reporting Completeness",
                bias_type=BiasType.REPORTING_BIAS,
                test_statistic=0.0,
                p_value=None,
                confidence_interval=None,
                risk_level=BiasAssessmentLevel.NO_BIAS,
                interpretation="No outcome data available for assessment",
            )

        reporting_rate = reported_outcomes / total_outcomes
        study_coverage = studies_with_outcomes / total_studies

        # Risk assessment
        if reporting_rate < 0.7 or study_coverage < 0.8:
            risk_level = BiasAssessmentLevel.HIGH_RISK
        elif reporting_rate < 0.85 or study_coverage < 0.9:
            risk_level = BiasAssessmentLevel.MODERATE_RISK
        elif reporting_rate < 0.95:
            risk_level = BiasAssessmentLevel.LOW_RISK
        else:
            risk_level = BiasAssessmentLevel.NO_BIAS

        interpretation = (
            f"Outcome reporting: {reporting_rate:.1%} of outcomes reported. "
            f"Study coverage: {study_coverage:.1%} of studies have outcome data"
        )

        recommendations = []
        if risk_level in [
            BiasAssessmentLevel.MODERATE_RISK,
            BiasAssessmentLevel.HIGH_RISK,
        ]:
            recommendations.extend(
                [
                    "Contact study authors for missing outcome data",
                    "Check study protocols for planned outcomes",
                    "Consider selective reporting as a bias source",
                ]
            )

        return BiasTest(
            test_name="Outcome Reporting Completeness",
            bias_type=BiasType.REPORTING_BIAS,
            test_statistic=reporting_rate,
            p_value=None,
            confidence_interval=None,
            risk_level=risk_level,
            interpretation=interpretation,
            recommendations=recommendations,
            test_data={
                "total_studies": total_studies,
                "studies_with_outcomes": studies_with_outcomes,
                "total_outcomes": total_outcomes,
                "reported_outcomes": reported_outcomes,
                "reporting_rate": reporting_rate,
                "study_coverage": study_coverage,
            },
        )

    async def _detect_p_hacking(self, studies: List[Dict[str, Any]]) -> BiasTest:
        """Detect potential p - hacking in reported p-values"""
        p_values = []

        for study in studies:
            outcomes = study.get("outcomes", [])
            for outcome in outcomes:
                p_val = outcome.get("p_value")
                if p_val is not None:
                    try:
                        p = float(p_val)
                        if 0 < p < 1:  # Valid p-value range
                            p_values.append(p)
                    except (ValueError, TypeError):
                        continue

        if len(p_values) < 10:
            return BiasTest(
                test_name="P - hacking Detection",
                bias_type=BiasType.REPORTING_BIAS,
                test_statistic=0.0,
                p_value=None,
                confidence_interval=None,
                risk_level=BiasAssessmentLevel.NO_BIAS,
                interpretation="Insufficient p - values for p-hacking assessment",
            )

        # Check for excess of p - values just below 0.05
        just_significant = sum(1 for p in p_values if 0.04 <= p < 0.05)
        barely_ns = sum(1 for p in p_values if 0.05 <= p < 0.06)

        # Calculate ratio
        if barely_ns > 0:
            significance_ratio = just_significant / barely_ns
        else:
            significance_ratio = float("inf") if just_significant > 0 else 1.0

        # Check for p-value clustering around 0.05
        near_05 = sum(1 for p in p_values if 0.04 <= p <= 0.06)
        clustering_rate = near_05 / len(p_values)

        # Risk assessment
        if significance_ratio > 3 or clustering_rate > 0.3:
            risk_level = BiasAssessmentLevel.HIGH_RISK
        elif significance_ratio > 2 or clustering_rate > 0.2:
            risk_level = BiasAssessmentLevel.MODERATE_RISK
        elif significance_ratio > 1.5 or clustering_rate > 0.15:
            risk_level = BiasAssessmentLevel.LOW_RISK
        else:
            risk_level = BiasAssessmentLevel.NO_BIAS

        interpretation = (
            f"P - value distribution analysis: {just_significant} p - values 0.04 - 0.05, "
            f"{barely_ns} p-values 0.05-0.06 (ratio: {significance_ratio:.2f}). "
            f"Clustering near 0.05: {clustering_rate:.1%}"
        )

        recommendations = []
        if risk_level in [
            BiasAssessmentLevel.MODERATE_RISK,
            BiasAssessmentLevel.HIGH_RISK,
        ]:
            recommendations.extend(
                [
                    "Examine p-value distribution for signs of selective reporting",
                    "Consider pre-registered analysis plans",
                    "Be cautious of results just reaching significance",
                ]
            )

        return BiasTest(
            test_name="P-hacking Detection",
            bias_type=BiasType.REPORTING_BIAS,
            test_statistic=significance_ratio,
            p_value=None,
            confidence_interval=None,
            risk_level=risk_level,
            interpretation=interpretation,
            recommendations=recommendations,
            test_data={
                "total_p_values": len(p_values),
                "just_significant": just_significant,
                "barely_non_significant": barely_ns,
                "significance_ratio": significance_ratio,
                "clustering_rate": clustering_rate,
                "p_value_range": [min(p_values), max(p_values)] if p_values else [0, 0],
            },
        )


class BiasDetectionSystem:
    """
    Comprehensive bias detection system combining all bias detection methods
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize bias detection system

        Args:
            config: Configuration for bias detection parameters
        """
        self.config = config or self._get_default_config()
        self.publication_detector = PublicationBiasDetector()
        self.selection_detector = SelectionBiasDetector()
        self.reporting_detector = ReportingBiasDetector()
        self.assessment_history: List[BiasAssessment] = []

        logger.info("Bias detection system initialized")

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default bias detection configuration"""
        return {
            "risk_weights": {
                BiasAssessmentLevel.CRITICAL_RISK: 4,
                BiasAssessmentLevel.HIGH_RISK: 3,
                BiasAssessmentLevel.MODERATE_RISK: 2,
                BiasAssessmentLevel.LOW_RISK: 1,
                BiasAssessmentLevel.NO_BIAS: 0,
            },
            "confidence_thresholds": {
                "high_confidence": 0.8,
                "moderate_confidence": 0.6,
                "low_confidence": 0.4,
            },
            "min_studies_for_publication_bias": 3,
        }

    async def comprehensive_bias_assessment(
        self,
        studies: List[Dict[str, Any]],
        search_strategy: Optional[Dict[str, Any]] = None,
    ) -> BiasAssessment:
        """
        Perform comprehensive bias assessment

        Args:
            studies: List of studies to assess
            search_strategy: Search strategy information

        Returns:
            Comprehensive bias assessment
        """
        logger.info("Starting comprehensive bias assessment")

        all_tests = []

        try:
            # Publication bias detection
            if len(studies) >= self.config["min_studies_for_publication_bias"]:
                pub_tests = await self.publication_detector.detect_publication_bias(
                    studies
                )
                all_tests.extend(pub_tests)
                logger.info(f"Publication bias tests completed: {len(pub_tests)} tests")
            else:
                logger.info("Insufficient studies for publication bias assessment")

            # Selection bias detection
            if search_strategy:
                sel_tests = await self.selection_detector.detect_selection_bias(
                    search_strategy, studies
                )
                all_tests.extend(sel_tests)
                logger.info(f"Selection bias tests completed: {len(sel_tests)} tests")

            # Reporting bias detection
            rep_tests = await self.reporting_detector.detect_reporting_bias(studies)
            all_tests.extend(rep_tests)
            logger.info(f"Reporting bias tests completed: {len(rep_tests)} tests")

            # Calculate overall risk assessment
            overall_risk = self._calculate_overall_risk(all_tests)

            # Generate summary and recommendations
            summary = self._generate_summary(all_tests, overall_risk)
            recommendations = self._generate_recommendations(all_tests, overall_risk)

            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(all_tests)

            assessment = BiasAssessment(
                overall_risk=overall_risk,
                individual_tests=all_tests,
                summary=summary,
                recommendations=recommendations,
                confidence_score=confidence_score,
            )

            self.assessment_history.append(assessment)

            logger.info(
                f"Comprehensive bias assessment completed: {overall_risk.value} risk level"
            )
            return assessment

        except Exception as e:
            logger.error(f"Bias assessment failed: {e}")

            # Return error assessment
            error_assessment = BiasAssessment(
                overall_risk=BiasAssessmentLevel.NO_BIAS,
                individual_tests=[],
                summary=f"Bias assessment failed: {str(e)}",
                recommendations=["Retry bias assessment with valid data"],
                confidence_score=0.0,
            )

            return error_assessment

    def _calculate_overall_risk(self, tests: List[BiasTest]) -> BiasAssessmentLevel:
        """Calculate overall bias risk level"""
        if not tests:
            return BiasAssessmentLevel.NO_BIAS

        # Weight risks by severity
        risk_weights = self.config["risk_weights"]
        total_weight = 0

        for test in tests:
            total_weight += risk_weights.get(test.risk_level, 0)

        # Average weighted risk
        avg_risk = total_weight / len(tests)

        # Map to risk level
        if avg_risk >= 3:
            return BiasAssessmentLevel.CRITICAL_RISK
        elif avg_risk >= 2.5:
            return BiasAssessmentLevel.HIGH_RISK
        elif avg_risk >= 1.5:
            return BiasAssessmentLevel.MODERATE_RISK
        elif avg_risk >= 0.5:
            return BiasAssessmentLevel.LOW_RISK
        else:
            return BiasAssessmentLevel.NO_BIAS

    def _generate_summary(
        self, tests: List[BiasTest], overall_risk: BiasAssessmentLevel
    ) -> str:
        """Generate bias assessment summary"""
        if not tests:
            return "No bias tests performed."

        # Count tests by type and risk level
        bias_types = {}
        risk_counts = {}

        for test in tests:
            bias_types[test.bias_type.value] = (
                bias_types.get(test.bias_type.value, 0) + 1
            )
            risk_counts[test.risk_level.value] = (
                risk_counts.get(test.risk_level.value, 0) + 1
            )

        summary_parts = [
            f"Comprehensive bias assessment completed with {len(tests)} tests.",
            f"Overall risk level: {overall_risk.value.replace('_', ' ').title()}.",
            f"Bias types assessed: {', '.join(bias_types.keys())}.",
        ]

        if (
            risk_counts.get("high_risk", 0) > 0
            or risk_counts.get("critical_risk", 0) > 0
        ):
            summary_parts.append(
                "Significant bias concerns identified requiring attention."
            )
        elif risk_counts.get("moderate_risk", 0) > 0:
            summary_parts.append("Moderate bias concerns identified.")
        else:
            summary_parts.append("No major bias concerns identified.")

        return " ".join(summary_parts)

    def _generate_recommendations(
        self, tests: List[BiasTest], overall_risk: BiasAssessmentLevel
    ) -> List[str]:
        """Generate bias mitigation recommendations"""
        recommendations = set()

        # Collect recommendations from individual tests
        for test in tests:
            recommendations.update(test.recommendations)

        # Add overall recommendations based on risk level
        if overall_risk in [
            BiasAssessmentLevel.HIGH_RISK,
            BiasAssessmentLevel.CRITICAL_RISK,
        ]:
            recommendations.add(
                "Consider sensitivity analyses to assess impact of bias"
            )
            recommendations.add("Document bias limitations in review conclusions")
            recommendations.add("Consider downgrading evidence certainty due to bias")

        return sorted(list(recommendations))

    def _calculate_confidence_score(self, tests: List[BiasTest]) -> float:
        """Calculate confidence score for bias assessment"""
        if not tests:
            return 0.0

        # Base confidence
        base_confidence = 0.7

        # Adjust based on number of tests
        test_factor = min(1.0, len(tests) / 10)

        # Adjust based on test quality (presence of p-values, statistical tests)
        statistical_tests = sum(1 for test in tests if test.p_value is not None)
        statistical_factor = statistical_tests / len(tests) if len(tests) > 0 else 0

        # Calculate final confidence
        confidence = base_confidence + test_factor * 0.2 + statistical_factor * 0.1

        return max(0.0, min(1.0, confidence))

    def get_assessment_summary(self, task_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get bias assessment summary

        Args:
            task_id: Optional task identifier for filtering

        Returns:
            Assessment summary
        """
        relevant_assessments = self.assessment_history

        if not relevant_assessments:
            return {"assessments": [], "summary": "No bias assessments found"}

        # Calculate summary statistics
        total_assessments = len(relevant_assessments)

        risk_distribution = {}
        for level in BiasAssessmentLevel:
            risk_distribution[level.value] = sum(
                1 for a in relevant_assessments if a.overall_risk == level
            )

        avg_confidence = (
            sum(a.confidence_score for a in relevant_assessments) / total_assessments
        )

        # Latest assessment
        latest = relevant_assessments[-1]

        return {
            "total_assessments": total_assessments,
            "risk_distribution": risk_distribution,
            "average_confidence": round(avg_confidence, 3),
            "latest_assessment": {
                "overall_risk": latest.overall_risk.value,
                "has_significant_bias": latest.has_significant_bias,
                "confidence_score": latest.confidence_score,
                "total_tests": len(latest.individual_tests),
                "assessment_date": latest.assessment_date.isoformat(),
            },
            "bias_trend": [
                {
                    "timestamp": a.assessment_date.isoformat(),
                    "overall_risk": a.overall_risk.value,
                    "has_significant_bias": a.has_significant_bias,
                }
                for a in relevant_assessments[-10:]  # Last 10 assessments
            ],
        }

    async def export_assessment(
        self, assessment: BiasAssessment, format_type: str = "json"
    ) -> str:
        """
        Export bias assessment in specified format

        Args:
            assessment: Assessment to export
            format_type: Export format (json, csv, html)

        Returns:
            Formatted assessment string
        """
        if format_type.lower() == "json":
            return json.dumps(
                {
                    "overall_risk": assessment.overall_risk.value,
                    "has_significant_bias": assessment.has_significant_bias,
                    "summary": assessment.summary,
                    "confidence_score": assessment.confidence_score,
                    "assessment_date": assessment.assessment_date.isoformat(),
                    "individual_tests": [
                        {
                            "test_name": test.test_name,
                            "bias_type": test.bias_type.value,
                            "risk_level": test.risk_level.value,
                            "test_statistic": test.test_statistic,
                            "p_value": test.p_value,
                            "interpretation": test.interpretation,
                            "recommendations": test.recommendations,
                        }
                        for test in assessment.individual_tests
                    ],
                    "recommendations": assessment.recommendations,
                },
                indent=2,
            )

        # Add other formats as needed
        return str(assessment)


# Example usage and testing functions
async def demo_bias_detection():
    """Demonstrate bias detection capabilities"""
    print("🔍 Bias Detection System Demo")
    print("=" * 50)

    # Initialize bias detection system
    bias_detector = BiasDetectionSystem()

    # Create example data
    studies = [
        {
            "id": "study_1",
            "effect_size": 0.8,
            "standard_error": 0.15,
            "sample_size": 200,
            "language": "english",
            "publication_type": "journal_article",
            "year": 2020,
            "outcomes": [{"p_value": 0.045, "reported": True}],
        },
        {
            "id": "study_2",
            "effect_size": 0.6,
            "standard_error": 0.20,
            "sample_size": 150,
            "language": "english",
            "publication_type": "journal_article",
            "year": 2021,
            "outcomes": [{"p_value": 0.048, "reported": True}],
        },
        {
            "id": "study_3",
            "effect_size": 1.2,
            "standard_error": 0.25,
            "sample_size": 100,
            "language": "spanish",
            "publication_type": "conference_abstract",
            "year": 2019,
            "outcomes": [{"p_value": 0.120, "reported": True}],
        },
        {
            "id": "study_4",
            "effect_size": 0.9,
            "standard_error": 0.18,
            "sample_size": 180,
            "language": "english",
            "publication_type": "journal_article",
            "year": 2022,
            "outcomes": [{"p_value": 0.049, "reported": True}],
        },
    ]

    search_strategy = {
        "databases": ["pubmed", "embase"],
        "date_limits": {"start_year": 2018, "end_year": 2023},
    }

    # Perform bias assessment
    assessment = await bias_detector.comprehensive_bias_assessment(
        studies, search_strategy
    )

    print("✅ Bias Assessment completed:")
    print(f"   Overall risk: {assessment.overall_risk.value}")
    print(f"   Has significant bias: {assessment.has_significant_bias}")
    print(f"   Confidence score: {assessment.confidence_score:.2f}")
    print(f"   Tests performed: {len(assessment.individual_tests)}")

    print("\n📋 Individual Test Results:")
    for test in assessment.individual_tests:
        print(
            f"   • {test.test_name}: {test.risk_level.value} "
            f"({test.interpretation[:60]}...)"
        )

    print("\n💡 Key Recommendations:")
    for rec in assessment.recommendations[:3]:
        print(f"   • {rec}")

    # Get assessment summary
    summary = bias_detector.get_assessment_summary()
    print("\n📊 Assessment Summary:")
    print(f"   Total assessments: {summary['total_assessments']}")
    print(f"   Average confidence: {summary['average_confidence']}")

    return bias_detector


if __name__ == "__main__":
    asyncio.run(demo_bias_detection())

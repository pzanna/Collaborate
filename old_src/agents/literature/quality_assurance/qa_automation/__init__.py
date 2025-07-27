"""
Quality Assurance Automation Package
===================================

This package provides automated quality assurance capabilities for systematic reviews,
including GRADE assessment, validation engines, bias detection, and quality metrics.

Modules:
    grade_automation: Automated GRADE assessment system
    validation_engine: Data integrity and consistency validation
    bias_detection: Publication and reporting bias detection
    metrics_dashboard: Quality metrics collection and reporting

Author: Eunice AI System
Date: July 2025
"""

from .bias_detection import (BiasAssessment, BiasDetectionSystem, BiasType,
                             PublicationBiasDetector, ReportingBiasDetector,
                             SelectionBiasDetector)
from .grade_automation import (EvidenceProfile, GRADEAssessment,
                               GRADEAutomation, GRADECriteria, GRADELevel,
                               GRADERecommendation)
from .metrics_dashboard import (DashboardConfig, MetricAggregator,
                                MetricCalculator, MetricType, QualityMetric,
                                QualityMetricsDashboard)
from .validation_engine import (ConsistencyValidator, DataIntegrityChecker,
                                QualityValidationEngine, ValidationResult,
                                ValidationRule, ValidationSeverity)

__all__ = [
    # GRADE Automation
    "GRADEAutomation",
    "GRADECriteria",
    "GRADELevel",
    "EvidenceProfile",
    "GRADEAssessment",
    "GRADERecommendation",
    # Validation Engine
    "QualityValidationEngine",
    "ValidationRule",
    "ValidationResult",
    "ValidationSeverity",
    "DataIntegrityChecker",
    "ConsistencyValidator",
    # Bias Detection
    "BiasDetectionSystem",
    "BiasType",
    "BiasAssessment",
    "PublicationBiasDetector",
    "SelectionBiasDetector",
    "ReportingBiasDetector",
    # Metrics Dashboard
    "QualityMetricsDashboard",
    "QualityMetric",
    "MetricType",
    "MetricCalculator",
    "DashboardConfig",
    "MetricAggregator",
]

# Package metadata
__version__ = "1.0.0"
__author__ = "Eunice AI System"
__description__ = "Automated Quality Assurance for Systematic Reviews"

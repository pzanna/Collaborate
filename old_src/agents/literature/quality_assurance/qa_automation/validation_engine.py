"""
Quality Validation Engine
========================

Comprehensive data integrity and consistency validation system for systematic reviews.

This module provides:
- Automated consistency checking across review components
- Data integrity validation for extracted information
- Missing data detection and flagging
- Outlier identification in meta-analyses

Author: Eunice AI System
Date: July 2025
"""

import asyncio
import json
import logging
import re
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

# Configure logging
logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Validation issue severity levels"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ValidationCategory(Enum):
    """Categories of validation checks"""

    DATA_INTEGRITY = "data_integrity"
    CONSISTENCY = "consistency"
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    FORMATTING = "formatting"
    LOGIC = "logic"


@dataclass
class ValidationRule:
    """Validation rule definition"""

    rule_id: str
    name: str
    description: str
    category: ValidationCategory
    severity: ValidationSeverity
    check_function: str  # Function name to call
    parameters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    auto_fix: bool = False


@dataclass
class ValidationIssue:
    """Individual validation issue"""

    rule_id: str
    severity: ValidationSeverity
    category: ValidationCategory
    field: str
    record_id: Optional[str]
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    suggested_fix: Optional[str] = None
    auto_fixable: bool = False
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ValidationResult:
    """Validation result summary"""

    total_records: int
    issues_found: List[ValidationIssue]
    passed_checks: int
    failed_checks: int
    critical_issues: int
    high_issues: int
    medium_issues: int
    low_issues: int
    validation_time: float
    completion_percentage: float = 100.0

    @property
    def is_valid(self) -> bool:
        """Check if validation passed (no critical or high issues)"""
        return self.critical_issues == 0 and self.high_issues == 0

    @property
    def total_issues(self) -> int:
        """Total number of issues found"""
        return len(self.issues_found)


class DataIntegrityChecker:
    """
    Data integrity validation for systematic review data
    """

    def __init__(self):
        self.validation_rules = self._initialize_integrity_rules()

    def _initialize_integrity_rules(self) -> List[ValidationRule]:
        """Initialize data integrity validation rules"""
        return [
            ValidationRule(
                rule_id="INTEGRITY_001",
                name="Required Fields",
                description="Check for required fields presence",
                category=ValidationCategory.DATA_INTEGRITY,
                severity=ValidationSeverity.CRITICAL,
                check_function="check_required_fields",
                parameters={"required_fields": ["title", "authors", "year"]},
            ),
            ValidationRule(
                rule_id="INTEGRITY_002",
                name="Data Types",
                description="Validate data types for numeric fields",
                category=ValidationCategory.DATA_INTEGRITY,
                severity=ValidationSeverity.HIGH,
                check_function="check_data_types",
            ),
            ValidationRule(
                rule_id="INTEGRITY_003",
                name="DOI Format",
                description="Validate DOI format compliance",
                category=ValidationCategory.FORMATTING,
                severity=ValidationSeverity.MEDIUM,
                check_function="check_doi_format",
            ),
            ValidationRule(
                rule_id="INTEGRITY_004",
                name="Year Range",
                description="Check publication year is within reasonable range",
                category=ValidationCategory.ACCURACY,
                severity=ValidationSeverity.MEDIUM,
                check_function="check_year_range",
                parameters={"min_year": 1800, "max_year": datetime.now().year + 1},
            ),
            ValidationRule(
                rule_id="INTEGRITY_005",
                name="Author Format",
                description="Validate author name formatting",
                category=ValidationCategory.FORMATTING,
                severity=ValidationSeverity.LOW,
                check_function="check_author_format",
            ),
        ]

    async def check_data_integrity(
        self, records: List[Dict[str, Any]]
    ) -> List[ValidationIssue]:
        """
        Check data integrity for a list of records

        Args:
            records: List of data records to validate

        Returns:
            List of validation issues found
        """
        issues = []

        for record in records:
            record_id = record.get("id", "unknown")

            for rule in self.validation_rules:
                if not rule.enabled:
                    continue

                try:
                    rule_issues = await self._apply_rule(rule, record, record_id)
                    issues.extend(rule_issues)
                except Exception as e:
                    logger.error(f"Error applying rule {rule.rule_id}: {e}")
                    issues.append(
                        ValidationIssue(
                            rule_id=rule.rule_id,
                            severity=ValidationSeverity.CRITICAL,
                            category=ValidationCategory.DATA_INTEGRITY,
                            field="system",
                            record_id=record_id,
                            message=f"Validation rule error: {str(e)}",
                        )
                    )

        return issues

    async def _apply_rule(
        self, rule: ValidationRule, record: Dict[str, Any], record_id: str
    ) -> List[ValidationIssue]:
        """Apply a single validation rule to a record"""
        method_name = rule.check_function
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            return await method(rule, record, record_id)
        else:
            logger.warning(f"Validation method {method_name} not found")
            return []

    async def check_required_fields(
        self, rule: ValidationRule, record: Dict[str, Any], record_id: str
    ) -> List[ValidationIssue]:
        """Check for required fields presence"""
        issues = []
        required_fields = rule.parameters.get("required_fields", [])

        for field_name in required_fields:
            if (
                field_name not in record
                or not record[field_name]
                or str(record[field_name]).strip() == ""
            ):
                issues.append(
                    ValidationIssue(
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        category=rule.category,
                        field=field,
                        record_id=record_id,
                        message=f"Required field '{field}' is missing or empty",
                        suggested_fix=f"Provide value for field '{field}'",
                        auto_fixable=False,
                    )
                )

        return issues

    async def check_data_types(
        self, rule: ValidationRule, record: Dict[str, Any], record_id: str
    ) -> List[ValidationIssue]:
        """Validate data types for numeric fields"""
        issues = []

        # Check year field
        if "year" in record and record["year"] is not None:
            try:
                year_val = int(record["year"])
                if year_val != record["year"]:  # Was converted from string / float
                    issues.append(
                        ValidationIssue(
                            rule_id=rule.rule_id,
                            severity=ValidationSeverity.LOW,
                            category=rule.category,
                            field="year",
                            record_id=record_id,
                            message="Year field should be integer type",
                            suggested_fix=f"Convert year to integer: {year_val}",
                            auto_fixable=True,
                        )
                    )
            except (ValueError, TypeError):
                issues.append(
                    ValidationIssue(
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        category=rule.category,
                        field="year",
                        record_id=record_id,
                        message=f"Year field contains invalid value: {record['year']}",
                        suggested_fix="Provide valid year as integer",
                    )
                )

        # Check participant count if present
        if "participants" in record and record["participants"] is not None:
            try:
                participants = int(record["participants"])
                if participants < 0:
                    issues.append(
                        ValidationIssue(
                            rule_id=rule.rule_id,
                            severity=rule.severity,
                            category=rule.category,
                            field="participants",
                            record_id=record_id,
                            message="Participant count cannot be negative",
                            suggested_fix="Provide positive participant count",
                        )
                    )
            except (ValueError, TypeError):
                issues.append(
                    ValidationIssue(
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        category=rule.category,
                        field="participants",
                        record_id=record_id,
                        message=f"Participants field contains invalid value: {record['participants']}",
                        suggested_fix="Provide valid participant count as integer",
                    )
                )

        return issues

    async def check_doi_format(
        self, rule: ValidationRule, record: Dict[str, Any], record_id: str
    ) -> List[ValidationIssue]:
        """Validate DOI format compliance"""
        issues = []

        if "doi" in record and record["doi"]:
            doi = str(record["doi"]).strip()

            # DOI format: 10.xxxx / yyyy
            doi_pattern = r"^10\.\d{4,}/[-._;()/:\w\[\]]+$"

            if not re.match(doi_pattern, doi, re.IGNORECASE):
                issues.append(
                    ValidationIssue(
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        category=rule.category,
                        field="doi",
                        record_id=record_id,
                        message=f"Invalid DOI format: {doi}",
                        suggested_fix="Provide DOI in format: 10.xxxx / yyyy",
                        details={
                            "provided_doi": doi,
                            "expected_pattern": "10.xxxx / yyyy",
                        },
                    )
                )

        return issues

    async def check_year_range(
        self, rule: ValidationRule, record: Dict[str, Any], record_id: str
    ) -> List[ValidationIssue]:
        """Check publication year is within reasonable range"""
        issues = []

        if "year" in record and record["year"] is not None:
            try:
                year = int(record["year"])
                min_year = rule.parameters.get("min_year", 1800)
                max_year = rule.parameters.get("max_year", datetime.now().year + 1)

                if year < min_year or year > max_year:
                    issues.append(
                        ValidationIssue(
                            rule_id=rule.rule_id,
                            severity=rule.severity,
                            category=rule.category,
                            field="year",
                            record_id=record_id,
                            message=f"Year {year} is outside reasonable range ({min_year}-{max_year})",
                            suggested_fix=f"Verify publication year is between {min_year} and {max_year}",
                            details={
                                "year": year,
                                "min_year": min_year,
                                "max_year": max_year,
                            },
                        )
                    )
            except (ValueError, TypeError):
                pass  # Handled by data type check

        return issues

    async def check_author_format(
        self, rule: ValidationRule, record: Dict[str, Any], record_id: str
    ) -> List[ValidationIssue]:
        """Validate author name formatting"""
        issues = []

        if "authors" in record and record["authors"]:
            authors = record["authors"]

            # Check if authors is a string that should be a list
            if isinstance(authors, str):
                # Look for common author separators
                separators = [";", " and ", ", ", " & "]
                for sep in separators:
                    if sep in authors:
                        issues.append(
                            ValidationIssue(
                                rule_id=rule.rule_id,
                                severity=rule.severity,
                                category=rule.category,
                                field="authors",
                                record_id=record_id,
                                message="Authors field appears to contain multiple authors as string",
                                suggested_fix=f"Split authors by '{sep}' separator into list",
                                auto_fixable=True,
                                details={
                                    "separator_found": sep,
                                    "authors_string": authors,
                                },
                            )
                        )
                        break

            elif isinstance(authors, list):
                # Check individual author format
                for i, author in enumerate(authors):
                    if not isinstance(author, str) or not author.strip():
                        issues.append(
                            ValidationIssue(
                                rule_id=rule.rule_id,
                                severity=rule.severity,
                                category=rule.category,
                                field=f"authors[{i}]",
                                record_id=record_id,
                                message=f"Author entry {i} is empty or invalid",
                                suggested_fix="Provide valid author name",
                            )
                        )

        return issues


class ConsistencyValidator:
    """
    Consistency validation across review components
    """

    def __init__(self):
        self.cross_reference_rules = self._initialize_consistency_rules()

    def _initialize_consistency_rules(self) -> List[ValidationRule]:
        """Initialize consistency validation rules"""
        return [
            ValidationRule(
                rule_id="CONSISTENCY_001",
                name="Duplicate Detection",
                description="Detect potential duplicate studies",
                category=ValidationCategory.CONSISTENCY,
                severity=ValidationSeverity.HIGH,
                check_function="check_duplicates",
            ),
            ValidationRule(
                rule_id="CONSISTENCY_002",
                name="meta-analysis Consistency",
                description="Check consistency between individual studies and meta-analysis",
                category=ValidationCategory.CONSISTENCY,
                severity=ValidationSeverity.HIGH,
                check_function="check_meta_analysis_consistency",
            ),
            ValidationRule(
                rule_id="CONSISTENCY_003",
                name="Screening Decisions",
                description="Check consistency in screening decisions",
                category=ValidationCategory.CONSISTENCY,
                severity=ValidationSeverity.MEDIUM,
                check_function="check_screening_consistency",
            ),
            ValidationRule(
                rule_id="CONSISTENCY_004",
                name="Effect Size Range",
                description="Check for outlier effect sizes",
                category=ValidationCategory.ACCURACY,
                severity=ValidationSeverity.MEDIUM,
                check_function="check_effect_size_outliers",
            ),
        ]

    async def check_consistency(self, data: Dict[str, Any]) -> List[ValidationIssue]:
        """
        Check consistency across review components

        Args:
            data: Review data including studies, meta-analyses, etc.

        Returns:
            List of consistency issues found
        """
        issues = []

        for rule in self.cross_reference_rules:
            if not rule.enabled:
                continue

            try:
                rule_issues = await self._apply_consistency_rule(rule, data)
                issues.extend(rule_issues)
            except Exception as e:
                logger.error(f"Error applying consistency rule {rule.rule_id}: {e}")
                issues.append(
                    ValidationIssue(
                        rule_id=rule.rule_id,
                        severity=ValidationSeverity.CRITICAL,
                        category=ValidationCategory.CONSISTENCY,
                        field="system",
                        record_id=None,
                        message=f"Consistency rule error: {str(e)}",
                    )
                )

        return issues

    async def _apply_consistency_rule(
        self, rule: ValidationRule, data: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """Apply a single consistency rule"""
        method_name = rule.check_function
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            return await method(rule, data)
        else:
            logger.warning(f"Consistency method {method_name} not found")
            return []

    async def check_duplicates(
        self, rule: ValidationRule, data: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """Detect potential duplicate studies"""
        issues = []
        studies = data.get("studies", [])

        # Check for exact matches
        seen_dois = set()
        seen_titles = set()

        for i, study in enumerate(studies):
            study_id = study.get("id", f"study_{i}")

            # DOI duplicates
            doi = study.get("doi")
            if doi and doi in seen_dois:
                issues.append(
                    ValidationIssue(
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        category=rule.category,
                        field="doi",
                        record_id=study_id,
                        message=f"Duplicate DOI found: {doi}",
                        suggested_fix="Remove duplicate study or verify DOI uniqueness",
                    )
                )
            elif doi:
                seen_dois.add(doi)

            # Title duplicates (normalized)
            title = study.get("title", "").lower().strip()
            if title and title in seen_titles:
                issues.append(
                    ValidationIssue(
                        rule_id=rule.rule_id,
                        severity=ValidationSeverity.MEDIUM,
                        category=rule.category,
                        field="title",
                        record_id=study_id,
                        message=f"Potential duplicate title found: {study.get('title', '')[:50]}...",
                        suggested_fix="Review for potential duplication",
                    )
                )
            elif title:
                seen_titles.add(title)

        return issues

    async def check_meta_analysis_consistency(
        self, rule: ValidationRule, data: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """Check consistency between individual studies and meta-analysis"""
        issues = []

        studies = data.get("studies", [])
        meta_analyses = data.get("meta_analyses", [])

        for meta_analysis in meta_analyses:
            ma_id = meta_analysis.get("id", "unknown")
            included_studies = meta_analysis.get("included_studies", [])

            # Check if all included studies exist
            study_ids = {study.get("id") for study in studies}
            for study_id in included_studies:
                if study_id not in study_ids:
                    issues.append(
                        ValidationIssue(
                            rule_id=rule.rule_id,
                            severity=rule.severity,
                            category=rule.category,
                            field="included_studies",
                            record_id=ma_id,
                            message=f"meta-analysis references non-existent study: {study_id}",
                            suggested_fix="Remove reference or add missing study",
                        )
                    )

            # Check effect size consistency
            if "overall_effect" in meta_analysis:
                individual_effects = []
                for study_id in included_studies:
                    study = next((s for s in studies if s.get("id") == study_id), None)
                    if study and "effect_size" in study:
                        individual_effects.append(study["effect_size"])

                if individual_effects:
                    overall_effect = meta_analysis["overall_effect"]
                    mean_individual = statistics.mean(individual_effects)

                    # Check if overall effect is reasonable given individual effects
                    if (
                        abs(overall_effect-mean_individual)
                        > 2 * statistics.stdev(individual_effects)
                        if len(individual_effects) > 1
                        else 0
                    ):
                        issues.append(
                            ValidationIssue(
                                rule_id=rule.rule_id,
                                severity=ValidationSeverity.MEDIUM,
                                category=rule.category,
                                field="overall_effect",
                                record_id=ma_id,
                                message="Overall effect appears inconsistent with individual study effects",
                                suggested_fix="Review meta-analysis calculation",
                                details={
                                    "overall_effect": overall_effect,
                                    "mean_individual": mean_individual,
                                    "individual_effects": individual_effects,
                                },
                            )
                        )

        return issues

    async def check_screening_consistency(
        self, rule: ValidationRule, data: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """Check consistency in screening decisions"""
        issues = []

        screening_decisions = data.get("screening_decisions", [])

        # Group decisions by study
        study_decisions = {}
        for decision in screening_decisions:
            study_id = decision.get("study_id")
            if study_id not in study_decisions:
                study_decisions[study_id] = []
            study_decisions[study_id].append(decision)

        # Check for inconsistent decisions
        for study_id, decisions in study_decisions.items():
            if len(decisions) > 1:
                # Check for conflicting decisions at same stage
                stages = {}
                for decision in decisions:
                    stage = decision.get("stage", "unknown")
                    if stage not in stages:
                        stages[stage] = []
                    stages[stage].append(decision.get("decision"))

                for stage, stage_decisions in stages.items():
                    unique_decisions = set(stage_decisions)
                    if (
                        len(unique_decisions) > 1
                        and "uncertain" not in unique_decisions
                    ):
                        issues.append(
                            ValidationIssue(
                                rule_id=rule.rule_id,
                                severity=rule.severity,
                                category=rule.category,
                                field="screening_decision",
                                record_id=study_id,
                                message=f"Conflicting screening decisions at {stage} stage: {unique_decisions}",
                                suggested_fix="Resolve screening conflicts through consensus",
                                details={
                                    "stage": stage,
                                    "decisions": list(unique_decisions),
                                },
                            )
                        )

        return issues

    async def check_effect_size_outliers(
        self, rule: ValidationRule, data: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """Check for outlier effect sizes"""
        issues = []

        studies = data.get("studies", [])
        effect_sizes = []

        # Collect effect sizes
        for study in studies:
            if "effect_size" in study and study["effect_size"] is not None:
                try:
                    effect_size = float(study["effect_size"])
                    effect_sizes.append((study.get("id", "unknown"), effect_size))
                except (ValueError, TypeError):
                    continue

        if len(effect_sizes) > 3:  # Need enough data for outlier detection
            values = [es[1] for es in effect_sizes]

            # Calculate outlier thresholds using IQR method
            q1 = statistics.quantiles(values, n=4)[0]  # 25th percentile
            q3 = statistics.quantiles(values, n=4)[2]  # 75th percentile
            iqr = q3 - q1

            lower_bound = q1-1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            # Identify outliers
            for study_id, effect_size in effect_sizes:
                if effect_size < lower_bound or effect_size > upper_bound:
                    issues.append(
                        ValidationIssue(
                            rule_id=rule.rule_id,
                            severity=rule.severity,
                            category=rule.category,
                            field="effect_size",
                            record_id=study_id,
                            message=f"Effect size {effect_size} appears to be an outlier",
                            suggested_fix="Review study data and effect size calculation",
                            details={
                                "effect_size": effect_size,
                                "lower_bound": lower_bound,
                                "upper_bound": upper_bound,
                                "median": statistics.median(values),
                            },
                        )
                    )

        return issues


class QualityValidationEngine:
    """
    Main quality validation engine combining all validation components
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize quality validation engine

        Args:
            config: Configuration for validation parameters
        """
        self.config = config or self._get_default_config()
        self.integrity_checker = DataIntegrityChecker()
        self.consistency_validator = ConsistencyValidator()
        self.validation_history: List[ValidationResult] = []

        logger.info("Quality validation engine initialized")

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default validation configuration"""
        return {
            "max_issues_per_category": 100,
            "auto_fix_enabled": False,
            "severity_weights": {
                ValidationSeverity.CRITICAL: 4,
                ValidationSeverity.HIGH: 3,
                ValidationSeverity.MEDIUM: 2,
                ValidationSeverity.LOW: 1,
                ValidationSeverity.INFO: 0,
            },
            "validation_timeout": 300,  # 5 minutes
        }

    async def validate_review_data(self, data: Dict[str, Any]) -> ValidationResult:
        """
        Perform comprehensive validation of review data

        Args:
            data: Review data to validate

        Returns:
            Comprehensive validation result
        """
        start_time = datetime.now()
        logger.info("Starting comprehensive review data validation")

        all_issues = []
        total_records = len(data.get("studies", []))

        try:
            # Data integrity validation
            studies = data.get("studies", [])
            if studies:
                integrity_issues = await self.integrity_checker.check_data_integrity(
                    studies
                )
                all_issues.extend(integrity_issues)
                logger.info(
                    f"Data integrity check completed: {len(integrity_issues)} issues found"
                )

            # Consistency validation
            consistency_issues = await self.consistency_validator.check_consistency(
                data
            )
            all_issues.extend(consistency_issues)
            logger.info(
                f"Consistency check completed: {len(consistency_issues)} issues found"
            )

            # Calculate summary statistics
            severity_counts = {severity: 0 for severity in ValidationSeverity}
            for issue in all_issues:
                severity_counts[issue.severity] += 1

            validation_time = (datetime.now()-start_time).total_seconds()

            result = ValidationResult(
                total_records=total_records,
                issues_found=all_issues,
                passed_checks=len(
                    [
                        issue
                        for issue in all_issues
                        if issue.severity
                        in [ValidationSeverity.LOW, ValidationSeverity.INFO]
                    ]
                ),
                failed_checks=len(
                    [
                        issue
                        for issue in all_issues
                        if issue.severity
                        in [
                            ValidationSeverity.CRITICAL,
                            ValidationSeverity.HIGH,
                            ValidationSeverity.MEDIUM,
                        ]
                    ]
                ),
                critical_issues=severity_counts[ValidationSeverity.CRITICAL],
                high_issues=severity_counts[ValidationSeverity.HIGH],
                medium_issues=severity_counts[ValidationSeverity.MEDIUM],
                low_issues=severity_counts[ValidationSeverity.LOW],
                validation_time=validation_time,
            )

            self.validation_history.append(result)

            logger.info(
                f"Validation completed in {validation_time:.2f}s: {result.total_issues} issues found"
            )
            return result

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            validation_time = (datetime.now()-start_time).total_seconds()

            error_result = ValidationResult(
                total_records=total_records,
                issues_found=[
                    ValidationIssue(
                        rule_id="SYSTEM_ERROR",
                        severity=ValidationSeverity.CRITICAL,
                        category=ValidationCategory.DATA_INTEGRITY,
                        field="system",
                        record_id=None,
                        message=f"Validation system error: {str(e)}",
                    )
                ],
                passed_checks=0,
                failed_checks=1,
                critical_issues=1,
                high_issues=0,
                medium_issues=0,
                low_issues=0,
                validation_time=validation_time,
                completion_percentage=0.0,
            )

            return error_result

    async def auto_fix_issues(
        self, issues: List[ValidationIssue], data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Automatically fix issues that can be auto-fixed

        Args:
            issues: List of validation issues
            data: Original data to fix

        Returns:
            Fixed data dictionary
        """
        if not self.config.get("auto_fix_enabled", False):
            logger.info("Auto-fix disabled in configuration")
            return data

        fixed_data = data.copy()
        fixed_count = 0

        for issue in issues:
            if issue.auto_fixable and issue.suggested_fix:
                try:
                    # Apply auto - fix based on issue type
                    if issue.rule_id == "INTEGRITY_002" and "year" in issue.field:
                        # Fix year data type
                        studies = fixed_data.get("studies", [])
                        for study in studies:
                            if study.get("id") == issue.record_id:
                                if "year" in study:
                                    study["year"] = int(float(study["year"]))
                                    fixed_count += 1
                                    break

                    elif issue.rule_id == "INTEGRITY_005" and "authors" in issue.field:
                        # Fix author format
                        studies = fixed_data.get("studies", [])
                        for study in studies:
                            if study.get("id") == issue.record_id:
                                if isinstance(study.get("authors"), str):
                                    separator = issue.details.get(
                                        "separator_found", ";"
                                    )
                                    study["authors"] = [
                                        a.strip()
                                        for a in study["authors"].split(separator)
                                    ]
                                    fixed_count += 1
                                    break

                except Exception as e:
                    logger.warning(f"Failed to auto-fix issue {issue.rule_id}: {e}")

        logger.info(f"Auto-fixed {fixed_count} issues")
        return fixed_data

    def get_validation_summary(self, task_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get validation summary for a task or overall

        Args:
            task_id: Optional task identifier for filtering

        Returns:
            Validation summary
        """
        relevant_results = self.validation_history

        if not relevant_results:
            return {"validation_results": [], "summary": "No validation results found"}

        # Calculate aggregate statistics
        total_validations = len(relevant_results)
        total_issues = sum(result.total_issues for result in relevant_results)
        avg_validation_time = (
            sum(result.validation_time for result in relevant_results)
            / total_validations
        )

        # Issue severity distribution
        severity_totals = {severity.value: 0 for severity in ValidationSeverity}
        for result in relevant_results:
            severity_totals[ValidationSeverity.CRITICAL.value] += result.critical_issues
            severity_totals[ValidationSeverity.HIGH.value] += result.high_issues
            severity_totals[ValidationSeverity.MEDIUM.value] += result.medium_issues
            severity_totals[ValidationSeverity.LOW.value] += result.low_issues

        # Recent validation status
        latest_result = relevant_results[-1]

        return {
            "total_validations": total_validations,
            "total_issues_found": total_issues,
            "average_validation_time": round(avg_validation_time, 2),
            "severity_distribution": severity_totals,
            "latest_validation": {
                "is_valid": latest_result.is_valid,
                "total_issues": latest_result.total_issues,
                "critical_issues": latest_result.critical_issues,
                "high_issues": latest_result.high_issues,
                "validation_time": latest_result.validation_time,
            },
            "validation_trend": [
                {
                    "timestamp": datetime.now().isoformat(),
                    "total_issues": result.total_issues,
                    "is_valid": result.is_valid,
                }
                for result in relevant_results[-10:]  # Last 10 validations
            ],
        }

    async def export_validation_report(
        self, result: ValidationResult, format_type: str = "json"
    ) -> str:
        """
        Export validation report in specified format

        Args:
            result: Validation result to export
            format_type: Export format (json, csv, html)

        Returns:
            Formatted validation report
        """
        if format_type.lower() == "json":
            return json.dumps(
                {
                    "validation_summary": {
                        "total_records": result.total_records,
                        "total_issues": result.total_issues,
                        "is_valid": result.is_valid,
                        "validation_time": result.validation_time,
                        "completion_percentage": result.completion_percentage,
                    },
                    "severity_breakdown": {
                        "critical": result.critical_issues,
                        "high": result.high_issues,
                        "medium": result.medium_issues,
                        "low": result.low_issues,
                    },
                    "issues": [
                        {
                            "rule_id": issue.rule_id,
                            "severity": issue.severity.value,
                            "category": issue.category.value,
                            "field": issue.field,
                            "record_id": issue.record_id,
                            "message": issue.message,
                            "suggested_fix": issue.suggested_fix,
                            "auto_fixable": issue.auto_fixable,
                            "detected_at": issue.detected_at.isoformat(),
                        }
                        for issue in result.issues_found
                    ],
                },
                indent=2,
            )

        # Add other formats as needed
        return str(result)


# Example usage and testing functions
async def demo_validation_engine():
    """Demonstrate validation engine capabilities"""
    print("🔍 Quality Validation Engine Demo")
    print("=" * 50)

    # Initialize validation engine
    validator = QualityValidationEngine()

    # Create example data with various issues
    test_data = {
        "studies": [
            {
                "id": "study_1",
                "title": "A Great Study on AI",
                "authors": ["Smith, J.", "Doe, A."],
                "year": 2023,
                "doi": "10.1000 / example.001",
                "effect_size": 0.8,
            },
            {
                "id": "study_2",
                "title": "",  # Missing title-CRITICAL
                "authors": "Johnson, B.; Wilson, C.",  # Wrong format-LOW
                "year": "2024",  # Wrong type-HIGH
                "doi": "invalid-doi",  # Invalid format-MEDIUM
                "effect_size": 15.5,  # Outlier-MEDIUM
            },
            {
                "id": "study_3",
                "title": "A Great Study on AI",  # Duplicate title-MEDIUM
                "authors": ["Brown, D.", "Taylor, E."],
                "year": 1799,  # Out of range-MEDIUM
                "doi": "10.1000 / example.003",
                "effect_size": 0.9,
            },
        ],
        "meta_analyses": [
            {
                "id": "meta_1",
                "included_studies": [
                    "study_1",
                    "study_2",
                    "nonexistent_study",
                ],  # Missing study-HIGH
                "overall_effect": 2.5,  # Inconsistent with individual effects-MEDIUM
            }
        ],
    }

    # Perform validation
    result = await validator.validate_review_data(test_data)

    print("✅ Validation completed:")
    print(f"   Total records: {result.total_records}")
    print(f"   Issues found: {result.total_issues}")
    print(f"   Is valid: {result.is_valid}")
    print(f"   Critical issues: {result.critical_issues}")
    print(f"   High issues: {result.high_issues}")
    print(f"   Medium issues: {result.medium_issues}")
    print(f"   Low issues: {result.low_issues}")
    print(f"   Validation time: {result.validation_time:.2f}s")

    # Show sample issues
    print("\n📋 Sample Issues Found:")
    for issue in result.issues_found[:5]:  # Show first 5 issues
        print(f"   • {issue.severity.value.upper()}: {issue.message}")
        if issue.suggested_fix:
            print(f"     Fix: {issue.suggested_fix}")

    # Get validation summary
    summary = validator.get_validation_summary()
    print("\n📊 Validation Summary:")
    print(f"   Total validations performed: {summary['total_validations']}")
    print(f"   Average validation time: {summary['average_validation_time']}s")

    return validator


if __name__ == "__main__":
    asyncio.run(demo_validation_engine())

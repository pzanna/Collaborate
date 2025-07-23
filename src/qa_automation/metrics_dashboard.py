"""
Quality Metrics Dashboard
========================

Real-time quality metrics collection and reporting system for systematic reviews.

This module provides:
- Real-time quality indicator monitoring
- Inter-rater reliability tracking
- Completion status and milestone tracking
- Quality assurance report generation

Author: Eunice AI System
Date: July 2025
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
from enum import Enum
from dataclasses import dataclass, field
import json
import asyncio
import statistics
import math
from collections import defaultdict, deque

# Configure logging
logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of quality metrics"""
    COMPLETION_RATE = "completion_rate"
    INTER_RATER_RELIABILITY = "inter_rater_reliability"
    DATA_QUALITY = "data_quality"
    CONSISTENCY = "consistency"
    TIMELINESS = "timeliness"
    BIAS_ASSESSMENT = "bias_assessment"
    GRADE_QUALITY = "grade_quality"
    VALIDATION_SCORE = "validation_score"


class MetricStatus(Enum):
    """Status of metric values"""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    CONCERNING = "concerning"
    CRITICAL = "critical"


@dataclass
class MetricThreshold:
    """Threshold configuration for metrics"""
    excellent: float
    good: float
    acceptable: float
    concerning: float
    # Below concerning is critical


@dataclass
class QualityMetric:
    """Individual quality metric"""
    metric_id: str
    name: str
    metric_type: MetricType
    value: float
    status: MetricStatus
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    trend: Optional[str] = None  # "improving", "stable", "declining"
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricAlert:
    """Quality metric alert"""
    alert_id: str
    metric_id: str
    severity: str  # "low", "medium", "high", "critical"
    message: str
    triggered_at: datetime
    acknowledged: bool = False
    resolved: bool = False
    resolution_note: Optional[str] = None


@dataclass
class DashboardConfig:
    """Dashboard configuration"""
    metric_thresholds: Dict[MetricType, MetricThreshold]
    update_interval: int = 300  # seconds
    retention_period: int = 30  # days
    alert_enabled: bool = True
    real_time_updates: bool = True


class MetricCalculator:
    """
    Metric calculation engine for various quality indicators
    """
    
    def __init__(self):
        self.calculators = {
            MetricType.COMPLETION_RATE: self._calculate_completion_rate,
            MetricType.INTER_RATER_RELIABILITY: self._calculate_inter_rater_reliability,
            MetricType.DATA_QUALITY: self._calculate_data_quality,
            MetricType.CONSISTENCY: self._calculate_consistency,
            MetricType.TIMELINESS: self._calculate_timeliness,
            MetricType.BIAS_ASSESSMENT: self._calculate_bias_assessment,
            MetricType.GRADE_QUALITY: self._calculate_grade_quality,
            MetricType.VALIDATION_SCORE: self._calculate_validation_score
        }
    
    async def calculate_metric(self, metric_type: MetricType, data: Dict[str, Any]) -> float:
        """
        Calculate specific metric value
        
        Args:
            metric_type: Type of metric to calculate
            data: Data required for calculation
            
        Returns:
            Calculated metric value
        """
        calculator = self.calculators.get(metric_type)
        if calculator:
            try:
                return await calculator(data)
            except Exception as e:
                logger.error(f"Error calculating {metric_type.value}: {e}")
                return 0.0
        else:
            logger.warning(f"No calculator found for metric type: {metric_type.value}")
            return 0.0
    
    async def _calculate_completion_rate(self, data: Dict[str, Any]) -> float:
        """Calculate review completion rate"""
        total_tasks = data.get('total_tasks', 0)
        completed_tasks = data.get('completed_tasks', 0)
        
        if total_tasks == 0:
            return 0.0
        
        return (completed_tasks / total_tasks) * 100
    
    async def _calculate_inter_rater_reliability(self, data: Dict[str, Any]) -> float:
        """Calculate inter-rater reliability (Kappa coefficient)"""
        agreements = data.get('agreements', [])
        
        if len(agreements) < 2:
            return 0.0
        
        # Calculate Cohen's Kappa for two raters
        # Simplified calculation - assumes binary decisions
        total_decisions = len(agreements)
        observed_agreement = sum(1 for agreement in agreements if agreement.get('agree', False))
        
        # Calculate expected agreement by chance
        rater1_positive = sum(1 for agreement in agreements if agreement.get('rater1_decision') == 'include')
        rater2_positive = sum(1 for agreement in agreements if agreement.get('rater2_decision') == 'include')
        
        p1_positive = rater1_positive / total_decisions
        p2_positive = rater2_positive / total_decisions
        
        expected_positive = p1_positive * p2_positive
        expected_negative = (1 - p1_positive) * (1 - p2_positive)
        expected_agreement = expected_positive + expected_negative
        
        observed_proportion = observed_agreement / total_decisions
        
        # Cohen's Kappa
        if expected_agreement == 1.0:
            return 1.0
        
        kappa = (observed_proportion - expected_agreement) / (1 - expected_agreement)
        return max(0.0, min(1.0, kappa * 100))  # Convert to percentage
    
    async def _calculate_data_quality(self, data: Dict[str, Any]) -> float:
        """Calculate overall data quality score"""
        validation_results = data.get('validation_results', {})
        
        if not validation_results:
            return 0.0
        
        # Weight different validation aspects
        weights = {
            'completeness': 0.3,
            'accuracy': 0.3,
            'consistency': 0.2,
            'validity': 0.2
        }
        
        total_score = 0.0
        for aspect, weight in weights.items():
            aspect_score = validation_results.get(aspect, 0.0)
            total_score += aspect_score * weight
        
        return total_score
    
    async def _calculate_consistency(self, data: Dict[str, Any]) -> float:
        """Calculate consistency across review components"""
        studies = data.get('studies', [])
        screening_decisions = data.get('screening_decisions', [])
        
        if not studies or not screening_decisions:
            return 0.0
        
        # Check consistency between different review stages
        consistency_scores = []
        
        # Title/abstract vs full-text consistency
        title_decisions = {}
        fulltext_decisions = {}
        
        for decision in screening_decisions:
            study_id = decision.get('study_id')
            stage = decision.get('stage')
            decision_value = decision.get('decision')
            
            if stage == 'title_abstract':
                title_decisions[study_id] = decision_value
            elif stage == 'full_text':
                fulltext_decisions[study_id] = decision_value
        
        # Calculate consistency rate
        consistent_decisions = 0
        total_compared = 0
        
        for study_id in title_decisions:
            if study_id in fulltext_decisions:
                total_compared += 1
                title_decision = title_decisions[study_id]
                fulltext_decision = fulltext_decisions[study_id]
                
                # Consistency rules: include->include, exclude->exclude, uncertain->any
                if title_decision == fulltext_decision:
                    consistent_decisions += 1
                elif title_decision == 'include' and fulltext_decision in ['include', 'uncertain']:
                    consistent_decisions += 1
                elif title_decision == 'uncertain':  # Uncertain can go either way
                    consistent_decisions += 1
        
        if total_compared == 0:
            return 100.0
        
        consistency_rate = (consistent_decisions / total_compared) * 100
        return consistency_rate
    
    async def _calculate_timeliness(self, data: Dict[str, Any]) -> float:
        """Calculate timeliness of review progress"""
        planned_duration = data.get('planned_duration_days', 0)
        actual_duration = data.get('actual_duration_days', 0)
        
        if planned_duration == 0:
            return 100.0
        
        # Calculate efficiency (inverse of delay)
        if actual_duration <= planned_duration:
            return 100.0
        else:
            delay_factor = actual_duration / planned_duration
            timeliness_score = max(0.0, 100.0 / delay_factor)
            return timeliness_score
    
    async def _calculate_bias_assessment(self, data: Dict[str, Any]) -> float:
        """Calculate bias assessment quality score"""
        bias_assessments = data.get('bias_assessments', [])
        
        if not bias_assessments:
            return 0.0
        
        # Score based on bias risk levels
        risk_scores = {
            'no_bias': 100,
            'low_risk': 85,
            'moderate_risk': 70,
            'high_risk': 50,
            'critical_risk': 25
        }
        
        total_score = 0.0
        for assessment in bias_assessments:
            risk_level = assessment.get('overall_risk', 'no_bias')
            total_score += risk_scores.get(risk_level, 50)
        
        return total_score / len(bias_assessments)
    
    async def _calculate_grade_quality(self, data: Dict[str, Any]) -> float:
        """Calculate GRADE assessment quality score"""
        grade_assessments = data.get('grade_assessments', [])
        
        if not grade_assessments:
            return 0.0
        
        # Score based on GRADE certainty levels
        certainty_scores = {
            'high': 100,
            'moderate': 85,
            'low': 70,
            'very_low': 55
        }
        
        total_score = 0.0
        confidence_bonus = 0.0
        
        for assessment in grade_assessments:
            certainty = assessment.get('final_certainty', 'very_low')
            confidence = assessment.get('confidence_score', 0.0)
            
            base_score = certainty_scores.get(certainty, 55)
            confidence_bonus += confidence * 10  # Up to 10 points bonus
            
            total_score += base_score
        
        avg_score = total_score / len(grade_assessments)
        avg_confidence_bonus = confidence_bonus / len(grade_assessments)
        
        return min(100.0, avg_score + avg_confidence_bonus)
    
    async def _calculate_validation_score(self, data: Dict[str, Any]) -> float:
        """Calculate validation quality score"""
        validation_result = data.get('validation_result', {})
        
        if not validation_result:
            return 0.0
        
        # Score based on validation issues
        critical_issues = validation_result.get('critical_issues', 0)
        high_issues = validation_result.get('high_issues', 0)
        medium_issues = validation_result.get('medium_issues', 0)
        low_issues = validation_result.get('low_issues', 0)
        total_records = validation_result.get('total_records', 1)
        
        # Calculate score based on issue severity and frequency
        issue_penalty = (
            critical_issues * 10 +
            high_issues * 5 +
            medium_issues * 2 +
            low_issues * 1
        )
        
        # Normalize by number of records
        penalty_per_record = issue_penalty / total_records
        
        # Convert to 0-100 scale (assuming max 20 penalty points per record)
        score = max(0.0, 100.0 - (penalty_per_record / 20.0) * 100.0)
        
        return score


class MetricAggregator:
    """
    Aggregates and analyzes quality metrics over time
    """
    
    def __init__(self, retention_period: int = 30):
        """
        Initialize metric aggregator
        
        Args:
            retention_period: Days to retain metric history
        """
        self.retention_period = retention_period
        self.metric_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
    
    def add_metric(self, metric: QualityMetric):
        """Add metric to history"""
        key = f"{metric.metric_type.value}_{metric.metric_id}"
        self.metric_history[key].append(metric)
        
        # Clean old metrics
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.retention_period)
        while (self.metric_history[key] and 
               self.metric_history[key][0].timestamp < cutoff_date):
            self.metric_history[key].popleft()
    
    def get_metric_trend(self, metric_type: MetricType, metric_id: str, days: int = 7) -> str:
        """
        Calculate trend for a specific metric
        
        Args:
            metric_type: Type of metric
            metric_id: Metric identifier
            days: Number of days to analyze
            
        Returns:
            Trend description: "improving", "stable", "declining"
        """
        key = f"{metric_type.value}_{metric_id}"
        metrics = list(self.metric_history[key])
        
        if len(metrics) < 2:
            return "stable"
        
        # Filter to recent days
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        recent_metrics = [m for m in metrics if m.timestamp >= cutoff_date]
        
        if len(recent_metrics) < 2:
            return "stable"
        
        # Calculate trend using linear regression slope
        values = [m.value for m in recent_metrics]
        n = len(values)
        
        if n < 2:
            return "stable"
        
        # Simple slope calculation
        x_mean = (n - 1) / 2
        y_mean = statistics.mean(values)
        
        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return "stable"
        
        slope = numerator / denominator
        
        # Determine trend based on slope
        if slope > 2:  # Significant improvement
            return "improving"
        elif slope < -2:  # Significant decline
            return "declining"
        else:
            return "stable"
    
    def get_metric_statistics(self, metric_type: MetricType, metric_id: str, days: int = 7) -> Dict[str, Any]:
        """
        Get statistical summary for a metric
        
        Args:
            metric_type: Type of metric
            metric_id: Metric identifier
            days: Number of days to analyze
            
        Returns:
            Statistical summary
        """
        key = f"{metric_type.value}_{metric_id}"
        metrics = list(self.metric_history[key])
        
        if not metrics:
            return {
                "count": 0,
                "mean": 0.0,
                "median": 0.0,
                "std_dev": 0.0,
                "min": 0.0,
                "max": 0.0,
                "trend": "stable"
            }
        
        # Filter to recent days
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        recent_metrics = [m for m in metrics if m.timestamp >= cutoff_date]
        
        if not recent_metrics:
            recent_metrics = metrics[-1:]  # At least include the latest
        
        values = [m.value for m in recent_metrics]
        
        return {
            "count": len(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0.0,
            "min": min(values),
            "max": max(values),
            "trend": self.get_metric_trend(metric_type, metric_id, days)
        }


class QualityMetricsDashboard:
    """
    Main quality metrics dashboard for systematic reviews
    """
    
    def __init__(self, config: Optional[DashboardConfig] = None):
        """
        Initialize quality metrics dashboard
        
        Args:
            config: Dashboard configuration
        """
        self.config = config or self._get_default_config()
        self.calculator = MetricCalculator()
        self.aggregator = MetricAggregator(self.config.retention_period)
        self.current_metrics: Dict[str, QualityMetric] = {}
        self.alerts: List[MetricAlert] = []
        self.is_running = False
        
        logger.info("Quality metrics dashboard initialized")
    
    def _get_default_config(self) -> DashboardConfig:
        """Get default dashboard configuration"""
        return DashboardConfig(
            metric_thresholds={
                MetricType.COMPLETION_RATE: MetricThreshold(95, 85, 75, 60),
                MetricType.INTER_RATER_RELIABILITY: MetricThreshold(90, 80, 70, 60),
                MetricType.DATA_QUALITY: MetricThreshold(95, 90, 80, 70),
                MetricType.CONSISTENCY: MetricThreshold(95, 90, 85, 75),
                MetricType.TIMELINESS: MetricThreshold(100, 95, 85, 75),
                MetricType.BIAS_ASSESSMENT: MetricThreshold(90, 80, 70, 60),
                MetricType.GRADE_QUALITY: MetricThreshold(90, 85, 75, 65),
                MetricType.VALIDATION_SCORE: MetricThreshold(95, 90, 85, 75)
            },
            update_interval=300,
            retention_period=30,
            alert_enabled=True,
            real_time_updates=True
        )
    
    async def start_monitoring(self):
        """Start real-time metrics monitoring"""
        if self.is_running:
            logger.warning("Dashboard monitoring already running")
            return
        
        self.is_running = True
        logger.info("Started quality metrics monitoring")
        
        # In a real implementation, this would run continuously
        # For demo purposes, we'll just mark it as started
    
    async def stop_monitoring(self):
        """Stop real-time metrics monitoring"""
        self.is_running = False
        logger.info("Stopped quality metrics monitoring")
    
    async def update_metric(self, metric_type: MetricType, metric_id: str, data: Dict[str, Any]):
        """
        Update a specific quality metric
        
        Args:
            metric_type: Type of metric to update
            metric_id: Metric identifier
            data: Data for metric calculation
        """
        try:
            # Calculate metric value
            value = await self.calculator.calculate_metric(metric_type, data)
            
            # Determine status
            status = self._determine_metric_status(metric_type, value)
            
            # Get trend
            trend = self.aggregator.get_metric_trend(metric_type, metric_id)
            
            # Create metric
            metric = QualityMetric(
                metric_id=metric_id,
                name=self._get_metric_name(metric_type),
                metric_type=metric_type,
                value=value,
                status=status,
                timestamp=datetime.now(timezone.utc),
                context=data.get('context', {}),
                trend=trend,
                details=data.get('details', {})
            )
            
            # Store current metric
            key = f"{metric_type.value}_{metric_id}"
            self.current_metrics[key] = metric
            
            # Add to aggregator
            self.aggregator.add_metric(metric)
            
            # Check for alerts
            if self.config.alert_enabled:
                await self._check_metric_alert(metric)
            
            logger.debug(f"Updated metric {metric_type.value}: {value:.2f} ({status.value})")
            
        except Exception as e:
            logger.error(f"Failed to update metric {metric_type.value}: {e}")
    
    def _determine_metric_status(self, metric_type: MetricType, value: float) -> MetricStatus:
        """Determine status based on metric value and thresholds"""
        thresholds = self.config.metric_thresholds.get(metric_type)
        
        if not thresholds:
            return MetricStatus.ACCEPTABLE
        
        if value >= thresholds.excellent:
            return MetricStatus.EXCELLENT
        elif value >= thresholds.good:
            return MetricStatus.GOOD
        elif value >= thresholds.acceptable:
            return MetricStatus.ACCEPTABLE
        elif value >= thresholds.concerning:
            return MetricStatus.CONCERNING
        else:
            return MetricStatus.CRITICAL
    
    def _get_metric_name(self, metric_type: MetricType) -> str:
        """Get human-readable metric name"""
        name_map = {
            MetricType.COMPLETION_RATE: "Completion Rate",
            MetricType.INTER_RATER_RELIABILITY: "Inter-rater Reliability",
            MetricType.DATA_QUALITY: "Data Quality",
            MetricType.CONSISTENCY: "Consistency Score",
            MetricType.TIMELINESS: "Timeliness",
            MetricType.BIAS_ASSESSMENT: "Bias Assessment Quality",
            MetricType.GRADE_QUALITY: "GRADE Quality",
            MetricType.VALIDATION_SCORE: "Validation Score"
        }
        return name_map.get(metric_type, metric_type.value.replace('_', ' ').title())
    
    async def _check_metric_alert(self, metric: QualityMetric):
        """Check if metric triggers an alert"""
        if metric.status in [MetricStatus.CRITICAL, MetricStatus.CONCERNING]:
            severity = "critical" if metric.status == MetricStatus.CRITICAL else "high"
            
            alert = MetricAlert(
                alert_id=f"alert_{metric.metric_id}_{int(metric.timestamp.timestamp())}",
                metric_id=metric.metric_id,
                severity=severity,
                message=f"{metric.name} is {metric.status.value} ({metric.value:.1f})",
                triggered_at=metric.timestamp
            )
            
            self.alerts.append(alert)
            logger.warning(f"Quality alert triggered: {alert.message}")
    
    def get_dashboard_summary(self, task_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get comprehensive dashboard summary
        
        Args:
            task_id: Optional task identifier for filtering
            
        Returns:
            Dashboard summary
        """
        # Filter metrics by task_id if provided
        relevant_metrics = self.current_metrics
        if task_id:
            relevant_metrics = {
                k: v for k, v in self.current_metrics.items() 
                if v.context.get('task_id') == task_id
            }
        
        if not relevant_metrics:
            return {
                "metrics": [],
                "summary": "No metrics available",
                "overall_status": "unknown"
            }
        
        # Calculate status distribution
        status_counts = {}
        for status in MetricStatus:
            status_counts[status.value] = sum(
                1 for metric in relevant_metrics.values() 
                if metric.status == status
            )
        
        # Determine overall status
        if status_counts.get('critical', 0) > 0:
            overall_status = "critical"
        elif status_counts.get('concerning', 0) > 0:
            overall_status = "concerning"
        elif status_counts.get('acceptable', 0) > 2:
            overall_status = "acceptable"
        elif status_counts.get('good', 0) > 0:
            overall_status = "good"
        else:
            overall_status = "excellent"
        
        # Recent alerts
        recent_alerts = [
            {
                "alert_id": alert.alert_id,
                "severity": alert.severity,
                "message": alert.message,
                "triggered_at": alert.triggered_at.isoformat(),
                "acknowledged": alert.acknowledged
            }
            for alert in self.alerts[-10:]  # Last 10 alerts
        ]
        
        # Metric summaries
        metric_summaries = []
        for metric in relevant_metrics.values():
            stats = self.aggregator.get_metric_statistics(
                metric.metric_type, 
                metric.metric_id
            )
            
            metric_summaries.append({
                "metric_id": metric.metric_id,
                "name": metric.name,
                "type": metric.metric_type.value,
                "current_value": metric.value,
                "status": metric.status.value,
                "trend": metric.trend,
                "statistics": stats,
                "last_updated": metric.timestamp.isoformat()
            })
        
        return {
            "overall_status": overall_status,
            "total_metrics": len(relevant_metrics),
            "status_distribution": status_counts,
            "recent_alerts": recent_alerts,
            "metrics": metric_summaries,
            "monitoring_active": self.is_running,
            "last_update": datetime.now(timezone.utc).isoformat()
        }
    
    def get_metric_history(self, metric_type: MetricType, metric_id: str, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get historical data for a specific metric
        
        Args:
            metric_type: Type of metric
            metric_id: Metric identifier
            days: Number of days of history
            
        Returns:
            Historical metric data
        """
        key = f"{metric_type.value}_{metric_id}"
        metrics = list(self.aggregator.metric_history[key])
        
        # Filter to requested time range
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        recent_metrics = [m for m in metrics if m.timestamp >= cutoff_date]
        
        return [
            {
                "timestamp": metric.timestamp.isoformat(),
                "value": metric.value,
                "status": metric.status.value,
                "trend": metric.trend
            }
            for metric in recent_metrics
        ]
    
    async def generate_quality_report(self, task_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate comprehensive quality report
        
        Args:
            task_id: Optional task identifier for filtering
            
        Returns:
            Quality report
        """
        dashboard_summary = self.get_dashboard_summary(task_id)
        
        # Calculate quality score
        metrics = dashboard_summary.get('metrics', [])
        if metrics:
            quality_score = statistics.mean([m['current_value'] for m in metrics])
        else:
            quality_score = 0.0
        
        # Identify areas for improvement
        concerning_metrics = [
            m for m in metrics 
            if m['status'] in ['critical', 'concerning']
        ]
        
        recommendations = []
        for metric in concerning_metrics:
            if metric['type'] == 'completion_rate':
                recommendations.append("Increase review progress pace to meet deadlines")
            elif metric['type'] == 'inter_rater_reliability':
                recommendations.append("Provide additional training to reviewers")
            elif metric['type'] == 'data_quality':
                recommendations.append("Implement additional data validation checks")
            elif metric['type'] == 'consistency':
                recommendations.append("Review screening criteria and decision guidelines")
        
        # Generate executive summary
        total_metrics = len(metrics)
        excellent_count = dashboard_summary['status_distribution'].get('excellent', 0)
        critical_count = dashboard_summary['status_distribution'].get('critical', 0)
        
        if critical_count > 0:
            summary = f"Quality concerns identified: {critical_count} critical metrics require immediate attention."
        elif excellent_count / total_metrics > 0.8:
            summary = f"High quality standards maintained: {excellent_count}/{total_metrics} metrics at excellent level."
        else:
            summary = f"Quality standards acceptable: monitoring {total_metrics} metrics with room for improvement."
        
        return {
            "report_date": datetime.now(timezone.utc).isoformat(),
            "task_id": task_id,
            "overall_quality_score": round(quality_score, 1),
            "executive_summary": summary,
            "metrics_summary": dashboard_summary,
            "areas_for_improvement": concerning_metrics,
            "recommendations": recommendations,
            "quality_trend": "stable",  # Could be calculated from historical data
            "monitoring_period": f"{self.config.retention_period} days"
        }
    
    async def acknowledge_alert(self, alert_id: str, note: Optional[str] = None):
        """
        Acknowledge a quality alert
        
        Args:
            alert_id: Alert identifier
            note: Optional acknowledgment note
        """
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                if note:
                    alert.resolution_note = note
                logger.info(f"Alert {alert_id} acknowledged")
                return
        
        logger.warning(f"Alert {alert_id} not found")
    
    async def export_dashboard_data(self, format_type: str = "json") -> str:
        """
        Export dashboard data in specified format
        
        Args:
            format_type: Export format (json, csv)
            
        Returns:
            Formatted dashboard data
        """
        if format_type.lower() == "json":
            dashboard_data = {
                "config": {
                    "update_interval": self.config.update_interval,
                    "retention_period": self.config.retention_period,
                    "alert_enabled": self.config.alert_enabled
                },
                "current_metrics": {
                    k: {
                        "metric_id": v.metric_id,
                        "name": v.name,
                        "type": v.metric_type.value,
                        "value": v.value,
                        "status": v.status.value,
                        "timestamp": v.timestamp.isoformat(),
                        "trend": v.trend
                    }
                    for k, v in self.current_metrics.items()
                },
                "alerts": [
                    {
                        "alert_id": alert.alert_id,
                        "metric_id": alert.metric_id,
                        "severity": alert.severity,
                        "message": alert.message,
                        "triggered_at": alert.triggered_at.isoformat(),
                        "acknowledged": alert.acknowledged,
                        "resolved": alert.resolved
                    }
                    for alert in self.alerts
                ],
                "export_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            return json.dumps(dashboard_data, indent=2)
        
        # Add other formats as needed
        return str(self.get_dashboard_summary())


# Example usage and testing functions
async def demo_quality_dashboard():
    """Demonstrate quality dashboard capabilities"""
    print("📊 Quality Metrics Dashboard Demo")
    print("=" * 50)
    
    # Initialize dashboard
    dashboard = QualityMetricsDashboard()
    
    # Start monitoring
    await dashboard.start_monitoring()
    
    # Update various metrics with sample data
    metrics_data = [
        (MetricType.COMPLETION_RATE, "review_001", {"total_tasks": 100, "completed_tasks": 75}),
        (MetricType.INTER_RATER_RELIABILITY, "review_001", {
            "agreements": [
                {"agree": True, "rater1_decision": "include", "rater2_decision": "include"},
                {"agree": False, "rater1_decision": "include", "rater2_decision": "exclude"},
                {"agree": True, "rater1_decision": "exclude", "rater2_decision": "exclude"},
                {"agree": True, "rater1_decision": "include", "rater2_decision": "include"}
            ]
        }),
        (MetricType.DATA_QUALITY, "review_001", {
            "validation_results": {
                "completeness": 95.0,
                "accuracy": 90.0,
                "consistency": 88.0,
                "validity": 92.0
            }
        }),
        (MetricType.VALIDATION_SCORE, "review_001", {
            "validation_result": {
                "critical_issues": 1,
                "high_issues": 2,
                "medium_issues": 5,
                "low_issues": 10,
                "total_records": 100
            }
        })
    ]
    
    print("📈 Updating metrics...")
    for metric_type, metric_id, data in metrics_data:
        await dashboard.update_metric(metric_type, metric_id, data)
    
    # Get dashboard summary
    summary = dashboard.get_dashboard_summary()
    
    print(f"✅ Dashboard Summary:")
    print(f"   Overall status: {summary['overall_status']}")
    print(f"   Total metrics: {summary['total_metrics']}")
    print(f"   Monitoring active: {summary['monitoring_active']}")
    
    print(f"\n📋 Current Metrics:")
    for metric in summary['metrics']:
        print(f"   • {metric['name']}: {metric['current_value']:.1f} ({metric['status']})")
        if metric['trend'] != 'stable':
            print(f"     Trend: {metric['trend']}")
    
    # Check for alerts
    if summary['recent_alerts']:
        print(f"\n🚨 Recent Alerts:")
        for alert in summary['recent_alerts']:
            print(f"   • {alert['severity'].upper()}: {alert['message']}")
    else:
        print(f"\n✅ No active alerts")
    
    # Generate quality report
    report = await dashboard.generate_quality_report()
    
    print(f"\n📊 Quality Report:")
    print(f"   Overall quality score: {report['overall_quality_score']}")
    print(f"   Executive summary: {report['executive_summary']}")
    
    if report['recommendations']:
        print(f"   Key recommendations:")
        for rec in report['recommendations'][:3]:
            print(f"     • {rec}")
    
    await dashboard.stop_monitoring()
    return dashboard


if __name__ == "__main__":
    asyncio.run(demo_quality_dashboard())

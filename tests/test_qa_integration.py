"""
Quality Assurance Automation Integration Test
===========================================

Comprehensive test of the QA automation package demonstrating
integrated capabilities across all modules.

This test demonstrates:
- GRADE automation for evidence assessment
- Data validation and integrity checking
- Statistical bias detection
- Quality metrics monitoring and reporting

Author: Eunice AI System
Date: July 2025
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any

# Import QA automation modules
import sys
import os

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from qa_automation import (
    # GRADE automation
    GRADEAutomation,
    EvidenceProfile,
    
    # Validation engine
    QualityValidationEngine,
    ValidationRule,
    ValidationSeverity,
    
    # Bias detection
    BiasDetectionSystem,
    BiasType,
    
    # Metrics dashboard
    QualityMetricsDashboard,
    MetricType
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QAIntegrationDemo:
    """
    Comprehensive demonstration of QA automation capabilities
    """
    
    def __init__(self):
        """Initialize QA systems"""
        self.grade_automation = GRADEAutomation()
        self.validation_engine = QualityValidationEngine()
        self.bias_detection = BiasDetectionSystem()
        self.metrics_dashboard = QualityMetricsDashboard()
        
        logger.info("QA Automation systems initialized")
    
    async def run_comprehensive_demo(self):
        """Run comprehensive QA automation demonstration"""
        print("🔧 Quality Assurance Automation Integration Test")
        print("=" * 60)
        
        # Sample systematic review data
        review_data = self._get_sample_review_data()
        
        # 1. Data Validation
        print("\n📋 Phase 1: Data Validation & Integrity Checking")
        await self._demo_validation_engine(review_data)
        
        # 2. Bias Detection
        print("\n🔍 Phase 2: Statistical Bias Detection")
        await self._demo_bias_detection(review_data)
        
        # 3. GRADE Assessment
        print("\n📊 Phase 3: GRADE Evidence Assessment")
        await self._demo_grade_automation(review_data)
        
        # 4. Quality Metrics Monitoring
        print("\n📈 Phase 4: Quality Metrics Dashboard")
        await self._demo_metrics_dashboard(review_data)
        
        # 5. Generate Comprehensive Report
        print("\n📄 Phase 5: Comprehensive Quality Report")
        await self._generate_quality_report()
        
        print("\n✅ QA Automation Integration Test Complete!")
    
    def _get_sample_review_data(self) -> Dict[str, Any]:
        """Generate sample systematic review data"""
        return {
            "review_id": "demo_review_001",
            "title": "Effectiveness of AI-assisted systematic reviews",
            "studies": [
                {
                    "study_id": "study_001",
                    "title": "AI tools for literature screening",
                    "authors": ["Smith, J.", "Johnson, A."],
                    "year": 2023,
                    "study_type": "rct",
                    "sample_size": 150,
                    "effect_size": 0.65,
                    "confidence_interval": [0.45, 0.85],
                    "p_value": 0.032,
                    "risk_of_bias": "low",
                    "extracted_data": {
                        "intervention": "AI-assisted screening",
                        "comparison": "Manual screening",
                        "outcome": "Screening accuracy",
                        "measure": "percentage"
                    }
                },
                {
                    "study_id": "study_002",
                    "title": "Machine learning in evidence synthesis",
                    "authors": ["Brown, K.", "Davis, L."],
                    "year": 2023,
                    "study_type": "cohort",
                    "sample_size": 200,
                    "effect_size": 0.72,
                    "confidence_interval": [0.58, 0.86],
                    "p_value": 0.018,
                    "risk_of_bias": "moderate",
                    "extracted_data": {
                        "intervention": "ML algorithms",
                        "comparison": "Traditional methods",
                        "outcome": "Review quality",
                        "measure": "score"
                    }
                },
                {
                    "study_id": "study_003",
                    "title": "Automated data extraction systems",
                    "authors": ["Wilson, R.", "Taylor, M."],
                    "year": 2024,
                    "study_type": "rct",
                    "sample_size": 120,
                    "effect_size": 0.58,
                    "confidence_interval": [0.38, 0.78],
                    "p_value": 0.045,
                    "risk_of_bias": "low",
                    "extracted_data": {
                        "intervention": "Automated extraction",
                        "comparison": "Manual extraction",
                        "outcome": "Extraction accuracy",
                        "measure": "percentage"
                    }
                }
            ],
            "screening_decisions": [
                {
                    "study_id": "study_001",
                    "stage": "title_abstract",
                    "decision": "include",
                    "reviewer": "reviewer_1"
                },
                {
                    "study_id": "study_001",
                    "stage": "full_text",
                    "decision": "include",
                    "reviewer": "reviewer_1"
                },
                {
                    "study_id": "study_002",
                    "stage": "title_abstract",
                    "decision": "include",
                    "reviewer": "reviewer_1"
                },
                {
                    "study_id": "study_002",
                    "stage": "full_text",
                    "decision": "include",
                    "reviewer": "reviewer_1"
                }
            ],
            "inter_rater_agreements": [
                {
                    "study_id": "study_001",
                    "agree": True,
                    "rater1_decision": "include",
                    "rater2_decision": "include"
                },
                {
                    "study_id": "study_002",
                    "agree": False,
                    "rater1_decision": "include",
                    "rater2_decision": "exclude"
                },
                {
                    "study_id": "study_003",
                    "agree": True,
                    "rater1_decision": "include",
                    "rater2_decision": "include"
                }
            ]
        }
    
    async def _demo_validation_engine(self, review_data: Dict[str, Any]):
        """Demonstrate data validation capabilities"""
        print("   🔍 Running data integrity checks...")
        
        # Configure validation rules
        rules = [
            ValidationRule(
                rule_id="required_fields",
                name="Required Field Check",
                description="Ensure all required fields are present",
                severity=ValidationSeverity.HIGH,
                check_function=lambda data: all(
                    field in data for field in ['study_id', 'title', 'authors']
                )
            ),
            ValidationRule(
                rule_id="sample_size_valid",
                name="Sample Size Validation",
                description="Sample size must be positive",
                severity=ValidationSeverity.MEDIUM,
                check_function=lambda data: data.get('sample_size', 0) > 0
            )
        ]
        
        for rule in rules:
            self.validation_engine.add_rule(rule)
        
        # Validate review data
        validation_result = await self.validation_engine.validate_review_data(review_data)
        
        print(f"   ✅ Validation complete:")
        print(f"      • Total issues: {validation_result.total_issues}")
        print(f"      • Critical: {validation_result.critical_issues}")
        print(f"      • High: {validation_result.high_issues}")
        print(f"      • Medium: {validation_result.medium_issues}")
        print(f"      • Valid: {validation_result.is_valid}")
        
        # Update metrics
        await self.metrics_dashboard.update_metric(
            MetricType.VALIDATION_SCORE,
            "demo_review",
            {
                "validation_result": {
                    "critical_issues": validation_result.critical_issues,
                    "high_issues": validation_result.high_issues,
                    "medium_issues": validation_result.medium_issues,
                    "low_issues": validation_result.low_issues,
                    "total_records": len(review_data['studies'])
                }
            }
        )
    
    async def _demo_bias_detection(self, review_data: Dict[str, Any]):
        """Demonstrate bias detection capabilities"""
        print("   📊 Analyzing publication and selection bias...")
        
        # Prepare data for bias analysis
        studies = review_data['studies']
        effect_sizes = [study['effect_size'] for study in studies]
        sample_sizes = [study['sample_size'] for study in studies]
        p_values = [study['p_value'] for study in studies]
        
        # Detect publication bias
        pub_bias_result = await self.bias_detection.detect_publication_bias({
            'effect_sizes': effect_sizes,
            'sample_sizes': sample_sizes,
            'p_values': p_values
        })
        
        print(f"   📈 Publication Bias Analysis:")
        print(f"      • Overall risk: {pub_bias_result.overall_risk}")
        print(f"      • Confidence: {pub_bias_result.confidence_score:.2f}")
        print(f"      • Egger's test p-value: {pub_bias_result.statistical_tests.get('eggers_p_value', 'N/A')}")
        
        # Detect selection bias
        selection_bias_result = await self.bias_detection.detect_selection_bias({
            'studies': studies,
            'databases': ['PubMed', 'Embase', 'Cochrane'],
            'languages': ['English'] * len(studies)
        })
        
        print(f"   🎯 Selection Bias Analysis:")
        print(f"      • Overall risk: {selection_bias_result.overall_risk}")
        print(f"      • Database coverage: {selection_bias_result.bias_indicators.get('database_coverage', 'N/A')}")
        
        # Update metrics
        await self.metrics_dashboard.update_metric(
            MetricType.BIAS_ASSESSMENT,
            "demo_review",
            {
                "bias_assessments": [
                    {"overall_risk": pub_bias_result.overall_risk},
                    {"overall_risk": selection_bias_result.overall_risk}
                ]
            }
        )
    
    async def _demo_grade_automation(self, review_data: Dict[str, Any]):
        """Demonstrate GRADE automation capabilities"""
        print("   📋 Performing automated GRADE assessment...")
        
        # Create evidence profile
        studies = review_data['studies']
        evidence_profile = EvidenceProfile(
            outcome="AI-assisted systematic review effectiveness",
            studies=studies,
            total_participants=sum(study['sample_size'] for study in studies),
            study_types=[study['study_type'] for study in studies],
            effect_estimates=[study['effect_size'] for study in studies],
            confidence_intervals=[study['confidence_interval'] for study in studies]
        )
        
        # Perform GRADE assessment
        grade_result = await self.grade_automation.assess_evidence(evidence_profile)
        
        print(f"   🏆 GRADE Assessment Results:")
        print(f"      • Final certainty: {grade_result.final_certainty}")
        print(f"      • Confidence score: {grade_result.confidence_score:.2f}")
        print(f"      • Recommendation strength: {grade_result.recommendation.strength}")
        print(f"      • Key factors:")
        for factor, assessment in grade_result.detailed_assessment.items():
            print(f"        - {factor}: {assessment.get('decision', 'Not assessed')}")
        
        # Update metrics
        await self.metrics_dashboard.update_metric(
            MetricType.GRADE_QUALITY,
            "demo_review",
            {
                "grade_assessments": [{
                    "final_certainty": grade_result.final_certainty,
                    "confidence_score": grade_result.confidence_score
                }]
            }
        )
    
    async def _demo_metrics_dashboard(self, review_data: Dict[str, Any]):
        """Demonstrate quality metrics dashboard"""
        print("   📊 Updating quality metrics dashboard...")
        
        # Start monitoring
        await self.metrics_dashboard.start_monitoring()
        
        # Update completion rate
        await self.metrics_dashboard.update_metric(
            MetricType.COMPLETION_RATE,
            "demo_review",
            {
                "total_tasks": 100,
                "completed_tasks": 85
            }
        )
        
        # Update inter-rater reliability
        await self.metrics_dashboard.update_metric(
            MetricType.INTER_RATER_RELIABILITY,
            "demo_review",
            {
                "agreements": review_data['inter_rater_agreements']
            }
        )
        
        # Update data quality
        await self.metrics_dashboard.update_metric(
            MetricType.DATA_QUALITY,
            "demo_review",
            {
                "validation_results": {
                    "completeness": 95.0,
                    "accuracy": 92.0,
                    "consistency": 88.0,
                    "validity": 91.0
                }
            }
        )
        
        # Get dashboard summary
        dashboard_summary = self.metrics_dashboard.get_dashboard_summary("demo_review")
        
        print(f"   📈 Dashboard Summary:")
        print(f"      • Overall status: {dashboard_summary['overall_status']}")
        print(f"      • Total metrics: {dashboard_summary['total_metrics']}")
        print(f"      • Active monitoring: {dashboard_summary['monitoring_active']}")
        
        # Show metric details
        for metric in dashboard_summary['metrics'][:3]:  # Show first 3 metrics
            print(f"      • {metric['name']}: {metric['current_value']:.1f} ({metric['status']})")
    
    async def _generate_quality_report(self):
        """Generate comprehensive quality assurance report"""
        print("   📄 Generating comprehensive quality report...")
        
        # Generate report
        quality_report = await self.metrics_dashboard.generate_quality_report("demo_review")
        
        print(f"   📊 Quality Report Summary:")
        print(f"      • Overall quality score: {quality_report['overall_quality_score']}")
        print(f"      • Executive summary: {quality_report['executive_summary']}")
        
        if quality_report['recommendations']:
            print(f"      • Key recommendations:")
            for rec in quality_report['recommendations'][:2]:
                print(f"        - {rec}")
        
        # Export dashboard data
        dashboard_export = await self.metrics_dashboard.export_dashboard_data("json")
        print(f"      • Dashboard data exported ({len(dashboard_export)} characters)")
        
        await self.metrics_dashboard.stop_monitoring()


async def run_qa_integration_test():
    """Run the complete QA automation integration test"""
    try:
        demo = QAIntegrationDemo()
        await demo.run_comprehensive_demo()
        
        print("\n🎉 Integration test completed successfully!")
        print("   All QA automation modules functioning correctly.")
        
    except Exception as e:
        logger.error(f"Integration test failed: {e}")
        print(f"\n❌ Integration test failed: {e}")
        raise


if __name__ == "__main__":
    # Run the comprehensive demonstration
    asyncio.run(run_qa_integration_test())

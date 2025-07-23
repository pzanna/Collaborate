"""
Study Type Classifier for Systematic Reviews - Phase 3 Implementation.

This module provides automated study design classification capabilities for systematic reviews,
enabling proper routing to appropriate quality assessment tools and synthesis methods.
"""

import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum


class StudyDesign(Enum):
    """Study design classifications."""
    RANDOMIZED_CONTROLLED_TRIAL = "randomized_controlled_trial"
    QUASI_EXPERIMENTAL = "quasi_experimental"
    COHORT = "cohort"
    CASE_CONTROL = "case_control"
    CROSS_SECTIONAL = "cross_sectional"
    CASE_SERIES = "case_series"
    CASE_REPORT = "case_report"
    SYSTEMATIC_REVIEW = "systematic_review"
    META_ANALYSIS = "meta_analysis"
    NARRATIVE_REVIEW = "narrative_review"
    QUALITATIVE = "qualitative"
    MIXED_METHODS = "mixed_methods"
    OTHER = "other"


class InterventionType(Enum):
    """Types of interventions studied."""
    PHARMACOLOGICAL = "pharmacological"
    SURGICAL = "surgical"
    BEHAVIORAL = "behavioral"
    EDUCATIONAL = "educational"
    TECHNOLOGICAL = "technological"
    POLICY = "policy"
    DIAGNOSTIC = "diagnostic"
    PREVENTIVE = "preventive"
    THERAPEUTIC = "therapeutic"
    OTHER = "other"
    NONE = "none"  # For observational studies


class StudyPhase(Enum):
    """Clinical trial phases."""
    PRECLINICAL = "preclinical"
    PHASE_I = "phase_1"
    PHASE_II = "phase_2"
    PHASE_III = "phase_3"
    PHASE_IV = "phase_4"
    NOT_APPLICABLE = "not_applicable"


@dataclass
class StudyCharacteristics:
    """Extracted study characteristics."""
    study_design: StudyDesign
    intervention_type: InterventionType
    study_phase: StudyPhase
    sample_size: Optional[int]
    study_duration: Optional[str]
    primary_outcome: Optional[str]
    secondary_outcomes: List[str]
    population_description: Optional[str]
    inclusion_criteria: List[str]
    exclusion_criteria: List[str]
    randomization_method: Optional[str]
    blinding_type: Optional[str]
    control_type: Optional[str]
    follow_up_duration: Optional[str]
    statistical_methods: List[str]
    confidence_score: float
    classification_rationale: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'study_design': self.study_design.value,
            'intervention_type': self.intervention_type.value,
            'study_phase': self.study_phase.value,
            'sample_size': self.sample_size,
            'study_duration': self.study_duration,
            'primary_outcome': self.primary_outcome,
            'secondary_outcomes': self.secondary_outcomes,
            'population_description': self.population_description,
            'inclusion_criteria': self.inclusion_criteria,
            'exclusion_criteria': self.exclusion_criteria,
            'randomization_method': self.randomization_method,
            'blinding_type': self.blinding_type,
            'control_type': self.control_type,
            'follow_up_duration': self.follow_up_duration,
            'statistical_methods': self.statistical_methods,
            'confidence_score': self.confidence_score,
            'classification_rationale': self.classification_rationale
        }


@dataclass
class ClassificationResult:
    """Result of study type classification."""
    study_id: str
    study_characteristics: StudyCharacteristics
    quality_assessment_tool: str
    synthesis_category: str
    classification_timestamp: str
    classifier_version: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'study_id': self.study_id,
            'study_characteristics': self.study_characteristics.to_dict(),
            'quality_assessment_tool': self.quality_assessment_tool,
            'synthesis_category': self.synthesis_category,
            'classification_timestamp': self.classification_timestamp,
            'classifier_version': self.classifier_version
        }


class StudyTypeClassifier:
    """
    AI-powered study design classifier for systematic reviews.
    
    Automatically classifies study designs and extracts key characteristics
    to route studies to appropriate quality assessment tools and synthesis methods.
    """
    
    VERSION = "1.0.0"
    
    def __init__(self, database: Any, ai_client: Any):
        """
        Initialize the study type classifier.
        
        Args:
            database: Database connection for systematic review data
            ai_client: AI client for LLM-assisted classification
        """
        self.database = database
        self.ai_client = ai_client
        self.logger = logging.getLogger(__name__)
        
        # Classification patterns for rule-based fallback
        self.design_patterns = {
            StudyDesign.RANDOMIZED_CONTROLLED_TRIAL: [
                r'\brandomized\b', r'\brct\b', r'\brandom\w*\s+controlled\b',
                r'\bdouble\s*blind\b', r'\bplacebo\s*controlled\b'
            ],
            StudyDesign.COHORT: [
                r'\bcohort\b', r'\blongitudinal\b', r'\bprospective\b',
                r'\bfollow\s*up\b', r'\bobservational\b'
            ],
            StudyDesign.CASE_CONTROL: [
                r'\bcase\s*control\b', r'\bretrospec\w*\b'
            ],
            StudyDesign.CROSS_SECTIONAL: [
                r'\bcross\s*sectional\b', r'\bsurvey\b', r'\bprevalence\b'
            ],
            StudyDesign.SYSTEMATIC_REVIEW: [
                r'\bsystematic\s*review\b', r'\bmeta\s*analysis\b'
            ],
            StudyDesign.QUALITATIVE: [
                r'\bqualitative\b', r'\binterview\b', r'\bfocus\s*group\b',
                r'\bethnograph\w*\b', r'\bphenomenolog\w*\b'
            ]
        }
    
    async def classify_study_design(self, study_record: Dict[str, Any]) -> ClassificationResult:
        """
        Classify study design and extract characteristics.
        
        Args:
            study_record: Study record containing title, abstract, and metadata
            
        Returns:
            Classification result with study characteristics and routing information
        """
        self.logger.info(f"Classifying study design for study {study_record.get('id', 'unknown')}")
        
        try:
            # Extract study characteristics using AI and rule-based methods
            characteristics = await self._extract_study_characteristics(study_record)
            
            # Determine quality assessment tool based on study design
            quality_tool = self._route_quality_assessment(characteristics.study_design)
            
            # Determine synthesis category
            synthesis_category = self._determine_synthesis_category(characteristics)
            
            # Create classification result
            result = ClassificationResult(
                study_id=study_record.get('id', 'unknown'),
                study_characteristics=characteristics,
                quality_assessment_tool=quality_tool,
                synthesis_category=synthesis_category,
                classification_timestamp=datetime.now().isoformat(),
                classifier_version=self.VERSION
            )
            
            # Store classification result
            await self._store_classification_result(result)
            
            self.logger.info(f"Classified study {study_record.get('id')} as {characteristics.study_design.value}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to classify study {study_record.get('id', 'unknown')}: {e}")
            # Return default classification
            return self._create_default_classification(study_record)
    
    async def batch_classify_studies(self, study_records: List[Dict[str, Any]]) -> List[ClassificationResult]:
        """
        Classify multiple studies in batch.
        
        Args:
            study_records: List of study records to classify
            
        Returns:
            List of classification results
        """
        self.logger.info(f"Batch classifying {len(study_records)} studies")
        
        results = []
        for study_record in study_records:
            try:
                result = await self.classify_study_design(study_record)
                results.append(result)
            except Exception as e:
                self.logger.warning(f"Failed to classify study {study_record.get('id', 'unknown')}: {e}")
                results.append(self._create_default_classification(study_record))
        
        self.logger.info(f"Completed batch classification of {len(results)} studies")
        return results
    
    def route_quality_assessment(self, study_design: StudyDesign) -> str:
        """
        Route study to appropriate quality assessment tool.
        
        Args:
            study_design: Classified study design
            
        Returns:
            Quality assessment tool identifier
        """
        return self._route_quality_assessment(study_design)
    
    async def _extract_study_characteristics(self, study_record: Dict[str, Any]) -> StudyCharacteristics:
        """Extract detailed study characteristics using AI and rule-based methods."""
        
        # Combine title and abstract for analysis
        title = study_record.get('title', '')
        abstract = study_record.get('abstract', '')
        full_text = study_record.get('full_text', '')
        
        # Use combined text for analysis
        analysis_text = f"Title: {title}\nAbstract: {abstract}"
        if full_text:
            analysis_text += f"\nFull text excerpt: {full_text[:1000]}..."
        
        # Rule-based classification as baseline
        rule_based_design = self._rule_based_classification(analysis_text)
        
        # For demonstration, create comprehensive characteristics
        # In production, this would use AI extraction
        characteristics = StudyCharacteristics(
            study_design=rule_based_design,
            intervention_type=self._extract_intervention_type(analysis_text),
            study_phase=self._extract_study_phase(analysis_text),
            sample_size=self._extract_sample_size(analysis_text),
            study_duration=self._extract_study_duration(analysis_text),
            primary_outcome=self._extract_primary_outcome(analysis_text),
            secondary_outcomes=self._extract_secondary_outcomes(analysis_text),
            population_description=self._extract_population_description(analysis_text),
            inclusion_criteria=self._extract_inclusion_criteria(analysis_text),
            exclusion_criteria=self._extract_exclusion_criteria(analysis_text),
            randomization_method=self._extract_randomization_method(analysis_text),
            blinding_type=self._extract_blinding_type(analysis_text),
            control_type=self._extract_control_type(analysis_text),
            follow_up_duration=self._extract_follow_up_duration(analysis_text),
            statistical_methods=self._extract_statistical_methods(analysis_text),
            confidence_score=0.8,  # Would be calculated based on AI confidence
            classification_rationale=f"Classified as {rule_based_design.value} based on textual analysis"
        )
        
        return characteristics
    
    def _rule_based_classification(self, text: str) -> StudyDesign:
        """Perform rule-based study design classification."""
        
        text_lower = text.lower()
        design_scores = {}
        
        # Score each design based on pattern matches
        for design, patterns in self.design_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text_lower))
                score += matches
            design_scores[design] = score
        
        # Return design with highest score, or OTHER if no matches
        if design_scores and max(design_scores.values()) > 0:
            best_design = StudyDesign.OTHER
            best_score = 0
            for design, score in design_scores.items():
                if score > best_score:
                    best_score = score
                    best_design = design
            return best_design
        else:
            return StudyDesign.OTHER
    
    def _extract_intervention_type(self, text: str) -> InterventionType:
        """Extract intervention type from text."""
        
        text_lower = text.lower()
        
        intervention_patterns = {
            InterventionType.PHARMACOLOGICAL: [r'\bdrug\b', r'\bmedication\b', r'\bpharma\w*\b'],
            InterventionType.SURGICAL: [r'\bsurg\w*\b', r'\boperation\b', r'\bprocedure\b'],
            InterventionType.BEHAVIORAL: [r'\bbehavior\w*\b', r'\btherapy\b', r'\bcounseling\b'],
            InterventionType.EDUCATIONAL: [r'\beducation\w*\b', r'\btraining\b', r'\bteaching\b'],
            InterventionType.TECHNOLOGICAL: [r'\btechnology\b', r'\bdevice\b', r'\bsoftware\b', r'\bai\b'],
            InterventionType.DIAGNOSTIC: [r'\bdiagno\w*\b', r'\bscreen\w*\b', r'\btest\w*\b']
        }
        
        for intervention_type, patterns in intervention_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return intervention_type
        
        return InterventionType.OTHER
    
    def _extract_study_phase(self, text: str) -> StudyPhase:
        """Extract study phase from text."""
        
        text_lower = text.lower()
        
        if re.search(r'\bphase\s*i{1,3}\b', text_lower):
            if 'phase i' in text_lower and 'phase ii' not in text_lower:
                return StudyPhase.PHASE_I
            elif 'phase ii' in text_lower:
                return StudyPhase.PHASE_II
            elif 'phase iii' in text_lower:
                return StudyPhase.PHASE_III
        
        if re.search(r'\bphase\s*iv\b', text_lower):
            return StudyPhase.PHASE_IV
        
        return StudyPhase.NOT_APPLICABLE
    
    def _extract_sample_size(self, text: str) -> Optional[int]:
        """Extract sample size from text."""
        
        # Look for patterns like "n = 150", "150 patients", "sample of 150"
        patterns = [
            r'\bn\s*=\s*(\d+)',
            r'(\d+)\s+patients?',
            r'(\d+)\s+participants?',
            r'(\d+)\s+subjects?',
            r'sample\s+of\s+(\d+)',
            r'enrolled\s+(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                try:
                    return int(match.group(1))
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def _extract_study_duration(self, text: str) -> Optional[str]:
        """Extract study duration from text."""
        
        duration_patterns = [
            r'(\d+)\s+months?',
            r'(\d+)\s+years?',
            r'(\d+)\s+weeks?',
            r'(\d+)\s+days?'
        ]
        
        for pattern in duration_patterns:
            match = re.search(pattern, text.lower())
            if match:
                return match.group(0)
        
        return None
    
    def _extract_primary_outcome(self, text: str) -> Optional[str]:
        """Extract primary outcome from text."""
        
        # Look for primary outcome mentions
        primary_patterns = [
            r'primary\s+outcome[:\s]+([^.]+)',
            r'main\s+outcome[:\s]+([^.]+)',
            r'primary\s+endpoint[:\s]+([^.]+)'
        ]
        
        for pattern in primary_patterns:
            match = re.search(pattern, text.lower())
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_secondary_outcomes(self, text: str) -> List[str]:
        """Extract secondary outcomes from text."""
        
        secondary_patterns = [
            r'secondary\s+outcomes?[:\s]+([^.]+)',
            r'secondary\s+endpoints?[:\s]+([^.]+)'
        ]
        
        outcomes = []
        for pattern in secondary_patterns:
            match = re.search(pattern, text.lower())
            if match:
                outcome_text = match.group(1).strip()
                # Split on common separators
                for separator in [',', ';', ' and ', '&']:
                    if separator in outcome_text:
                        outcomes.extend([o.strip() for o in outcome_text.split(separator)])
                        break
                else:
                    outcomes.append(outcome_text)
        
        return outcomes
    
    def _extract_population_description(self, text: str) -> Optional[str]:
        """Extract population description from text."""
        
        # Look for population descriptions
        population_patterns = [
            r'patients?\s+with\s+([^.]+)',
            r'participants?\s+with\s+([^.]+)',
            r'subjects?\s+with\s+([^.]+)',
            r'population[:\s]+([^.]+)'
        ]
        
        for pattern in population_patterns:
            match = re.search(pattern, text.lower())
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_inclusion_criteria(self, text: str) -> List[str]:
        """Extract inclusion criteria from text."""
        
        criteria_patterns = [
            r'inclusion\s+criteria[:\s]+([^.]+)',
            r'included\s+if[:\s]+([^.]+)'
        ]
        
        criteria = []
        for pattern in criteria_patterns:
            match = re.search(pattern, text.lower())
            if match:
                criteria_text = match.group(1).strip()
                # Split on common separators
                criteria.extend([c.strip() for c in criteria_text.split(',')])
        
        return criteria
    
    def _extract_exclusion_criteria(self, text: str) -> List[str]:
        """Extract exclusion criteria from text."""
        
        criteria_patterns = [
            r'exclusion\s+criteria[:\s]+([^.]+)',
            r'excluded\s+if[:\s]+([^.]+)'
        ]
        
        criteria = []
        for pattern in criteria_patterns:
            match = re.search(pattern, text.lower())
            if match:
                criteria_text = match.group(1).strip()
                criteria.extend([c.strip() for c in criteria_text.split(',')])
        
        return criteria
    
    def _extract_randomization_method(self, text: str) -> Optional[str]:
        """Extract randomization method from text."""
        
        randomization_patterns = [
            r'random\w*\s+using\s+([^.]+)',
            r'randomization\s+method[:\s]+([^.]+)',
            r'block\s+randomization',
            r'stratified\s+randomization',
            r'simple\s+randomization'
        ]
        
        for pattern in randomization_patterns:
            match = re.search(pattern, text.lower())
            if match:
                if hasattr(match, 'groups') and match.groups():
                    return match.group(1).strip()
                else:
                    return match.group(0).strip()
        
        return None
    
    def _extract_blinding_type(self, text: str) -> Optional[str]:
        """Extract blinding type from text."""
        
        text_lower = text.lower()
        
        if 'double blind' in text_lower or 'double-blind' in text_lower:
            return 'double_blind'
        elif 'single blind' in text_lower or 'single-blind' in text_lower:
            return 'single_blind'
        elif 'triple blind' in text_lower or 'triple-blind' in text_lower:
            return 'triple_blind'
        elif 'open label' in text_lower or 'unblinded' in text_lower:
            return 'open_label'
        
        return None
    
    def _extract_control_type(self, text: str) -> Optional[str]:
        """Extract control type from text."""
        
        text_lower = text.lower()
        
        if 'placebo' in text_lower:
            return 'placebo'
        elif 'active control' in text_lower:
            return 'active_control'
        elif 'historical control' in text_lower:
            return 'historical_control'
        elif 'no treatment' in text_lower:
            return 'no_treatment'
        
        return None
    
    def _extract_follow_up_duration(self, text: str) -> Optional[str]:
        """Extract follow-up duration from text."""
        
        followup_patterns = [
            r'follow\s*up\s+(?:of\s+)?(\d+\s+\w+)',
            r'followed\s+for\s+(\d+\s+\w+)'
        ]
        
        for pattern in followup_patterns:
            match = re.search(pattern, text.lower())
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_statistical_methods(self, text: str) -> List[str]:
        """Extract statistical methods from text."""
        
        text_lower = text.lower()
        methods = []
        
        statistical_terms = [
            't-test', 'chi-square', 'anova', 'regression', 'correlation',
            'mann-whitney', 'wilcoxon', 'fisher', 'mcnemar', 'kruskal-wallis'
        ]
        
        for term in statistical_terms:
            if term in text_lower:
                methods.append(term)
        
        return methods
    
    def _route_quality_assessment(self, study_design: StudyDesign) -> str:
        """Route study to appropriate quality assessment tool."""
        
        routing_map = {
            StudyDesign.RANDOMIZED_CONTROLLED_TRIAL: "rob2",
            StudyDesign.QUASI_EXPERIMENTAL: "robins_i",
            StudyDesign.COHORT: "robins_i",
            StudyDesign.CASE_CONTROL: "robins_i",
            StudyDesign.CROSS_SECTIONAL: "robins_i",
            StudyDesign.CASE_SERIES: "ihe_case_series",
            StudyDesign.CASE_REPORT: "ihe_case_report",
            StudyDesign.SYSTEMATIC_REVIEW: "amstar_2",
            StudyDesign.META_ANALYSIS: "amstar_2",
            StudyDesign.QUALITATIVE: "casp_qualitative",
            StudyDesign.MIXED_METHODS: "mmat",
            StudyDesign.OTHER: "generic_quality"
        }
        
        return routing_map.get(study_design, "generic_quality")
    
    def _determine_synthesis_category(self, characteristics: StudyCharacteristics) -> str:
        """Determine synthesis category based on study characteristics."""
        
        design = characteristics.study_design
        intervention_type = characteristics.intervention_type
        
        # Categorize for synthesis purposes
        if design in [StudyDesign.RANDOMIZED_CONTROLLED_TRIAL, StudyDesign.QUASI_EXPERIMENTAL]:
            if intervention_type in [InterventionType.PHARMACOLOGICAL, InterventionType.SURGICAL]:
                return "intervention_quantitative"
            else:
                return "intervention_other"
        elif design in [StudyDesign.COHORT, StudyDesign.CASE_CONTROL]:
            return "observational_quantitative"
        elif design == StudyDesign.QUALITATIVE:
            return "qualitative"
        elif design in [StudyDesign.SYSTEMATIC_REVIEW, StudyDesign.META_ANALYSIS]:
            return "review"
        else:
            return "other"
    
    def _create_default_classification(self, study_record: Dict[str, Any]) -> ClassificationResult:
        """Create default classification for failed classifications."""
        
        default_characteristics = StudyCharacteristics(
            study_design=StudyDesign.OTHER,
            intervention_type=InterventionType.OTHER,
            study_phase=StudyPhase.NOT_APPLICABLE,
            sample_size=None,
            study_duration=None,
            primary_outcome=None,
            secondary_outcomes=[],
            population_description=None,
            inclusion_criteria=[],
            exclusion_criteria=[],
            randomization_method=None,
            blinding_type=None,
            control_type=None,
            follow_up_duration=None,
            statistical_methods=[],
            confidence_score=0.0,
            classification_rationale="Default classification due to processing error"
        )
        
        return ClassificationResult(
            study_id=study_record.get('id', 'unknown'),
            study_characteristics=default_characteristics,
            quality_assessment_tool="generic_quality",
            synthesis_category="other",
            classification_timestamp=datetime.now().isoformat(),
            classifier_version=self.VERSION
        )
    
    async def _store_classification_result(self, result: ClassificationResult) -> None:
        """Store classification result in database."""
        
        try:
            result_data = result.to_dict()
            
            # Use the existing database pattern
            if hasattr(self.database, 'create_study_classification'):
                self.database.create_study_classification(result_data)
            else:
                # Log that storage is not implemented
                self.logger.info(f"Study classification storage not implemented. Result: {result.study_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to store classification result: {e}")
            # Don't raise exception to allow classification to complete


# Integration function for Phase 3 testing
async def demonstrate_study_classification():
    """Demonstrate study type classification capabilities."""
    
    print("🔍 Phase 3: Study Type Classifier Demonstration")
    print("=" * 60)
    
    # Mock database and AI client for demonstration
    class MockDatabase:
        def create_study_classification(self, data):
            print(f"📊 Study classification stored: {data['study_id']} -> {data['study_characteristics']['study_design']}")
    
    class MockAIClient:
        def get_response(self, prompt):
            return "Mock AI response for study classification"
    
    # Initialize classifier
    db = MockDatabase()
    ai_client = MockAIClient()
    classifier = StudyTypeClassifier(db, ai_client)
    
    # Example studies to classify
    study_records = [
        {
            'id': 'study_001',
            'title': 'A Randomized Controlled Trial of AI-Assisted Diagnosis in Emergency Medicine',
            'abstract': 'Background: This double-blind, placebo-controlled randomized controlled trial examined the effectiveness of AI-assisted diagnostic tools. Methods: 300 patients were randomly assigned to AI-assisted diagnosis or standard care. Primary outcome was diagnostic accuracy. Results: AI group showed significantly higher accuracy (p < 0.001).',
            'authors': 'Smith et al.',
            'year': 2023
        },
        {
            'id': 'study_002',
            'title': 'Longitudinal Cohort Study of Machine Learning Implementation in Primary Care',
            'abstract': 'Background: We conducted a prospective cohort study following 1,500 primary care patients over 2 years. Methods: Patients were followed for implementation of ML tools. Outcomes included time to diagnosis and patient satisfaction. Results: ML implementation was associated with reduced diagnostic time.',
            'authors': 'Johnson et al.',
            'year': 2023
        },
        {
            'id': 'study_003',
            'title': 'Case-Control Study of AI Diagnostic Errors in Radiology',
            'abstract': 'Background: This retrospective case-control study examined factors associated with AI diagnostic errors. Methods: 200 cases with AI errors were matched with 400 controls. Inclusion criteria included complete imaging data. Results: Image quality was significantly associated with errors.',
            'authors': 'Chen et al.',
            'year': 2024
        },
        {
            'id': 'study_004',
            'title': 'Qualitative Exploration of Physician Experiences with AI Tools',
            'abstract': 'Background: We conducted in-depth interviews with 25 physicians about their experiences with AI diagnostic tools. Methods: Semi-structured interviews were conducted and analyzed using thematic analysis. Results: Three main themes emerged: trust, workflow integration, and training needs.',
            'authors': 'Davis et al.',
            'year': 2024
        }
    ]
    
    print(f"📚 Classifying {len(study_records)} studies")
    
    # Classify studies
    classification_results = await classifier.batch_classify_studies(study_records)
    
    print(f"\n🎯 Classification Results Summary")
    print(f"   Total studies classified: {len(classification_results)}")
    
    # Summarize results
    design_counts = {}
    tool_counts = {}
    synthesis_counts = {}
    
    for result in classification_results:
        design = result.study_characteristics.study_design.value
        tool = result.quality_assessment_tool
        synthesis = result.synthesis_category
        
        design_counts[design] = design_counts.get(design, 0) + 1
        tool_counts[tool] = tool_counts.get(tool, 0) + 1
        synthesis_counts[synthesis] = synthesis_counts.get(synthesis, 0) + 1
    
    print(f"\n📊 Study Design Distribution:")
    for design, count in design_counts.items():
        print(f"   {design.replace('_', ' ').title()}: {count}")
    
    print(f"\n🔧 Quality Assessment Tool Routing:")
    for tool, count in tool_counts.items():
        print(f"   {tool.upper()}: {count}")
    
    print(f"\n📋 Synthesis Categories:")
    for category, count in synthesis_counts.items():
        print(f"   {category.replace('_', ' ').title()}: {count}")
    
    print(f"\n📝 Detailed Classifications:")
    for result in classification_results:
        char = result.study_characteristics
        print(f"\n   Study {result.study_id}:")
        print(f"     Design: {char.study_design.value}")
        print(f"     Intervention: {char.intervention_type.value}")
        print(f"     Sample Size: {char.sample_size or 'Not extracted'}")
        print(f"     Quality Tool: {result.quality_assessment_tool}")
        print(f"     Synthesis Category: {result.synthesis_category}")
        print(f"     Confidence: {char.confidence_score:.2f}")
    
    print(f"\n✅ Phase 3 Study Type Classifier demonstration completed!")
    return classification_results


if __name__ == "__main__":
    import asyncio
    asyncio.run(demonstrate_study_classification())

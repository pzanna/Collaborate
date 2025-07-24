"""
Evidence Synthesis Engine for Systematic Reviews - Phase 3 Implementation.

This module provides automated evidence synthesis capabilities for systematic reviews,
including evidence table generation, thematic synthesis, and confidence assessment.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union


class SynthesisMethod(Enum):
    """Available synthesis methodologies."""

    NARRATIVE = "narrative"
    THEMATIC = "thematic"
    META_AGGREGATION = "meta_aggregation"


class ConfidenceLevel(Enum):
    """GRADE - inspired confidence levels."""

    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class EvidenceType(Enum):
    """Types of evidence extracted from studies."""

    QUANTITATIVE = "quantitative"
    QUALITATIVE = "qualitative"
    MIXED_METHODS = "mixed_methods"


@dataclass
class EvidenceRow:
    """Individual evidence table row."""

    study_id: str
    study_title: str
    authors: str
    year: int
    study_design: str
    population: str
    intervention: Optional[str]
    comparison: Optional[str]
    outcome: str
    effect_measure: Optional[str]
    effect_size: Optional[Union[float, str]]
    confidence_interval: Optional[str]
    significance: Optional[str]
    quality_score: Optional[str]
    bias_assessment: Optional[str]
    notes: Optional[str]
    evidence_type: EvidenceType

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "study_id": self.study_id,
            "study_title": self.study_title,
            "authors": self.authors,
            "year": self.year,
            "study_design": self.study_design,
            "population": self.population,
            "intervention": self.intervention,
            "comparison": self.comparison,
            "outcome": self.outcome,
            "effect_measure": self.effect_measure,
            "effect_size": self.effect_size,
            "confidence_interval": self.confidence_interval,
            "significance": self.significance,
            "quality_score": self.quality_score,
            "bias_assessment": self.bias_assessment,
            "notes": self.notes,
            "evidence_type": self.evidence_type.value,
        }


@dataclass
class SynthesisResult:
    """Result of evidence synthesis."""

    synthesis_id: str
    task_id: str
    synthesis_method: SynthesisMethod
    evidence_table: List[EvidenceRow]
    themes: List[Dict[str, Any]]
    contradictions: List[Dict[str, Any]]
    confidence_assessment: Dict[str, Any]
    narrative_summary: str
    recommendations: List[str]
    limitations: List[str]
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "synthesis_id": self.synthesis_id,
            "task_id": self.task_id,
            "synthesis_method": self.synthesis_method.value,
            "evidence_table": [row.to_dict() for row in self.evidence_table],
            "themes": self.themes,
            "contradictions": self.contradictions,
            "confidence_assessment": self.confidence_assessment,
            "narrative_summary": self.narrative_summary,
            "recommendations": self.recommendations,
            "limitations": self.limitations,
            "created_at": self.created_at,
        }


class EvidenceSynthesisEngine:
    """
    Evidence synthesis engine for systematic reviews.

    Provides automated evidence extraction, synthesis, and assessment
    capabilities for PRISMA - compliant systematic reviews.
    """

    def __init__(self, database: Any, ai_client: Any):
        """
        Initialize the evidence synthesis engine.

        Args:
            database: Database connection for systematic review data
            ai_client: AI client for LLM - assisted synthesis
        """
        self.database = database
        self.ai_client = ai_client
        self.logger = logging.getLogger(__name__)

    async def build_evidence_table(
        self, included_studies: List[Dict[str, Any]], research_question: str, outcomes: List[str]
    ) -> List[EvidenceRow]:
        """
        Build evidence table from included studies.

        Args:
            included_studies: List of study records that passed screening
            research_question: Primary research question
            outcomes: List of outcomes of interest

        Returns:
            List of evidence rows extracted from studies
        """
        self.logger.info(f"Building evidence table from {len(included_studies)} studies")

        evidence_rows = []

        for study in included_studies:
            try:
                # Extract evidence for each outcome
                for outcome in outcomes:
                    evidence_row = await self._extract_evidence_row(study, research_question, outcome)
                    if evidence_row:
                        evidence_rows.append(evidence_row)

            except Exception as e:
                self.logger.warning(f"Failed to extract evidence from study {study.get('id', 'unknown')}: {e}")
                continue

        self.logger.info(f"Extracted {len(evidence_rows)} evidence rows")
        return evidence_rows

    async def perform_synthesis(
        self, evidence_rows: List[EvidenceRow], synthesis_method: SynthesisMethod, task_id: str, research_question: str
    ) -> SynthesisResult:
        """
        Perform evidence synthesis using specified method.

        Args:
            evidence_rows: Evidence extracted from included studies
            synthesis_method: Method to use for synthesis
            task_id: Task identifier
            research_question: Primary research question

        Returns:
            Complete synthesis results
        """
        self.logger.info(f"Performing {synthesis_method.value} synthesis on {len(evidence_rows)} evidence rows")

        synthesis_id = f"synthesis_{datetime.now().strftime('%Y % m%d_ % H%M % S')}_{hash(str(evidence_rows))%10000}"

        # Perform method - specific synthesis
        if synthesis_method == SynthesisMethod.NARRATIVE:
            themes, narrative_summary = await self._narrative_synthesis(evidence_rows, research_question)
        elif synthesis_method == SynthesisMethod.THEMATIC:
            themes, narrative_summary = await self._thematic_synthesis(evidence_rows, research_question)
        elif synthesis_method == SynthesisMethod.META_AGGREGATION:
            themes, narrative_summary = await self._meta_aggregation_synthesis(evidence_rows, research_question)
        else:
            themes, narrative_summary = await self._narrative_synthesis(evidence_rows, research_question)

        # Detect contradictions
        contradictions = await self.detect_contradictions(evidence_rows)

        # Assess confidence
        confidence_assessment = await self.assess_confidence(evidence_rows, themes)

        # Generate recommendations and limitations
        recommendations = await self._generate_recommendations(themes, confidence_assessment)
        limitations = await self._identify_limitations(evidence_rows, contradictions)

        synthesis_result = SynthesisResult(
            synthesis_id=synthesis_id,
            task_id=task_id,
            synthesis_method=synthesis_method,
            evidence_table=evidence_rows,
            themes=themes,
            contradictions=contradictions,
            confidence_assessment=confidence_assessment,
            narrative_summary=narrative_summary,
            recommendations=recommendations,
            limitations=limitations,
            created_at=datetime.now().isoformat(),
        )

        # Store synthesis result
        await self._store_synthesis_result(synthesis_result)

        self.logger.info(f"Synthesis completed: {synthesis_id}")
        return synthesis_result

    async def detect_contradictions(self, evidence_rows: List[EvidenceRow]) -> List[Dict[str, Any]]:
        """
        Detect contradictory findings across studies.

        Args:
            evidence_rows: Evidence extracted from studies

        Returns:
            List of detected contradictions with details
        """
        self.logger.info("Detecting contradictions in evidence")

        contradictions = []

        # Group evidence by outcome
        outcomes_evidence = {}
        for row in evidence_rows:
            outcome = row.outcome.lower().strip()
            if outcome not in outcomes_evidence:
                outcomes_evidence[outcome] = []
            outcomes_evidence[outcome].append(row)

        # Check for contradictions within each outcome
        for outcome, rows in outcomes_evidence.items():
            if len(rows) < 2:
                continue

            # Simple contradiction detection for demo purposes
            # In production, this would use AI analysis
            effect_sizes = [row.effect_size for row in rows if row.effect_size]
            significances = [row.significance for row in rows if row.significance]

            # Check for conflicting significances
            if len(set(significances)) > 1:
                contradictions.append(
                    {
                        "outcome": outcome,
                        "conflicting_studies": [row.study_id for row in rows],
                        "contradiction_type": "significance",
                        "description": f"Conflicting significance results for {outcome}",
                        "severity": "moderate",
                        "potential_explanations": ["Different study populations", "Methodological differences"],
                    }
                )

        self.logger.info(f"Found {len(contradictions)} contradictions")
        return contradictions

    async def assess_confidence(self, evidence_rows: List[EvidenceRow], themes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Assess confidence in evidence using GRADE - inspired approach.

        Args:
            evidence_rows: Evidence extracted from studies
            themes: Synthesized themes from evidence

        Returns:
            Confidence assessment with ratings and justifications
        """
        self.logger.info("Assessing confidence in evidence")

        confidence_assessment = {}

        # Group evidence by outcome
        outcomes_evidence = {}
        for row in evidence_rows:
            outcome = row.outcome.lower().strip()
            if outcome not in outcomes_evidence:
                outcomes_evidence[outcome] = []
            outcomes_evidence[outcome].append(row)

        # Assess confidence for each outcome
        for outcome, rows in outcomes_evidence.items():
            # Simple confidence assessment based on study count and design
            study_designs = [row.study_design.lower() for row in rows]
            rct_count = sum(1 for design in study_designs if "rct" in design or "randomized" in design)
            total_studies = len(rows)

            if total_studies >= 5 and rct_count >= 2:
                confidence_level = "high"
            elif total_studies >= 3:
                confidence_level = "moderate"
            elif total_studies >= 2:
                confidence_level = "low"
            else:
                confidence_level = "very_low"

            confidence_assessment[outcome] = {
                "confidence_level": confidence_level,
                "rationale": f"Based on {total_studies} studies ({rct_count} RCTs)",
                "factors": {
                    "study_design": f"{rct_count} RCTs, {total_studies - rct_count} observational",
                    "risk_of_bias": "Not assessed",
                    "consistency": "Requires detailed analysis",
                    "directness": "Direct evidence",
                    "precision": "Adequate sample size" if total_studies >= 3 else "Limited sample size",
                },
            }

        # Overall confidence assessment
        individual_levels = [assessment["confidence_level"] for assessment in confidence_assessment.values()]
        level_hierarchy = {"very_low": 0, "low": 1, "moderate": 2, "high": 3}

        if individual_levels:
            avg_level = sum(level_hierarchy[level] for level in individual_levels) / len(individual_levels)
            overall_level = list(level_hierarchy.keys())[int(avg_level)]
        else:
            overall_level = "very_low"

        confidence_assessment["overall"] = {
            "overall_confidence": overall_level,
            "rationale": f"Based on {len(evidence_rows)} evidence rows across {len(outcomes_evidence)} outcomes",
            "key_strengths": ["Systematic methodology", "Multiple outcomes assessed"],
            "key_limitations": ["Limited time for comprehensive assessment", "Simplified confidence grading"],
        }

        return confidence_assessment

    async def _extract_evidence_row(
        self, study: Dict[str, Any], research_question: str, outcome: str
    ) -> Optional[EvidenceRow]:
        """Extract evidence row for specific outcome from study."""

        # Simplified extraction for demo purposes
        # In production, this would use AI to extract structured data

        try:
            # Basic evidence row construction from available study data
            return EvidenceRow(
                study_id=study.get("id", "unknown"),
                study_title=study.get("title", "Unknown"),
                authors=study.get("authors", "Unknown"),
                year=study.get("year", 0),
                study_design=study.get("study_design", "Unknown"),
                population=study.get("population", "Not specified"),
                intervention=study.get("intervention"),
                comparison=study.get("comparison"),
                outcome=outcome,
                effect_measure=study.get("effect_measure"),
                effect_size=study.get("effect_size"),
                confidence_interval=study.get("confidence_interval"),
                significance=study.get("significance"),
                quality_score=study.get("quality_score"),
                bias_assessment=study.get("bias_assessment"),
                notes=f"Extracted for outcome: {outcome}",
                evidence_type=EvidenceType.QUANTITATIVE,
            )

        except Exception as e:
            self.logger.warning(f"Failed to extract evidence for outcome {outcome} from study {study.get('id')}: {e}")
            return None

    async def _narrative_synthesis(
        self, evidence_rows: List[EvidenceRow], research_question: str
    ) -> Tuple[List[Dict[str, Any]], str]:
        """Perform narrative synthesis of evidence."""

        # Simplified narrative synthesis for demo
        themes = []

        # Group by study design
        design_groups = {}
        for row in evidence_rows:
            design = row.study_design
            if design not in design_groups:
                design_groups[design] = []
            design_groups[design].append(row)

        # Create themes based on study designs
        for design, studies in design_groups.items():
            themes.append(
                {
                    "theme": f"Evidence from {design} studies",
                    "description": f"Findings from {len(studies)} {design} studies",
                    "supporting_studies": [study.study_id for study in studies],
                    "strength": "moderate" if len(studies) >= 3 else "weak",
                }
            )

        # Generate narrative summary
        narrative_summary = f"""
        Narrative synthesis of {len(evidence_rows)} evidence rows for: {research_question}

        The evidence comes from {len(design_groups)} different study designs.
        Key themes identified include:
        {', '.join([theme['theme'] for theme in themes])}

        Overall, the evidence suggests further research is needed to establish definitive conclusions.
        """

        return themes, narrative_summary.strip()

    async def _thematic_synthesis(
        self, evidence_rows: List[EvidenceRow], research_question: str
    ) -> Tuple[List[Dict[str, Any]], str]:
        """Perform thematic synthesis of evidence."""

        # Simplified thematic synthesis
        themes = [
            {
                "theme": "Effectiveness patterns",
                "type": "descriptive",
                "description": "Patterns of effectiveness across studies",
                "sub_themes": ["Positive effects", "Null effects", "Negative effects"],
                "supporting_studies": [row.study_id for row in evidence_rows],
                "conceptual_contribution": "Understanding intervention effectiveness",
            }
        ]

        narrative_summary = f"Thematic synthesis identified {len(themes)} themes from {len(evidence_rows)} studies."

        return themes, narrative_summary

    async def _meta_aggregation_synthesis(
        self, evidence_rows: List[EvidenceRow], research_question: str
    ) -> Tuple[List[Dict[str, Any]], str]:
        """Perform meta - aggregation synthesis following JBI approach."""

        # Simplified meta - aggregation
        themes = [
            {
                "theme": "Aggregated finding 1",
                "description": "Synthesized finding from multiple categories",
                "supporting_studies": [row.study_id for row in evidence_rows],
                "strength": "moderate",
                "credibility": "credible",
            }
        ]

        narrative_summary = f"Meta - aggregation synthesis of {len(evidence_rows)} studies."

        return themes, narrative_summary

    async def _generate_recommendations(
        self, themes: List[Dict[str, Any]], confidence_assessment: Dict[str, Any]
    ) -> List[str]:
        """Generate evidence - based recommendations."""

        recommendations = [
            "Further high - quality studies are needed to strengthen the evidence base.",
            "Consider implementing interventions with appropriate monitoring and evaluation.",
            "Address identified limitations in future research designs.",
        ]

        return recommendations

    async def _identify_limitations(
        self, evidence_rows: List[EvidenceRow], contradictions: List[Dict[str, Any]]
    ) -> List[str]:
        """Identify limitations of the synthesis."""

        limitations = []

        # Study design limitations
        study_designs = [row.study_design for row in evidence_rows]
        if all(design.lower() in ["cross - sectional", "case study", "case series"] for design in study_designs):
            limitations.append("Limited to cross - sectional and case studies; causal inferences cannot be made.")

        # Sample size considerations
        if len(evidence_rows) < 10:
            limitations.append(f"Small number of studies included (n={len(evidence_rows)}) may limit generalizability.")

        # Contradiction considerations
        if len(contradictions) > 0:
            limitations.append(
                f"Contradictory findings identified across studies (n={len(contradictions)}) suggest caution in interpretation."
            )

        # Standard limitations
        limitations.extend(
            [
                "Potential publication bias cannot be ruled out without comprehensive grey literature search.",
                "Quality assessment may be limited by available study reporting.",
                "Simplified synthesis methods used for demonstration purposes.",
            ]
        )

        return limitations

    async def _store_synthesis_result(self, synthesis_result: SynthesisResult) -> None:
        """Store synthesis result in database."""

        try:
            synthesis_data = synthesis_result.to_dict()

            # Use the existing database create method pattern
            if hasattr(self.database, "create_evidence_table"):
                self.database.create_evidence_table(synthesis_data)
            else:
                # Log that storage is not implemented
                self.logger.info(
                    f"Evidence table storage not implemented. Synthesis result: {synthesis_result.synthesis_id}"
                )

        except Exception as e:
            self.logger.error(f"Failed to store synthesis result: {e}")
            # Don't raise exception to allow synthesis to complete


# Integration function for Phase 3 testing
async def demonstrate_evidence_synthesis():
    """Demonstrate evidence synthesis capabilities."""

    print("🔬 Phase 3: Evidence Synthesis Engine Demonstration")
    print("=" * 60)

    # Mock database and AI client for demonstration
    class MockDatabase:
        def create_evidence_table(self, data):
            print(f"📊 Evidence table stored: {data['synthesis_id']}")

    class MockAIClient:
        def get_response(self, prompt):
            return "Mock AI response for synthesis analysis"

    # Initialize synthesis engine
    db = MockDatabase()
    ai_client = MockAIClient()
    synthesis_engine = EvidenceSynthesisEngine(db, ai_client)

    # Example included studies
    included_studies = [
        {
            "id": "study_001",
            "title": "Effects of AI on Diagnostic Accuracy in Emergency Medicine",
            "authors": "Smith et al.",
            "year": 2023,
            "study_design": "Randomized Controlled Trial",
            "population": "Emergency department patients",
            "intervention": "AI - assisted diagnosis",
            "comparison": "Standard diagnosis",
            "effect_measure": "Diagnostic accuracy",
            "effect_size": "0.85",
            "confidence_interval": "0.78 - 0.92",
            "significance": "p < 0.001",
            "quality_score": "High",
            "bias_assessment": "Low risk",
        },
        {
            "id": "study_002",
            "title": "AI Diagnostic Tools in Primary Care Settings",
            "authors": "Johnson et al.",
            "year": 2023,
            "study_design": "Cohort Study",
            "population": "Primary care patients",
            "intervention": "AI diagnostic support",
            "comparison": "Usual care",
            "effect_measure": "Time to diagnosis",
            "effect_size": "-15 minutes",
            "confidence_interval": "-25 to -5 minutes",
            "significance": "p = 0.003",
            "quality_score": "Moderate",
            "bias_assessment": "Moderate risk",
        },
        {
            "id": "study_003",
            "title": "Machine Learning in Radiology Diagnosis",
            "authors": "Chen et al.",
            "year": 2024,
            "study_design": "Cross - sectional Study",
            "population": "Radiology patients",
            "intervention": "ML - based image analysis",
            "comparison": "Radiologist interpretation",
            "effect_measure": "Diagnostic accuracy",
            "effect_size": "0.92",
            "confidence_interval": "0.87 - 0.97",
            "significance": "p < 0.001",
            "quality_score": "High",
            "bias_assessment": "Low risk",
        },
    ]

    print(f"📚 Processing {len(included_studies)} included studies")

    # Build evidence table
    evidence_rows = await synthesis_engine.build_evidence_table(
        included_studies=included_studies,
        research_question="What is the effectiveness of AI - assisted diagnostic tools in healthcare?",
        outcomes=["diagnostic_accuracy", "time_to_diagnosis", "patient_satisfaction"],
    )

    print(f"📋 Built evidence table with {len(evidence_rows)} evidence rows")

    # Perform narrative synthesis
    synthesis_result = await synthesis_engine.perform_synthesis(
        evidence_rows=evidence_rows,
        synthesis_method=SynthesisMethod.NARRATIVE,
        task_id="demo_task_001",
        research_question="What is the effectiveness of AI - assisted diagnostic tools in healthcare?",
    )

    print(f"\n🎯 Synthesis Results Summary")
    print(f"   Synthesis ID: {synthesis_result.synthesis_id}")
    print(f"   Method: {synthesis_result.synthesis_method.value}")
    print(f"   Themes identified: {len(synthesis_result.themes)}")
    print(f"   Contradictions found: {len(synthesis_result.contradictions)}")
    print(
        f"   Overall confidence: {synthesis_result.confidence_assessment.get('overall', {}).get('overall_confidence', 'unknown')}"
    )
    print(f"   Recommendations: {len(synthesis_result.recommendations)}")
    print(f"   Limitations: {len(synthesis_result.limitations)}")

    print(f"\n📝 Key Themes:")
    for i, theme in enumerate(synthesis_result.themes, 1):
        print(f"   {i}. {theme['theme']} (strength: {theme.get('strength', 'unknown')})")

    print(f"\n💡 Recommendations:")
    for i, rec in enumerate(synthesis_result.recommendations, 1):
        print(f"   {i}. {rec}")

    print(f"\n⚠️  Key Limitations:")
    for i, limitation in enumerate(synthesis_result.limitations[:3], 1):  # Show first 3
        print(f"   {i}. {limitation}")

    print(f"\n✅ Phase 3 Evidence Synthesis Engine demonstration completed!")
    return synthesis_result


if __name__ == "__main__":
    import asyncio

    asyncio.run(demonstrate_evidence_synthesis())

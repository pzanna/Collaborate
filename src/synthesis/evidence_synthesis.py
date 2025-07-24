"""
Evidence Synthesis Engine for Systematic Reviews.

This module implements automated evidence synthesis capabilities including:
- Evidence table generation from included studies
- Multiple synthesis methodologies (narrative, thematic, meta - aggregation)
- Contradiction detection across studies
- Confidence grading for evidence claims
- GRADE assessment integration

Follows PRISMA 2020 guidelines and integrates with the systematic review workflow.
"""

import asyncio
import hashlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from ..ai_clients.openai_client import OpenAIClient
from ..ai_clients.xai_client import XAIClient
from ..storage.systematic_review_database import SystematicReviewDatabase
from ..utils.error_handler import handle_errors
from ..utils.id_utils import generate_timestamped_id


class SynthesisMethod(Enum):
    """Available synthesis methodologies."""

    NARRATIVE = "narrative"
    THEMATIC = "thematic"
    META_AGGREGATION = "meta_aggregation"
    FRAMEWORK = "framework"
    CONTENT_ANALYSIS = "content_analysis"


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
    SYSTEMATIC_REVIEW = "systematic_review"
    META_ANALYSIS = "meta_analysis"


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

    def __init__(self, database: SystematicReviewDatabase, ai_client: Union[OpenAIClient, XAIClient]):
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

        synthesis_id = generate_timestamped_id("synthesis")

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

            # Use AI to detect contradictions
            contradiction_analysis = await self._analyze_contradictions(outcome, rows)
            if contradiction_analysis.get("has_contradictions", False):
                contradictions.append(
                    {
                        "outcome": outcome,
                        "conflicting_studies": contradiction_analysis.get("conflicting_studies", []),
                        "contradiction_type": contradiction_analysis.get("type", "unknown"),
                        "description": contradiction_analysis.get("description", ""),
                        "severity": contradiction_analysis.get("severity", "moderate"),
                        "potential_explanations": contradiction_analysis.get("explanations", []),
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
            confidence_level = await self._assess_outcome_confidence(outcome, rows)
            confidence_assessment[outcome] = confidence_level

        # Overall confidence assessment
        overall_confidence = await self._assess_overall_confidence(confidence_assessment, themes)
        confidence_assessment["overall"] = overall_confidence

        return confidence_assessment

    async def _extract_evidence_row(
        self, study: Dict[str, Any], research_question: str, outcome: str
    ) -> Optional[EvidenceRow]:
        """Extract evidence row for specific outcome from study."""

        # Create extraction prompt
        extraction_prompt = f"""
        Extract evidence information from this study for the outcome: {outcome}

        Research Question: {research_question}

        Study Information:
        Title: {study.get('title', 'Unknown')}
        Authors: {study.get('authors', 'Unknown')}
        Abstract: {study.get('abstract', 'No abstract available')}

        Please extract the following information:
        1. Population characteristics
        2. Intervention / exposure (if applicable)
        3. Comparison / control (if applicable)
        4. Effect measure and size for the outcome
        5. Confidence intervals or uncertainty measures
        6. Statistical significance
        7. Study design
        8. Any relevant notes

        If the study does not report on this outcome, respond with "NO_DATA".

        Format your response as JSON with these fields:
        {{
            "has_outcome_data": boolean,
            "population": string,
            "intervention": string or null,
            "comparison": string or null,
            "effect_measure": string or null,
            "effect_size": string or null,
            "confidence_interval": string or null,
            "significance": string or null,
            "study_design": string,
            "notes": string or null,
            "evidence_type": "quantitative|qualitative|mixed_methods"
        }}
        """

        try:
            # Use the get_response method instead of chat_completion
            response_content = await asyncio.get_event_loop().run_in_executor(
                None, self.ai_client.get_response, extraction_prompt
            )

            extracted_data = json.loads(response_content)

            if not extracted_data.get("has_outcome_data", False):
                return None

            # Determine evidence type
            evidence_type_str = extracted_data.get("evidence_type", "quantitative")
            try:
                evidence_type = EvidenceType(evidence_type_str)
            except ValueError:
                evidence_type = EvidenceType.QUANTITATIVE

            return EvidenceRow(
                study_id=study.get("id", "unknown"),
                study_title=study.get("title", "Unknown"),
                authors=study.get("authors", "Unknown"),
                year=study.get("year", 0),
                study_design=extracted_data.get("study_design", "Unknown"),
                population=extracted_data.get("population", ""),
                intervention=extracted_data.get("intervention"),
                comparison=extracted_data.get("comparison"),
                outcome=outcome,
                effect_measure=extracted_data.get("effect_measure"),
                effect_size=extracted_data.get("effect_size"),
                confidence_interval=extracted_data.get("confidence_interval"),
                significance=extracted_data.get("significance"),
                quality_score=study.get("quality_score"),
                bias_assessment=study.get("bias_assessment"),
                notes=extracted_data.get("notes"),
                evidence_type=evidence_type,
            )

        except Exception as e:
            self.logger.warning(f"Failed to extract evidence for outcome {outcome} from study {study.get('id')}: {e}")
            return None

    async def _narrative_synthesis(
        self, evidence_rows: List[EvidenceRow], research_question: str
    ) -> Tuple[List[Dict[str, Any]], str]:
        """Perform narrative synthesis of evidence."""

        synthesis_prompt = f"""
        Perform a narrative synthesis of the following evidence for the research question: {research_question}

        Evidence Summary:
        {self._format_evidence_for_synthesis(evidence_rows)}

        Please provide:
        1. Key themes emerging from the evidence
        2. Patterns and trends across studies
        3. Areas of agreement and disagreement
        4. Overall narrative summary

        Format as JSON:
        {{
            "themes": [
                {{
                    "theme": "theme name",
                    "description": "detailed description",
                    "supporting_studies": ["study_id1", "study_id2"],
                    "strength": "strong|moderate|weak"
                }}
            ],
            "narrative_summary": "comprehensive narrative summary"
        }}
        """

        try:
            response = await self.ai_client.chat_completion(
                messages=[{"role": "user", "content": synthesis_prompt}], temperature=0.2, max_tokens=2000
            )

            synthesis_data = json.loads(response.choices[0].message.content)
            return synthesis_data.get("themes", []), synthesis_data.get("narrative_summary", "")

        except Exception as e:
            self.logger.error(f"Failed to perform narrative synthesis: {e}")
            return [], "Synthesis failed due to processing error."

    async def _thematic_synthesis(
        self, evidence_rows: List[EvidenceRow], research_question: str
    ) -> Tuple[List[Dict[str, Any]], str]:
        """Perform thematic synthesis of evidence."""

        # Thematic synthesis follows Thomas & Harden approach
        synthesis_prompt = f"""
        Perform a thematic synthesis following the Thomas & Harden approach for: {research_question}

        Evidence Summary:
        {self._format_evidence_for_synthesis(evidence_rows)}

        Follow these steps:
        1. Line - by - line coding of findings
        2. Development of descriptive themes
        3. Generation of analytical themes
        4. Development of conceptual model

        Format as JSON:
        {{
            "themes": [
                {{
                    "theme": "theme name",
                    "type": "descriptive|analytical",
                    "description": "detailed description",
                    "sub_themes": ["sub - theme1", "sub - theme2"],
                    "supporting_studies": ["study_id1", "study_id2"],
                    "conceptual_contribution": "how this theme contributes to understanding"
                }}
            ],
            "conceptual_model": "overall conceptual framework",
            "narrative_summary": "synthesis narrative"
        }}
        """

        try:
            response = await self.ai_client.chat_completion(
                messages=[{"role": "user", "content": synthesis_prompt}], temperature=0.2, max_tokens=2500
            )

            synthesis_data = json.loads(response.choices[0].message.content)
            return synthesis_data.get("themes", []), synthesis_data.get("narrative_summary", "")

        except Exception as e:
            self.logger.error(f"Failed to perform thematic synthesis: {e}")
            return [], "Thematic synthesis failed due to processing error."

    async def _meta_aggregation_synthesis(
        self, evidence_rows: List[EvidenceRow], research_question: str
    ) -> Tuple[List[Dict[str, Any]], str]:
        """Perform meta - aggregation synthesis following JBI approach."""

        synthesis_prompt = f"""
        Perform meta - aggregation synthesis following the JBI approach for: {research_question}

        Evidence Summary:
        {self._format_evidence_for_synthesis(evidence_rows)}

        Follow these steps:
        1. Extract findings from each study
        2. Categorize findings
        3. Aggregate categories into synthesized findings
        4. Generate recommendations

        Format as JSON:
        {{
            "synthesized_findings": [
                {{
                    "finding": "synthesized finding statement",
                    "categories": ["category1", "category2"],
                    "supporting_studies": ["study_id1", "study_id2"],
                    "confidence": "high|moderate|low",
                    "credibility": "unequivocal|credible|unsupported"
                }}
            ],
            "narrative_summary": "meta - aggregation summary"
        }}
        """

        try:
            response = await self.ai_client.chat_completion(
                messages=[{"role": "user", "content": synthesis_prompt}], temperature=0.1, max_tokens=2000
            )

            synthesis_data = json.loads(response.choices[0].message.content)
            # Convert synthesized findings to themes format
            themes = [
                {
                    "theme": finding["finding"],
                    "description": f"Synthesized from categories: {', '.join(finding['categories'])}",
                    "supporting_studies": finding["supporting_studies"],
                    "strength": finding["confidence"],
                    "credibility": finding.get("credibility", "credible"),
                }
                for finding in synthesis_data.get("synthesized_findings", [])
            ]
            return themes, synthesis_data.get("narrative_summary", "")

        except Exception as e:
            self.logger.error(f"Failed to perform meta - aggregation synthesis: {e}")
            return [], "Meta - aggregation synthesis failed due to processing error."

    async def _analyze_contradictions(self, outcome: str, evidence_rows: List[EvidenceRow]) -> Dict[str, Any]:
        """Analyze potential contradictions for specific outcome."""

        evidence_summary = "\n".join(
            [
                f"Study {row.study_id}: {row.effect_measure} = {row.effect_size}, "
                f"Significance: {row.significance}, Design: {row.study_design}"
                for row in evidence_rows
            ]
        )

        contradiction_prompt = f"""
        Analyze potential contradictions in findings for outcome: {outcome}

        Evidence:
        {evidence_summary}

        Look for:
        1. Conflicting effect directions
        2. Significant vs non - significant results
        3. Different effect magnitudes
        4. Methodological differences that might explain conflicts

        Format as JSON:
        {{
            "has_contradictions": boolean,
            "conflicting_studies": ["study_id1", "study_id2"],
            "type": "effect_direction|significance|magnitude|methodology",
            "description": "description of the contradiction",
            "severity": "minor|moderate|major",
            "explanations": ["possible explanation 1", "possible explanation 2"]
        }}
        """

        try:
            response = await self.ai_client.chat_completion(
                messages=[{"role": "user", "content": contradiction_prompt}], temperature=0.1, max_tokens=800
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            self.logger.warning(f"Failed to analyze contradictions for {outcome}: {e}")
            return {"has_contradictions": False}

    async def _assess_outcome_confidence(self, outcome: str, evidence_rows: List[EvidenceRow]) -> Dict[str, Any]:
        """Assess confidence for specific outcome using GRADE principles."""

        confidence_prompt = f"""
        Assess confidence in evidence for outcome: {outcome}

        Evidence ({len(evidence_rows)} studies):
        {self._format_evidence_for_confidence(evidence_rows)}

        Consider GRADE criteria:
        1. Study design (RCTs start high, observational start low)
        2. Risk of bias
        3. Inconsistency
        4. Indirectness
        5. Imprecision
        6. Publication bias

        Rate confidence as: very_low, low, moderate, high

        Format as JSON:
        {{
            "confidence_level": "very_low|low|moderate|high",
            "rationale": "detailed justification",
            "factors": {{
                "study_design": "assessment",
                "risk_of_bias": "assessment",
                "consistency": "assessment",
                "directness": "assessment",
                "precision": "assessment"
            }}
        }}
        """

        try:
            response = await self.ai_client.chat_completion(
                messages=[{"role": "user", "content": confidence_prompt}], temperature=0.1, max_tokens=1000
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            self.logger.warning(f"Failed to assess confidence for {outcome}: {e}")
            return {"confidence_level": "low", "rationale": "Unable to assess due to processing error", "factors": {}}

    async def _assess_overall_confidence(
        self, outcome_confidences: Dict[str, Any], themes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Assess overall confidence across all outcomes."""

        overall_prompt = f"""
        Assess overall confidence in the systematic review findings.

        Individual Outcome Confidences:
        {json.dumps(outcome_confidences, indent=2)}

        Synthesis Themes:
        {json.dumps(themes, indent=2)}

        Consider:
        1. Consistency across outcomes
        2. Strength of themes
        3. Overall coherence of findings
        4. Limitations and gaps

        Format as JSON:
        {{
            "overall_confidence": "very_low|low|moderate|high",
            "rationale": "detailed justification",
            "key_strengths": ["strength1", "strength2"],
            "key_limitations": ["limitation1", "limitation2"]
        }}
        """

        try:
            response = await self.ai_client.chat_completion(
                messages=[{"role": "user", "content": overall_prompt}], temperature=0.1, max_tokens=800
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            self.logger.warning(f"Failed to assess overall confidence: {e}")
            return {
                "overall_confidence": "low",
                "rationale": "Unable to assess due to processing error",
                "key_strengths": [],
                "key_limitations": ["Assessment error"],
            }

    async def _generate_recommendations(
        self, themes: List[Dict[str, Any]], confidence_assessment: Dict[str, Any]
    ) -> List[str]:
        """Generate evidence - based recommendations."""

        recommendations_prompt = f"""
        Generate evidence - based recommendations from the synthesis.

        Themes:
        {json.dumps(themes, indent=2)}

        Confidence Assessment:
        {json.dumps(confidence_assessment, indent=2)}

        Provide practical, evidence - based recommendations that:
        1. Are supported by the evidence
        2. Consider confidence levels
        3. Are actionable
        4. Consider implementation context

        Format as JSON list of recommendation strings.
        """

        try:
            response = await self.ai_client.chat_completion(
                messages=[{"role": "user", "content": recommendations_prompt}], temperature=0.2, max_tokens=1000
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            self.logger.warning(f"Failed to generate recommendations: {e}")
            return ["Unable to generate recommendations due to processing error."]

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

        # Publication bias
        limitations.append(
            "Potential publication bias cannot be ruled out without comprehensive grey literature search."
        )

        # Study quality
        quality_scores = [row.quality_score for row in evidence_rows if row.quality_score]
        if not quality_scores:
            limitations.append("Quality assessment scores not available for all studies.")

        return limitations

    def _format_evidence_for_synthesis(self, evidence_rows: List[EvidenceRow]) -> str:
        """Format evidence rows for synthesis prompts."""

        formatted_evidence = []
        for row in evidence_rows:
            evidence_text = f"""
Study ID: {row.study_id}
Title: {row.study_title}
Authors: {row.authors} ({row.year})
Design: {row.study_design}
Population: {row.population}
Intervention: {row.intervention or 'N / A'}
Comparison: {row.comparison or 'N / A'}
Outcome: {row.outcome}
Effect: {row.effect_measure or 'N / A'} = {row.effect_size or 'N / A'}
Significance: {row.significance or 'N / A'}
Quality: {row.quality_score or 'N / A'}
Notes: {row.notes or 'None'}
---"""
            formatted_evidence.append(evidence_text)

        return "\n".join(formatted_evidence)

    def _format_evidence_for_confidence(self, evidence_rows: List[EvidenceRow]) -> str:
        """Format evidence rows for confidence assessment."""

        formatted_evidence = []
        for row in evidence_rows:
            evidence_text = (
                f"Study {row.study_id}: {row.study_design}, "
                f"Quality: {row.quality_score or 'N / A'}, "
                f"Effect: {row.effect_size or 'N / A'}, "
                f"Significance: {row.significance or 'N / A'}"
            )
            formatted_evidence.append(evidence_text)

        return "\n".join(formatted_evidence)

    async def _store_synthesis_result(self, synthesis_result: SynthesisResult) -> None:
        """Store synthesis result in database."""

        try:
            synthesis_data = synthesis_result.to_dict()

            # Store in evidence_tables (assuming this table exists or will be created)
            query = """
                INSERT INTO evidence_tables (id, task_id, table_data, synthesis_method,
                                           confidence_assessment, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """

            await self.database.execute_query(
                query,
                (
                    synthesis_result.synthesis_id,
                    synthesis_result.task_id,
                    json.dumps(synthesis_data),
                    synthesis_result.synthesis_method.value,
                    json.dumps(synthesis_result.confidence_assessment),
                    synthesis_result.created_at,
                ),
            )

            self.logger.info(f"Stored synthesis result: {synthesis_result.synthesis_id}")

        except Exception as e:
            self.logger.error(f"Failed to store synthesis result: {e}")
            raise


# Example usage functions
async def example_evidence_synthesis(research_question: Optional[str] = None, example_domain: str = "research"):
    """Example usage of the evidence synthesis engine with configurable research question."""

    from ..ai_clients.openai_client import OpenAIClient
    from ..config.config_manager import ConfigManager
    from ..storage.systematic_review_database import SystematicReviewDatabase

    # Initialize components
    config_manager = ConfigManager()
    db = SystematicReviewDatabase(":memory:")
    ai_client = OpenAIClient(config_manager)

    # Initialize synthesis engine
    synthesis_engine = EvidenceSynthesisEngine(db, ai_client)

    # Default research question if none provided
    if not research_question:
        research_question = "What are the current approaches and methodologies in the research domain?"

    # Example included studies - GENERIC template, no hardcoded content
    included_studies = [
        {
            "id": "study_001",
            "title": f"Methodological Approaches in {example_domain.title()} Research",
            "authors": "Author A et al.",
            "year": 2023,
            "abstract": f"This study examined methodological approaches in {example_domain} research...",
            "quality_score": "High",
            "bias_assessment": "Low risk",
        },
        {
            "id": "study_002",
            "title": f"Contemporary Practices in {example_domain.title()} Studies",
            "authors": "Author B et al.",
            "year": 2023,
            "abstract": f"A comprehensive study of contemporary practices in {example_domain} research...",
            "quality_score": "Moderate",
            "bias_assessment": "Moderate risk",
        },
    ]

    # Build evidence table
    evidence_rows = await synthesis_engine.build_evidence_table(
        included_studies=included_studies,
        research_question=research_question,
        outcomes=["methodology", "effectiveness"],
    )

    # Perform synthesis
    synthesis_result = await synthesis_engine.perform_synthesis(
        evidence_rows=evidence_rows,
        synthesis_method=SynthesisMethod.NARRATIVE,
        task_id="task_001",
        research_question=research_question,
    )

    print(f"Synthesis completed: {synthesis_result.synthesis_id}")
    print(f"Found {len(synthesis_result.themes)} themes")
    print(f"Detected {len(synthesis_result.contradictions)} contradictions")
    print(
        f"Overall confidence: {synthesis_result.confidence_assessment.get('overall', {}).get('overall_confidence', 'unknown')}"
    )


if __name__ == "__main__":
    # Example with configurable research question
    example_question = "How can neuron cells be cultured in a laboratory using accessible materials and techniques?"
    asyncio.run(example_evidence_synthesis(example_question, "cell culture"))

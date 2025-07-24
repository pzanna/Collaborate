"""
ROBINS - I (Risk Of Bias In Non - randomized Studies - of Interventions) plugin.

This plugin implements the ROBINS - I tool for assessing risk of bias
in non - randomized studies of interventions.

Reference: Sterne et al. (2016). ROBINS - I: a tool for assessing risk of bias
in non - randomised studies of interventions. BMJ, 355, i4919.
"""

from typing import Any, Dict, List

from ..quality_appraisal.plugin_architecture import (AssessmentDomain,
                                                     BaseAIQualityPlugin)


class RobinsIPlugin(BaseAIQualityPlugin):
    """ROBINS - I assessment plugin for non - randomized studies."""

    @property
    def tool_id(self) -> str:
        """TODO: Add docstring for tool_id."""
        return "robins - i"

    @property
    def tool_name(self) -> str:
        """TODO: Add docstring for tool_name."""
        return (
            "ROBINS - I (Risk of Bias in Non - randomized Studies - of Interventions)"
        )

    @property
    def applicable_study_types(self) -> List[str]:
        """TODO: Add docstring for applicable_study_types."""
        return [
            "cohort",
            "case - control",
            "cross - sectional",
            "before - after",
            "interrupted time series",
            "controlled before - after",
            "non - randomized controlled trial",
        ]

    @property
    def assessment_domains(self) -> List[AssessmentDomain]:
        """TODO: Add docstring for assessment_domains."""
        return [
            AssessmentDomain.CONFOUNDING,
            AssessmentDomain.SELECTION,
            AssessmentDomain.CLASSIFICATION_INTERVENTION,
            AssessmentDomain.DEVIATION_INTERVENTION,
            AssessmentDomain.MISSING_DATA,
            AssessmentDomain.MEASUREMENT_OUTCOME,
            AssessmentDomain.SELECTION_REPORTED_RESULT,
        ]

    def _build_assessment_prompt(
        self, study: Dict[str, Any], criteria: Dict[str, Any]
    ) -> str:
        """Build ROBINS - I assessment prompt."""
        return f"""
Please conduct a ROBINS - I (Risk of Bias in Non - randomized Studies - of Interventions) assessment for this study.

STUDY INFORMATION:
Title: {study.get('title', 'No title available')}
Authors: {', '.join(study.get('authors', []))}
Year: {study.get('year', 'Unknown')}
Study Design: {study.get('metadata', {}).get('study_type', 'Not specified')}
Journal: {study.get('metadata', {}).get('journal', 'Unknown')}

STUDY ABSTRACT:
{study.get('abstract', 'No abstract available')}

FULL TEXT (if available):
{study.get('full_text', 'Full text not available - base assessment on available information')}

INTERVENTION AND COMPARISON:
Target Intervention: {criteria.get('intervention', 'Not specified')}
Comparison: {criteria.get('comparison', 'Not specified')}
Target Population: {criteria.get('population', 'Not specified')}
Outcomes of Interest: {', '.join(criteria.get('outcomes', []))}

ROBINS - I ASSESSMENT DOMAINS:
Please assess each domain and provide an overall risk of bias rating.

1. BIAS DUE TO CONFOUNDING
   - Were there important confounders that could affect the outcome?
   - Were confounders appropriately measured and controlled for?
   - Was the analysis appropriate for the confounders present?

2. BIAS IN SELECTION OF PARTICIPANTS
   - Was selection of participants based on characteristics observed after intervention?
   - Were there systematic differences in baseline characteristics?
   - Was follow - up time sufficient?

3. BIAS IN CLASSIFICATION OF INTERVENTIONS
   - Was intervention status well - defined and recorded?
   - Could classification of intervention be affected by knowledge of outcomes?
   - Were co - interventions similar between groups?

4. BIAS DUE TO DEVIATIONS FROM INTENDED INTERVENTIONS
   - Were there systematic differences in care provided apart from intervention?
   - Were departures from intended intervention balanced between groups?
   - Could outcomes be influenced by departures from intervention?

5. BIAS DUE TO MISSING DATA
   - Were outcome data available for all or nearly all participants?
   - Were reasons for missing data similar across groups?
   - Could missingness depend on true value of outcome?

6. BIAS IN MEASUREMENT OF OUTCOMES
   - Was outcome measure appropriate and unlikely to be influenced by knowledge of intervention?
   - Were outcome assessors aware of intervention status?
   - Were outcome measurement methods similar across groups?

7. BIAS IN SELECTION OF REPORTED RESULT
   - Was outcome measurement and analysis plan pre - specified?
   - Were analyses clearly reported for all planned outcomes?
   - Was outcome selection likely based on results?

BIAS LEVELS:
- Low: Study comparable to well - performed randomized trial
- Moderate: Study sound for non - randomized study but not comparable to rigorous RCT
- Serious: Study has important problems
- Critical: Study too problematic to provide useful evidence
- No information: Insufficient information to assess

Please provide your assessment in JSON format:
{{
    "overall_bias": "low|moderate|serious|critical|no_information",
    "overall_rationale": "Detailed explanation of overall assessment",
    "domains": [
        {{
            "domain": "confounding",
            "bias_level": "low|moderate|serious|critical|no_information",
            "rationale": "Detailed reasoning for this domain",
            "supporting_evidence": ["key quotes or findings from the study"],
            "confidence": 0.0 - 1.0
        }},
        {{
            "domain": "selection",
            "bias_level": "low|moderate|serious|critical|no_information",
            "rationale": "Detailed reasoning for this domain",
            "supporting_evidence": ["key quotes or findings from the study"],
            "confidence": 0.0 - 1.0
        }},
        {{
            "domain": "classification_intervention",
            "bias_level": "low|moderate|serious|critical|no_information",
            "rationale": "Detailed reasoning for this domain",
            "supporting_evidence": ["key quotes or findings from the study"],
            "confidence": 0.0 - 1.0
        }},
        {{
            "domain": "deviation_intervention",
            "bias_level": "low|moderate|serious|critical|no_information",
            "rationale": "Detailed reasoning for this domain",
            "supporting_evidence": ["key quotes or findings from the study"],
            "confidence": 0.0 - 1.0
        }},
        {{
            "domain": "missing_data",
            "bias_level": "low|moderate|serious|critical|no_information",
            "rationale": "Detailed reasoning for this domain",
            "supporting_evidence": ["key quotes or findings from the study"],
            "confidence": 0.0 - 1.0
        }},
        {{
            "domain": "measurement_outcome",
            "bias_level": "low|moderate|serious|critical|no_information",
            "rationale": "Detailed reasoning for this domain",
            "supporting_evidence": ["key quotes or findings from the study"],
            "confidence": 0.0 - 1.0
        }},
        {{
            "domain": "selection_reported_result",
            "bias_level": "low|moderate|serious|critical|no_information",
            "rationale": "Detailed reasoning for this domain",
            "supporting_evidence": ["key quotes or findings from the study"],
            "confidence": 0.0 - 1.0
        }}
    ]
}}
"""

    def _get_system_prompt(self) -> str:
        """Get system prompt for ROBINS - I assessment."""
        return """
You are an expert methodologist conducting ROBINS - I assessments for systematic reviews.
ROBINS - I is used to assess risk of bias in non - randomized studies of interventions.

Guidelines for assessment:
1. Overall risk of bias is determined by the highest risk domain
2. Consider the specific research question and context
3. Base judgments on information provided in the study
4. Be conservative - if information is unclear, lean towards higher risk ratings
5. Provide specific quotes and evidence to support your assessments
6. Consider both internal validity and external validity concerns

Key principles:
- Low risk: Study is comparable to a well - performed randomized trial
- Moderate risk: Study is sound for a non - randomized study but has limitations
- Serious risk: Study has important problems that limit reliability
- Critical risk: Study is too problematic to provide useful evidence
- No information: Insufficient information reported to make an assessment

Always provide detailed rationales with specific evidence from the study text.
Response must be valid JSON format only.
"""


# Example usage and testing
if __name__ == "__main__":
    # This would typically be used by the QualityAppraisalManager
    pass

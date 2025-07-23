"""
RoB 2 (Risk of Bias tool for randomized trials) plugin.

This plugin implements the RoB 2 tool for assessing risk of bias 
in randomized controlled trials.

Reference: Sterne et al. (2019). RoB 2: a revised tool for assessing risk of bias 
in randomised trials. BMJ, 366, l4898.
"""

from typing import Dict, List, Any
from ..quality_appraisal.plugin_architecture import (
    BaseAIQualityPlugin, 
    AssessmentDomain, 
    BiasLevel,
    QualityAssessment
)


class Rob2Plugin(BaseAIQualityPlugin):
    """RoB 2 assessment plugin for randomized controlled trials."""
    
    @property
    def tool_id(self) -> str:
        return "rob2"
    
    @property
    def tool_name(self) -> str:
        return "RoB 2 (Risk of Bias tool for randomized trials)"
    
    @property
    def applicable_study_types(self) -> List[str]:
        return [
            "randomized controlled trial",
            "rct",
            "randomized trial",
            "randomised controlled trial",
            "randomised trial",
            "clinical trial",
            "parallel group trial",
            "crossover trial",
            "cluster randomized trial"
        ]
    
    @property 
    def assessment_domains(self) -> List[AssessmentDomain]:
        return [
            AssessmentDomain.RANDOMIZATION,
            AssessmentDomain.DEVIATION_INTENDED,
            AssessmentDomain.MISSING_OUTCOME_DATA,
            AssessmentDomain.MEASUREMENT_OUTCOME_ROB2,
            AssessmentDomain.SELECTION_REPORTED_ROB2
        ]
    
    def _build_assessment_prompt(self, study: Dict[str, Any], criteria: Dict[str, Any]) -> str:
        """Build RoB 2 assessment prompt."""
        return f"""
Please conduct a RoB 2 (Risk of Bias tool for randomized trials) assessment for this study.

STUDY INFORMATION:
Title: {study.get('title', 'No title available')}
Authors: {', '.join(study.get('authors', []))}
Year: {study.get('year', 'Unknown')}
Study Design: {study.get('metadata', {}).get('study_type', 'Not specified')}
Journal: {study.get('metadata', {}).get('journal', 'Unknown')}
Trial Registration: {study.get('metadata', {}).get('trial_registration', 'Not reported')}

STUDY ABSTRACT:
{study.get('abstract', 'No abstract available')}

FULL TEXT (if available):
{study.get('full_text', 'Full text not available - base assessment on available information')}

INTERVENTION AND COMPARISON:
Intervention: {criteria.get('intervention', 'Not specified')}
Control/Comparison: {criteria.get('comparison', 'Not specified')}
Population: {criteria.get('population', 'Not specified')}
Primary Outcome: {criteria.get('outcomes', ['Not specified'])[0] if criteria.get('outcomes') else 'Not specified'}
All Outcomes: {', '.join(criteria.get('outcomes', []))}

ROB 2 ASSESSMENT DOMAINS:
Please assess each domain for risk of bias. For each domain, consider the signaling questions and provide an overall judgment.

1. BIAS ARISING FROM THE RANDOMIZATION PROCESS
   Signaling questions:
   - Was the allocation sequence random?
   - Was the allocation sequence concealed until participants were enrolled and assigned?
   - Were baseline differences between groups suggestive of problems with randomization?
   
   Consider: sequence generation, allocation concealment, baseline balance

2. BIAS DUE TO DEVIATIONS FROM INTENDED INTERVENTIONS (effect of assignment to intervention)
   Signaling questions:
   - Were participants aware of their assigned intervention during the trial?
   - Were carers and people delivering intervention aware of assigned intervention?
   - Were there deviations from intended intervention that arose because of the experimental context?
   - Were these deviations likely to have affected the outcome?
   - Were these deviations from intended intervention balanced between groups?
   - Was the analysis appropriate for the study's intended effect?
   
   Consider: blinding, protocol deviations, intention-to-treat analysis

3. BIAS DUE TO MISSING OUTCOME DATA
   Signaling questions:
   - Were data for this outcome available for all, or nearly all, participants randomized?
   - Is there evidence that result was not biased by missing outcome data?
   - Could missingness in the outcome depend on its true value?
   - Is it likely that missingness in the outcome depended on its true value?
   
   Consider: completeness of data, reasons for missing data, methods for handling missing data

4. BIAS IN MEASUREMENT OF THE OUTCOME
   Signaling questions:
   - Was the method of measuring the outcome inappropriate?
   - Could measurement or ascertainment of outcome have differed between groups?
   - Were outcome assessors aware of the intervention received by study participants?
   - Could assessment of the outcome have been influenced by knowledge of intervention received?
   
   Consider: outcome measurement methods, blinding of outcome assessors

5. BIAS IN SELECTION OF THE REPORTED RESULT
   Signaling questions:
   - Were outcome measurements/analyses clearly pre-specified?
   - Is the numerical result being assessed likely to have been selected based on the results?
   - Is the reported effect estimate likely to be selected based on the results?
   
   Consider: protocol registration, selective reporting, multiple analyses

RISK OF BIAS LEVELS:
- Low: Low risk of bias
- Some concerns: Some concerns about risk of bias  
- High: High risk of bias

OVERALL RISK OF BIAS:
The overall risk of bias is the highest level assigned to any domain.

Please provide your assessment in JSON format:
{{
    "overall_bias": "low|moderate|serious", 
    "overall_rationale": "Detailed explanation of overall assessment with reference to domain judgments",
    "domains": [
        {{
            "domain": "randomization",
            "bias_level": "low|moderate|serious",
            "rationale": "Detailed reasoning addressing signaling questions",
            "supporting_evidence": ["specific quotes or findings from study"],
            "confidence": 0.0-1.0
        }},
        {{
            "domain": "deviation_intended", 
            "bias_level": "low|moderate|serious",
            "rationale": "Detailed reasoning addressing signaling questions",
            "supporting_evidence": ["specific quotes or findings from study"],
            "confidence": 0.0-1.0
        }},
        {{
            "domain": "missing_outcome_data",
            "bias_level": "low|moderate|serious", 
            "rationale": "Detailed reasoning addressing signaling questions",
            "supporting_evidence": ["specific quotes or findings from study"],
            "confidence": 0.0-1.0
        }},
        {{
            "domain": "measurement_outcome_rob2",
            "bias_level": "low|moderate|serious",
            "rationale": "Detailed reasoning addressing signaling questions", 
            "supporting_evidence": ["specific quotes or findings from study"],
            "confidence": 0.0-1.0
        }},
        {{
            "domain": "selection_reported_rob2",
            "bias_level": "low|moderate|serious",
            "rationale": "Detailed reasoning addressing signaling questions",
            "supporting_evidence": ["specific quotes or findings from study"],
            "confidence": 0.0-1.0
        }}
    ]
}}

Note: Use "moderate" for RoB 2's "some concerns" category, and "serious" for "high risk".
"""
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for RoB 2 assessment."""
        return """
You are an expert methodologist conducting RoB 2 assessments for systematic reviews.
RoB 2 is used to assess risk of bias in randomized controlled trials.

Guidelines for assessment:
1. Address each signaling question systematically
2. Overall risk of bias is determined by the highest risk domain
3. Use the three-level scale: Low risk, Some concerns (moderate), High risk (serious)
4. Base assessments on reported information in the study
5. Consider the specific outcome being assessed
6. Provide specific evidence from the study text to support judgments

Key principles:
- Low risk: The study is judged to be at low risk of bias for all domains
- Some concerns: The study raises some concerns in at least one domain, but not high risk
- High risk: The study is judged to be at high risk of bias in at least one domain, or has serious concerns across multiple domains

Focus on:
- Quality of randomization process and allocation concealment
- Blinding and adherence to intended interventions  
- Completeness of outcome data and appropriate analysis
- Appropriate outcome measurement and assessment
- Evidence of selective outcome reporting

Always provide detailed rationales with specific evidence from the study.
Map RoB 2 categories to response format: Low→low, Some concerns→moderate, High→serious.
Response must be valid JSON format only.
"""


# Example usage and testing
if __name__ == "__main__":
    # This would typically be used by the QualityAppraisalManager
    pass

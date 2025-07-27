"""
Writer Agent (WA) for the Eunice Research Platform.

This agent transforms synthesized data into structured, scholarly manuscripts
following PRISMA guidelines and PhD-level literature review standards.

Based on the Literature Review Agents Design Specification.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal

from pydantic import BaseModel, Field
from ..base_agent import BaseAgent
from ...config.config_manager import ConfigManager


class DraftRequest(BaseModel):
    """Draft request data model."""
    lit_review_id: str = Field(description="Literature review identifier")
    format: Literal["markdown", "latex", "docx"] = Field(default="markdown", description="Output format")
    style: Literal["apa", "vancouver"] = Field(default="apa", description="Citation style")
    sections: List[str] = Field(default_factory=lambda: ["introduction", "methods", "results", "discussion"], description="Sections to include")


class DraftResponse(BaseModel):
    """Draft response data model."""
    manuscript_text: str = Field(description="Generated manuscript text")
    references: List[Dict[str, Any]] = Field(description="Reference list")
    word_count: int = Field(description="Word count")
    generated_at: datetime = Field(default_factory=datetime.now)


class ManuscriptSection(BaseModel):
    """Manuscript section data model."""
    section_name: str = Field(description="Section name")
    content: str = Field(description="Section content")
    subsections: List['ManuscriptSection'] = Field(default_factory=list, description="Subsections")


class WriterAgent(BaseAgent):
    """
    Writer Agent for manuscript generation and formatting.
    
    Core Responsibilities:
    - Draft Introduction, Methods, Results, and Discussion sections
    - Integrate PRISMA flowcharts and evidence tables
    - Ensure proper citation formatting (APA, Vancouver, etc.)
    - Validate citations against the Literature Database
    - Support PRISMA-to-Thesis conversion
    """

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the Writer Agent.

        Args:
            config_manager: Configuration manager instance
        """
        super().__init__("writer", config_manager)
        self.logger = logging.getLogger(__name__)
        
        # Initialize manuscript storage
        self.manuscripts: Dict[str, DraftResponse] = {}
        self.templates: Dict[str, str] = self._load_templates()

    def _load_templates(self) -> Dict[str, str]:
        """Load manuscript templates."""
        # Basic templates - in production these would be loaded from files
        return {
            "introduction": """# Introduction

## Background
{background_text}

## Objectives
{objectives_text}

## Research Questions
{research_questions}
""",
            "methods": """# Methods

## Protocol Registration
This systematic review was conducted following PRISMA 2020 guidelines.

## Search Strategy
{search_strategy}

## Study Selection
{selection_criteria}

## Data Extraction
{extraction_methods}

## Quality Assessment
{quality_assessment}

## Statistical Analysis
{statistical_methods}
""",
            "results": """# Results

## Study Selection
{prisma_flowchart}

## Study Characteristics
{study_characteristics}

## Risk of Bias Assessment
{bias_assessment}

## Synthesis of Results
{synthesis_results}

## Meta-Analysis
{meta_analysis_results}
""",
            "discussion": """# Discussion

## Summary of Evidence
{evidence_summary}

## Implications
{implications}

## Limitations
{limitations}

## Conclusions
{conclusions}
"""
        }

    async def draft_manuscript(self, draft_request: DraftRequest, context_data: Dict[str, Any]) -> DraftResponse:
        """
        Generate a manuscript draft.
        
        Args:
            draft_request: Draft generation parameters
            context_data: Context data for manuscript generation
            
        Returns:
            Generated manuscript draft
        """
        self.logger.info(f"Generating manuscript for review {draft_request.lit_review_id}")
        
        # Generate sections
        sections = []
        for section_name in draft_request.sections:
            section_content = await self._generate_section(section_name, context_data)
            sections.append(section_content)
        
        # Combine sections
        manuscript_text = "\n\n".join(sections)
        
        # Generate references
        references = self._generate_references(context_data.get('studies', []), draft_request.style)
        
        # Add references section
        ref_section = self._format_references_section(references, draft_request.style)
        manuscript_text += f"\n\n{ref_section}"
        
        # Calculate word count
        word_count = len(manuscript_text.split())
        
        # Create draft response
        draft_response = DraftResponse(
            manuscript_text=manuscript_text,
            references=references,
            word_count=word_count
        )
        
        # Store manuscript
        self.manuscripts[draft_request.lit_review_id] = draft_response
        
        self.logger.info(f"Generated {word_count} word manuscript for review {draft_request.lit_review_id}")
        
        return draft_response

    async def _generate_section(self, section_name: str, context_data: Dict[str, Any]) -> str:
        """
        Generate a specific manuscript section.
        
        Args:
            section_name: Name of the section to generate
            context_data: Context data for generation
            
        Returns:
            Generated section content
        """
        template = self.templates.get(section_name, "# {section_name}\n\n[Content to be generated]")
        
        if section_name == "introduction":
            return template.format(
                background_text=context_data.get('background', 'Background information to be added.'),
                objectives_text=context_data.get('objectives', 'Objectives to be defined.'),
                research_questions=context_data.get('research_questions', 'Research questions to be formulated.')
            )
        
        elif section_name == "methods":
            return template.format(
                search_strategy=self._format_search_strategy(context_data.get('search_data', {})),
                selection_criteria=self._format_selection_criteria(context_data.get('criteria', [])),
                extraction_methods=context_data.get('extraction_methods', 'Data extraction methods to be described.'),
                quality_assessment=context_data.get('quality_assessment', 'Quality assessment methods to be described.'),
                statistical_methods=context_data.get('statistical_methods', 'Statistical analysis methods to be described.')
            )
        
        elif section_name == "results":
            return template.format(
                prisma_flowchart=self._format_prisma_flowchart(context_data.get('prisma_data', {})),
                study_characteristics=self._format_study_characteristics(context_data.get('studies', [])),
                bias_assessment=context_data.get('bias_assessment', 'Risk of bias assessment results to be added.'),
                synthesis_results=context_data.get('narrative_synthesis', 'Synthesis results to be added.'),
                meta_analysis_results=self._format_meta_analysis_results(context_data.get('meta_results', []))
            )
        
        elif section_name == "discussion":
            return template.format(
                evidence_summary=context_data.get('evidence_summary', 'Evidence summary to be added.'),
                implications=context_data.get('implications', 'Implications to be discussed.'),
                limitations=context_data.get('limitations', 'Limitations to be acknowledged.'),
                conclusions=context_data.get('conclusions', 'Conclusions to be drawn.')
            )
        
        else:
            return f"# {section_name.title()}\n\nContent for {section_name} section to be generated."

    def _format_search_strategy(self, search_data: Dict[str, Any]) -> str:
        """Format search strategy description."""
        if not search_data:
            return "Search strategy details to be added."
        
        strategy_parts = []
        
        # Databases searched
        sources = search_data.get('sources', [])
        if sources:
            strategy_parts.append(f"The following databases were searched: {', '.join(sources)}")
        
        # Search terms
        query = search_data.get('query', '')
        if query:
            strategy_parts.append(f"Search terms: {query}")
        
        # Date range
        filters = search_data.get('filters', {})
        if 'date_range' in filters:
            date_range = filters['date_range']
            strategy_parts.append(f"Date range: {date_range.get('start', '')} to {date_range.get('end', '')}")
        
        return "\n\n".join(strategy_parts) if strategy_parts else "Search strategy details to be added."

    def _format_selection_criteria(self, criteria: List[Dict[str, Any]]) -> str:
        """Format study selection criteria."""
        if not criteria:
            return "Selection criteria to be defined."
        
        inclusion_criteria = []
        exclusion_criteria = []
        
        for criterion in criteria:
            if criterion.get('type') == 'include':
                inclusion_criteria.append(f"- {criterion.get('description', '')}")
            else:
                exclusion_criteria.append(f"- {criterion.get('description', '')}")
        
        result = []
        if inclusion_criteria:
            result.append("**Inclusion Criteria:**")
            result.extend(inclusion_criteria)
        
        if exclusion_criteria:
            result.append("\n**Exclusion Criteria:**")
            result.extend(exclusion_criteria)
        
        return "\n".join(result) if result else "Selection criteria to be defined."

    def _format_prisma_flowchart(self, prisma_data: Dict[str, Any]) -> str:
        """Format PRISMA flowchart description."""
        if not prisma_data:
            return "PRISMA flowchart to be inserted here."
        
        flowchart_text = "**PRISMA Flow Diagram**\n\n"
        
        # Identification
        if 'identification' in prisma_data:
            records_identified = prisma_data['identification'].get('records_identified', 0)
            flowchart_text += f"Records identified through database searching: {records_identified}\n"
        
        # Screening
        if 'screening' in prisma_data:
            screened = prisma_data['screening'].get('records_screened', 0)
            excluded = prisma_data['screening'].get('records_excluded', 0)
            flowchart_text += f"Records screened: {screened}\n"
            flowchart_text += f"Records excluded: {excluded}\n"
        
        # Eligibility
        if 'eligibility' in prisma_data:
            assessed = prisma_data['eligibility'].get('full_text_assessed', 0)
            excluded = prisma_data['eligibility'].get('full_text_excluded', 0)
            flowchart_text += f"Full-text articles assessed for eligibility: {assessed}\n"
            flowchart_text += f"Full-text articles excluded: {excluded}\n"
        
        # Included
        if 'included' in prisma_data:
            included = prisma_data['included'].get('studies_included', 0)
            flowchart_text += f"Studies included in qualitative synthesis: {included}\n"
        
        return flowchart_text

    def _format_study_characteristics(self, studies: List[Dict[str, Any]]) -> str:
        """Format study characteristics table."""
        if not studies:
            return "Study characteristics table to be added."
        
        characteristics = []
        characteristics.append("| Study | Year | Design | Participants | Intervention | Outcome |")
        characteristics.append("|-------|------|--------|-------------|--------------|----------|")
        
        for study in studies[:10]:  # Limit to first 10 studies for readability
            author = study.get('authors', ['Unknown'])[0] if study.get('authors') else 'Unknown'
            year = study.get('year', 'Unknown')
            design = study.get('study_design', 'Not specified')
            participants = study.get('participants', 'Not specified')
            intervention = study.get('intervention', 'Not specified')
            outcome = study.get('primary_outcome', 'Not specified')
            
            characteristics.append(f"| {author} | {year} | {design} | {participants} | {intervention} | {outcome} |")
        
        if len(studies) > 10:
            characteristics.append(f"| ... | ... | ... | ... | ... | ... |")
            characteristics.append(f"| Total: {len(studies)} studies | | | | | |")
        
        return "\n".join(characteristics)

    def _format_meta_analysis_results(self, meta_results: List[Dict[str, Any]]) -> str:
        """Format meta-analysis results."""
        if not meta_results:
            return "Meta-analysis results to be added."
        
        results_text = []
        
        for result in meta_results:
            outcome_name = result.get('outcome_name', 'Unknown outcome')
            pooled_effect = result.get('pooled_effect', 0.0)
            ci = result.get('ci', [0.0, 0.0])
            studies = result.get('studies_included', 0)
            participants = result.get('total_participants', 0)
            
            results_text.append(
                f"**{outcome_name}**: Pooled effect size = {pooled_effect:.2f} "
                f"(95% CI: {ci[0]:.2f} to {ci[1]:.2f}), {studies} studies, {participants} participants"
            )
        
        return "\n\n".join(results_text)

    def _generate_references(self, studies: List[Dict[str, Any]], style: str) -> List[Dict[str, Any]]:
        """Generate reference list from studies."""
        references = []
        
        for i, study in enumerate(studies, 1):
            ref = {
                'id': i,
                'authors': study.get('authors', ['Unknown']),
                'title': study.get('title', 'Unknown title'),
                'journal': study.get('journal', 'Unknown journal'),
                'year': study.get('year', 'Unknown'),
                'doi': study.get('doi', ''),
                'formatted': self._format_reference(study, style)
            }
            references.append(ref)
        
        return references

    def _format_reference(self, study: Dict[str, Any], style: str) -> str:
        """Format a single reference according to citation style."""
        authors = study.get('authors', ['Unknown'])
        title = study.get('title', 'Unknown title')
        journal = study.get('journal', 'Unknown journal')
        year = study.get('year', 'Unknown')
        doi = study.get('doi', '')
        
        if style == "apa":
            # APA format
            author_string = ', '.join(authors[:3])  # Limit to first 3 authors
            if len(authors) > 3:
                author_string += ', et al.'
            
            ref = f"{author_string} ({year}). {title}. *{journal}*."
            if doi:
                ref += f" https://doi.org/{doi}"
            
            return ref
        
        elif style == "vancouver":
            # Vancouver format
            author_string = ', '.join([f"{author}" for author in authors[:6]])  # Limit to first 6
            if len(authors) > 6:
                author_string += ', et al'
            
            return f"{author_string}. {title}. {journal}. {year}."
        
        else:
            # Default format
            return f"{', '.join(authors)} ({year}). {title}. {journal}."

    def _format_references_section(self, references: List[Dict[str, Any]], style: str) -> str:
        """Format the references section."""
        ref_section = ["# References", ""]
        
        for ref in references:
            if style == "vancouver":
                ref_section.append(f"{ref['id']}. {ref['formatted']}")
            else:
                ref_section.append(ref['formatted'])
        
        return "\n".join(ref_section)

    async def revise_section(
        self, 
        lit_review_id: str, 
        section_name: str, 
        revised_content: str
    ) -> bool:
        """
        Revise a specific section of a manuscript.
        
        Args:
            lit_review_id: Literature review identifier
            section_name: Name of section to revise
            revised_content: New content for the section
            
        Returns:
            Success status
        """
        if lit_review_id not in self.manuscripts:
            return False
        
        manuscript = self.manuscripts[lit_review_id]
        
        # Simple section replacement (in production, would use more sophisticated parsing)
        current_text = manuscript.manuscript_text
        
        # Find section and replace content
        section_header = f"# {section_name.title()}"
        sections = current_text.split("# ")
        
        for i, section in enumerate(sections):
            if section.startswith(section_name.title()):
                sections[i] = f"{section_name.title()}\n\n{revised_content}"
                break
        
        # Reconstruct manuscript
        manuscript.manuscript_text = "# ".join(sections)
        manuscript.word_count = len(manuscript.manuscript_text.split())
        
        self.logger.info(f"Revised {section_name} section for review {lit_review_id}")
        
        return True

    async def export_manuscript(
        self, 
        lit_review_id: str, 
        format: Literal["markdown", "latex", "docx"] = "markdown"
    ) -> bytes:
        """
        Export manuscript in specified format.
        
        Args:
            lit_review_id: Literature review identifier
            format: Export format
            
        Returns:
            Exported manuscript as bytes
        """
        if lit_review_id not in self.manuscripts:
            raise ValueError(f"Manuscript not found for review {lit_review_id}")
        
        manuscript = self.manuscripts[lit_review_id]
        
        if format == "markdown":
            return manuscript.manuscript_text.encode('utf-8')
        
        elif format == "latex":
            # Convert markdown to LaTeX (simplified)
            latex_content = self._convert_to_latex(manuscript.manuscript_text)
            return latex_content.encode('utf-8')
        
        elif format == "docx":
            # In production, would use python-docx or similar
            # For now, return markdown content
            return manuscript.manuscript_text.encode('utf-8')
        
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def _convert_to_latex(self, markdown_text: str) -> str:
        """Convert markdown to LaTeX (simplified conversion)."""
        latex_text = markdown_text
        
        # Basic conversions
        latex_text = latex_text.replace("# ", "\\section{").replace("\n", "}\n")
        latex_text = latex_text.replace("## ", "\\subsection{").replace("\n", "}\n")
        latex_text = latex_text.replace("**", "\\textbf{").replace("**", "}")
        latex_text = latex_text.replace("*", "\\textit{").replace("*", "}")
        
        # Add document structure
        latex_document = f"""\\documentclass{{article}}
\\usepackage{{amsmath}}
\\usepackage{{graphicx}}
\\usepackage{{url}}

\\begin{{document}}

{latex_text}

\\end{{document}}"""
        
        return latex_document

    async def handle_action(self, action) -> Dict[str, Any]:
        """
        Handle research actions for manuscript writing.
        
        Args:
            action: Research action to handle
            
        Returns:
            Action result
        """
        try:
            action_type = getattr(action, 'action_type', getattr(action, 'type', 'unknown'))
            parameters = getattr(action, 'parameters', getattr(action, 'data', {}))
            
            if action_type == "draft_manuscript":
                draft_request = DraftRequest(**parameters.get('draft_request', {}))
                context_data = parameters.get('context_data', {})
                
                draft_response = await self.draft_manuscript(draft_request, context_data)
                
                return {
                    'status': 'success',
                    'agent': self.agent_id,
                    'action_type': action_type,
                    'result': draft_response.dict(),
                    'timestamp': datetime.now().isoformat()
                }
            
            elif action_type == "revise_section":
                success = await self.revise_section(
                    parameters.get('lit_review_id', ''),
                    parameters.get('section_name', ''),
                    parameters.get('revised_content', '')
                )
                
                return {
                    'status': 'success' if success else 'error',
                    'agent': self.agent_id,
                    'action_type': action_type,
                    'result': {'revised': success},
                    'timestamp': datetime.now().isoformat()
                }
            
            elif action_type == "export_manuscript":
                manuscript_bytes = await self.export_manuscript(
                    parameters.get('lit_review_id', ''),
                    parameters.get('format', 'markdown')
                )
                
                return {
                    'status': 'success',
                    'agent': self.agent_id,
                    'action_type': action_type,
                    'result': {
                        'size_bytes': len(manuscript_bytes),
                        'format': parameters.get('format', 'markdown')
                    },
                    'timestamp': datetime.now().isoformat()
                }
            
            else:
                return {
                    'status': 'error',
                    'agent': self.agent_id,
                    'action_type': action_type,
                    'error': f"Unsupported action type: {action_type}",
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Error handling action: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'agent': self.agent_id,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    async def get_health_status(self) -> Dict[str, Any]:
        """Get agent health status."""
        return {
            'agent': self.agent_id,
            'status': 'healthy',
            'manuscripts_stored': len(self.manuscripts),
            'templates_loaded': len(self.templates),
            'timestamp': datetime.now().isoformat()
        }

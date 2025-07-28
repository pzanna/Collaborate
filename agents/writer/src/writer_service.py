"""
Writer Agent Service for Eunice Research Platform.

This module provides a containerized Writer Agent that specializes in:
- Manuscript generation and academic writing
- Citation formatting and bibliography management
- Document template processing and export
- Integration with MCP protocol for task coordination
"""

import asyncio
import json
import logging
import re
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Literal, Union
from io import BytesIO

import aiohttp
import uvicorn
import websockets
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from jinja2 import Template

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class ManuscriptSection:
    """Manuscript section data model."""
    section_name: str
    content: str
    subsections: List['ManuscriptSection'] = field(default_factory=list)
    word_count: int = 0
    references: List[str] = field(default_factory=list)


@dataclass
class Reference:
    """Reference data model."""
    id: str
    authors: List[str]
    title: str
    journal: str = ""
    year: int = 0
    volume: str = ""
    issue: str = ""
    pages: str = ""
    doi: str = ""
    pmid: str = ""
    url: str = ""


@dataclass
class ManuscriptDraft:
    """Complete manuscript draft data model."""
    manuscript_id: str
    title: str
    authors: List[str]
    sections: List[ManuscriptSection]
    references: List[Reference]
    metadata: Dict[str, Any]
    format: str
    word_count: int
    generated_at: datetime = field(default_factory=datetime.now)


class WriterService:
    """
    Writer Service for manuscript generation and formatting.
    
    Handles academic writing, citation management, and document export
    with integration to MCP protocol.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Writer Service."""
        self.config = config
        self.agent_id = "writer"
        self.agent_type = "writer"
        
        # Service configuration
        self.service_host = config.get("service_host", "0.0.0.0")
        self.service_port = config.get("service_port", 8006)
        self.mcp_server_url = config.get("mcp_server_url", "ws://mcp-server:9000")
        
        # Writing configuration
        self.output_formats = config.get("output_formats", ["markdown", "latex", "docx"])
        self.citation_styles = config.get("citation_styles", ["apa", "vancouver"])
        self.default_sections = ["introduction", "methods", "results", "discussion"]
        
        # MCP connection
        self.websocket = None
        self.mcp_connected = False
        
        # HTTP session for API calls
        self.session = None
        
        # Task processing queue
        self.task_queue = asyncio.Queue()
        
        # Document templates
        self.templates = self._load_templates()
        
        logger.info(f"Writer Service initialized on port {self.service_port}")
    
    def _load_templates(self) -> Dict[str, Template]:
        """Load document templates."""
        templates = {}
        
        # Basic manuscript template
        manuscript_template = """
# {{ title }}

{% if authors %}
**Authors**: {{ authors | join(', ') }}
{% endif %}

{% if abstract %}
## Abstract

{{ abstract }}
{% endif %}

{% for section in sections %}
## {{ section.section_name | title }}

{{ section.content }}

{% if section.subsections %}
{% for subsection in section.subsections %}
### {{ subsection.section_name | title }}

{{ subsection.content }}

{% endfor %}
{% endif %}

{% endfor %}

{% if references %}
## References

{% for ref in references %}
{{ loop.index }}. {{ ref.authors | join(', ') }} ({{ ref.year }}). {{ ref.title }}. {% if ref.journal %}*{{ ref.journal }}*{% endif %}{% if ref.volume %}, {{ ref.volume }}{% endif %}{% if ref.issue %}({{ ref.issue }}){% endif %}{% if ref.pages %}, {{ ref.pages }}{% endif %}. {% if ref.doi %}https://doi.org/{{ ref.doi }}{% endif %}

{% endfor %}
{% endif %}
"""
        
        templates['manuscript'] = Template(manuscript_template)
        
        # Literature review template
        lit_review_template = """
# {{ title }}: A Systematic Literature Review

{% if authors %}
**Authors**: {{ authors | join(', ') }}
{% endif %}

## Abstract

### Background
{{ background }}

### Objective
{{ objective }}

### Methods
{{ methods_summary }}

### Results
{{ results_summary }}

### Conclusions
{{ conclusions }}

## Introduction

{{ introduction }}

## Methods

### Search Strategy
{{ search_strategy }}

### Inclusion and Exclusion Criteria
{{ inclusion_criteria }}

### Data Extraction
{{ data_extraction }}

### Quality Assessment
{{ quality_assessment }}

## Results

### Study Selection
{{ study_selection }}

### Study Characteristics
{{ study_characteristics }}

### Evidence Synthesis
{{ evidence_synthesis }}

{% if meta_analysis %}
### Meta-Analysis Results
{{ meta_analysis }}
{% endif %}

## Discussion

### Summary of Evidence
{{ evidence_summary }}

### Strengths and Limitations
{{ limitations }}

### Implications for Practice
{{ implications }}

### Future Research
{{ future_research }}

## Conclusions

{{ conclusions_detailed }}

## References

{% for ref in references %}
{{ loop.index }}. {{ ref.authors | join(', ') }} ({{ ref.year }}). {{ ref.title }}. {% if ref.journal %}*{{ ref.journal }}*{% endif %}{% if ref.volume %}, {{ ref.volume }}{% endif %}{% if ref.issue %}({{ ref.issue }}){% endif %}{% if ref.pages %}, {{ ref.pages }}{% endif %}. {% if ref.doi %}https://doi.org/{{ ref.doi }}{% endif %}

{% endfor %}
"""
        
        templates['literature_review'] = Template(lit_review_template)
        
        return templates
    
    async def start(self):
        """Start the Writer Service."""
        try:
            # Initialize HTTP session
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={'User-Agent': 'Eunice-Research-Platform/1.0'}
            )
            
            # Connect to MCP server
            await self._connect_to_mcp_server()
            
            # Start task processing
            asyncio.create_task(self._process_task_queue())
            
            logger.info("Writer Service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Writer Service: {e}")
            raise
    
    async def stop(self):
        """Stop the Writer Service."""
        try:
            # Close HTTP session
            if self.session:
                await self.session.close()
            
            # Close MCP connection
            if self.websocket:
                await self.websocket.close()
            
            logger.info("Writer Service stopped")
            
        except Exception as e:
            logger.error(f"Error stopping Writer Service: {e}")
    
    async def _connect_to_mcp_server(self):
        """Connect to MCP server."""
        max_retries = 10
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Connecting to MCP server at {self.mcp_server_url} (attempt {attempt + 1})")
                
                self.websocket = await websockets.connect(
                    self.mcp_server_url,
                    ping_interval=30,
                    ping_timeout=10
                )
                
                # Register with MCP server
                await self._register_with_mcp_server()
                
                # Start message handler
                asyncio.create_task(self._handle_mcp_messages())
                
                self.mcp_connected = True
                logger.info("Successfully connected to MCP server")
                return
                
            except Exception as e:
                logger.warning(f"Failed to connect to MCP server (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error("Failed to connect to MCP server after all retries")
                    raise
    
    async def _register_with_mcp_server(self):
        """Register this agent with the MCP server."""
        capabilities = [
            "manuscript_generation",
            "academic_writing",
            "citation_formatting",
            "bibliography_management",
            "document_templates",
            "export_formats",
            "prisma_flowcharts",
            "evidence_tables",
            "literature_review_writing",
            "systematic_review_writing"
        ]
        
        registration_message = {
            "type": "register",
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": capabilities,
            "service_info": {
                "host": self.service_host,
                "port": self.service_port,
                "health_endpoint": f"http://{self.service_host}:{self.service_port}/health"
            }
        }
        
        if self.websocket:
            await self.websocket.send(json.dumps(registration_message))
        logger.info(f"Registered with MCP server: {len(capabilities)} capabilities")
    
    async def _handle_mcp_messages(self):
        """Handle incoming MCP messages."""
        try:
            while self.websocket:
                message = await self.websocket.recv()
                data = json.loads(message)
                
                if data.get("type") == "task":
                    await self.task_queue.put(data)
                elif data.get("type") == "ping":
                    await self.websocket.send(json.dumps({"type": "pong"}))
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("MCP server connection closed")
            self.mcp_connected = False
        except Exception as e:
            logger.error(f"Error handling MCP messages: {e}")
            self.mcp_connected = False
    
    async def _process_task_queue(self):
        """Process tasks from the MCP queue."""
        while True:
            try:
                # Get task from queue
                task_data = await self.task_queue.get()
                
                # Process the task
                result = await self._process_writer_task(task_data)
                
                # Send result back to MCP server
                if self.websocket and self.mcp_connected:
                    response = {
                        "type": "task_result",
                        "task_id": task_data.get("task_id"),
                        "agent_id": self.agent_id,
                        "result": result
                    }
                    await self.websocket.send(json.dumps(response))
                
                # Mark task as done
                self.task_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error processing task: {e}")
                await asyncio.sleep(1)
    
    async def _process_writer_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a writer task."""
        try:
            action = task_data.get("action", "")
            payload = task_data.get("payload", {})
            
            # Route to appropriate handler
            if action == "generate_manuscript":
                return await self._handle_generate_manuscript(payload)
            elif action == "format_citations":
                return await self._handle_format_citations(payload)
            elif action == "generate_bibliography":
                return await self._handle_generate_bibliography(payload)
            elif action == "export_document":
                return await self._handle_export_document(payload)
            elif action == "generate_literature_review":
                return await self._handle_generate_literature_review(payload)
            else:
                return {
                    "status": "failed",
                    "error": f"Unknown action: {action}",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error processing writer task: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_generate_manuscript(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle manuscript generation request."""
        try:
            title = payload.get("title", "Untitled Manuscript")
            authors = payload.get("authors", [])
            sections_data = payload.get("sections", [])
            references_data = payload.get("references", [])
            format = payload.get("format", "markdown")
            template_type = payload.get("template", "manuscript")
            
            # Create manuscript sections
            sections = []
            for section_data in sections_data:
                section = ManuscriptSection(
                    section_name=section_data.get("name", ""),
                    content=section_data.get("content", ""),
                    word_count=len(section_data.get("content", "").split())
                )
                
                # Add subsections if provided
                for subsection_data in section_data.get("subsections", []):
                    subsection = ManuscriptSection(
                        section_name=subsection_data.get("name", ""),
                        content=subsection_data.get("content", ""),
                        word_count=len(subsection_data.get("content", "").split())
                    )
                    section.subsections.append(subsection)
                
                sections.append(section)
            
            # Create references
            references = []
            for ref_data in references_data:
                reference = Reference(
                    id=ref_data.get("id", str(uuid.uuid4())),
                    authors=ref_data.get("authors", []),
                    title=ref_data.get("title", ""),
                    journal=ref_data.get("journal", ""),
                    year=ref_data.get("year", 0),
                    volume=ref_data.get("volume", ""),
                    issue=ref_data.get("issue", ""),
                    pages=ref_data.get("pages", ""),
                    doi=ref_data.get("doi", ""),
                    pmid=ref_data.get("pmid", ""),
                    url=ref_data.get("url", "")
                )
                references.append(reference)
            
            # Generate manuscript
            manuscript = await self._generate_manuscript(
                title=title,
                authors=authors,
                sections=sections,
                references=references,
                format=format,
                template_type=template_type
            )
            
            return {
                "status": "completed",
                "manuscript": {
                    "manuscript_id": manuscript.manuscript_id,
                    "title": manuscript.title,
                    "content": await self._render_manuscript(manuscript),
                    "word_count": manuscript.word_count,
                    "format": manuscript.format,
                    "sections_count": len(manuscript.sections),
                    "references_count": len(manuscript.references),
                    "generated_at": manuscript.generated_at.isoformat()
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to handle generate manuscript: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_format_citations(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle citation formatting request."""
        try:
            citations = payload.get("citations", [])
            style = payload.get("style", "apa")
            
            formatted_citations = []
            for citation in citations:
                formatted = await self._format_citation(citation, style)
                formatted_citations.append(formatted)
            
            return {
                "status": "completed",
                "formatted_citations": formatted_citations,
                "style": style,
                "count": len(formatted_citations),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to handle format citations: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_generate_bibliography(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle bibliography generation request."""
        try:
            references = payload.get("references", [])
            style = payload.get("style", "apa")
            
            bibliography = await self._generate_bibliography(references, style)
            
            return {
                "status": "completed",
                "bibliography": bibliography,
                "style": style,
                "references_count": len(references),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to handle generate bibliography: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_export_document(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle document export request."""
        try:
            content = payload.get("content", "")
            format = payload.get("format", "pdf")
            title = payload.get("title", "Document")
            
            exported_content = await self._export_document(content, format, title)
            
            return {
                "status": "completed",
                "exported_document": {
                    "format": format,
                    "title": title,
                    "content": exported_content,
                    "size": len(exported_content) if isinstance(exported_content, str) else len(exported_content.getvalue())
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to handle export document: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_generate_literature_review(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle literature review generation request."""
        try:
            title = payload.get("title", "Literature Review")
            research_question = payload.get("research_question", "")
            studies = payload.get("studies", [])
            synthesis_data = payload.get("synthesis_data", {})
            meta_analysis = payload.get("meta_analysis", {})
            
            literature_review = await self._generate_literature_review(
                title=title,
                research_question=research_question,
                studies=studies,
                synthesis_data=synthesis_data,
                meta_analysis=meta_analysis
            )
            
            return {
                "status": "completed",
                "literature_review": literature_review,
                "studies_included": len(studies),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to handle generate literature review: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _generate_manuscript(self, title: str, authors: List[str], sections: List[ManuscriptSection], 
                                 references: List[Reference], format: str, template_type: str) -> ManuscriptDraft:
        """Generate a complete manuscript draft."""
        try:
            manuscript_id = str(uuid.uuid4())
            
            # Calculate total word count
            total_words = sum(section.word_count for section in sections)
            
            # Create manuscript metadata
            metadata = {
                "template_type": template_type,
                "creation_date": datetime.now().isoformat(),
                "citation_style": "apa",  # Default
                "language": "en"
            }
            
            manuscript = ManuscriptDraft(
                manuscript_id=manuscript_id,
                title=title,
                authors=authors,
                sections=sections,
                references=references,
                metadata=metadata,
                format=format,
                word_count=total_words
            )
            
            return manuscript
            
        except Exception as e:
            logger.error(f"Error generating manuscript: {e}")
            raise
    
    async def _render_manuscript(self, manuscript: ManuscriptDraft) -> str:
        """Render manuscript using appropriate template."""
        try:
            template_type = manuscript.metadata.get("template_type", "manuscript")
            template = self.templates.get(template_type, self.templates["manuscript"])
            
            # Prepare template context
            context = {
                "title": manuscript.title,
                "authors": manuscript.authors,
                "sections": manuscript.sections,
                "references": manuscript.references,
                "word_count": manuscript.word_count,
                "generated_at": manuscript.generated_at.strftime("%Y-%m-%d")
            }
            
            # Render template
            rendered_content = template.render(**context)
            
            return rendered_content
            
        except Exception as e:
            logger.error(f"Error rendering manuscript: {e}")
            return f"Error rendering manuscript: {str(e)}"
    
    async def _format_citation(self, citation: Dict[str, Any], style: str) -> str:
        """Format a single citation according to the specified style."""
        try:
            authors = citation.get("authors", [])
            title = citation.get("title", "")
            journal = citation.get("journal", "")
            year = citation.get("year", "")
            volume = citation.get("volume", "")
            issue = citation.get("issue", "")
            pages = citation.get("pages", "")
            doi = citation.get("doi", "")
            
            if style.lower() == "apa":
                # APA format
                author_str = ", ".join(authors[:3])  # Limit to first 3 authors
                if len(authors) > 3:
                    author_str += ", et al."
                
                formatted = f"{author_str} ({year}). {title}."
                if journal:
                    formatted += f" *{journal}*"
                if volume:
                    formatted += f", {volume}"
                if issue:
                    formatted += f"({issue})"
                if pages:
                    formatted += f", {pages}"
                if doi:
                    formatted += f". https://doi.org/{doi}"
                
            elif style.lower() == "vancouver":
                # Vancouver format
                author_str = ", ".join(authors)
                formatted = f"{author_str}. {title}. {journal}. {year}"
                if volume:
                    formatted += f";{volume}"
                if issue:
                    formatted += f"({issue})"
                if pages:
                    formatted += f":{pages}"
                formatted += "."
                
            else:
                # Default format
                formatted = f"{', '.join(authors)} ({year}). {title}. {journal}."
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error formatting citation: {e}")
            return f"Error formatting citation: {str(e)}"
    
    async def _generate_bibliography(self, references: List[Dict[str, Any]], style: str) -> str:
        """Generate a formatted bibliography."""
        try:
            bibliography_entries = []
            
            for ref in references:
                formatted_citation = await self._format_citation(ref, style)
                bibliography_entries.append(formatted_citation)
            
            # Sort alphabetically by first author
            bibliography_entries.sort()
            
            # Create bibliography
            bibliography = "# References\n\n"
            for i, entry in enumerate(bibliography_entries, 1):
                bibliography += f"{i}. {entry}\n\n"
            
            return bibliography
            
        except Exception as e:
            logger.error(f"Error generating bibliography: {e}")
            return f"Error generating bibliography: {str(e)}"
    
    async def _export_document(self, content: str, format: str, title: str) -> Union[str, BytesIO]:
        """Export document to specified format."""
        try:
            if format.lower() == "markdown":
                return content
            
            elif format.lower() == "html":
                # Convert markdown to HTML (simplified)
                html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #666; }}
        blockquote {{ border-left: 3px solid #ccc; padding-left: 20px; }}
    </style>
</head>
<body>
{self._markdown_to_html(content)}
</body>
</html>
"""
                return html_content
            
            elif format.lower() == "latex":
                # Convert to LaTeX (simplified)
                latex_content = f"""
\\documentclass{{article}}
\\usepackage[utf8]{{inputenc}}
\\title{{{title}}}
\\author{{Generated by Eunice}}
\\date{{\\today}}

\\begin{{document}}
\\maketitle

{self._markdown_to_latex(content)}

\\end{{document}}
"""
                return latex_content
            
            else:
                return f"Export format '{format}' not supported yet."
                
        except Exception as e:
            logger.error(f"Error exporting document: {e}")
            return f"Error exporting document: {str(e)}"
    
    def _markdown_to_html(self, markdown_content: str) -> str:
        """Simple markdown to HTML conversion."""
        try:
            html = markdown_content
            
            # Headers
            html = re.sub(r'^# (.*$)', r'<h1>\1</h1>', html, flags=re.MULTILINE)
            html = re.sub(r'^## (.*$)', r'<h2>\1</h2>', html, flags=re.MULTILINE)
            html = re.sub(r'^### (.*$)', r'<h3>\1</h3>', html, flags=re.MULTILINE)
            
            # Bold and italic
            html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
            html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
            
            # Paragraphs
            html = re.sub(r'\n\n', '</p>\n<p>', html)
            html = f'<p>{html}</p>'
            
            return html
            
        except Exception as e:
            logger.error(f"Error converting markdown to HTML: {e}")
            return f"Error converting markdown to HTML: {str(e)}"
    
    def _markdown_to_latex(self, markdown_content: str) -> str:
        """Simple markdown to LaTeX conversion."""
        try:
            latex = markdown_content
            
            # Headers
            latex = re.sub(r'^# (.*$)', r'\\section{\1}', latex, flags=re.MULTILINE)
            latex = re.sub(r'^## (.*$)', r'\\subsection{\1}', latex, flags=re.MULTILINE)
            latex = re.sub(r'^### (.*$)', r'\\subsubsection{\1}', latex, flags=re.MULTILINE)
            
            # Bold and italic
            latex = re.sub(r'\*\*(.*?)\*\*', r'\\textbf{\1}', latex)
            latex = re.sub(r'\*(.*?)\*', r'\\textit{\1}', latex)
            
            # Escape special characters
            latex = latex.replace('&', '\\&')
            latex = latex.replace('%', '\\%')
            latex = latex.replace('$', '\\$')
            
            return latex
            
        except Exception as e:
            logger.error(f"Error converting markdown to LaTeX: {e}")
            return f"Error converting markdown to LaTeX: {str(e)}"
    
    async def _generate_literature_review(self, title: str, research_question: str, 
                                        studies: List[Dict[str, Any]], synthesis_data: Dict[str, Any],
                                        meta_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a complete literature review."""
        try:
            template = self.templates.get("literature_review", self.templates["manuscript"])
            
            # Prepare context for literature review
            context = {
                "title": title,
                "authors": ["Eunice Research Platform"],
                "background": synthesis_data.get("background", ""),
                "objective": research_question,
                "methods_summary": synthesis_data.get("methods", ""),
                "results_summary": synthesis_data.get("results_summary", ""),
                "conclusions": synthesis_data.get("conclusions", ""),
                "introduction": synthesis_data.get("introduction", ""),
                "search_strategy": synthesis_data.get("search_strategy", ""),
                "inclusion_criteria": synthesis_data.get("inclusion_criteria", ""),
                "data_extraction": synthesis_data.get("data_extraction", ""),
                "quality_assessment": synthesis_data.get("quality_assessment", ""),
                "study_selection": synthesis_data.get("study_selection", ""),
                "study_characteristics": synthesis_data.get("study_characteristics", ""),
                "evidence_synthesis": synthesis_data.get("evidence_synthesis", ""),
                "meta_analysis": meta_analysis.get("results", "") if meta_analysis else "",
                "evidence_summary": synthesis_data.get("evidence_summary", ""),
                "limitations": synthesis_data.get("limitations", ""),
                "implications": synthesis_data.get("implications", ""),
                "future_research": synthesis_data.get("future_research", ""),
                "conclusions_detailed": synthesis_data.get("conclusions_detailed", ""),
                "references": studies  # Use studies as references
            }
            
            # Render literature review
            rendered_review = template.render(**context)
            
            return {
                "title": title,
                "content": rendered_review,
                "word_count": len(rendered_review.split()),
                "sections": [
                    "Abstract", "Introduction", "Methods", "Results", 
                    "Discussion", "Conclusions", "References"
                ],
                "studies_included": len(studies),
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating literature review: {e}")
            return {"error": str(e)}


# Request/Response models for FastAPI
class ManuscriptGenerationRequest(BaseModel):
    title: str = Field(description="Manuscript title")
    authors: List[str] = Field(default_factory=list, description="Author list")
    sections: List[Dict[str, Any]] = Field(description="Manuscript sections")
    references: List[Dict[str, Any]] = Field(default_factory=list, description="References")
    format: str = Field(default="markdown", description="Output format")
    template: str = Field(default="manuscript", description="Template type")


class CitationFormattingRequest(BaseModel):
    citations: List[Dict[str, Any]] = Field(description="Citations to format")
    style: str = Field(default="apa", description="Citation style")


class BibliographyGenerationRequest(BaseModel):
    references: List[Dict[str, Any]] = Field(description="References for bibliography")
    style: str = Field(default="apa", description="Citation style")


class DocumentExportRequest(BaseModel):
    content: str = Field(description="Document content")
    format: str = Field(description="Export format")
    title: str = Field(default="Document", description="Document title")


class LiteratureReviewRequest(BaseModel):
    title: str = Field(description="Literature review title")
    research_question: str = Field(description="Research question")
    studies: List[Dict[str, Any]] = Field(description="Studies for review")
    synthesis_data: Dict[str, Any] = Field(default_factory=dict, description="Synthesis data")
    meta_analysis: Dict[str, Any] = Field(default_factory=dict, description="Meta-analysis results")


class TaskRequest(BaseModel):
    action: str
    payload: Dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    agent_type: str
    mcp_connected: bool
    capabilities: List[str]
    output_formats: List[str]
    citation_styles: List[str]


# Global service instance
writer_service: Optional[WriterService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global writer_service
    
    # Load configuration
    config_path = Path("/app/config/config.json")
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
    else:
        config = {
            "service_host": "0.0.0.0",
            "service_port": 8006,
            "mcp_server_url": "ws://mcp-server:9000",
            "output_formats": ["markdown", "latex", "docx", "html"],
            "citation_styles": ["apa", "vancouver", "harvard", "chicago"]
        }
    
    # Start service
    writer_service = WriterService(config)
    await writer_service.start()
    
    try:
        yield
    finally:
        # Cleanup
        if writer_service:
            await writer_service.stop()


# FastAPI application
app = FastAPI(
    title="Writer Service",
    description="Writer Agent for manuscript generation and academic writing",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    if not writer_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    capabilities = [
        "manuscript_generation",
        "academic_writing",
        "citation_formatting",
        "bibliography_management",
        "document_templates",
        "export_formats",
        "prisma_flowcharts",
        "evidence_tables"
    ]
    
    return HealthResponse(
        status="healthy",
        agent_type="writer",
        mcp_connected=writer_service.mcp_connected,
        capabilities=capabilities,
        output_formats=writer_service.output_formats,
        citation_styles=writer_service.citation_styles
    )


@app.post("/generate-manuscript")
async def generate_manuscript(request: ManuscriptGenerationRequest):
    """Generate manuscript."""
    if not writer_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        result = await writer_service._handle_generate_manuscript({
            "title": request.title,
            "authors": request.authors,
            "sections": request.sections,
            "references": request.references,
            "format": request.format,
            "template": request.template
        })
        return result
    except Exception as e:
        logger.error(f"Error generating manuscript: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/format-citations")
async def format_citations(request: CitationFormattingRequest):
    """Format citations."""
    if not writer_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        result = await writer_service._handle_format_citations({
            "citations": request.citations,
            "style": request.style
        })
        return result
    except Exception as e:
        logger.error(f"Error formatting citations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-bibliography")
async def generate_bibliography(request: BibliographyGenerationRequest):
    """Generate bibliography."""
    if not writer_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        result = await writer_service._handle_generate_bibliography({
            "references": request.references,
            "style": request.style
        })
        return result
    except Exception as e:
        logger.error(f"Error generating bibliography: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/export-document")
async def export_document(request: DocumentExportRequest):
    """Export document."""
    if not writer_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        result = await writer_service._handle_export_document({
            "content": request.content,
            "format": request.format,
            "title": request.title
        })
        return result
    except Exception as e:
        logger.error(f"Error exporting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-literature-review")
async def generate_literature_review(request: LiteratureReviewRequest):
    """Generate literature review."""
    if not writer_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        result = await writer_service._handle_generate_literature_review({
            "title": request.title,
            "research_question": request.research_question,
            "studies": request.studies,
            "synthesis_data": request.synthesis_data,
            "meta_analysis": request.meta_analysis
        })
        return result
    except Exception as e:
        logger.error(f"Error generating literature review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/task")
async def process_task(request: TaskRequest):
    """Process a writer task directly (for testing)."""
    if not writer_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        result = await writer_service._process_writer_task({
            "action": request.action,
            "payload": request.payload
        })
        return result
    except Exception as e:
        logger.error(f"Error processing task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "writer_service:app",
        host="0.0.0.0",
        port=8006,
        log_level="info"
    )

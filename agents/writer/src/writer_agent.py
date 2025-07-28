"""
Writer Agent - Pure MCP Client Implementation

Architecture-compliant writer agent that specializes in:
- Manuscript generation and formatting
- Citation management and bibliography
- Multi-format document export
- Pure MCP protocol communication only
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path
import sys

# Import base MCP agent
sys.path.append('/app')
from base_mcp_agent import BaseMCPAgent, create_agent_main

logger = logging.getLogger(__name__)


class WriterAgent(BaseMCPAgent):
    """
    Writer Agent - Pure MCP Client
    
    Handles manuscript generation, citation formatting, and document export
    through MCP protocol only.
    """
    
    def __init__(self, agent_type: str, config: Dict[str, Any]):
        """Initialize Writer Agent."""
        super().__init__(agent_type, config)
        
        # Writer-specific configuration
        self.supported_formats = config.get("supported_formats", ["markdown", "latex", "docx", "pdf", "html"])
        self.citation_styles = config.get("citation_styles", ["APA", "Vancouver", "Harvard", "Chicago"])
        self.max_document_length = config.get("max_document_length", 50000)
        
        self.logger.info("Writer Agent initialized with MCP client")
    
    def get_capabilities(self) -> List[str]:
        """Return writer agent capabilities."""
        return [
            "manuscript_generation",
            "citation_formatting",
            "bibliography_creation",
            "document_export",
            "multi_format_support",
            "reference_management",
            "template_application",
            "academic_writing",
            "document_structuring",
            "figure_table_integration",
            "cross_referencing",
            "version_control"
        ]
    
    def setup_task_handlers(self) -> Dict[str, Any]:
        """Setup task handlers for writer operations."""
        return {
            "generate_manuscript": self._handle_generate_manuscript,
            "format_citations": self._handle_format_citations,
            "create_bibliography": self._handle_create_bibliography,
            "export_document": self._handle_export_document,
            "apply_template": self._handle_apply_template,
            "structure_document": self._handle_structure_document,
            "integrate_figures": self._handle_integrate_figures,
            "create_cross_references": self._handle_create_cross_references,
            "format_document": self._handle_format_document,
            "generate_outline": self._handle_generate_outline
        }
    
    # Task Handlers
    
    async def _handle_generate_manuscript(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle manuscript generation."""
        try:
            title = data.get("title", "Untitled Document")
            content = data.get("content", "")
            format_type = data.get("format", "markdown")
            template = data.get("template", "default")
            metadata = data.get("metadata", {})
            
            if format_type not in self.supported_formats:
                raise ValueError(f"Unsupported format: {format_type}. Supported: {self.supported_formats}")
            
            self.logger.info(f"Generating manuscript: {title} in {format_type} format")
            
            # Generate manuscript based on format
            manuscript = await self._generate_formatted_manuscript(
                title, content, format_type, template, metadata
            )
            
            return {
                "manuscript_id": str(uuid.uuid4()),
                "title": title,
                "content": manuscript["content"],
                "format": format_type,
                "template": template,
                "metadata": {
                    **metadata,
                    "generated_at": datetime.now().isoformat(),
                    "word_count": manuscript["word_count"],
                    "sections_count": manuscript["sections_count"],
                    "estimated_pages": manuscript.get("estimated_pages", 0)
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error generating manuscript: {e}")
            raise
    
    async def _handle_format_citations(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle citation formatting."""
        try:
            citations = data.get("citations", [])
            style = data.get("style", "APA")
            
            if style not in self.citation_styles:
                raise ValueError(f"Unsupported citation style: {style}. Supported: {self.citation_styles}")
            
            if not citations:
                raise ValueError("Citations list is required")
            
            self.logger.info(f"Formatting {len(citations)} citations in {style} style")
            
            # Format citations
            formatted_citations = await self._format_citations_by_style(citations, style)
            
            return {
                "formatted_citations": formatted_citations,
                "style": style,
                "citation_count": len(formatted_citations),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error formatting citations: {e}")
            raise
    
    async def _handle_create_bibliography(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle bibliography creation."""
        try:
            references = data.get("references", [])
            style = data.get("style", "APA")
            sort_order = data.get("sort_order", "alphabetical")
            
            if not references:
                raise ValueError("References list is required")
            
            self.logger.info(f"Creating bibliography with {len(references)} references in {style} style")
            
            # Create bibliography
            bibliography = await self._create_formatted_bibliography(references, style, sort_order)
            
            return {
                "bibliography": bibliography,
                "style": style,
                "sort_order": sort_order,
                "reference_count": len(references),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error creating bibliography: {e}")
            raise
    
    async def _handle_export_document(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle document export."""
        try:
            content = data.get("content", "")
            source_format = data.get("source_format", "markdown")
            target_format = data.get("target_format", "pdf")
            export_options = data.get("export_options", {})
            
            if target_format not in self.supported_formats:
                raise ValueError(f"Unsupported target format: {target_format}")
            
            self.logger.info(f"Exporting document from {source_format} to {target_format}")
            
            # Export document
            exported_doc = await self._export_document_format(
                content, source_format, target_format, export_options
            )
            
            return {
                "export_result": exported_doc,
                "source_format": source_format,
                "target_format": target_format,
                "file_size": len(exported_doc.get("content", "")),
                "export_options": export_options,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error exporting document: {e}")
            raise
    
    async def _handle_apply_template(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle template application."""
        try:
            content = data.get("content", "")
            template_name = data.get("template", "default")
            variables = data.get("variables", {})
            
            self.logger.info(f"Applying template: {template_name}")
            
            # Apply template
            templated_content = await self._apply_document_template(
                content, template_name, variables
            )
            
            return {
                "templated_content": templated_content,
                "template": template_name,
                "variables_applied": len(variables),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error applying template: {e}")
            raise
    
    async def _handle_structure_document(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle document structuring."""
        try:
            content = data.get("content", "")
            structure_type = data.get("structure_type", "research_paper")
            
            self.logger.info(f"Structuring document as {structure_type}")
            
            # Structure document
            structured_doc = await self._structure_document_content(content, structure_type)
            
            return {
                "structured_content": structured_doc["content"],
                "structure_type": structure_type,
                "sections": structured_doc["sections"],
                "outline": structured_doc["outline"],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error structuring document: {e}")
            raise
    
    async def _handle_integrate_figures(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle figure and table integration."""
        try:
            content = data.get("content", "")
            figures = data.get("figures", [])
            tables = data.get("tables", [])
            
            self.logger.info(f"Integrating {len(figures)} figures and {len(tables)} tables")
            
            # Integrate figures and tables
            integrated_content = await self._integrate_figures_tables(content, figures, tables)
            
            return {
                "integrated_content": integrated_content,
                "figures_count": len(figures),
                "tables_count": len(tables),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error integrating figures: {e}")
            raise
    
    async def _handle_create_cross_references(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle cross-reference creation."""
        try:
            content = data.get("content", "")
            reference_type = data.get("reference_type", "all")
            
            self.logger.info(f"Creating cross-references for: {reference_type}")
            
            # Create cross-references
            cross_refs = await self._create_cross_references(content, reference_type)
            
            return {
                "cross_references": cross_refs,
                "reference_type": reference_type,
                "references_count": len(cross_refs),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error creating cross-references: {e}")
            raise
    
    async def _handle_format_document(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle document formatting."""
        try:
            content = data.get("content", "")
            format_options = data.get("format_options", {})
            
            self.logger.info("Formatting document with custom options")
            
            # Format document
            formatted_content = await self._format_document_content(content, format_options)
            
            return {
                "formatted_content": formatted_content,
                "format_options": format_options,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error formatting document: {e}")
            raise
    
    async def _handle_generate_outline(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle outline generation."""
        try:
            content = data.get("content", "")
            outline_type = data.get("outline_type", "hierarchical")
            max_levels = data.get("max_levels", 4)
            
            self.logger.info(f"Generating {outline_type} outline with {max_levels} levels")
            
            # Generate outline
            outline = await self._generate_document_outline(content, outline_type, max_levels)
            
            return {
                "outline": outline,
                "outline_type": outline_type,
                "max_levels": max_levels,
                "sections_count": len(outline.get("sections", [])),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error generating outline: {e}")
            raise
    
    # Business Logic Methods
    
    async def _generate_formatted_manuscript(self, title: str, content: str, format_type: str, template: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Generate formatted manuscript."""
        try:
            # Basic manuscript structure
            sections = self._parse_content_sections(content)
            
            if format_type == "markdown":
                formatted_content = self._format_as_markdown(title, sections, metadata)
            elif format_type == "latex":
                formatted_content = self._format_as_latex(title, sections, metadata)
            elif format_type == "html":
                formatted_content = self._format_as_html(title, sections, metadata)
            else:
                # Default to markdown
                formatted_content = self._format_as_markdown(title, sections, metadata)
            
            # Calculate metrics
            word_count = len(formatted_content.split())
            sections_count = len(sections)
            estimated_pages = max(1, word_count // 250)  # ~250 words per page
            
            return {
                "content": formatted_content,
                "word_count": word_count,
                "sections_count": sections_count,
                "estimated_pages": estimated_pages
            }
            
        except Exception as e:
            self.logger.error(f"Error generating formatted manuscript: {e}")
            raise
    
    def _parse_content_sections(self, content: str) -> List[Dict[str, Any]]:
        """Parse content into sections."""
        if not content.strip():
            return [{"title": "Introduction", "content": "Content to be added."}]
        
        # Simple section parsing
        lines = content.split('\n')
        sections = []
        current_section = {"title": "Introduction", "content": ""}
        
        for line in lines:
            line = line.strip()
            if line.startswith('#') or line.startswith('##'):
                # New section
                if current_section["content"].strip():
                    sections.append(current_section)
                current_section = {
                    "title": line.lstrip('#').strip(),
                    "content": ""
                }
            else:
                current_section["content"] += line + "\n"
        
        # Add last section
        if current_section["content"].strip() or not sections:
            sections.append(current_section)
        
        return sections
    
    def _format_as_markdown(self, title: str, sections: List[Dict[str, Any]], metadata: Dict[str, Any]) -> str:
        """Format as Markdown."""
        content = f"# {title}\n\n"
        
        # Add metadata if present
        if metadata:
            content += "---\n"
            for key, value in metadata.items():
                content += f"{key}: {value}\n"
            content += "---\n\n"
        
        # Add sections
        for section in sections:
            content += f"## {section['title']}\n\n"
            content += f"{section['content']}\n\n"
        
        return content
    
    def _format_as_latex(self, title: str, sections: List[Dict[str, Any]], metadata: Dict[str, Any]) -> str:
        """Format as LaTeX."""
        content = "\\documentclass{article}\n"
        content += "\\usepackage[utf8]{inputenc}\n"
        content += "\\usepackage{amsmath}\n"
        content += "\\usepackage{graphicx}\n\n"
        
        # Title and metadata
        content += f"\\title{{{title}}}\n"
        if metadata.get("author"):
            content += f"\\author{{{metadata['author']}}}\n"
        if metadata.get("date"):
            content += f"\\date{{{metadata['date']}}}\n"
        
        content += "\\begin{document}\n"
        content += "\\maketitle\n\n"
        
        # Add sections
        for section in sections:
            content += f"\\section{{{section['title']}}}\n"
            content += f"{section['content']}\n\n"
        
        content += "\\end{document}\n"
        return content
    
    def _format_as_html(self, title: str, sections: List[Dict[str, Any]], metadata: Dict[str, Any]) -> str:
        """Format as HTML."""
        content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #666; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
"""
        
        # Add sections
        for section in sections:
            content += f"    <h2>{section['title']}</h2>\n"
            content += f"    <p>{section['content'].replace(chr(10), '<br>')}</p>\n"
        
        content += "</body>\n</html>\n"
        return content
    
    async def _format_citations_by_style(self, citations: List[Dict[str, Any]], style: str) -> List[str]:
        """Format citations by style."""
        formatted = []
        
        for citation in citations:
            if style == "APA":
                formatted_citation = self._format_apa_citation(citation)
            elif style == "Vancouver":
                formatted_citation = self._format_vancouver_citation(citation)
            elif style == "Harvard":
                formatted_citation = self._format_harvard_citation(citation)
            elif style == "Chicago":
                formatted_citation = self._format_chicago_citation(citation)
            else:
                formatted_citation = self._format_apa_citation(citation)  # Default to APA
            
            formatted.append(formatted_citation)
        
        return formatted
    
    def _format_apa_citation(self, citation: Dict[str, Any]) -> str:
        """Format citation in APA style."""
        authors = citation.get("authors", ["Unknown"])
        year = citation.get("year", "n.d.")
        title = citation.get("title", "Untitled")
        journal = citation.get("journal", "")
        
        author_str = ", ".join(authors[:3])  # Limit to first 3 authors
        if len(authors) > 3:
            author_str += ", et al."
        
        if journal:
            return f"{author_str} ({year}). {title}. {journal}."
        else:
            return f"{author_str} ({year}). {title}."
    
    def _format_vancouver_citation(self, citation: Dict[str, Any]) -> str:
        """Format citation in Vancouver style."""
        authors = citation.get("authors", ["Unknown"])
        year = citation.get("year", "")
        title = citation.get("title", "Untitled")
        journal = citation.get("journal", "")
        
        author_str = ", ".join([
            author.split()[-1] + " " + "".join([n[0] for n in author.split()[:-1]]) if len(author.split()) > 1
            else author
            for author in authors[:6]
        ])
        
        if journal:
            return f"{author_str}. {title}. {journal}. {year}."
        else:
            return f"{author_str}. {title}. {year}."
    
    def _format_harvard_citation(self, citation: Dict[str, Any]) -> str:
        """Format citation in Harvard style."""
        return self._format_apa_citation(citation)  # Similar to APA
    
    def _format_chicago_citation(self, citation: Dict[str, Any]) -> str:
        """Format citation in Chicago style."""
        authors = citation.get("authors", ["Unknown"])
        year = citation.get("year", "")
        title = citation.get("title", "Untitled")
        journal = citation.get("journal", "")
        
        if authors:
            author_str = authors[0]
            if len(authors) > 1:
                author_str += ", et al."
        else:
            author_str = "Unknown"
        
        if journal:
            return f'{author_str}. "{title}." {journal} ({year}).'
        else:
            return f'{author_str}. "{title}." {year}.'
    
    async def _create_formatted_bibliography(self, references: List[Dict[str, Any]], style: str, sort_order: str) -> List[str]:
        """Create formatted bibliography."""
        # Format all citations
        formatted_refs = await self._format_citations_by_style(references, style)
        
        # Sort bibliography
        if sort_order == "alphabetical":
            formatted_refs.sort()
        elif sort_order == "chronological":
            # Sort by year (simplified)
            year_refs = [(ref.get("year", 0), formatted_ref) for ref, formatted_ref in zip(references, formatted_refs)]
            year_refs.sort(key=lambda x: x[0])
            formatted_refs = [ref[1] for ref in year_refs]
        
        return formatted_refs
    
    async def _export_document_format(self, content: str, source_format: str, target_format: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Export document to different format."""
        # Simple format conversion (in real implementation, would use pandoc or similar)
        if source_format == target_format:
            return {"content": content, "converted": False}
        
        # Basic conversions
        if source_format == "markdown" and target_format == "html":
            # Simple markdown to HTML conversion
            html_content = content.replace("# ", "<h1>").replace("## ", "<h2>")
            html_content = f"<html><body>{html_content}</body></html>"
            return {"content": html_content, "converted": True}
        else:
            # For other conversions, return original with note
            return {"content": content, "converted": False, "note": f"Conversion from {source_format} to {target_format} not implemented"}
    
    async def _apply_document_template(self, content: str, template_name: str, variables: Dict[str, Any]) -> str:
        """Apply template to document."""
        # Simple template application
        templated_content = content
        
        # Replace variables
        for var_name, var_value in variables.items():
            placeholder = f"{{{{{var_name}}}}}"
            templated_content = templated_content.replace(placeholder, str(var_value))
        
        # Apply template structure based on name
        if template_name == "research_paper":
            if not templated_content.startswith("#"):
                templated_content = f"# {variables.get('title', 'Research Paper')}\n\n{templated_content}"
        
        return templated_content
    
    async def _structure_document_content(self, content: str, structure_type: str) -> Dict[str, Any]:
        """Structure document content."""
        sections = self._parse_content_sections(content)
        
        if structure_type == "research_paper":
            # Ensure standard research paper structure
            standard_sections = ["Abstract", "Introduction", "Methods", "Results", "Discussion", "Conclusion", "References"]
            structured_sections = []
            
            for std_section in standard_sections:
                found = False
                for section in sections:
                    if std_section.lower() in section["title"].lower():
                        structured_sections.append(section)
                        found = True
                        break
                if not found:
                    structured_sections.append({"title": std_section, "content": f"[{std_section} content to be added]"})
        else:
            structured_sections = sections
        
        # Rebuild content
        structured_content = ""
        outline = []
        
        for i, section in enumerate(structured_sections, 1):
            structured_content += f"## {section['title']}\n\n{section['content']}\n\n"
            outline.append(f"{i}. {section['title']}")
        
        return {
            "content": structured_content,
            "sections": structured_sections,
            "outline": outline
        }
    
    async def _integrate_figures_tables(self, content: str, figures: List[Dict[str, Any]], tables: List[Dict[str, Any]]) -> str:
        """Integrate figures and tables into content."""
        integrated_content = content
        
        # Add figures
        for i, figure in enumerate(figures, 1):
            figure_ref = f"![Figure {i}: {figure.get('caption', 'Figure')}]({figure.get('path', '')})"
            integrated_content += f"\n\n{figure_ref}\n"
        
        # Add tables
        for i, table in enumerate(tables, 1):
            table_content = f"\n\n**Table {i}: {table.get('caption', 'Table')}**\n\n"
            if table.get("data"):
                # Simple table formatting
                table_content += "| Column 1 | Column 2 |\n"
                table_content += "|----------|----------|\n"
                for row in table["data"][:5]:  # Limit to 5 rows
                    table_content += f"| {row.get('col1', '')} | {row.get('col2', '')} |\n"
            integrated_content += table_content
        
        return integrated_content
    
    async def _create_cross_references(self, content: str, reference_type: str) -> List[Dict[str, Any]]:
        """Create cross-references in document."""
        cross_refs = []
        
        # Simple cross-reference detection
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('#'):
                section_title = line.lstrip('#').strip()
                cross_refs.append({
                    "type": "section",
                    "title": section_title,
                    "line_number": i + 1,
                    "reference": f"[{section_title}](#{section_title.lower().replace(' ', '-')})"
                })
            elif "Figure" in line or "Table" in line:
                cross_refs.append({
                    "type": "figure_table",
                    "content": line.strip(),
                    "line_number": i + 1,
                    "reference": line.strip()
                })
        
        return cross_refs
    
    async def _format_document_content(self, content: str, format_options: Dict[str, Any]) -> str:
        """Format document with custom options."""
        formatted_content = content
        
        # Apply formatting options
        if format_options.get("line_spacing"):
            # Add line spacing (simplified)
            formatted_content = formatted_content.replace('\n\n', '\n\n\n')
        
        if format_options.get("capitalize_headings"):
            lines = formatted_content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('#'):
                    lines[i] = line.upper()
            formatted_content = '\n'.join(lines)
        
        return formatted_content
    
    async def _generate_document_outline(self, content: str, outline_type: str, max_levels: int) -> Dict[str, Any]:
        """Generate document outline."""
        sections = self._parse_content_sections(content)
        
        outline = {
            "type": outline_type,
            "max_levels": max_levels,
            "sections": []
        }
        
        for i, section in enumerate(sections, 1):
            outline["sections"].append({
                "level": 1,
                "number": i,
                "title": section["title"],
                "page": i,  # Simplified page numbering
                "subsections": []
            })
        
        return outline


# Create main entry point
main = create_agent_main(WriterAgent, "writer")

if __name__ == "__main__":
    asyncio.run(main())

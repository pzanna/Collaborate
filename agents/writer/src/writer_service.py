"""
Writer Agent Service for Eunice Research Platform.

This module provides a containerized Writer Agent that handles:
- Manuscript generation and academic writing
- Citation formatting and bibliography management
- Document template processing and export
- Academic writing assistance and formatting
- Multi-format document generation

ARCHITECTURE COMPLIANCE:
- ONLY exposes health check API endpoint (/health)
- ALL business operations via MCP protocol exclusively
- NO direct HTTP/REST endpoints for business logic
"""

import asyncio
import json
import logging
import re
import uuid
import sys
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Literal, Union

import uvicorn
import websockets
from fastapi import FastAPI
from websockets.exceptions import ConnectionClosed, WebSocketException

# Import the standardized health check service
sys.path.append(str(Path(__file__).parent.parent))
from health_check_service import create_health_check_app

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
    via MCP protocol.
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
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.mcp_connected = False
        self.should_run = True
        
        # Data storage
        self.manuscript_drafts: Dict[str, ManuscriptDraft] = {}
        self.writing_sessions: Dict[str, Dict[str, Any]] = {}
        self.templates: Dict[str, str] = {}
        
        # Task processing queue
        self.task_queue = asyncio.Queue()
        
        # Start time for uptime tracking
        self.start_time = datetime.now()
        
        # Capabilities
        self.capabilities = [
            "generate_manuscript",
            "format_citations",
            "create_bibliography",
            "export_document",
            "process_templates",
            "manage_writing_sessions"
        ]
        
        # Initialize default templates
        self._initialize_templates()
        
        logger.info(f"Writer Service initialized on port {self.service_port}")
    
    def _initialize_templates(self):
        """Initialize default document templates."""
        self.templates["apa_manuscript"] = """
# {title}

{authors}

## Abstract
{abstract}

## Introduction
{introduction}

## Methods
{methods}

## Results
{results}

## Discussion
{discussion}

## References
{references}
"""
        
        self.templates["research_report"] = """
# {title}

**Prepared by:** {authors}
**Date:** {date}

## Executive Summary
{executive_summary}

## Background
{background}

## Methodology
{methodology}

## Findings
{findings}

## Conclusions and Recommendations
{conclusions}

## References
{references}
"""
    
    async def start(self):
        """Start the Writer Service."""
        try:
            # Connect to MCP server
            await self._connect_to_mcp_server()
            
            # Start task processing
            asyncio.create_task(self._process_task_queue())
            
            # Listen for MCP messages
            await self._listen_for_tasks()
            
            logger.info("Writer Service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Writer Service: {e}")
            raise
    
    async def stop(self):
        """Stop the Writer Service."""
        try:
            self.should_run = False
            
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
        if not self.websocket:
            raise Exception("WebSocket connection not available")
            
        registration_message = {
            "type": "agent_register",
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": self.capabilities,
            "timestamp": datetime.now().isoformat(),
            "service_info": {
                    "host": self.service_host,
                    "port": self.service_port,
                    "health_endpoint": f"http://{self.service_host}:{self.service_port}/health"
                }
            
        }
        
        await self.websocket.send(json.dumps(registration_message))
        logger.info(f"Registered with MCP server: {len(self.capabilities)} capabilities")
    
    async def _listen_for_tasks(self):
        """Listen for tasks from MCP server."""
        try:
            if not self.websocket:
                logger.error("Cannot listen for tasks: no websocket connection")
                return
                
            logger.info("Starting to listen for tasks from MCP server")
            
            async for message in self.websocket:
                if not self.should_run:
                    break
                    
                try:
                    data = json.loads(message)
                    await self.task_queue.put(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse MCP message: {e}")
                except Exception as e:
                    logger.error(f"Error handling MCP message: {e}")
                    
        except ConnectionClosed:
            logger.warning("MCP server connection closed")
            self.mcp_connected = False
            # Attempt to reconnect
            asyncio.create_task(self._reconnect_to_mcp_server())
        except WebSocketException as e:
            logger.error(f"WebSocket error: {e}")
            self.mcp_connected = False
            # Attempt to reconnect
            asyncio.create_task(self._reconnect_to_mcp_server())
        except Exception as e:
            logger.error(f"Unexpected error in message listener: {e}")
            self.mcp_connected = False
    
    async def _reconnect_to_mcp_server(self):
        """Attempt to reconnect to MCP server after connection loss."""
        logger.info("Attempting to reconnect to MCP server...")
        max_retries = 5
        retry_delay = 3
        
        for attempt in range(max_retries):
            try:
                await asyncio.sleep(retry_delay)  # Wait before retry
                
                logger.info(f"Reconnection attempt {attempt + 1}/{max_retries}")
                
                # Close existing connection if any
                if self.websocket:
                    try:
                        await self.websocket.close()
                    except:
                        pass
                
                # Create new connection
                self.websocket = await websockets.connect(
                    self.mcp_server_url,
                    ping_interval=20,  # More frequent pings during long operations
                    ping_timeout=15    # Longer timeout for ping responses
                )
                
                # Re-register with MCP server
                await self._register_with_mcp_server()
                
                # Restart message handler
                asyncio.create_task(self._listen_for_tasks())
                
                self.mcp_connected = True
                logger.info("✅ Successfully reconnected to MCP server")
                
                return
                
            except Exception as e:
                logger.warning(f"Reconnection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    retry_delay = min(retry_delay * 2, 30)  # Exponential backoff, max 30s
                else:
                    logger.error("❌ Failed to reconnect to MCP server after all attempts")
                    self.mcp_connected = False
    
    async def _process_task_queue(self):
        """Process tasks from the MCP queue."""
        while self.should_run:
            try:
                # Get task from queue
                task_data = await self.task_queue.get()
                
                # Process the task
                result = await self._process_writing_task(task_data)
                
                # Send result back to MCP server
                if self.websocket and self.mcp_connected:
                    response = {
                        "jsonrpc": "2.0",
                        "id": task_data.get("id"),
                        "result": result
                    }
                    await self.websocket.send(json.dumps(response))
                
                # Mark task as done
                self.task_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error processing task: {e}")
                await asyncio.sleep(1)
    
    async def _process_writing_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a writing-related task."""
        try:
            method = task_data.get("method", "")
            params = task_data.get("params", {})
            
            # Route to appropriate handler
            if method == "task/execute":
                task_type = params.get("task_type", "")
                data = params.get("data", {})
                
                if task_type == "generate_manuscript":
                    return await self._handle_generate_manuscript(data)
                elif task_type == "format_citations":
                    return await self._handle_format_citations(data)
                elif task_type == "create_bibliography":
                    return await self._handle_create_bibliography(data)
                elif task_type == "export_document":
                    return await self._handle_export_document(data)
                elif task_type == "process_templates":
                    return await self._handle_process_templates(data)
                elif task_type == "manage_writing_sessions":
                    return await self._handle_manage_writing_sessions(data)
                else:
                    return {
                        "status": "failed",
                        "error": f"Unknown task type: {task_type}",
                        "timestamp": datetime.now().isoformat()
                    }
            elif method == "agent/ping":
                return {"status": "alive", "timestamp": datetime.now().isoformat()}
            elif method == "agent/status":
                return await self._get_agent_status()
            else:
                return {
                    "status": "failed",
                    "error": f"Unknown method: {method}",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error processing writing task: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_generate_manuscript(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle manuscript generation request."""
        try:
            title = data.get("title", "Untitled Manuscript")
            authors = data.get("authors", [])
            sections_data = data.get("sections", [])
            template_name = data.get("template", "apa_manuscript")
            output_format = data.get("format", "markdown")
            
            # Generate manuscript
            manuscript = await self._generate_manuscript(title, authors, sections_data, template_name, output_format)
            
            # Store manuscript
            self.manuscript_drafts[manuscript.manuscript_id] = manuscript
            
            return {
                "status": "completed",
                "manuscript_id": manuscript.manuscript_id,
                "title": manuscript.title,
                "word_count": manuscript.word_count,
                "format": manuscript.format,
                "sections_count": len(manuscript.sections),
                "references_count": len(manuscript.references),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate manuscript: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_format_citations(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle citation formatting request."""
        try:
            citations = data.get("citations", [])
            style = data.get("style", "apa")
            in_text = data.get("in_text", False)
            
            if not citations:
                return {
                    "status": "failed",
                    "error": "Citations are required for formatting",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Format citations
            formatted_citations = await self._format_citations(citations, style, in_text)
            
            return {
                "status": "completed",
                "style": style,
                "in_text": in_text,
                "formatted_citations": formatted_citations,
                "citations_processed": len(citations),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to format citations: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_create_bibliography(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle bibliography creation request."""
        try:
            references = data.get("references", [])
            style = data.get("style", "apa")
            sort_order = data.get("sort_order", "alphabetical")
            
            if not references:
                return {
                    "status": "failed",
                    "error": "References are required for bibliography creation",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Create bibliography
            bibliography = await self._create_bibliography(references, style, sort_order)
            
            return {
                "status": "completed",
                "style": style,
                "sort_order": sort_order,
                "bibliography": bibliography,
                "references_count": len(references),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to create bibliography: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_export_document(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle document export request."""
        try:
            manuscript_id = data.get("manuscript_id", "")
            export_format = data.get("format", "markdown")
            include_metadata = data.get("include_metadata", True)
            
            if not manuscript_id:
                return {
                    "status": "failed",
                    "error": "Manuscript ID is required for export",
                    "timestamp": datetime.now().isoformat()
                }
            
            manuscript = self.manuscript_drafts.get(manuscript_id)
            if not manuscript:
                return {
                    "status": "failed",
                    "error": f"Manuscript {manuscript_id} not found",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Export document
            exported_content = await self._export_document(manuscript, export_format, include_metadata)
            
            return {
                "status": "completed",
                "manuscript_id": manuscript_id,
                "export_format": export_format,
                "content": exported_content,
                "word_count": manuscript.word_count,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to export document: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_process_templates(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle template processing request."""
        try:
            template_name = data.get("template_name", "")
            template_content = data.get("template_content", "")
            variables = data.get("variables", {})
            operation = data.get("operation", "render")
            
            if operation == "render":
                if not template_name and not template_content:
                    return {
                        "status": "failed",
                        "error": "Template name or content is required",
                        "timestamp": datetime.now().isoformat()
                    }
                
                # Render template
                rendered_content = await self._render_template(template_name, template_content, variables)
                
                return {
                    "status": "completed",
                    "operation": "render",
                    "template_name": template_name,
                    "rendered_content": rendered_content,
                    "variables_used": len(variables),
                    "timestamp": datetime.now().isoformat()
                }
            
            elif operation == "create":
                if not template_name or not template_content:
                    return {
                        "status": "failed",
                        "error": "Template name and content are required for creation",
                        "timestamp": datetime.now().isoformat()
                    }
                
                # Store custom template
                self.templates[template_name] = template_content
                
                return {
                    "status": "completed",
                    "operation": "create",
                    "template_name": template_name,
                    "created": True,
                    "timestamp": datetime.now().isoformat()
                }
            
            else:
                return {
                    "status": "failed",
                    "error": f"Unknown operation: {operation}",
                    "available_operations": ["render", "create"],
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to process templates: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_manage_writing_sessions(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle writing session management request."""
        try:
            operation = data.get("operation", "")
            
            if operation == "create":
                return await self._create_writing_session(data)
            elif operation == "get":
                return await self._get_writing_session(data)
            elif operation == "update":
                return await self._update_writing_session(data)
            elif operation == "delete":
                return await self._delete_writing_session(data)
            elif operation == "list":
                return await self._list_writing_sessions()
            else:
                return {
                    "status": "failed",
                    "error": f"Unknown operation: {operation}",
                    "available_operations": ["create", "get", "update", "delete", "list"],
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to manage writing sessions: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _generate_manuscript(self, title: str, authors: List[str], sections_data: List[Dict[str, Any]], 
                                 template_name: str, output_format: str) -> ManuscriptDraft:
        """Generate a complete manuscript."""
        manuscript_id = str(uuid.uuid4())
        
        # Process sections
        sections = []
        total_word_count = 0
        
        for section_data in sections_data:
            section = ManuscriptSection(
                section_name=section_data.get("name", ""),
                content=section_data.get("content", ""),
                references=section_data.get("references", [])
            )
            section.word_count = len(section.content.split())
            total_word_count += section.word_count
            sections.append(section)
        
        # Extract references
        all_references = []
        for section_data in sections_data:
            for ref_data in section_data.get("references", []):
                reference = Reference(
                    id=ref_data.get("id", str(uuid.uuid4())),
                    authors=ref_data.get("authors", []),
                    title=ref_data.get("title", ""),
                    journal=ref_data.get("journal", ""),
                    year=ref_data.get("year", 2023),
                    doi=ref_data.get("doi", "")
                )
                all_references.append(reference)
        
        manuscript = ManuscriptDraft(
            manuscript_id=manuscript_id,
            title=title,
            authors=authors,
            sections=sections,
            references=all_references,
            metadata={"template": template_name},
            format=output_format,
            word_count=total_word_count
        )
        
        return manuscript
    
    async def _format_citations(self, citations: List[Dict[str, Any]], style: str, in_text: bool) -> List[str]:
        """Format citations according to specified style."""
        formatted = []
        
        for citation in citations:
            if style.lower() == "apa":
                formatted_citation = await self._format_apa_citation(citation, in_text)
            elif style.lower() == "vancouver":
                formatted_citation = await self._format_vancouver_citation(citation, in_text)
            else:
                formatted_citation = await self._format_basic_citation(citation, in_text)
            
            formatted.append(formatted_citation)
        
        return formatted
    
    async def _format_apa_citation(self, citation: Dict[str, Any], in_text: bool) -> str:
        """Format citation in APA style."""
        authors = citation.get("authors", [])
        year = citation.get("year", "")
        title = citation.get("title", "")
        
        if in_text:
            if len(authors) == 1:
                return f"{authors[0].split()[-1]} ({year})"
            elif len(authors) == 2:
                return f"{authors[0].split()[-1]} & {authors[1].split()[-1]} ({year})"
            else:
                return f"{authors[0].split()[-1]} et al. ({year})"
        else:
            author_str = ", ".join(authors)
            journal = citation.get("journal", "")
            return f"{author_str} ({year}). {title}. {journal}."
    
    async def _format_vancouver_citation(self, citation: Dict[str, Any], in_text: bool) -> str:
        """Format citation in Vancouver style."""
        if in_text:
            citation_id = citation.get("id", "1")
            return f"({citation_id})"
        else:
            authors = citation.get("authors", [])
            title = citation.get("title", "")
            journal = citation.get("journal", "")
            year = citation.get("year", "")
            
            author_str = ", ".join(authors)
            return f"{author_str}. {title}. {journal}. {year}."
    
    async def _format_basic_citation(self, citation: Dict[str, Any], in_text: bool) -> str:
        """Format citation in basic style."""
        authors = citation.get("authors", [])
        year = citation.get("year", "")
        title = citation.get("title", "")
        
        if in_text:
            first_author = authors[0].split()[-1] if authors else "Unknown"
            return f"{first_author} ({year})"
        else:
            author_str = ", ".join(authors)
            return f"{author_str} ({year}). {title}."
    
    async def _create_bibliography(self, references: List[Dict[str, Any]], style: str, sort_order: str) -> str:
        """Create a formatted bibliography."""
        # Sort references
        if sort_order == "alphabetical":
            references.sort(key=lambda x: x.get("authors", [""])[0])
        elif sort_order == "chronological":
            references.sort(key=lambda x: x.get("year", 0))
        
        # Format references
        bibliography_entries = []
        for i, ref in enumerate(references, 1):
            if style.lower() == "vancouver":
                formatted_ref = f"{i}. " + await self._format_vancouver_citation(ref, False)
            else:
                formatted_ref = await self._format_apa_citation(ref, False)
            
            bibliography_entries.append(formatted_ref)
        
        return "\n".join(bibliography_entries)
    
    async def _export_document(self, manuscript: ManuscriptDraft, export_format: str, 
                             include_metadata: bool) -> str:
        """Export manuscript to specified format."""
        content_parts = []
        
        # Add metadata if requested
        if include_metadata:
            content_parts.append(f"# {manuscript.title}")
            content_parts.append(f"**Authors:** {', '.join(manuscript.authors)}")
            content_parts.append(f"**Generated:** {manuscript.generated_at.isoformat()}")
            content_parts.append(f"**Word Count:** {manuscript.word_count}")
            content_parts.append("")
        
        # Add sections
        for section in manuscript.sections:
            if export_format.lower() == "markdown":
                content_parts.append(f"## {section.section_name}")
                content_parts.append(section.content)
                content_parts.append("")
            elif export_format.lower() == "latex":
                content_parts.append(f"\\section{{{section.section_name}}}")
                content_parts.append(section.content)
                content_parts.append("")
            else:  # Plain text or HTML
                content_parts.append(f"{section.section_name.upper()}")
                content_parts.append(section.content)
                content_parts.append("")
        
        # Add references if available
        if manuscript.references:
            if export_format.lower() == "markdown":
                content_parts.append("## References")
            elif export_format.lower() == "latex":
                content_parts.append("\\section{References}")
            else:
                content_parts.append("REFERENCES")
            
            for ref in manuscript.references:
                ref_text = f"{', '.join(ref.authors)} ({ref.year}). {ref.title}. {ref.journal}."
                content_parts.append(ref_text)
        
        return "\n".join(content_parts)
    
    async def _render_template(self, template_name: str, template_content: str, variables: Dict[str, Any]) -> str:
        """Render a template with provided variables."""
        # Use template content if provided, otherwise use stored template
        if template_content:
            template_str = template_content
        elif template_name and template_name in self.templates:
            template_str = self.templates[template_name]
        else:
            raise ValueError(f"Template '{template_name}' not found and no content provided")
        
        # Simple template rendering (replace variables in {variable} format)
        rendered = template_str
        for key, value in variables.items():
            rendered = rendered.replace(f"{{{key}}}", str(value))
        
        return rendered
    
    async def _create_writing_session(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new writing session."""
        session_id = data.get("session_id", str(uuid.uuid4()))
        project_title = data.get("project_title", "Untitled Project")
        session_type = data.get("session_type", "manuscript")
        
        session = {
            "session_id": session_id,
            "project_title": project_title,
            "session_type": session_type,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "manuscripts": [],
            "templates_used": [],
            "word_count_total": 0
        }
        
        self.writing_sessions[session_id] = session
        
        return {
            "created": True,
            "session_id": session_id,
            "project_title": project_title,
            "session_type": session_type
        }
    
    async def _get_writing_session(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Get a writing session."""
        session_id = data.get("session_id", "")
        session = self.writing_sessions.get(session_id)
        
        if not session:
            return {"error": f"Session {session_id} not found"}
        
        return session
    
    async def _update_writing_session(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a writing session."""
        session_id = data.get("session_id", "")
        session = self.writing_sessions.get(session_id)
        
        if not session:
            return {"error": f"Session {session_id} not found"}
        
        # Update fields if provided
        if "project_title" in data:
            session["project_title"] = data["project_title"]
        if "session_type" in data:
            session["session_type"] = data["session_type"]
        
        session["updated_at"] = datetime.now().isoformat()
        
        return {"updated": True, "session_id": session_id}
    
    async def _delete_writing_session(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a writing session."""
        session_id = data.get("session_id", "")
        
        if session_id in self.writing_sessions:
            del self.writing_sessions[session_id]
            return {"deleted": True, "session_id": session_id}
        
        return {"error": f"Session {session_id} not found"}
    
    async def _list_writing_sessions(self) -> Dict[str, Any]:
        """List all writing sessions."""
        sessions = []
        for session_id, session in self.writing_sessions.items():
            sessions.append({
                "session_id": session["session_id"],
                "project_title": session["project_title"],
                "session_type": session["session_type"],
                "created_at": session["created_at"],
                "updated_at": session["updated_at"],
                "manuscripts_count": len(session["manuscripts"]),
                "word_count_total": session["word_count_total"]
            })
        
        return {
            "sessions": sessions,
            "total_sessions": len(sessions)
        }
    
    async def _get_agent_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "status": "ready" if self.mcp_connected else "disconnected",
            "capabilities": self.capabilities,
            "timestamp": datetime.now().isoformat(),
            "mcp_connected": self.mcp_connected,
            "manuscript_drafts": len(self.manuscript_drafts),
            "writing_sessions": len(self.writing_sessions),
            "templates_available": len(self.templates),
            "supported_formats": self.output_formats,
            "supported_citation_styles": self.citation_styles,
            "uptime_seconds": uptime,
            "timestamp": datetime.now().isoformat()
        }


# Global service instance
writer_service: Optional[WriterService] = None


def get_mcp_status() -> Dict[str, Any]:
    """Get MCP connection status for health check."""
    if writer_service:
        return {
            "connected": writer_service.mcp_connected,
            "last_heartbeat": datetime.now().isoformat()
        }
    return {"connected": False, "last_heartbeat": "never"}


def get_additional_metadata() -> Dict[str, Any]:
    """Get additional metadata for health check."""
    if writer_service:
        return {
            "capabilities": writer_service.capabilities,
            "manuscript_drafts": len(writer_service.manuscript_drafts),
            "writing_sessions": len(writer_service.writing_sessions),
            "templates_available": len(writer_service.templates),
            "agent_id": writer_service.agent_id
        }
    return {}


# Create health check only FastAPI application
app = create_health_check_app(
    agent_type="writer",
    agent_id="writer-agent",
    version="1.0.0",
    get_mcp_status=get_mcp_status,
    get_additional_metadata=get_additional_metadata
)


async def main():
    """Main entry point for the writer agent service."""
    global writer_service
    
    try:
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
                "output_formats": ["markdown", "latex", "docx"],
                "citation_styles": ["apa", "vancouver"]
            }
        
        # Initialize service
        writer_service = WriterService(config)
        
        # Start FastAPI health check server in background
        config_uvicorn = uvicorn.Config(
            app,
            host=config["service_host"],
            port=config["service_port"],
            log_level="info"
        )
        server = uvicorn.Server(config_uvicorn)
        
        logger.info("🚨 ARCHITECTURE COMPLIANCE: Writer Agent")
        logger.info("✅ ONLY health check API exposed")
        logger.info("✅ All business operations via MCP protocol exclusively")
        
        # Start server and MCP service concurrently
        await asyncio.gather(
            server.serve(),
            writer_service.start()
        )
        
    except KeyboardInterrupt:
        logger.info("Writer agent shutdown requested")
    except Exception as e:
        logger.error(f"Writer agent failed: {e}")
        sys.exit(1)
    finally:
        if writer_service:
            await writer_service.stop()


if __name__ == "__main__":
    asyncio.run(main())

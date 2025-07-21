"""Export manager for conversation data."""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import markdown
from jinja2 import Template

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# Import models
try:
    from ..models.data_models import ConversationSession, Message, Project
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from models.data_models import ConversationSession, Message, Project


class ExportManager:
    """Manages export functionality for conversations."""
    
    def __init__(self, export_path: str = "exports"):
        self.export_path = Path(export_path)
        self.export_path.mkdir(exist_ok=True)
    
    def export_conversation(self, session: ConversationSession, format_type: str, filename: Optional[str] = None) -> str:
        """Export conversation in specified format."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_title = "".join(c for c in session.conversation.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_title = safe_title.replace(' ', '_')[:50]  # Limit length
            filename = f"{safe_title}_{timestamp}"
        
        if format_type.lower() == "json":
            return self._export_json(session, filename)
        elif format_type.lower() == "markdown":
            return self._export_markdown(session, filename)
        elif format_type.lower() == "html":
            return self._export_html(session, filename)
        elif format_type.lower() == "pdf":
            return self._export_pdf(session, filename)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")
    
    def _export_json(self, session: ConversationSession, filename: str) -> str:
        """Export conversation as JSON."""
        export_data = {
            "metadata": {
                "export_timestamp": datetime.now().isoformat(),
                "export_format": "json",
                "exporter": "Eunice v1.0"
            },
            "project": {
                "id": session.project.id if session.project else None,
                "name": session.project.name if session.project else "Unknown",
                "description": session.project.description if session.project else ""
            },
            "conversation": {
                "id": session.conversation.id,
                "title": session.conversation.title,
                "created_at": session.conversation.created_at.isoformat(),
                "updated_at": session.conversation.updated_at.isoformat(),
                "participants": session.conversation.participants,
                "status": session.conversation.status
            },
            "messages": [
                {
                    "id": msg.id,
                    "participant": msg.participant,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "message_type": msg.message_type,
                    "metadata": msg.metadata
                }
                for msg in session.messages
            ],
            "statistics": {
                "total_messages": len(session.messages),
                "user_messages": len([m for m in session.messages if m.participant == "user"]),
                "openai_messages": len([m for m in session.messages if m.participant == "openai"]),
                "xai_messages": len([m for m in session.messages if m.participant == "xai"]),
                "conversation_duration": self._calculate_duration(session.messages)
            }
        }
        
        filepath = self.export_path / f"{filename}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        return str(filepath)
    
    def _export_markdown(self, session: ConversationSession, filename: str) -> str:
        """Export conversation as Markdown."""
        content = []
        
        # Header
        content.append(f"# {session.conversation.title}")
        content.append("")
        content.append(f"**Project:** {session.project.name if session.project else 'Unknown'}")
        content.append(f"**Created:** {session.conversation.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        content.append(f"**Participants:** {', '.join(session.conversation.participants)}")
        content.append("")
        
        # Description
        if session.project and session.project.description:
            content.append("## Project Description")
            content.append(session.project.description)
            content.append("")
        
        # Conversation
        content.append("## Conversation")
        content.append("")
        
        for msg in session.messages:
            timestamp = msg.timestamp.strftime("%H:%M:%S")
            participant_icon = {
                "user": "👤",
                "openai": "🤖",
                "xai": "🤖"
            }.get(msg.participant, "💬")
            
            participant_name = {
                "user": "You",
                "openai": "OpenAI",
                "xai": "xAI"
            }.get(msg.participant, msg.participant.title())
            
            content.append(f"### {participant_icon} {participant_name} [{timestamp}]")
            content.append("")
            content.append(msg.content)
            content.append("")
        
        # Statistics
        content.append("---")
        content.append("## Statistics")
        content.append("")
        content.append(f"- **Total Messages:** {len(session.messages)}")
        content.append(f"- **User Messages:** {len([m for m in session.messages if m.participant == 'user'])}")
        content.append(f"- **OpenAI Messages:** {len([m for m in session.messages if m.participant == 'openai'])}")
        content.append(f"- **xAI Messages:** {len([m for m in session.messages if m.participant == 'xai'])}")
        content.append(f"- **Duration:** {self._calculate_duration(session.messages)}")
        content.append("")
        content.append(f"*Exported on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by Eunice v1.0*")
        
        markdown_content = "\n".join(content)
        
        filepath = self.export_path / f"{filename}.md"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        return str(filepath)
    
    def _export_html(self, session: ConversationSession, filename: str) -> str:
        """Export conversation as HTML."""
        template_str = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ conversation.title }}</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #fafafa;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        .header h1 {
            margin: 0 0 10px 0;
        }
        .metadata {
            opacity: 0.9;
            font-size: 0.9em;
        }
        .message {
            background: white;
            margin: 20px 0;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .message-header {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
            font-weight: bold;
        }
        .participant-icon {
            font-size: 1.2em;
            margin-right: 10px;
        }
        .timestamp {
            margin-left: auto;
            font-size: 0.8em;
            opacity: 0.7;
            font-weight: normal;
        }
        .user { border-left: 4px solid #4CAF50; }
        .openai { border-left: 4px solid #2196F3; }
        .xai { border-left: 4px solid #9C27B0; }
        .content {
            white-space: pre-wrap;
            line-height: 1.6;
        }
        .statistics {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-top: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .stat-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        .stat-item {
            text-align: center;
            padding: 10px;
            background: #f5f5f5;
            border-radius: 5px;
        }
        .stat-value {
            font-size: 1.5em;
            font-weight: bold;
            color: #333;
        }
        .stat-label {
            font-size: 0.8em;
            opacity: 0.7;
        }
        .footer {
            text-align: center;
            margin-top: 40px;
            opacity: 0.7;
            font-size: 0.8em;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ conversation.title }}</h1>
        <div class="metadata">
            <strong>Project:</strong> {{ project.name }}<br>
            <strong>Created:</strong> {{ conversation.created_at.strftime('%Y-%m-%d %H:%M:%S') }}<br>
            <strong>Participants:</strong> {{ ', '.join(conversation.participants) }}
        </div>
    </div>

    {% if project.description %}
    <div class="message">
        <div class="message-header">
            📋 Project Description
        </div>
        <div class="content">{{ project.description }}</div>
    </div>
    {% endif %}

    {% for message in messages %}
    <div class="message {{ message.participant }}">
        <div class="message-header">
            <span class="participant-icon">
                {% if message.participant == 'user' %}👤
                {% elif message.participant == 'openai' %}🤖
                {% elif message.participant == 'xai' %}🤖
                {% else %}💬{% endif %}
            </span>
            <span>
                {% if message.participant == 'user' %}You
                {% elif message.participant == 'openai' %}OpenAI
                {% elif message.participant == 'xai' %}xAI
                {% else %}{{ message.participant.title() }}{% endif %}
            </span>
            <span class="timestamp">{{ message.timestamp.strftime('%H:%M:%S') }}</span>
        </div>
        <div class="content">{{ message.content }}</div>
    </div>
    {% endfor %}

    <div class="statistics">
        <h3>📊 Conversation Statistics</h3>
        <div class="stat-grid">
            <div class="stat-item">
                <div class="stat-value">{{ statistics.total_messages }}</div>
                <div class="stat-label">Total Messages</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{{ statistics.user_messages }}</div>
                <div class="stat-label">User Messages</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{{ statistics.openai_messages }}</div>
                <div class="stat-label">OpenAI Messages</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{{ statistics.xai_messages }}</div>
                <div class="stat-label">xAI Messages</div>
            </div>
        </div>
        <p style="text-align: center; margin-top: 20px;">
            <strong>Duration:</strong> {{ statistics.duration }}
        </p>
    </div>

    <div class="footer">
        Exported on {{ export_timestamp }} by Eunice v1.0
    </div>
</body>
</html>
        """
        
        template = Template(template_str)
        
        statistics = {
            "total_messages": len(session.messages),
            "user_messages": len([m for m in session.messages if m.participant == "user"]),
            "openai_messages": len([m for m in session.messages if m.participant == "openai"]),
            "xai_messages": len([m for m in session.messages if m.participant == "xai"]),
            "duration": self._calculate_duration(session.messages)
        }
        
        html_content = template.render(
            conversation=session.conversation,
            project=session.project or type('obj', (object,), {'name': 'Unknown', 'description': ''})(),
            messages=session.messages,
            statistics=statistics,
            export_timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        
        filepath = self.export_path / f"{filename}.html"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(filepath)
    
    def _export_pdf(self, session: ConversationSession, filename: str) -> str:
        """Export conversation as PDF."""
        if not PDF_AVAILABLE:
            raise ImportError("PDF export requires reportlab. Install with: pip install reportlab")
        
        filepath = self.export_path / f"{filename}.pdf"
        doc = SimpleDocTemplate(str(filepath), pagesize=letter)
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=18,
            spaceAfter=20,
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceBefore=15,
            spaceAfter=10,
        )
        
        story = []
        
        # Title
        story.append(Paragraph(session.conversation.title, title_style))
        story.append(Spacer(1, 12))
        
        # Metadata
        metadata_text = f"""
        <b>Project:</b> {session.project.name if session.project else 'Unknown'}<br/>
        <b>Created:</b> {session.conversation.created_at.strftime('%Y-%m-%d %H:%M:%S')}<br/>
        <b>Participants:</b> {', '.join(session.conversation.participants)}
        """
        story.append(Paragraph(metadata_text, styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Description
        if session.project and session.project.description:
            story.append(Paragraph("Project Description", heading_style))
            story.append(Paragraph(session.project.description, styles['Normal']))
            story.append(Spacer(1, 20))
        
        # Conversation
        story.append(Paragraph("Conversation", heading_style))
        
        for msg in session.messages:
            timestamp = msg.timestamp.strftime("%H:%M:%S")
            participant_name = {
                "user": "You",
                "openai": "OpenAI", 
                "xai": "xAI"
            }.get(msg.participant, msg.participant.title())
            
            # Message header
            header_text = f"<b>{participant_name}</b> [{timestamp}]"
            story.append(Paragraph(header_text, styles['Heading3']))
            
            # Message content
            content = msg.content.replace('\n', '<br/>')
            story.append(Paragraph(content, styles['Normal']))
            story.append(Spacer(1, 12))
        
        # Statistics
        story.append(Spacer(1, 20))
        story.append(Paragraph("Statistics", heading_style))
        
        stats_text = f"""
        <b>Total Messages:</b> {len(session.messages)}<br/>
        <b>User Messages:</b> {len([m for m in session.messages if m.participant == 'user'])}<br/>
        <b>OpenAI Messages:</b> {len([m for m in session.messages if m.participant == 'openai'])}<br/>
        <b>xAI Messages:</b> {len([m for m in session.messages if m.participant == 'xai'])}<br/>
        <b>Duration:</b> {self._calculate_duration(session.messages)}
        """
        story.append(Paragraph(stats_text, styles['Normal']))
        
        # Footer
        story.append(Spacer(1, 20))
        footer_text = f"<i>Exported on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by Eunice v1.0</i>"
        story.append(Paragraph(footer_text, styles['Normal']))
        
        doc.build(story)
        return str(filepath)
    
    def _calculate_duration(self, messages: List[Message]) -> str:
        """Calculate conversation duration."""
        if len(messages) < 2:
            return "N/A"
        
        start_time = min(msg.timestamp for msg in messages)
        end_time = max(msg.timestamp for msg in messages)
        duration = end_time - start_time
        
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    def list_exports(self) -> List[Dict[str, Any]]:
        """List all exported files."""
        exports = []
        for filepath in self.export_path.iterdir():
            if filepath.is_file():
                exports.append({
                    "filename": filepath.name,
                    "format": filepath.suffix[1:].upper(),
                    "size": filepath.stat().st_size,
                    "created": datetime.fromtimestamp(filepath.stat().st_ctime),
                    "path": str(filepath)
                })
        
        return sorted(exports, key=lambda x: x["created"], reverse=True)
    
    def get_export_formats(self) -> List[str]:
        """Get list of available export formats."""
        formats = ["json", "markdown", "html"]
        if PDF_AVAILABLE:
            formats.append("pdf")
        return formats
    
    # Compatibility methods for tests
    def export_to_json(self, conversation_data: Dict[str, Any], filename: str) -> str:
        """Export conversation data to JSON format."""
        # Convert dict to ConversationSession-like object for compatibility
        from datetime import datetime
        
        def parse_datetime(dt_value):
            """Parse datetime from string or return datetime object."""
            if isinstance(dt_value, str):
                try:
                    return datetime.fromisoformat(dt_value.replace('Z', '+00:00'))
                except ValueError:
                    return datetime.now()
            elif isinstance(dt_value, datetime):
                return dt_value
            else:
                return datetime.now()
        
        # Create a minimal session object
        class MockSession:
            def __init__(self, data):
                self.conversation = type('obj', (object,), {
                    'id': data.get('id', data.get('conversation_id', 'export-id')),
                    'title': data.get('title', 'Exported Conversation'),
                    'created_at': parse_datetime(data.get('created_at', datetime.now())),
                    'updated_at': parse_datetime(data.get('updated_at', datetime.now())),
                    'participants': data.get('participants', ['user', 'assistant']),
                    'status': data.get('status', 'active')
                })()
                self.project = type('obj', (object,), {
                    'id': data.get('project_id', 'project-id'),
                    'name': data.get('project_name', 'Test Project'),
                    'description': data.get('project_description', 'Test project description')
                })()
                self.messages = []
                # Convert messages if they exist
                for msg_data in data.get('messages', []):
                    msg = type('obj', (object,), {
                        'id': msg_data.get('id', f'msg-{len(self.messages)}'),
                        'participant': msg_data.get('participant', 'user'),
                        'content': msg_data.get('content', ''),
                        'timestamp': parse_datetime(msg_data.get('timestamp', datetime.now())),
                        'message_type': msg_data.get('message_type', 'text'),
                        'metadata': msg_data.get('metadata', {}),
                        'role': msg_data.get('role', 'user')
                    })()
                    self.messages.append(msg)
        
        mock_session = MockSession(conversation_data)
        return self._export_json(mock_session, filename)
    
    def export_to_markdown(self, conversation_data: Dict[str, Any], filename: str) -> str:
        """Export conversation data to Markdown format."""
        from datetime import datetime
        
        def parse_datetime(dt_value):
            """Parse datetime from string or return datetime object."""
            if isinstance(dt_value, str):
                try:
                    return datetime.fromisoformat(dt_value.replace('Z', '+00:00'))
                except ValueError:
                    return datetime.now()
            elif isinstance(dt_value, datetime):
                return dt_value
            else:
                return datetime.now()
        
        # Create a minimal session object
        class MockSession:
            def __init__(self, data):
                self.conversation = type('obj', (object,), {
                    'id': data.get('id', data.get('conversation_id', 'export-id')),
                    'title': data.get('title', 'Exported Conversation'),
                    'created_at': parse_datetime(data.get('created_at', datetime.now())),
                    'updated_at': parse_datetime(data.get('updated_at', datetime.now())),
                    'participants': data.get('participants', ['user', 'assistant']),
                    'status': data.get('status', 'active')
                })()
                self.project = type('obj', (object,), {
                    'id': data.get('project_id', 'project-id'),
                    'name': data.get('project_name', 'Test Project'),
                    'description': data.get('project_description', 'Test project description')
                })()
                self.messages = []
                # Convert messages if they exist
                for msg_data in data.get('messages', []):
                    msg = type('obj', (object,), {
                        'id': msg_data.get('id', f'msg-{len(self.messages)}'),
                        'participant': msg_data.get('participant', 'user'),
                        'content': msg_data.get('content', ''),
                        'timestamp': parse_datetime(msg_data.get('timestamp', datetime.now())),
                        'message_type': msg_data.get('message_type', 'text'),
                        'metadata': msg_data.get('metadata', {}),
                        'role': msg_data.get('role', 'user')
                    })()
                    self.messages.append(msg)
        
        mock_session = MockSession(conversation_data)
        return self._export_markdown(mock_session, filename)
    
    def export_to_pdf(self, conversation_data: Dict[str, Any], filename: str) -> str:
        """Export conversation data to PDF format."""
        from datetime import datetime
        
        def parse_datetime(dt_value):
            """Parse datetime from string or return datetime object."""
            if isinstance(dt_value, str):
                try:
                    return datetime.fromisoformat(dt_value.replace('Z', '+00:00'))
                except ValueError:
                    return datetime.now()
            elif isinstance(dt_value, datetime):
                return dt_value
            else:
                return datetime.now()
        
        # Create a minimal session object
        class MockSession:
            def __init__(self, data):
                self.conversation = type('obj', (object,), {
                    'id': data.get('id', data.get('conversation_id', 'export-id')),
                    'title': data.get('title', 'Exported Conversation'),
                    'created_at': parse_datetime(data.get('created_at', datetime.now())),
                    'updated_at': parse_datetime(data.get('updated_at', datetime.now())),
                    'participants': data.get('participants', ['user', 'assistant']),
                    'status': data.get('status', 'active')
                })()
                self.project = type('obj', (object,), {
                    'id': data.get('project_id', 'project-id'),
                    'name': data.get('project_name', 'Test Project'),
                    'description': data.get('project_description', 'Test project description')
                })()
                self.messages = []
                # Convert messages if they exist
                for msg_data in data.get('messages', []):
                    msg = type('obj', (object,), {
                        'id': msg_data.get('id', f'msg-{len(self.messages)}'),
                        'participant': msg_data.get('participant', 'user'),
                        'content': msg_data.get('content', ''),
                        'timestamp': parse_datetime(msg_data.get('timestamp', datetime.now())),
                        'message_type': msg_data.get('message_type', 'text'),
                        'metadata': msg_data.get('metadata', {}),
                        'role': msg_data.get('role', 'user')
                    })()
                    self.messages.append(msg)
        
        mock_session = MockSession(conversation_data)
        return self._export_pdf(mock_session, filename)
    
    def export_conversation_session(self, session: ConversationSession, format_type: str) -> str:
        """Export a conversation session in the specified format."""
        return self.export_conversation(session, format_type)
    
    def cleanup_old_exports(self, retention_days: int = 30) -> int:
        """Clean up old export files."""
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        cleaned_count = 0
        
        for filepath in self.export_path.iterdir():
            if filepath.is_file():
                file_time = datetime.fromtimestamp(filepath.stat().st_ctime)
                if file_time < cutoff_date:
                    try:
                        filepath.unlink()
                        cleaned_count += 1
                    except OSError:
                        pass  # Ignore errors for files in use
        
        return cleaned_count

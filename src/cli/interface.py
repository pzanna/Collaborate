"""Basic CLI interface for the Collaborate application."""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from ..config.config_manager import ConfigManager
from ..storage.database import DatabaseManager
from ..core.ai_client_manager import AIClientManager
from ..models.data_models import Project, Conversation, Message

console = Console()


class CollaborateCLI:
    """Main CLI interface for the Collaborate application."""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.db_manager = DatabaseManager(self.config_manager.config.storage.database_path)
        try:
            self.ai_manager = AIClientManager(self.config_manager)
        except Exception as e:
            console.print(f"[red]Warning: Could not initialize AI clients: {e}[/red]")
            self.ai_manager = None
    
    def show_welcome(self):
        """Display welcome message."""
        welcome_text = Text("Welcome to Collaborate", style="bold blue")
        welcome_panel = Panel(
            welcome_text,
            subtitle="Three-Way AI Collaboration Platform",
            border_style="blue"
        )
        console.print(welcome_panel)
    
    def list_projects(self):
        """List all projects."""
        projects = self.db_manager.list_projects()
        
        if not projects:
            console.print("[yellow]No projects found. Create a project first.[/yellow]")
            return
        
        table = Table(title="Projects")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Description", style="green")
        table.add_column("Updated", style="yellow")
        
        for project in projects:
            table.add_row(
                project.id[:8] + "...",
                project.name,
                project.description[:50] + "..." if len(project.description) > 50 else project.description,
                project.updated_at.strftime("%Y-%m-%d %H:%M")
            )
        
        console.print(table)
    
    def create_project(self, name: str, description: str = ""):
        """Create a new project."""
        project = Project(name=name, description=description)
        self.db_manager.create_project(project)
        console.print(f"[green]Created project: {name} (ID: {project.id})[/green]")
        return project
    
    def list_conversations(self, project_id: str = None):
        """List conversations for a project."""
        conversations = self.db_manager.list_conversations(project_id)
        
        if not conversations:
            console.print("[yellow]No conversations found.[/yellow]")
            return
        
        table = Table(title="Conversations")
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="magenta")
        table.add_column("Status", style="green")
        table.add_column("Updated", style="yellow")
        
        for conv in conversations:
            table.add_row(
                conv.id[:8] + "...",
                conv.title,
                conv.status,
                conv.updated_at.strftime("%Y-%m-%d %H:%M")
            )
        
        console.print(table)
    
    def start_conversation(self, project_id: str, title: str):
        """Start a new conversation."""
        # Check if project exists
        project = self.db_manager.get_project(project_id)
        if not project:
            console.print(f"[red]Project {project_id} not found.[/red]")
            return None
        
        conversation = Conversation(project_id=project_id, title=title)
        self.db_manager.create_conversation(conversation)
        console.print(f"[green]Started conversation: {title} (ID: {conversation.id})[/green]")
        return conversation
    
    def show_conversation(self, conversation_id: str):
        """Display a conversation with its messages."""
        session = self.db_manager.get_conversation_session(conversation_id)
        if not session:
            console.print(f"[red]Conversation {conversation_id} not found.[/red]")
            return
        
        # Display conversation header
        conv_panel = Panel(
            f"Title: {session.conversation.title}\n"
            f"Project: {session.project.name if session.project else 'Unknown'}\n"
            f"Participants: {', '.join(session.conversation.participants)}\n"
            f"Status: {session.conversation.status}",
            title="Conversation Details",
            border_style="blue"
        )
        console.print(conv_panel)
        
        # Display messages
        if session.messages:
            console.print("\n[bold]Messages:[/bold]")
            for msg in session.messages:
                style = {
                    "user": "bold green",
                    "openai": "bold blue",
                    "xai": "bold magenta"
                }.get(msg.participant, "white")
                
                message_panel = Panel(
                    msg.content,
                    title=f"{msg.participant.upper()} - {msg.timestamp.strftime('%H:%M:%S')}",
                    border_style=style.split()[1] if "bold" in style else style
                )
                console.print(message_panel)
        else:
            console.print("[yellow]No messages in this conversation yet.[/yellow]")
    
    def test_ai_connection(self):
        """Test AI client connections."""
        if not self.ai_manager:
            console.print("[red]AI manager not initialized.[/red]")
            return
        
        providers = self.ai_manager.get_available_providers()
        
        if not providers:
            console.print("[red]No AI providers available.[/red]")
            return
        
        console.print(f"[green]Available AI providers: {', '.join(providers)}[/green]")
        
        # Test with a simple message
        test_messages = [
            Message(
                conversation_id="test",
                participant="user",
                content="Hello! This is a test message."
            )
        ]
        
        responses = self.ai_manager.get_all_responses(test_messages)
        
        for provider, response in responses.items():
            console.print(f"\n[bold]{provider.upper()}:[/bold]")
            console.print(Panel(response, border_style="green" if not response.startswith("Error") else "red"))


@click.group()
@click.pass_context
def cli(ctx):
    """Collaborate - Three-Way AI Collaboration Platform"""
    ctx.ensure_object(dict)
    ctx.obj['cli'] = CollaborateCLI()


@cli.command()
@click.pass_context
def welcome(ctx):
    """Show welcome message"""
    ctx.obj['cli'].show_welcome()


@cli.command()
@click.pass_context
def projects(ctx):
    """List all projects"""
    ctx.obj['cli'].list_projects()


@cli.command()
@click.argument('name')
@click.option('--description', '-d', default='', help='Project description')
@click.pass_context
def create_project(ctx, name, description):
    """Create a new project"""
    ctx.obj['cli'].create_project(name, description)


@cli.command()
@click.option('--project-id', '-p', help='Filter by project ID')
@click.pass_context
def conversations(ctx, project_id):
    """List conversations"""
    ctx.obj['cli'].list_conversations(project_id)


@cli.command()
@click.argument('project_id')
@click.argument('title')
@click.pass_context
def start(ctx, project_id, title):
    """Start a new conversation"""
    ctx.obj['cli'].start_conversation(project_id, title)


@cli.command()
@click.argument('conversation_id')
@click.pass_context
def show(ctx, conversation_id):
    """Show a conversation"""
    ctx.obj['cli'].show_conversation(conversation_id)


@cli.command()
@click.pass_context
def test_ai(ctx):
    """Test AI client connections"""
    ctx.obj['cli'].test_ai_connection()


if __name__ == '__main__':
    cli()

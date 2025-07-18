#!/usr/bin/env python3
"""
Enhanced Collaborate - Three-Way AI Collaboration Platform with Real-Time Streaming

This CLI application provides a comprehensive interface for AI collaboration
with enhanced real-time streaming capabilities for natural conversations.

Features:
- Real-time word-by-word streaming responses
- Natural AI-to-AI conversation handoffs
- Interruption detection and handling
- Smart response coordination
- Conversation repair mechanics
- Full database management
- Export capabilities
- Health monitoring

Usage:
    python collaborate.py              # Interactive CLI
    python collaborate.py --demo       # Show streaming improvements demo
    python collaborate.py --health     # Check system health
"""

import os
import sys
import argparse
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config.config_manager import ConfigManager
from storage.database import DatabaseManager
from core.ai_client_manager import AIClientManager
from core.streaming_coordinator import StreamingResponseCoordinator
from models.data_models import Project, Conversation, Message
from utils.export_manager import ExportManager
from utils.error_handler import (
    get_error_handler, safe_execute, format_error_for_user, 
    CollaborateError, NetworkError, APIError, DatabaseError
)
import asyncio
import sys
from typing import List


class EnhancedCollaborationManager:
    """Enhanced collaboration manager with real-time streaming support."""
    
    def __init__(self, config_manager, db_manager, ai_manager):
        self.config_manager = config_manager
        self.db_manager = db_manager
        self.ai_manager = ai_manager
        self.streaming_coordinator = StreamingResponseCoordinator(
            config_manager=config_manager,
            ai_manager=ai_manager,
            db_manager=db_manager
        )
        
    async def stream_conversation_response(
        self, 
        user_message: Message, 
        context: List[Message],
        conversation_id: str
    ):
        """Stream AI responses in real-time for a more natural conversation flow."""
        
        available_providers = self.ai_manager.get_available_providers()
        if not available_providers:
            print("❌ No AI providers available")
            return
        
        print(f"\n💭 Processing: '{user_message.content[:50]}{'...' if len(user_message.content) > 50 else ''}'")
        
        # Track responses for database storage
        completed_responses = {}
        
        try:
            async for update in self.streaming_coordinator.stream_conversation_chain(
                user_message, context
            ):
                update_type = update.get('type')
                
                if update_type == 'queue_determined':
                    providers = update.get('queue', [])
                    print(f"🎯 Response queue: {' → '.join(providers)}")
                    
                elif update_type == 'interruption_detected':
                    providers = update.get('providers', [])
                    print(f"🚨 Interruption! Prioritizing: {', '.join(providers)}")
                    
                elif update_type == 'repair_needed':
                    provider = update.get('provider', '')
                    print(f"🔧 Routing clarification to {provider.upper()}")
                    
                elif update_type == 'provider_starting':
                    provider = update.get('provider', '')
                    position = update.get('position', 0)
                    total = update.get('total', 0)
                    print(f"\n🤖 {provider.upper()} ({position}/{total}): ", end='', flush=True)
                    
                elif update_type == 'response_chunk':
                    chunk = update.get('chunk', '')
                    print(chunk, end='', flush=True)
                    
                elif update_type == 'token':
                    content = update.get('content', '')
                    print(content, end='', flush=True)
                    
                elif update_type == 'provider_completed':
                    provider = update.get('provider', '')
                    response = update.get('response', '')
                    completed_responses[provider] = response
                    print(f"\n✅ {provider.upper()} completed and saved")
                    
                elif update_type == 'chain_detected':
                    from_provider = update.get('from_provider', '')
                    to_provider = update.get('to_provider', '')
                    print(f"\n🔗 {from_provider.upper()} is calling on {to_provider.upper()}")
                    
                elif update_type == 'queue_updated':
                    added_provider = update.get('added_provider', '')
                    print(f"📝 Added {added_provider.upper()} to speaking queue")
                    
                elif update_type == 'provider_error':
                    provider = update.get('provider', '')
                    error = update.get('error', '')
                    print(f"\n❌ Error from {provider.upper()}: {error}")
                    
                elif update_type == 'conversation_completed':
                    total_providers = update.get('total_providers', 0)
                    print(f"\n🎉 Conversation chain completed ({total_providers} responses)")
                    
                # Small delay for readability
                await asyncio.sleep(0.01)
                
        except Exception as e:
            print(f"\n❌ Streaming error: {e}")
            
        return completed_responses
    
    def get_streaming_vs_batch_comparison(self):
        """Return comparison data for streaming vs batch processing."""
        return {
            'batch_processing': {
                'flow': 'User → Wait → All responses at once',
                'user_experience': 'Long wait, then information dump',
                'conversation_feel': 'Robotic, disconnected',
                'chaining': 'No real-time chaining',
                'interruptions': 'Cannot handle mid-conversation interruptions',
                'typical_wait_time': '10-30 seconds'
            },
            'streaming_processing': {
                'flow': 'User → Immediate response stream → Chain continues',
                'user_experience': 'Immediate feedback, natural progression',
                'conversation_feel': 'Slack-like, engaging',
                'chaining': 'Real-time AI-to-AI handoffs',
                'interruptions': 'Can detect and respond to interruptions',
                'typical_wait_time': '1-3 seconds to first response'
            },
            'benefits': [
                'More engaging conversation experience',
                'Natural AI-to-AI collaboration in real-time',
                'Better handling of conversational interruptions',
                'Immediate visual feedback on progress',
                'Feels like chatting with real people on Slack',
                'Enables true conversation repair mechanics'
            ]
        }


class SimpleCollaborateCLI:
    """Simple CLI for testing the Collaborate application."""
    
    def __init__(self):
        print("🚀 Initializing Collaborate...")
        
        # Initialize components
        self.config_manager = ConfigManager()
        self.db_manager = DatabaseManager(self.config_manager.config.storage.database_path)
        self.export_manager = ExportManager(self.config_manager.config.storage.export_path)
        
        try:
            self.ai_manager = AIClientManager(self.config_manager)
            available_providers = self.ai_manager.get_available_providers()
            
            # Initialize streaming coordinator
            self.streaming_coordinator = StreamingResponseCoordinator(
                config_manager=self.config_manager,
                ai_manager=self.ai_manager,
                db_manager=self.db_manager
            )
            
            # Initialize enhanced collaboration manager
            self.enhanced_manager = EnhancedCollaborationManager(
                self.config_manager, 
                self.db_manager, 
                self.ai_manager
            )
            
            print(f"✓ AI providers available: {', '.join(available_providers)}")
            print("✓ Real-time streaming enabled")
            print("✓ Enhanced collaboration features enabled")
        except Exception as e:
            print(f"⚠ AI providers not available: {e}")
            self.ai_manager = None
            self.streaming_coordinator = None
            self.enhanced_manager = None
        
        print("✓ Collaborate initialized successfully!\n")
    
    def show_menu(self):
        """Display the main menu."""
        print("=" * 60)
        print("🤝 COLLABORATE - Three-Way AI Collaboration Platform")
        print("✨ Real-Time Streaming Mode")
        print("=" * 60)
        print("1. List Projects")
        print("2. Create Project")
        print("3. List Conversations")
        print("4. Start Conversation (Real-Time Streaming)")
        print("5. Resume Conversation (Real-Time Streaming)")
        print("6. Test AI Connections")
        print("7. Show Configuration")
        print("8. Export Data")
        print("9. View Response Statistics")
        print("10. Configure Smart Responses")
        print("11. System Health & Diagnostics")
        print("12. Enhanced Streaming Demo")
        print("13. Streaming vs Batch Comparison")
        print("0. Exit")
        print("=" * 60)
    
    def list_projects(self):
        """List all projects with enhanced error handling."""
        try:
            projects = self.db_manager.list_projects()
            
            if not projects:
                print("📁 No projects found. Create a project first.")
                return
            
            print("\n📁 Projects:")
            print("-" * 40)
            for i, project in enumerate(projects, 1):
                print(f"{i}. {project.name}")
                print(f"   ID: {project.id}")
                print(f"   Description: {project.description}")
                print(f"   Updated: {project.updated_at.strftime('%Y-%m-%d %H:%M')}")
                print()
        except Exception as e:
            print(f"❌ Error listing projects: {e}")
            print("   Please check your database connection and try again.")
    
    def create_project(self):
        """Create a new project with enhanced error handling."""
        print("\n📁 Create New Project")
        print("-" * 30)
        
        try:
            name = self.safe_input("Project name: ").strip()
            if not name:
                print("❌ Project name cannot be empty")
                return
            
            if len(name) > 255:
                print("❌ Project name too long (max 255 characters)")
                return
            
            description = self.safe_input("Project description: ").strip()
            
            project = Project(name=name, description=description)
            
            # Attempt to create project
            created_project = self.db_manager.create_project(project)
            
            if created_project:
                print(f"✅ Project '{name}' created successfully!")
                print(f"   ID: {created_project.id}")
            else:
                print("❌ Failed to create project. Please try again.")
                
        except CollaborateError as e:
            print(format_error_for_user(e))
        except KeyboardInterrupt:
            print("\n❌ Project creation cancelled")
        except Exception as e:
            print(f"❌ Unexpected error creating project: {e}")
    
    def list_conversations(self):
        """List all conversations with enhanced error handling."""
        try:
            conversations = self.db_manager.list_conversations()
            
            if not conversations:
                print("💬 No conversations found. Start a conversation first.")
                return
            
            print("\n💬 Conversations:")
            print("-" * 40)
            for i, conv in enumerate(conversations, 1):
                project = self.db_manager.get_project(conv.project_id)
                project_name = project.name if project else "Unknown"
                
                print(f"{i}. {conv.title}")
                print(f"   ID: {conv.id}")
                print(f"   Project: {project_name}")
                print(f"   Status: {conv.status}")
                print(f"   Updated: {conv.updated_at.strftime('%Y-%m-%d %H:%M')}")
                print()
        except Exception as e:
            print(f"❌ Error listing conversations: {e}")
            print("   Please check your database connection and try again.")
    
    def start_conversation(self):
        """Start a new conversation with enhanced error handling."""
        print("\n💬 Start New Conversation")
        print("-" * 30)
        
        try:
            # First, show available projects
            projects = self.db_manager.list_projects()
            if not projects:
                print("❌ No projects available. Create a project first.")
                return

            print("Available projects:")
            for i, project in enumerate(projects, 1):
                print(f"{i}. {project.name}")

            try:
                project_choice = int(self.safe_input(f"Select project (1-{len(projects)}): "))
                if project_choice < 1 or project_choice > len(projects):
                    print("❌ Invalid selection.")
                    return

                selected_project = projects[project_choice - 1]
            except ValueError:
                print("❌ Invalid input. Please enter a number.")
                return

            # Get conversation title
            title = self.safe_input("Conversation title: ").strip()
            if not title:
                print("❌ Conversation title cannot be empty")
                return

            # Create conversation
            conversation = Conversation(
                project_id=selected_project.id,
                title=title
            )

            created_conversation = self.db_manager.create_conversation(conversation)
            
            if created_conversation:
                print(f"✅ Conversation '{title}' created successfully!")
                print(f"   ID: {created_conversation.id}")
                
                # Ask if user wants to start chatting immediately
                if self.safe_input("\nStart chatting now? (y/n): ").lower().startswith('y'):
                    self.run_conversation(created_conversation.id)
            else:
                print("❌ Failed to create conversation. Please try again.")

        except CollaborateError as e:
            print(format_error_for_user(e))
        except KeyboardInterrupt:
            print("\n❌ Conversation creation cancelled")
        except Exception as e:
            print(f"❌ Unexpected error starting conversation: {e}")
    
    def run_conversation(self, conversation_id: str):
        """Run a conversation session with real-time streaming."""
        session = self.db_manager.get_conversation_session(conversation_id)
        if not session:
            print("❌ Conversation not found.")
            return
        
        print(f"\n🤝 Starting conversation: {session.conversation.title}")
        print("=" * 60)
        print("Type 'exit' to end the conversation")
        print("Type 'history' to see conversation history")
        print("✨ Real-time streaming enabled - responses appear as they're generated")
        print("=" * 60)
        
        # Show existing messages
        if session.messages:
            print("\n📜 Conversation History:")
            self.show_messages(session.messages)
        
        # Run async conversation loop
        try:
            asyncio.run(self._async_conversation_loop(conversation_id))
        except KeyboardInterrupt:
            print("\n👋 Ending conversation...")
        except Exception as e:
            print(f"❌ Error in conversation: {e}")
    
    async def _async_conversation_loop(self, conversation_id: str):
        """Async conversation loop for real-time streaming."""
        while True:
            try:
                # Get user input (this blocks, but that's OK for CLI)
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, self._get_user_input
                )
                
                if user_input.lower() == 'exit':
                    print("👋 Ending conversation...")
                    break
                
                if user_input.lower() == 'history':
                    session = self.db_manager.get_conversation_session(conversation_id)
                    if session.messages:
                        print("\n📜 Conversation History:")
                        self.show_messages(session.messages)
                    else:
                        print("📜 No messages in conversation yet.")
                    continue
                
                if not user_input.strip():
                    continue
                
                # Create and save user message
                user_message = Message(
                    conversation_id=conversation_id,
                    participant="user",
                    content=user_input
                )
                self.db_manager.create_message(user_message)
                
                # Get context and stream AI responses
                if self.streaming_coordinator:
                    session = self.db_manager.get_conversation_session(conversation_id)
                    context_messages = session.get_context_messages(
                        self.config_manager.config.conversation.max_context_tokens
                    )
                    
                    print("\n🤖 AI responses (streaming):")
                    print("-" * 40)
                    
                    # Stream the conversation chain
                    try:
                        response_count = 0
                        async for update in self.streaming_coordinator.stream_conversation_chain(
                            user_message, context_messages
                        ):
                            # Display real-time updates
                            if update.get('type') == "provider_starting":
                                print(f"\n💭 {update.get('provider', '').upper()} is thinking...", flush=True)
                            elif update.get('type') == "provider_response_start":
                                print(f"\n🤖 {update.get('provider', '').upper()}: ", end="", flush=True)
                            elif update.get('type') == "token":
                                print(update.get('content', ''), end="", flush=True)
                            elif update.get('type') == "response_chunk":
                                print(update.get('chunk', ''), end="", flush=True)
                            elif update.get('type') == "provider_completed":
                                # print(f"\n✓ {update.get('provider', '')} completed")
                                print(f"\n")
                                response_count += 1
                            elif update.get('type') == "conversation_completed":
                                print(f"\n📋 Chain completed: {update.get('total_providers', 0)} provider(s) responded")
                            elif update.get('type') == "queue_determined":
                                print(f"🎯 Response queue: {', '.join(update.get('queue', []))}")
                            elif update.get('type') == "provider_error":
                                print(f"\n❌ {update.get('message', '')}")
                            elif update.get('type') == "database_error":
                                print(f"\n⚠️ {update.get('message', '')}")
                        
                        if response_count == 0:
                            print("⚠ No AI responses generated")
                    
                    except Exception as e:
                        print(f"\n❌ Streaming error: {e}")
                        print("🔄 Falling back to batch mode...")
                        
                        # Emergency fallback to batch mode
                        if self.ai_manager:
                            responses = self.ai_manager.get_smart_responses(context_messages)
                            for provider, response in responses.items():
                                if not response.startswith("Error:"):
                                    print(f"\n🤖 {provider.upper()}: {response}")
                                    # Create AI message
                                    try:
                                        ai_message = Message(
                                            conversation_id=conversation_id,
                                            participant=provider,
                                            content=response
                                        )
                                        self.db_manager.create_message(ai_message)
                                    except Exception as save_e:
                                        print(f"⚠️ Error saving AI response: {save_e}")
                        else:
                            print("⚠ AI manager not available for fallback")
                    
                    print()  # Add final newline
                else:
                    print("⚠ Streaming not available. Message saved but no AI responses.")
                
            except KeyboardInterrupt:
                print("\n👋 Ending conversation...")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    def _get_user_input(self) -> str:
        """Get user input synchronously."""
        return self.safe_input("\n👤 You: ").strip()
    
    def get_ai_responses(self, conversation_id: str):
        """Get responses from AI providers using smart response logic with enhanced error handling."""
        try:
            session = self.db_manager.get_conversation_session(conversation_id)
            if not session:
                print("❌ Could not load conversation session")
                return

            # Get context messages (recent conversation history)
            context_messages = session.get_context_messages(
                self.config_manager.config.conversation.max_context_tokens
            )

            # Use smart response logic to determine which AIs should respond
            if self.ai_manager:
                responses = self.ai_manager.get_smart_responses(context_messages)
            else:
                print("⚠️  AI manager not available.")
                return

            if not responses:
                print("⚠️  No AI responses generated. This might be due to:")
                print("   • Network connectivity issues")
                print("   • API key problems")
                print("   • Service temporarily unavailable")
                print("   • Smart response logic filtered out all responses")
                return

            # Display and save responses
            successful_responses = 0
            for provider, response in responses.items():
                if not response.startswith("Error:"):
                    print(f"\n🤖 {provider.upper()}: {response}")
                    
                    # Create AI message
                    try:
                        ai_message = Message(
                            conversation_id=conversation_id,
                            participant=provider,
                            content=response
                        )
                        self.db_manager.create_message(ai_message)
                        successful_responses += 1
                    except Exception as e:
                        print(f"⚠️  Failed to save response from {provider}: {e}")
                else:
                    print(f"\n❌ {provider.upper()}: {response}")

            # Show response stats if multiple AIs responded
            if successful_responses > 1:
                print(f"\n📊 {successful_responses} AI(s) responded successfully")
            elif successful_responses == 1:
                print(f"\n📊 1 AI responded successfully")
            else:
                print(f"\n⚠️  No responses were saved successfully")

        except CollaborateError as e:
            print(format_error_for_user(e))
        except Exception as e:
            print(f"❌ Unexpected error getting AI responses: {e}")
            print("   Please try again or contact support if the issue persists.")

    def show_messages(self, messages):
        """Display messages in a formatted way."""
        for msg in messages:
            timestamp = msg.timestamp.strftime("%H:%M:%S")
            if msg.participant == "user":
                print(f"[{timestamp}] 👤 You: {msg.content}")
            else:
                print(f"[{timestamp}] 🤖 {msg.participant.upper()}: {msg.content}")
    
    def test_ai_connections(self):
        """Test AI connections and streaming capability."""
        print("\n🔧 Testing AI Connections & Streaming")
        print("-" * 40)
        
        if not self.ai_manager:
            print("❌ AI manager not initialized.")
            return
        
        if not self.streaming_coordinator:
            print("❌ Streaming coordinator not initialized.")
            return
        
        providers = self.ai_manager.get_available_providers()
        if not providers:
            print("❌ No AI providers available.")
            return
        
        print(f"Available providers: {', '.join(providers)}")
        print("✨ Real-time streaming: ✓ Ready")
        
        # Test with a simple message
        test_messages = [
            Message(
                conversation_id="test",
                participant="user",
                content="Hello! This is a test message. Please respond briefly."
            )
        ]
        
        for provider in providers:
            try:
                print(f"\n🤖 Testing {provider.upper()}...")
                response = self.ai_manager.get_response(provider, test_messages)
                print(f"✅ {provider.upper()} Response: {response}")
            except Exception as e:
                print(f"❌ {provider.upper()} Error: {e}")
        
        print("\n🚀 All systems ready for real-time streaming conversations!")
    
    def show_configuration(self):
        """Show current configuration."""
        print("\n⚙️ Configuration")
        print("-" * 30)
        
        config = self.config_manager.config
        
        print(f"Database Path: {config.storage.database_path}")
        print(f"Export Path: {config.storage.export_path}")
        print(f"Max Context Tokens: {config.conversation.max_context_tokens}")
        print(f"Auto Save: {config.conversation.auto_save}")
        print(f"Response Coordination: {config.conversation.response_coordination}")
        print(f"Real-Time Streaming: {'✓ Enabled' if self.streaming_coordinator else '❌ Disabled'}")
        
        print("\nAI Providers:")
        for name, provider_config in config.ai_providers.items():
            print(f"  {name}:")
            print(f"    Model: {provider_config.model}")
            print(f"    Temperature: {provider_config.temperature}")
            print(f"    Max Tokens: {provider_config.max_tokens}")
            print(f"    Role Adaptation: {provider_config.role_adaptation}")
        
        if self.streaming_coordinator:
            print("\n✨ Streaming Features:")
            print("  • Real-time word-by-word response display")
            print("  • Natural conversation flow")
            print("  • Interruption support")
            print("  • Smart response coordination")
    
    def export_data(self):
        """Export data to files."""
        print("\n📤 Export Data")
        print("-" * 30)
        
        # Get export path from config
        export_path = self.config_manager.config.storage.export_path
        if not export_path or not Path(export_path).is_dir():
            print("❌ Invalid export path. Please check your configuration.")
            return
        
        # Get projects and conversations
        projects = self.db_manager.list_projects()
        conversations = self.db_manager.list_conversations()
        
        # Export projects
        for project in projects:
            project_file = Path(export_path) / f"project_{project.id}.txt"
            with open(project_file, 'w', encoding='utf-8') as f:
                f.write(f"Project ID: {project.id}\n")
                f.write(f"Name: {project.name}\n")
                f.write(f"Description: {project.description}\n")
                f.write(f"Updated: {project.updated_at.strftime('%Y-%m-%d %H:%M')}\n")
                f.write("\nConversations:\n")
                
                # Get conversations for the project
                project_convs = [c for c in conversations if c.project_id == project.id]
                for conv in project_convs:
                    f.write(f"- {conv.title} (ID: {conv.id})\n")
            
            print(f"✅ Exported project {project.id} to {project_file}")
        
        print("\n📂 Exported Projects:")
        for file in Path(export_path).glob("project_*.txt"):
            print(f"- {file.name}")
    
    def export_conversation(self):
        """Export a conversation."""
        conversations = self.db_manager.list_conversations()
        
        if not conversations:
            print("📁 No conversations found to export.")
            return
        
        print("\n📋 Available Conversations:")
        print("-" * 40)
        for i, conv in enumerate(conversations, 1):
            project = self.db_manager.get_project(conv.project_id)
            print(f"{i}. {conv.title}")
            print(f"   Project: {project.name if project else 'Unknown'}")
            print(f"   Updated: {conv.updated_at.strftime('%Y-%m-%d %H:%M')}")
            print()
        
        try:
            choice = int(self.safe_input("Select conversation number: "))
            if 1 <= choice <= len(conversations):
                conversation = conversations[choice - 1]
            else:
                print("❌ Invalid conversation number.")
                return
        except ValueError:
            print("❌ Please enter a valid number.")
            return
        
        # Get conversation session
        session = self.db_manager.get_conversation_session(conversation.id)
        if not session:
            print("❌ Failed to load conversation session.")
            return
        
        # Show available formats
        formats = self.export_manager.get_export_formats()
        print("\n📄 Available Export Formats:")
        for i, fmt in enumerate(formats, 1):
            print(f"{i}. {fmt.upper()}")
        
        try:
            format_choice = int(self.safe_input("Select format: "))
            if 1 <= format_choice <= len(formats):
                format_type = formats[format_choice - 1]
            else:
                print("❌ Invalid format number.")
                return
        except ValueError:
            print("❌ Please enter a valid number.")
            return
        
        # Optional custom filename
        custom_filename = self.safe_input("Custom filename (press Enter for auto): ").strip()
        filename = custom_filename if custom_filename else None
        
        try:
            print(f"\n📤 Exporting conversation to {format_type.upper()}...")
            filepath = self.export_manager.export_conversation(session, format_type, filename)
            print(f"✅ Successfully exported to: {filepath}")
            
            # Show file size
            file_size = Path(filepath).stat().st_size
            if file_size < 1024:
                size_str = f"{file_size} bytes"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            else:
                size_str = f"{file_size / (1024 * 1024):.1f} MB"
            print(f"📊 File size: {size_str}")
            
        except Exception as e:
            print(f"❌ Export failed: {e}")
    
    def list_exports(self):
        """List all exported files."""
        exports = self.export_manager.list_exports()
        
        if not exports:
            print("📁 No exported files found.")
            return
        
        print("\n📋 Exported Files:")
        print("-" * 60)
        for export in exports:
            size_kb = export["size"] / 1024
            print(f"📄 {export['filename']}")
            print(f"   Format: {export['format']}")
            print(f"   Size: {size_kb:.1f} KB")
            print(f"   Created: {export['created'].strftime('%Y-%m-%d %H:%M:%S')}")
            print()
    
    def view_response_stats(self):
        """View response statistics for a conversation."""
        print("\n📊 Response Statistics")
        print("-" * 30)
        
        conversations = self.db_manager.list_conversations()
        
        if not conversations:
            print("💬 No conversations found.")
            return
        
        print("Available conversations:")
        for i, conv in enumerate(conversations, 1):
            print(f"{i}. {conv.title}")
        
        try:
            conv_choice = int(self.safe_input(f"Select conversation (1-{len(conversations)}): "))
            if conv_choice < 1 or conv_choice > len(conversations):
                print("❌ Invalid selection.")
                return
            
            selected_conv = conversations[conv_choice - 1]
            session = self.db_manager.get_conversation_session(selected_conv.id)
            
            if not session:
                print("❌ Could not load conversation session.")
                return
            
            # Get statistics
            if self.ai_manager:
                stats = self.ai_manager.get_response_stats(session)
                
                print(f"\n📈 Statistics for: {selected_conv.title}")
                print("-" * 50)
                print(f"Total messages: {stats['total_messages']}")
                print(f"User messages: {stats['user_messages']}")
                print(f"AI responses: {sum(stats['ai_responses'].values())}")
                print("\nResponse breakdown:")
                for provider, count in stats['ai_responses'].items():
                    rate = stats['response_rate'][provider] * 100
                    print(f"  {provider.upper()}: {count} messages ({rate:.1f}%)")
            else:
                print("⚠️  AI manager not available.")
                
        except ValueError:
            print("❌ Invalid input. Please enter a number.")
    
    def configure_smart_responses(self):
        """Configure smart response settings."""
        print("\n⚙️  Smart Response Configuration")
        print("-" * 35)
        
        if not self.ai_manager:
            print("⚠️  AI manager not available.")
            return
        
        print("Current settings:")
        coordinator = self.ai_manager.response_coordinator
        print(f"Response threshold: {coordinator.response_threshold}")
        print(f"Max consecutive responses: {coordinator.max_consecutive_responses}")
        print()
        
        print("1. Update response threshold (0.0-1.0)")
        print("2. Update max consecutive responses")
        print("3. Reset to defaults")
        print("4. Back to main menu")
        
        try:
            choice = int(self.safe_input("Select option (1-4): "))
            
            if choice == 1:
                new_threshold = float(self.safe_input("Enter new threshold (0.0-1.0): "))
                if 0.0 <= new_threshold <= 1.0:
                    self.ai_manager.update_response_settings(response_threshold=new_threshold)
                    print(f"✅ Response threshold updated to {new_threshold}")
                else:
                    print("❌ Invalid threshold. Must be between 0.0 and 1.0.")
            
            elif choice == 2:
                new_max = int(self.safe_input("Enter max consecutive responses (1-10): "))
                if 1 <= new_max <= 10:
                    self.ai_manager.update_response_settings(max_consecutive_responses=new_max)
                    print(f"✅ Max consecutive responses updated to {new_max}")
                else:
                    print("❌ Invalid value. Must be between 1 and 10.")
            
            elif choice == 3:
                self.ai_manager.update_response_settings(
                    response_threshold=0.3,
                    max_consecutive_responses=3
                )
                print("✅ Settings reset to defaults")
            
            elif choice == 4:
                return
            
            else:
                print("❌ Invalid choice.")
                
        except ValueError:
            print("❌ Invalid input. Please enter a number.")
        except Exception as e:
            print(f"❌ Error: {e}")

    def show_system_health(self):
        """Show system health and diagnostics."""
        print("\n🔧 System Health & Diagnostics")
        print("-" * 40)
        
        # Database health
        print("📊 Database Status:")
        db_stats = self.db_manager.get_database_stats()
        if db_stats.get("status") == "healthy":
            print(f"   ✅ Database: {db_stats['status']}")
            print(f"   📁 Projects: {db_stats['projects']}")
            print(f"   💬 Conversations: {db_stats['conversations']}")
            print(f"   📝 Messages: {db_stats['messages']}")
            if db_stats['database_size_bytes'] > 0:
                size_mb = db_stats['database_size_bytes'] / (1024 * 1024)
                print(f"   💾 Database size: {size_mb:.2f} MB")
        else:
            print(f"   ❌ Database: {db_stats.get('status', 'unknown')}")
            if 'error' in db_stats:
                print(f"   Error: {db_stats['error']}")
        
        # AI providers health
        print("\n🤖 AI Providers Status:")
        if self.ai_manager:
            provider_health = self.ai_manager.get_provider_health()
            for provider, health in provider_health.items():
                status_emoji = "✅" if health["status"] == "healthy" else "⚠️" if health["status"] == "degraded" else "❌"
                print(f"   {status_emoji} {provider.upper()}: {health['status']}")
                if health["failure_count"] > 0:
                    print(f"      Failures: {health['failure_count']}/{health['max_retries']}")
        else:
            print("   ❌ AI manager not available")
            
        # Error statistics
        print("\n📈 Error Statistics:")
        error_handler = get_error_handler()
        error_stats = error_handler.get_error_stats()
        
        if error_stats["total_errors"] > 0:
            print(f"   Total errors: {error_stats['total_errors']}")
            for error_type, count in error_stats["error_counts"].items():
                print(f"   {error_type}: {count}")
        else:
            print("   ✅ No errors recorded")
        
        # System recommendations
        print("\n💡 Recommendations:")
        recommendations = []
        
        if db_stats.get("status") != "healthy":
            recommendations.append("• Check database permissions and disk space")
        
        if self.ai_manager:
            provider_health = self.ai_manager.get_provider_health()
            unhealthy_providers = [p for p, h in provider_health.items() if h["status"] == "unhealthy"]
            if unhealthy_providers:
                recommendations.append(f"• Check API keys and connectivity for: {', '.join(unhealthy_providers)}")
        else:
            recommendations.append("• AI manager not available - check configuration and API keys")
        
        if error_stats["total_errors"] > 10:
            recommendations.append("• High error count - consider restarting the application")
        
        if not recommendations:
            recommendations.append("• System is running normally")
        
        for rec in recommendations:
            print(f"   {rec}")

    def check_system_health_standalone(self):
        """Check system health and exit (for non-interactive use)."""
        print("\n🔧 System Health & Diagnostics")
        print("-" * 40)
        
        # Database health
        print("📊 Database Status:")
        db_stats = self.db_manager.get_database_stats()
        if db_stats.get("status") == "healthy":
            print(f"   ✅ Database: {db_stats['status']}")
            print(f"   📁 Projects: {db_stats['projects']}")
            print(f"   💬 Conversations: {db_stats['conversations']}")
            print(f"   📝 Messages: {db_stats['messages']}")
            if db_stats['database_size_bytes'] > 0:
                size_mb = db_stats['database_size_bytes'] / (1024 * 1024)
                print(f"   💾 Database size: {size_mb:.2f} MB")
        else:
            print(f"   ❌ Database: {db_stats.get('status', 'unknown')}")
            if 'error' in db_stats:
                print(f"   Error: {db_stats['error']}")
        
        # AI providers health
        print("\n🤖 AI Providers Status:")
        if self.ai_manager:
            provider_health = self.ai_manager.get_provider_health()
            for provider, health in provider_health.items():
                status_emoji = "✅" if health["status"] == "healthy" else "⚠️" if health["status"] == "degraded" else "❌"
                print(f"   {status_emoji} {provider.upper()}: {health['status']}")
                if health["failure_count"] > 0:
                    print(f"      Failures: {health['failure_count']}/{health['max_retries']}")
        else:
            print("   ❌ AI manager not available")
            
        # Error statistics
        print("\n📈 Error Statistics:")
        error_handler = get_error_handler()
        error_stats = error_handler.get_error_stats()
        
        if error_stats["total_errors"] > 0:
            print(f"   Total errors: {error_stats['total_errors']}")
            for error_type, count in error_stats["error_counts"].items():
                print(f"   {error_type}: {count}")
        else:
            print("   ✅ No errors recorded")
        
        # System recommendations
        print("\n💡 Recommendations:")
        recommendations = []
        
        if db_stats.get("status") != "healthy":
            recommendations.append("• Check database permissions and disk space")
        
        if self.ai_manager:
            provider_health = self.ai_manager.get_provider_health()
            unhealthy_providers = [p for p, h in provider_health.items() if h["status"] == "unhealthy"]
            if unhealthy_providers:
                recommendations.append(f"• Check API keys and connectivity for: {', '.join(unhealthy_providers)}")
        else:
            recommendations.append("• AI manager not available - check configuration and API keys")
        
        if error_stats["total_errors"] > 10:
            recommendations.append("• High error count - consider restarting the application")
        
        if not recommendations:
            recommendations.append("• System is running normally")
        
        for rec in recommendations:
            print(f"   {rec}")
            
        print("")  # Add blank line at end
    
    def safe_input(self, prompt: str) -> str:
        """Safe input handling that gracefully handles EOF errors."""
        try:
            return input(prompt)
        except EOFError:
            print("\n👋 Non-interactive mode detected. Exiting...")
            sys.exit(0)
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            sys.exit(0)

    def run(self):
        """Run the CLI interface."""
        while True:
            try:
                self.show_menu()
                choice = self.safe_input("Select option: ").strip()
                
                if choice == '0':
                    print("👋 Goodbye!")
                    break
                elif choice == '1':
                    self.list_projects()
                elif choice == '2':
                    self.create_project()
                elif choice == '3':
                    self.list_conversations()
                elif choice == '4':
                    self.start_conversation()
                elif choice == '5':
                    self.resume_conversation()
                elif choice == '6':
                    self.test_ai_connections()
                elif choice == '7':
                    self.show_configuration()
                elif choice == '8':
                    self.export_conversation()
                elif choice == '9':
                    self.view_response_stats()
                elif choice == '10':
                    self.configure_smart_responses()
                elif choice == '11':
                    self.show_system_health()
                elif choice == '12':
                    self.enhanced_streaming_demo()
                elif choice == '13':
                    self.show_streaming_comparison()
                else:
                    print("❌ Invalid option. Please try again.")
                
                self.safe_input("\nPress Enter to continue...")
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ An error occurred: {e}")
                self.safe_input("\nPress Enter to continue...")
    
    def resume_conversation(self):
        """Resume an existing conversation."""
        print("\n🔄 Resume Conversation")
        print("-" * 30)
        
        try:
            # Get list of conversations
            conversations = self.db_manager.list_conversations()
            
            if not conversations:
                print("❌ No conversations found. Create a conversation first.")
                return
            
            # Show available conversations
            print("Available conversations:")
            for i, conv in enumerate(conversations, 1):
                project = self.db_manager.get_project(conv.project_id)
                project_name = project.name if project else "Unknown"
                print(f"{i}. {conv.title} (Project: {project_name})")
            
            # Get user choice
            try:
                choice = int(self.safe_input(f"Select conversation (1-{len(conversations)}): "))
                if choice < 1 or choice > len(conversations):
                    print("❌ Invalid selection.")
                    return
                    
                selected_conversation = conversations[choice - 1]
                self.run_conversation(selected_conversation.id)
                
            except ValueError:
                print("❌ Invalid input. Please enter a number.")
                return
                
        except Exception as e:
            print(f"❌ Error resuming conversation: {e}")
    
    def enhanced_streaming_demo(self):
        """Demonstrate enhanced streaming capabilities with a sample conversation."""
        print("\n🚀 Enhanced Streaming Demo")
        print("-" * 40)
        
        if not self.enhanced_manager:
            print("❌ Enhanced streaming not available.")
            return
            
        print("This demo shows the enhanced real-time streaming capabilities.")
        print("It demonstrates how AI responses flow naturally in real-time.")
        print("\nFeatures demonstrated:")
        print("• Real-time word-by-word streaming")
        print("• Natural conversation flow")
        print("• AI-to-AI handoffs")
        print("• Interruption handling")
        print("• Conversation repair mechanics")
        
        proceed = self.safe_input("\nRun demo conversation? (y/n): ")
        if not proceed.lower().startswith('y'):
            return
            
        # Create a demo conversation
        demo_project = None
        projects = self.db_manager.list_projects()
        
        # Find or create a demo project
        for project in projects:
            if project.name == "Demo Project":
                demo_project = project
                break
        
        if not demo_project:
            demo_project = Project(name="Demo Project", description="For streaming demos")
            demo_project = self.db_manager.create_project(demo_project)
        
        # Create demo conversation
        demo_conversation = Conversation(
            project_id=demo_project.id,
            title="Enhanced Streaming Demo"
        )
        demo_conversation = self.db_manager.create_conversation(demo_conversation)
        
        # Demo message
        demo_message = Message(
            conversation_id=demo_conversation.id,
            participant="user",
            content="Please demonstrate how you all work together to solve complex problems. Show me your collaboration in action!"
        )
        self.db_manager.create_message(demo_message)
        
        print(f"\n💬 Demo conversation created: {demo_conversation.title}")
        print("=" * 50)
        
        # Run the enhanced streaming demo
        try:
            asyncio.run(self._run_enhanced_demo(demo_conversation.id, demo_message))
        except Exception as e:
            print(f"❌ Demo error: {e}")
    
    async def _run_enhanced_demo(self, conversation_id: str, user_message: Message):
        """Run the enhanced streaming demo."""
        session = self.db_manager.get_conversation_session(conversation_id)
        context_messages = session.get_context_messages(
            self.config_manager.config.conversation.max_context_tokens
        )
        
        print(f"👤 Demo User: {user_message.content}")
        
        # Use enhanced streaming
        responses = await self.enhanced_manager.stream_conversation_response(
            user_message, context_messages, conversation_id
        )
        
        response_count = len(responses) if responses else 0
        print(f"\n🎉 Demo completed with {response_count} AI responses!")
        print("This demonstrates the natural flow of real-time AI collaboration.")
    
    def show_streaming_comparison(self):
        """Show comparison between streaming and batch processing."""
        print("\n📊 Streaming vs Batch Processing Comparison")
        print("-" * 50)
        
        if not self.enhanced_manager:
            print("❌ Enhanced streaming not available.")
            return
            
        comparison = self.enhanced_manager.get_streaming_vs_batch_comparison()
        
        print("\n🐌 OLD BATCH PROCESSING:")
        print("-" * 25)
        batch = comparison['batch_processing']
        for key, value in batch.items():
            print(f"  • {key.replace('_', ' ').title()}: {value}")
        
        print("\n⚡ NEW STREAMING PROCESSING:")
        print("-" * 27)
        streaming = comparison['streaming_processing']
        for key, value in streaming.items():
            print(f"  • {key.replace('_', ' ').title()}: {value}")
        
        print("\n🎯 KEY BENEFITS:")
        print("-" * 15)
        for benefit in comparison['benefits']:
            print(f"  ✓ {benefit}")
        
        print("\n💡 USAGE TIPS:")
        print("-" * 13)
        print("  • Use option 4 or 5 to experience real-time streaming")
        print("  • Try interrupting with 'wait' or 'actually' during responses")
        print("  • Ask for clarification to see conversation repair in action")
        print("  • Watch how AIs naturally hand off to each other")
        print("  • Notice the immediate feedback vs waiting for batch responses")


def demonstrate_realtime_improvements():
    """Demonstrate the real-time streaming improvements."""
    print("🚀 REAL-TIME CONVERSATION STREAMING")
    print("=" * 50)
    
    try:
        cli = SimpleCollaborateCLI()
        if cli.enhanced_manager:
            comparison = cli.enhanced_manager.get_streaming_vs_batch_comparison()
            
            print("\n📊 BATCH vs STREAMING COMPARISON")
            print("-" * 30)
            
            print("\n🐌 OLD BATCH PROCESSING:")
            batch = comparison['batch_processing']
            for key, value in batch.items():
                print(f"  • {key.replace('_', ' ').title()}: {value}")
            
            print("\n⚡ NEW STREAMING PROCESSING:")
            streaming = comparison['streaming_processing']
            for key, value in streaming.items():
                print(f"  • {key.replace('_', ' ').title()}: {value}")
            
            print("\n🎯 KEY BENEFITS:")
            for benefit in comparison['benefits']:
                print(f"  ✓ {benefit}")
                
            print("\n💡 HOW TO USE:")
            print("  1. Run: python collaborate.py")
            print("  2. Choose option 12 for enhanced streaming demo")
            print("  3. Choose option 13 for detailed comparison")
            print("  4. Use options 4 or 5 for real streaming conversations")
            print("  5. Try interrupting with 'wait' or 'actually' to see interruption handling")
            print("  6. Ask for clarification to see conversation repair in action")
        else:
            print("❌ Enhanced streaming not available. Check your configuration.")
    except Exception as e:
        print(f"❌ Error demonstrating improvements: {e}")


def main():
    """Main entry point with command-line argument support."""
    parser = argparse.ArgumentParser(description='Collaborate - Three-Way AI Collaboration Platform')
    parser.add_argument('--health', action='store_true', 
                       help='Check system health and exit')
    parser.add_argument('--demo', action='store_true',
                       help='Show real-time streaming improvements demo')
    parser.add_argument('--version', action='version', version='Collaborate 1.0.0')
    
    args = parser.parse_args()
    
    try:
        if args.demo:
            demonstrate_realtime_improvements()
            return
            
        cli = SimpleCollaborateCLI()
        
        if args.health:
            cli.check_system_health_standalone()
            return
        
        cli.run()
        
    except Exception as e:
        print(f"❌ Failed to start Collaborate: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Support both direct execution and module import
    if len(sys.argv) > 1 and sys.argv[1] == "--demo-only":
        # For backward compatibility with enhanced_collaboration.py
        try:
            demonstrate_realtime_improvements()
        except Exception as e:
            print(f"❌ Demo error: {e}")
    else:
        main()

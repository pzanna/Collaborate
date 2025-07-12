#!/usr/bin/env python3
"""
Simple CLI interface for testing the Collaborate application
"""

import os
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config.config_manager import ConfigManager
from storage.database import DatabaseManager
from core.ai_client_manager import AIClientManager
from models.data_models import Project, Conversation, Message


class SimpleCollaborateCLI:
    """Simple CLI for testing the Collaborate application."""
    
    def __init__(self):
        print("🚀 Initializing Collaborate...")
        
        # Initialize components
        self.config_manager = ConfigManager()
        self.db_manager = DatabaseManager(self.config_manager.config.storage.database_path)
        
        try:
            self.ai_manager = AIClientManager(self.config_manager)
            available_providers = self.ai_manager.get_available_providers()
            print(f"✓ AI providers available: {', '.join(available_providers)}")
        except Exception as e:
            print(f"⚠ AI providers not available: {e}")
            self.ai_manager = None
        
        print("✓ Collaborate initialized successfully!\n")
    
    def show_menu(self):
        """Display the main menu."""
        print("=" * 60)
        print("🤝 COLLABORATE - Three-Way AI Collaboration Platform")
        print("=" * 60)
        print("1. List Projects")
        print("2. Create Project")
        print("3. List Conversations")
        print("4. Start Conversation")
        print("5. Resume Conversation")
        print("6. Test AI Connections")
        print("7. Show Configuration")
        print("0. Exit")
        print("=" * 60)
    
    def list_projects(self):
        """List all projects."""
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
    
    def create_project(self):
        """Create a new project."""
        print("\n📁 Create New Project")
        print("-" * 30)
        
        name = input("Project name: ").strip()
        if not name:
            print("❌ Project name cannot be empty.")
            return
        
        description = input("Description (optional): ").strip()
        
        project = Project(name=name, description=description)
        self.db_manager.create_project(project)
        
        print(f"✅ Project '{name}' created successfully!")
        print(f"   ID: {project.id}")
    
    def list_conversations(self):
        """List all conversations."""
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
    
    def start_conversation(self):
        """Start a new conversation."""
        print("\n💬 Start New Conversation")
        print("-" * 30)
        
        # First, show available projects
        projects = self.db_manager.list_projects()
        if not projects:
            print("❌ No projects available. Create a project first.")
            return
        
        print("Available projects:")
        for i, project in enumerate(projects, 1):
            print(f"{i}. {project.name}")
        
        try:
            project_choice = int(input(f"Select project (1-{len(projects)}): "))
            if project_choice < 1 or project_choice > len(projects):
                print("❌ Invalid selection.")
                return
            
            selected_project = projects[project_choice - 1]
        except ValueError:
            print("❌ Invalid input. Please enter a number.")
            return
        
        title = input("Conversation title: ").strip()
        if not title:
            print("❌ Conversation title cannot be empty.")
            return
        
        conversation = Conversation(project_id=selected_project.id, title=title)
        self.db_manager.create_conversation(conversation)
        
        print(f"✅ Conversation '{title}' started successfully!")
        print(f"   ID: {conversation.id}")
        
        # Start the conversation
        self.run_conversation(conversation.id)
    
    def resume_conversation(self):
        """Resume an existing conversation."""
        print("\n💬 Resume Conversation")
        print("-" * 30)
        
        conversations = self.db_manager.list_conversations()
        if not conversations:
            print("❌ No conversations available. Start a conversation first.")
            return
        
        print("Available conversations:")
        for i, conv in enumerate(conversations, 1):
            print(f"{i}. {conv.title} (Status: {conv.status})")
        
        try:
            conv_choice = int(input(f"Select conversation (1-{len(conversations)}): "))
            if conv_choice < 1 or conv_choice > len(conversations):
                print("❌ Invalid selection.")
                return
            
            selected_conv = conversations[conv_choice - 1]
        except ValueError:
            print("❌ Invalid input. Please enter a number.")
            return
        
        self.run_conversation(selected_conv.id)
    
    def run_conversation(self, conversation_id: str):
        """Run a conversation session."""
        session = self.db_manager.get_conversation_session(conversation_id)
        if not session:
            print("❌ Conversation not found.")
            return
        
        print(f"\n🤝 Starting conversation: {session.conversation.title}")
        print("=" * 60)
        print("Type 'exit' to end the conversation")
        print("Type 'history' to see conversation history")
        print("=" * 60)
        
        # Show existing messages
        if session.messages:
            print("\n📜 Conversation History:")
            self.show_messages(session.messages)
        
        while True:
            try:
                user_input = input("\n👤 You: ").strip()
                
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
                
                if not user_input:
                    continue
                
                # Create user message
                user_message = Message(
                    conversation_id=conversation_id,
                    participant="user",
                    content=user_input
                )
                self.db_manager.create_message(user_message)
                
                # Get AI responses
                if self.ai_manager:
                    self.get_ai_responses(conversation_id)
                else:
                    print("⚠ AI providers not available. Message saved but no AI responses.")
                
            except KeyboardInterrupt:
                print("\n👋 Ending conversation...")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    def get_ai_responses(self, conversation_id: str):
        """Get responses from AI providers."""
        session = self.db_manager.get_conversation_session(conversation_id)
        if not session:
            return
        
        # Get context messages (recent conversation history)
        context_messages = session.get_context_messages(
            self.config_manager.config.conversation.max_context_tokens
        )
        
        providers = self.ai_manager.get_available_providers()
        
        for provider in providers:
            try:
                print(f"\n🤖 {provider.upper()} is thinking...")
                
                # Get AI response
                response = self.ai_manager.get_response(provider, context_messages)
                
                # Create AI message
                ai_message = Message(
                    conversation_id=conversation_id,
                    participant=provider,
                    content=response
                )
                self.db_manager.create_message(ai_message)
                
                # Display response
                print(f"🤖 {provider.upper()}: {response}")
                
            except Exception as e:
                print(f"❌ Error getting response from {provider}: {e}")
    
    def show_messages(self, messages):
        """Display messages in a formatted way."""
        for msg in messages:
            timestamp = msg.timestamp.strftime("%H:%M:%S")
            if msg.participant == "user":
                print(f"[{timestamp}] 👤 You: {msg.content}")
            else:
                print(f"[{timestamp}] 🤖 {msg.participant.upper()}: {msg.content}")
    
    def test_ai_connections(self):
        """Test AI connections."""
        print("\n🔧 Testing AI Connections")
        print("-" * 30)
        
        if not self.ai_manager:
            print("❌ AI manager not initialized.")
            return
        
        providers = self.ai_manager.get_available_providers()
        if not providers:
            print("❌ No AI providers available.")
            return
        
        print(f"Available providers: {', '.join(providers)}")
        
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
        
        print("\nAI Providers:")
        for name, provider_config in config.ai_providers.items():
            print(f"  {name}:")
            print(f"    Model: {provider_config.model}")
            print(f"    Temperature: {provider_config.temperature}")
            print(f"    Max Tokens: {provider_config.max_tokens}")
            print(f"    Role Adaptation: {provider_config.role_adaptation}")
    
    def run(self):
        """Run the CLI interface."""
        while True:
            try:
                self.show_menu()
                choice = input("Select option: ").strip()
                
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
                else:
                    print("❌ Invalid option. Please try again.")
                
                input("\nPress Enter to continue...")
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ An error occurred: {e}")
                input("\nPress Enter to continue...")


def main():
    """Main entry point."""
    try:
        cli = SimpleCollaborateCLI()
        cli.run()
    except Exception as e:
        print(f"❌ Failed to start Collaborate: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

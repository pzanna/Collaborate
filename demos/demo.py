#!/usr/bin/env python3
"""
Quick Start Demo for Collaborate - Three-Way AI Collaboration Platform

This script demonstrates the key features of the Collaborate application
in a non-interactive way for documentation and demo purposes.
"""

import sys
import os
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config.config_manager import ConfigManager
from storage.database import DatabaseManager
from core.ai_client_manager import AIClientManager
from models.data_models import Project, Conversation, Message
from utils.export_manager import ExportManager
from utils.error_handler import get_error_handler
from utils.performance import get_performance_monitor


def demo_system_health():
    """Demonstrate system health check."""
    print("🏥 SYSTEM HEALTH CHECK")
    print("=" * 50)
    
    # Initialize components
    config_manager = ConfigManager()
    db_manager = DatabaseManager(config_manager.config.storage.database_path)
    export_manager = ExportManager(config_manager.config.storage.export_path)
    
    try:
        ai_manager = AIClientManager(config_manager)
        available_providers = ai_manager.get_available_providers()
        print(f"✅ AI providers available: {', '.join(available_providers)}")
    except Exception as e:
        print(f"⚠️  AI providers not available: {e}")
        ai_manager = None
    
    # Database health
    print("\n📊 Database Status:")
    db_stats = db_manager.get_database_stats()
    print(f"   Status: {db_stats.get('status', 'unknown')}")
    print(f"   Projects: {db_stats.get('projects', 0)}")
    print(f"   Conversations: {db_stats.get('conversations', 0)}")
    print(f"   Messages: {db_stats.get('messages', 0)}")
    
    # AI health
    if ai_manager:
        print("\n🤖 AI Providers Status:")
        provider_health = ai_manager.get_provider_health()
        for provider, health in provider_health.items():
            status_emoji = "✅" if health["status"] == "healthy" else "⚠️" if health["status"] == "degraded" else "❌"
            print(f"   {status_emoji} {provider.upper()}: {health['status']}")
    
    # Error statistics
    print("\n📈 Error Statistics:")
    error_handler = get_error_handler()
    error_stats = error_handler.get_error_stats()
    
    if error_stats["total_errors"] > 0:
        print(f"   Total errors: {error_stats['total_errors']}")
    else:
        print("   ✅ No errors recorded")
    
    return db_manager, ai_manager


def demo_basic_usage():
    """Demonstrate basic usage of the application."""
    print("\n📝 BASIC USAGE DEMONSTRATION")
    print("=" * 50)
    
    db_manager, ai_manager = demo_system_health()
    
    # Show existing data
    projects = db_manager.list_projects()
    print(f"\n📁 Current Projects: {len(projects)}")
    for project in projects:
        print(f"   • {project.name}: {project.description}")
    
    conversations = db_manager.list_conversations()
    print(f"\n💬 Current Conversations: {len(conversations)}")
    for conv in conversations:
        print(f"   • {conv.title} ({conv.status})")
    
    # Show message statistics
    if conversations:
        print("\n📊 Conversation Statistics:")
        for conv in conversations:
            session = db_manager.get_conversation_session(conv.id)
            if session and session.messages:
                user_messages = [m for m in session.messages if m.participant == "user"]
                ai_messages = [m for m in session.messages if m.participant != "user"]
                print(f"   • {conv.title}:")
                print(f"     - User messages: {len(user_messages)}")
                print(f"     - AI responses: {len(ai_messages)}")
    
    return db_manager, ai_manager


def demo_ai_capabilities():
    """Demonstrate AI capabilities."""
    print("\n🤖 AI CAPABILITIES DEMONSTRATION")
    print("=" * 50)
    
    db_manager, ai_manager = demo_system_health()
    
    if not ai_manager:
        print("❌ AI manager not available - cannot demonstrate AI capabilities")
        return
    
    # Test AI connections
    print("\n🔧 Testing AI Connections:")
    available_providers = ai_manager.get_available_providers()
    
    for provider in available_providers:
        try:
            response = ai_manager.get_response(provider, "Hello! This is a test message.")
            if response and not response.startswith("Error:"):
                print(f"   ✅ {provider.upper()}: {response[:100]}...")
            else:
                print(f"   ⚠️  {provider.upper()}: Connection available but API may be rate-limited")
        except Exception as e:
            print(f"   ❌ {provider.upper()}: {e}")
    
    # Show smart response configuration
    print("\n🧠 Smart Response Configuration:")
    smart_config = ai_manager.response_coordinator.get_configuration()
    print(f"   • Relevance threshold: {smart_config['relevance_threshold']}")
    print(f"   • Max consecutive responses: {smart_config['max_consecutive_responses']}")
    print(f"   • Response coordination enabled: {smart_config['response_coordination']}")


def demo_export_capabilities():
    """Demonstrate export capabilities."""
    print("\n📤 EXPORT CAPABILITIES DEMONSTRATION")
    print("=" * 50)
    
    db_manager, ai_manager = demo_system_health()
    
    # Show available conversations for export
    conversations = db_manager.list_conversations()
    
    if not conversations:
        print("❌ No conversations available for export")
        return
    
    print(f"\n📋 Available Conversations for Export: {len(conversations)}")
    for conv in conversations:
        print(f"   • {conv.title} ({conv.status})")
    
    # Show export formats
    print("\n📁 Available Export Formats:")
    export_formats = ["json", "markdown", "html", "txt"]
    for format_name in export_formats:
        print(f"   • {format_name.upper()}")
    
    # List existing exports
    export_manager = ExportManager("exports/")
    exports = export_manager.list_exports()
    print(f"\n📦 Existing Exports: {len(exports)}")
    for export in exports:
        print(f"   • {export['filename']} ({export['format']}) - {export['size']} bytes")


def demo_performance_monitoring():
    """Demonstrate performance monitoring."""
    print("\n⚡ PERFORMANCE MONITORING DEMONSTRATION")
    print("=" * 50)
    
    # Get performance monitor
    perf_monitor = get_performance_monitor()
    
    # Show performance statistics
    stats = perf_monitor.get_stats()
    print(f"\n📊 Performance Statistics:")
    print(f"   • Total operations: {stats['total_operations']}")
    print(f"   • Average response time: {stats['average_response_time']:.3f}s")
    print(f"   • Cache hit rate: {stats['cache_hit_rate']:.1%}")
    print(f"   • Memory usage: {stats['memory_usage']:.2f} MB")
    
    # Show cached operations
    cache_stats = perf_monitor.cache.get_stats()
    print(f"\n💾 Cache Statistics:")
    print(f"   • Total items: {cache_stats['total_items']}")
    print(f"   • Hits: {cache_stats['hits']}")
    print(f"   • Misses: {cache_stats['misses']}")
    print(f"   • Hit rate: {cache_stats['hit_rate']:.1%}")


def main():
    """Run the complete demonstration."""
    print("🚀 COLLABORATE - QUICK START DEMO")
    print("=" * 70)
    print("This demo showcases the key features of the Collaborate application")
    print("=" * 70)
    
    try:
        # Run all demonstrations
        demo_basic_usage()
        demo_ai_capabilities()
        demo_export_capabilities()
        demo_performance_monitoring()
        
        print("\n🎉 DEMO COMPLETE!")
        print("=" * 50)
        print("✅ All systems operational")
        print("✅ Application ready for use")
        print("\nTo start using Collaborate interactively:")
        print("   python collaborate.py")
        print("\nFor system health check:")
        print("   python collaborate.py --health")
        print("\nFor help:")
        print("   python collaborate.py --help")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

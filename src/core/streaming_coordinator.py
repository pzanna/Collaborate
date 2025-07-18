"""Simplified Real-time Streaming Response Coordinator

Enables real-time display of AI responses as they're generated, creating a more
natural conversation flow similar to Slack where responses appear immediately.
"""

import asyncio
import time
import os
import sys
from typing import List, Dict, Optional, AsyncGenerator, Any
from datetime import datetime

# Import project structures with fallback for direct execution
try:
    from ..models.data_models import Message
    from ..config.config_manager import ConfigManager
    from .simplified_coordinator import SimplifiedCoordinator
except ImportError:
    # Allow standalone execution when run outside package
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from models.data_models import Message
    from config.config_manager import ConfigManager
    from core.simplified_coordinator import SimplifiedCoordinator


class SimplifiedStreamingCoordinator:
    """Simplified streaming for real-time responses"""
    
    def __init__(self, ai_manager, db_manager=None):
        self.ai_manager = ai_manager
        self.db_manager = db_manager
    
    async def stream_group_conversation(self, user_message, conversation_history):
        """Stream group responses in real-time"""
        
        available_providers = self.ai_manager.get_available_providers()
        
        if not available_providers:
            yield {'type': 'error', 'message': 'No providers available'}
            return
        
        # Get participants
        participants = self.ai_manager.coordinator.get_participating_providers(
            user_message.content, available_providers, conversation_history
        )
        
        yield {
            'type': 'queue_determined',
            'queue': participants,
            'message': f"🎯 {', '.join(participants)} will respond"
        }
        
        # Stream responses from each participant
        shared_context = conversation_history + [user_message]
        
        for i, provider in enumerate(participants):
            yield {
                'type': 'provider_starting',
                'provider': provider,
                'position': i + 1,
                'total': len(participants),
                'message': f"🤖 {provider.upper()} is responding..."
            }
            
            try:
                # Get response (in real implementation, this would stream)
                group_prompt = self.ai_manager._create_group_prompt(provider)
                
                # Simulate streaming by getting full response then chunking
                response = await asyncio.get_event_loop().run_in_executor(
                    None, self.ai_manager.get_response, 
                    provider, shared_context, group_prompt
                )
                
                if response and not response.startswith("Error:"):
                    # Signal that provider is about to start streaming
                    yield {
                        'type': 'provider_response_start',
                        'provider': provider,
                        'message': f"🤖 {provider.upper()} is responding..."
                    }
                    
                    # Simulate streaming chunks
                    words = response.split()
                    chunk_size = max(1, len(words) // 8)
                    
                    partial_response = ""
                    for j in range(0, len(words), chunk_size):
                        chunk = ' '.join(words[j:j + chunk_size])
                        if j + chunk_size < len(words):
                            chunk += ' '
                        
                        partial_response += chunk
                        
                        yield {
                            'type': 'response_chunk',
                            'provider': provider,
                            'chunk': chunk,
                            'content': chunk,
                            'partial_response': partial_response
                        }
                        
                        await asyncio.sleep(0.1)  # Simulate typing
                    
                    # Save to database if available
                    if self.db_manager:
                        ai_message = Message(
                            conversation_id=user_message.conversation_id,
                            participant=provider,
                            content=response,
                            timestamp=datetime.now()
                        )
                        try:
                            self.db_manager.create_message(ai_message)
                        except Exception as e:
                            print(f"Database error: {e}")
                    
                    # Add to shared context for next provider
                    ai_message = Message(
                        conversation_id=user_message.conversation_id,
                        participant=provider,
                        content=response,
                        timestamp=datetime.now()
                    )
                    shared_context.append(ai_message)
                    
                    yield {
                        'type': 'provider_completed',
                        'provider': provider,
                        'response': response,
                        'message': f"✅ {provider.upper()} completed"
                    }
                    
            except Exception as e:
                yield {
                    'type': 'provider_error',
                    'provider': provider,
                    'error': str(e),
                    'message': f"❌ Error from {provider.upper()}: {str(e)}"
                }
        
        yield {
            'type': 'conversation_completed',
            'total_responses': len(participants),
            'message': "🎉 Group conversation completed"
        }

# Backward compatibility - keep the original class name
class StreamingResponseCoordinator(SimplifiedStreamingCoordinator):
    """Backward compatibility class"""
    
    def __init__(self, config_manager: ConfigManager, response_coordinator=None,
                 ai_manager=None, db_manager=None):
        """Initialize with backward compatibility"""
        super().__init__(ai_manager, db_manager)
        self.config_manager = config_manager
        
    async def stream_conversation_chain(self, user_message, context, **kwargs):
        """Backward compatibility method"""
        async for update in self.stream_group_conversation(user_message, context):
            yield update

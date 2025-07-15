"""Real-time Streaming Response Coordinator

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
    from .response_coordinator import ResponseCoordinator
except ImportError:
    # Allow standalone execution when run outside package
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from models.data_models import Message
    from config.config_manager import ConfigManager
    from core.response_coordinator import ResponseCoordinator


class StreamingResponseCoordinator:
    """Coordinates real-time streaming responses for natural conversation flow."""
    
    def __init__(self, config_manager: ConfigManager, response_coordinator: Optional[ResponseCoordinator] = None,
                 ai_manager=None, db_manager=None):
        """Initialize streaming coordinator.
        
        Args:
            config_manager: Configuration manager instance
            response_coordinator: Response coordinator instance (optional, will be created if not provided)
            ai_manager: AI client manager (optional, for alternative constructor)
            db_manager: Database manager (optional, for alternative constructor)
        """
        self.config_manager = config_manager
        
        # Handle different constructor patterns
        if response_coordinator is not None:
            # Enhanced collaboration manager pattern
            self.response_coordinator = response_coordinator
            self.ai_manager = ai_manager
            self.db_manager = db_manager
        else:
            # Main application pattern
            self.ai_manager = ai_manager
            self.db_manager = db_manager
            # Create response coordinator if not provided
            self.response_coordinator = ResponseCoordinator(config_manager)
            
        self.active_streams = {}
        
    async def stream_conversation_chain(
        self, 
        user_message: Message, 
        context: List[Message]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream conversation responses in real-time as they're generated.
        
        Yields updates as each AI responds, enabling real-time display.
        """
        
        # Get available providers from ai_manager
        available_providers = self.ai_manager.get_available_providers() if self.ai_manager else []
        if not available_providers:
            yield {
                'type': 'error',
                'message': 'No AI providers available',
                'timestamp': time.time()
            }
            return
        
        # Get initial speaking queue
        speaking_queue = self.response_coordinator.coordinate_responses(
            user_message, context, available_providers
        )
        
        yield {
            'type': 'queue_determined',
            'queue': speaking_queue,
            'timestamp': time.time(),
            'message': f"🎯 Response queue: {', '.join(speaking_queue)}"
        }
        
        # Build temporary conversation history for chaining
        temp_history = context[:]
        temp_history.append(user_message)
        
        # Process each provider in the queue
        for i, provider in enumerate(speaking_queue):
            yield {
                'type': 'provider_starting',
                'provider': provider,
                'position': i + 1,
                'total': len(speaking_queue),
                'timestamp': time.time(),
                'message': f"🤖 {provider.upper()} is thinking..."
            }
            
            try:
                # Signal that provider is about to start streaming response
                yield {
                    'type': 'provider_response_start',
                    'provider': provider,
                    'timestamp': time.time()
                }
                
                # Stream the response from this provider
                response_chunks = []
                async for chunk in self._stream_provider_response(
                    provider, temp_history
                ):
                    response_chunks.append(chunk)
                    
                    yield {
                        'type': 'response_chunk',
                        'provider': provider,
                        'chunk': chunk,
                        'partial_response': ''.join(response_chunks),
                        'timestamp': time.time()
                    }
                
                # Complete response
                full_response = ''.join(response_chunks)
                if full_response and not full_response.startswith("Error:"):
                    # Create AI message for database storage
                    ai_message = Message(
                        conversation_id=user_message.conversation_id,
                        participant=provider,
                        content=full_response,
                        timestamp=datetime.now()
                    )
                    
                    # Save to database if available
                    if self.db_manager:
                        try:
                            self.db_manager.create_message(ai_message)
                        except Exception as e:
                            yield {
                                'type': 'database_error',
                                'provider': provider,
                                'error': str(e),
                                'timestamp': time.time(),
                                'message': f"⚠️ Database save error for {provider.upper()}: {str(e)}"
                            }
                    
                    # Add to temp history for next provider
                    temp_history.append(ai_message)
                    
                    yield {
                        'type': 'provider_completed',
                        'provider': provider,
                        'response': full_response,
                        'timestamp': time.time(),
                        'message': f"✅ {provider.upper()} completed"
                    }
                    
                    # Check for chaining cues in this response
                    cued_provider = self.response_coordinator.detect_chaining_cue(
                        full_response, available_providers
                    )
                    
                    if cued_provider and cued_provider not in speaking_queue:
                        yield {
                            'type': 'chain_detected',
                            'from_provider': provider,
                            'to_provider': cued_provider,
                            'timestamp': time.time(),
                            'message': f"🔗 {provider.upper()} is calling on {cued_provider.upper()}"
                        }
                        
                        # Add chained provider to queue
                        speaking_queue.append(cued_provider)
                        
                        yield {
                            'type': 'queue_updated',
                            'queue': speaking_queue,
                            'added_provider': cued_provider,
                            'timestamp': time.time(),
                            'message': f"📝 Added {cued_provider.upper()} to speaking queue"
                        }
                
            except Exception as e:
                yield {
                    'type': 'provider_error',
                    'provider': provider,
                    'error': str(e),
                    'timestamp': time.time(),
                    'message': f"❌ Error from {provider.upper()}: {str(e)}"
                }
        
        yield {
            'type': 'conversation_completed',
            'total_providers': len(speaking_queue),
            'timestamp': time.time(),
            'message': "🎉 Conversation chain completed"
        }
    
    async def _stream_provider_response(
        self, 
        provider: str, 
        messages: List[Message]
    ) -> AsyncGenerator[str, None]:
        """Stream response from a specific provider.
        
        This simulates streaming by breaking the response into chunks.
        In a real implementation, you'd integrate with actual streaming APIs.
        """
        try:
            if not self.ai_manager:
                yield "Error: AI manager not available"
                return
                
            # Adapt system prompt (includes collaboration context generation)
            adapted_prompt = self.ai_manager.adapt_system_prompt(
                provider, messages[-1].content, messages
            )
            
            # Get the full response (in real implementation, this would be streaming)
            response = await asyncio.get_event_loop().run_in_executor(
                None, self.ai_manager.get_response, provider, messages, adapted_prompt
            )
            
            if not response or response.startswith("Error:"):
                yield response or f"Error: No response from {provider}"
                return
            
            # Simulate streaming by yielding word chunks
            words = response.split()
            chunk_size = max(1, len(words) // 8)  # Stream in ~8 chunks
            
            for i in range(0, len(words), chunk_size):
                chunk = ' '.join(words[i:i + chunk_size])
                if i + chunk_size < len(words):
                    chunk += ' '
                
                yield chunk
                await asyncio.sleep(0.2)  # Simulate typing delay
                
        except Exception as e:
            yield f"Error streaming from {provider}: {str(e)}"
    
    async def stream_with_interruption_support(
        self,
        user_message: Message,
        context: List[Message],
        available_providers: List[str],
        ai_client_manager
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream responses with support for interruptions and conversation repair."""
        
        # Check for interruption opportunities first
        interruption_scores = self.response_coordinator.detect_interruption_opportunity(
            user_message, context
        )
        
        high_interruption_providers = [
            provider for provider, score in interruption_scores.items()
            if score > 0.5
        ]
        
        if high_interruption_providers:
            yield {
                'type': 'interruption_detected',
                'providers': high_interruption_providers,
                'scores': interruption_scores,
                'timestamp': time.time(),
                'message': f"🚨 Interruption detected! Prioritizing: {', '.join(high_interruption_providers)}"
            }
        
        # Check for conversation repair needs
        repair_provider = self.response_coordinator.detect_conversation_repair_needs(context)
        if repair_provider:
            yield {
                'type': 'repair_needed',
                'provider': repair_provider,
                'timestamp': time.time(),
                'message': f"🔧 Routing clarification to {repair_provider.upper()}"
            }
        
        # Stream the conversation
        async for update in self.stream_conversation_chain(
            user_message, context
        ):
            yield update
    
    def get_stream_status(self) -> Dict[str, Any]:
        """Get current status of all active streams."""
        return {
            'active_streams': len(self.active_streams),
            'stream_ids': list(self.active_streams.keys()),
            'timestamp': time.time()
        }

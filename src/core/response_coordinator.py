"""Response Coordinator for intelligent AI response management."""

import os
import sys
import re
from typing import List, Dict, Set, Optional, Any
from collections import defaultdict

# Import models
try:
    from ..models.data_models import Message, ConversationSession
    from ..config.config_manager import ConfigManager
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from models.data_models import Message, ConversationSession
    from config.config_manager import ConfigManager


class ResponseCoordinator:
    """Coordinates AI responses based on context and relevance."""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.response_threshold = 0.3  # Minimum relevance score to respond
        self.max_consecutive_responses = 3  # Max consecutive responses from same AI
        
    def should_ai_respond(self, provider: str, message: Message, context: List[Message]) -> bool:
        """Determine if an AI should respond based on context and relevance."""
        
        # Always respond if no context (first message)
        if not context:
            return True
        
        # Check if AI was directly mentioned
        if self._is_ai_mentioned(message, provider):
            return True
        
        # Check relevance score
        relevance_score = self._calculate_relevance(message, provider, context)
        if relevance_score < self.response_threshold:
            return False
        
        # Check for consecutive responses from same AI
        if self._has_too_many_consecutive_responses(provider, context):
            return False
        
        # Check for redundancy with recent responses
        if self._is_response_redundant(message, provider, context):
            return False
        
        return True
    
    def coordinate_responses(self, message: Message, context: List[Message], 
                           available_providers: List[str]) -> List[str]:
        """Return all AI providers to respond to every message."""
        return available_providers
    
    def _is_ai_mentioned(self, message: Message, provider: str) -> bool:
        """Check if the AI provider is directly mentioned in the message."""
        content = message.content.lower()
        
        # Check for direct mentions
        provider_keywords = {
            'openai': ['openai', 'gpt', 'chatgpt', 'assistant'],
            'xai': ['xai', 'grok', 'x.ai']
        }
        
        if provider in provider_keywords:
            for keyword in provider_keywords[provider]:
                if keyword in content:
                    return True
        
        # Check for @mentions
        if f'@{provider}' in content:
            return True
        
        return False
    
    def _calculate_relevance(self, message: Message, provider: str, context: List[Message]) -> float:
        """Calculate relevance score for an AI provider to respond."""
        content = message.content.lower()
        score = 0.0
        
        # Provider-specific relevance keywords
        provider_strengths = {
            'openai': {
                'keywords': ['code', 'programming', 'development', 'technical', 'software', 
                           'algorithm', 'debug', 'implementation', 'analysis', 'research'],
                'weight': 0.8
            },
            'xai': {
                'keywords': ['creative', 'brainstorm', 'idea', 'innovative', 'perspective', 
                           'alternative', 'opinion', 'think', 'approach', 'strategy'],
                'weight': 0.8
            }
        }
        
        if provider in provider_strengths:
            keywords = provider_strengths[provider]['keywords']
            weight = provider_strengths[provider]['weight']
            
            for keyword in keywords:
                if keyword in content:
                    score += weight
        
        # Base relevance for general questions
        question_indicators = ['?', 'how', 'what', 'why', 'when', 'where', 'can you', 'please']
        for indicator in question_indicators:
            if indicator in content:
                score += 0.4
                break
        
        # Check conversation context for topic continuity
        if context:
            recent_messages = context[-5:]  # Last 5 messages
            provider_messages = [msg for msg in recent_messages if msg.participant == provider]
            
            if provider_messages:
                # If AI was recently active in this topic, slightly increase relevance
                score += 0.2
        
        # Normalize score
        return min(score, 1.0)
    
    def _has_too_many_consecutive_responses(self, provider: str, context: List[Message]) -> bool:
        """Check if AI has too many consecutive responses."""
        if not context:
            return False
        
        consecutive_count = 0
        for message in reversed(context):
            if message.participant == provider:
                consecutive_count += 1
            else:
                break
        
        return consecutive_count >= self.max_consecutive_responses
    
    def _is_response_redundant(self, message: Message, provider: str, context: List[Message]) -> bool:
        """Check if AI response would be redundant with recent responses."""
        if not context:
            return False
        
        # Check last few messages for similar content
        recent_messages = context[-3:]
        message_content = message.content.lower()
        
        for msg in recent_messages:
            if msg.participant != provider and msg.participant != 'user':
                # Check if another AI already addressed this topic
                if self._calculate_content_similarity(message_content, msg.content.lower()) > 0.7:
                    return True
        
        return False
    
    def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity between two pieces of content."""
        # Simple word-based similarity
        words1 = set(re.findall(r'\w+', content1))
        words2 = set(re.findall(r'\w+', content2))
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _select_best_provider(self, message: Message, context: List[Message], 
                            available_providers: List[str]) -> str:
        """Select the best AI provider based on relevance scores."""
        best_provider = available_providers[0]
        best_score = 0.0
        
        for provider in available_providers:
            score = self._calculate_relevance(message, provider, context)
            if score > best_score:
                best_score = score
                best_provider = provider
        
        return best_provider
    
    def get_response_stats(self, session: ConversationSession) -> Dict[str, Any]:
        """Get statistics about AI responses in a conversation."""
        stats = {
            'total_messages': len(session.messages),
            'user_messages': 0,
            'ai_responses': defaultdict(int),
            'response_rate': defaultdict(float)
        }
        
        for message in session.messages:
            if message.participant == 'user':
                stats['user_messages'] += 1
            else:
                stats['ai_responses'][message.participant] += 1
        
        # Calculate response rates
        total_ai_messages = sum(stats['ai_responses'].values())
        for provider, count in stats['ai_responses'].items():
            stats['response_rate'][provider] = count / total_ai_messages if total_ai_messages > 0 else 0.0
        
        return stats
    
    def update_settings(self, **kwargs) -> None:
        """Update coordinator settings."""
        if 'response_threshold' in kwargs:
            self.response_threshold = float(kwargs['response_threshold'])
        if 'max_consecutive_responses' in kwargs:
            self.max_consecutive_responses = int(kwargs['max_consecutive_responses'])
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get current response coordination configuration."""
        return {
            "relevance_threshold": self.response_threshold,
            "max_consecutive_responses": self.max_consecutive_responses,
            "response_coordination": True
        }

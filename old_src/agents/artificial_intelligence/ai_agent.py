"""
AI Agent - Centralized AI service abstraction for Eunice Research Platform

This module implements the AI Agent service as specified in Architecture.md Phase 2.
It provides a unified interface to multiple AI providers with advanced features:

Key Features:
- Multi-provider AI model abstraction (OpenAI, xAI, future: Anthropic, local LLMs)
- Centralized cost tracking and optimization
- Retry logic with exponential backoff
- Fallback mechanisms for provider failures
- Streaming and batch response modes
- Context management and conversation history
- Performance monitoring and analytics

Architecture Compliance:
- Serves as the centralized AI service for all other agents
- Implements Architecture.md specifications for AI Agent service
- Provides standardized interface for NLP, reasoning, and data analysis
- Supports horizontal scaling and load balancing
"""

import asyncio
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
from uuid import uuid4

from ...config.config_manager import ConfigManager
from ...utils.error_handler import APIError, NetworkError, handle_errors
from ..base_agent import BaseAgent
from .ai_client_manager import AIClientManager


class AIAgent(BaseAgent):
    """
    Centralized AI Agent service providing unified access to multiple AI providers.
    
    This agent serves as the central AI service abstraction for the Eunice platform,
    handling all AI model interactions for other agents and services.
    """

    def __init__(self, config_manager: ConfigManager):
        """Initialize the AI Agent with multi-provider support."""
        super().__init__("ai_agent", config_manager)
        
        # Initialize the AI client manager
        self.ai_client_manager = AIClientManager(config_manager)
        
        # Service metadata
        self.service_id = str(uuid4())
        self.start_time = time.time()
        self.request_count = 0
        self.total_cost = 0.0
        
        # Performance tracking
        self.response_times: List[float] = []
        self.error_count = 0
        self.successful_requests = 0
        
        self.logger.info(f"AI Agent service initialized (ID: {self.service_id})")

    # Abstract method implementations
    
    def _get_capabilities(self) -> List[str]:
        """Get AI Agent capabilities."""
        return [
            "text_generation",
            "streaming_generation", 
            "embeddings",
            "text_analysis",
            "translation",
            "summarization",
            "entity_extraction",
            "sentiment_analysis",
            "health_check",
            "statistics"
        ]

    async def _initialize_agent(self) -> None:
        """Initialize AI Agent-specific resources."""
        # Agent-specific initialization already done in __init__
        self.logger.info("AI Agent specific initialization completed")

    async def _cleanup_agent(self) -> None:
        """Clean up AI Agent-specific resources."""
        # Log cleanup
        self.logger.info("AI Agent cleanup completed")

    async def _process_task_impl(self, task) -> Dict[str, Any]:
        """
        Process AI-related tasks from other agents.
        
        Supported actions:
        - generate_text: Generate text response from AI model
        - generate_stream: Generate streaming text response
        - get_embedding: Get text embeddings
        - analyze_text: Perform text analysis
        - translate_text: Translate text between languages
        - summarize_text: Summarize long text content
        - extract_entities: Extract named entities from text
        - sentiment_analysis: Analyze sentiment of text
        """
        action = task.action
        payload = task.payload
        
        self.request_count += 1
        start_time = time.time()
        
        try:
            if action == "generate_text":
                result = await self._generate_text(payload)
            elif action == "generate_stream":
                result = await self._generate_stream(payload)
            elif action == "get_embedding":
                result = await self._get_embedding(payload)
            elif action == "analyze_text":
                result = await self._analyze_text(payload)
            elif action == "translate_text":
                result = await self._translate_text(payload)
            elif action == "summarize_text":
                result = await self._summarize_text(payload)
            elif action == "extract_entities":
                result = await self._extract_entities(payload)
            elif action == "sentiment_analysis":
                result = await self._sentiment_analysis(payload)
            elif action == "health_check":
                result = await self._health_check(payload)
            elif action == "get_stats":
                result = await self._get_stats(payload)
            else:
                raise ValueError(f"Unknown AI action: {action}")
            
            # Track successful request
            response_time = time.time() - start_time
            self.response_times.append(response_time)
            self.successful_requests += 1
            
            # Keep only last 1000 response times for memory management
            if len(self.response_times) > 1000:
                self.response_times = self.response_times[-1000:]
            
            return result
            
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"AI Agent error processing {action}: {e}", exc_info=True)
            raise

    @handle_errors(context="generate_text", reraise=True)
    async def _generate_text(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate text response using specified or default AI provider."""
        prompt = payload.get("prompt", "")
        provider = payload.get("provider")
        temperature = payload.get("temperature")
        max_tokens = payload.get("max_tokens")
        system_prompt = payload.get("system_prompt")
        metadata = payload.get("metadata", {})
        
        if not prompt:
            raise ValueError("Prompt is required for text generation")
        
        # Add request metadata
        metadata.update({
            "service_id": self.service_id,
            "request_id": str(uuid4()),
            "timestamp": time.time()
        })
        
        # Use the AI client manager for generation
        full_response = ""
        provider_used = None
        
        async for chunk in self.ai_client_manager.generate_text(
            prompt=prompt,
            provider=provider,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            metadata=metadata
        ):
            if "text" in chunk:
                full_response += chunk["text"]
            if "provider" in chunk:
                provider_used = chunk["provider"]
            if "error" in chunk:
                raise APIError(f"AI generation failed: {chunk['error']}", provider_used or "unknown")
        
        return {
            "response": full_response,
            "provider": provider_used,
            "metadata": metadata,
            "prompt_length": len(prompt),
            "response_length": len(full_response),
            "cost": self.ai_client_manager.get_total_cost() - self.total_cost
        }

    @handle_errors(context="generate_stream", reraise=True)
    async def _generate_stream(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate streaming text response."""
        prompt = payload.get("prompt", "")
        provider = payload.get("provider")
        temperature = payload.get("temperature")
        max_tokens = payload.get("max_tokens")
        system_prompt = payload.get("system_prompt")
        metadata = payload.get("metadata", {})
        
        if not prompt:
            raise ValueError("Prompt is required for streaming generation")
        
        # Add request metadata
        metadata.update({
            "service_id": self.service_id,
            "request_id": str(uuid4()),
            "timestamp": time.time(),
            "streaming": True
        })
        
        # Return an async generator for streaming
        async def stream_generator():
            async for chunk in self.ai_client_manager.generate_text(
                prompt=prompt,
                provider=provider,
                temperature=temperature,
                max_tokens=max_tokens,
                system_prompt=system_prompt,
                metadata=metadata
            ):
                yield chunk
        
        return {
            "stream": stream_generator(),
            "metadata": metadata
        }

    @handle_errors(context="get_embedding", reraise=True)
    async def _get_embedding(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Get text embeddings using specified or default provider."""
        text = payload.get("text", "")
        provider = payload.get("provider")
        
        if not text:
            raise ValueError("Text is required for embedding generation")
        
        try:
            embedding = await self.ai_client_manager.get_embedding(text, provider)
            return {
                "embedding": embedding,
                "dimensions": len(embedding),
                "text_length": len(text),
                "provider": provider or "default"
            }
        except Exception as e:
            raise APIError(f"Embedding generation failed: {e}", provider or "unknown")

    @handle_errors(context="analyze_text", reraise=True)
    async def _analyze_text(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive text analysis."""
        text = payload.get("text", "")
        analysis_type = payload.get("analysis_type", "comprehensive")
        provider = payload.get("provider")
        
        if not text:
            raise ValueError("Text is required for analysis")
        
        # Create analysis prompt based on type
        if analysis_type == "comprehensive":
            system_prompt = """You are an expert text analyst. Analyze the provided text and return a JSON response with:
            {
                "summary": "Brief summary of the text",
                "key_topics": ["list", "of", "main", "topics"],
                "sentiment": "positive/negative/neutral",
                "readability": "easy/medium/difficult",
                "word_count": number,
                "language": "detected language",
                "confidence": 0.95
            }"""
        elif analysis_type == "academic":
            system_prompt = """You are an expert academic text analyst. Analyze this academic text and provide:
            {
                "research_area": "field of study",
                "methodology": "research methodology used",
                "key_findings": ["finding1", "finding2"],
                "citations_needed": true/false,
                "academic_level": "undergraduate/graduate/doctoral/professional",
                "confidence": 0.95
            }"""
        else:
            system_prompt = "Analyze the following text and provide insights."
        
        prompt = f"Analyze this text:\n\n{text}"
        
        result = await self._generate_text({
            "prompt": prompt,
            "system_prompt": system_prompt,
            "provider": provider,
            "temperature": 0.3,  # Lower temperature for analysis consistency
            "metadata": {"analysis_type": analysis_type}
        })
        
        return {
            "analysis": result["response"],
            "analysis_type": analysis_type,
            "text_length": len(text),
            "provider": result["provider"]
        }

    @handle_errors(context="translate_text", reraise=True)
    async def _translate_text(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Translate text between languages."""
        text = payload.get("text", "")
        source_lang = payload.get("source_lang", "auto")
        target_lang = payload.get("target_lang", "en")
        provider = payload.get("provider")
        
        if not text:
            raise ValueError("Text is required for translation")
        
        system_prompt = f"""You are a professional translator. Translate the following text from {source_lang} to {target_lang}. 
        Maintain the original meaning, tone, and style. If the source language is 'auto', detect it first.
        Return only the translated text."""
        
        prompt = f"Translate this text: {text}"
        
        result = await self._generate_text({
            "prompt": prompt,
            "system_prompt": system_prompt,
            "provider": provider,
            "temperature": 0.2,  # Low temperature for consistent translation
            "metadata": {"source_lang": source_lang, "target_lang": target_lang}
        })
        
        return {
            "translation": result["response"],
            "source_lang": source_lang,
            "target_lang": target_lang,
            "original_length": len(text),
            "translated_length": len(result["response"]),
            "provider": result["provider"]
        }

    @handle_errors(context="summarize_text", reraise=True)
    async def _summarize_text(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize long text content."""
        text = payload.get("text", "")
        summary_type = payload.get("summary_type", "concise")  # concise, detailed, bullet_points
        max_length = payload.get("max_length", 200)
        provider = payload.get("provider")
        
        if not text:
            raise ValueError("Text is required for summarization")
        
        # Create summary prompt based on type
        if summary_type == "concise":
            system_prompt = f"Provide a concise summary of the following text in no more than {max_length} words. Focus on the main points and key information."
        elif summary_type == "detailed":
            system_prompt = f"Provide a detailed summary of the following text in no more than {max_length} words. Include important details and context."
        elif summary_type == "bullet_points":
            system_prompt = f"Summarize the following text as bullet points, with no more than {max_length} words total. Focus on key facts and main ideas."
        else:
            system_prompt = f"Summarize the following text in no more than {max_length} words."
        
        prompt = f"Text to summarize:\n\n{text}"
        
        result = await self._generate_text({
            "prompt": prompt,
            "system_prompt": system_prompt,
            "provider": provider,
            "temperature": 0.4,
            "metadata": {"summary_type": summary_type, "max_length": max_length}
        })
        
        return {
            "summary": result["response"],
            "summary_type": summary_type,
            "original_length": len(text),
            "summary_length": len(result["response"]),
            "compression_ratio": len(result["response"]) / len(text),
            "provider": result["provider"]
        }

    @handle_errors(context="extract_entities", reraise=True)
    async def _extract_entities(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract named entities from text."""
        text = payload.get("text", "")
        entity_types = payload.get("entity_types", ["PERSON", "ORG", "LOCATION", "DATE", "MONEY"])
        provider = payload.get("provider")
        
        if not text:
            raise ValueError("Text is required for entity extraction")
        
        system_prompt = f"""Extract named entities from the following text. Focus on these entity types: {', '.join(entity_types)}.
        Return the results as JSON in this format:
        {{
            "entities": [
                {{"text": "entity text", "type": "ENTITY_TYPE", "start": 0, "end": 10}},
                ...
            ]
        }}"""
        
        prompt = f"Extract entities from this text:\n\n{text}"
        
        result = await self._generate_text({
            "prompt": prompt,
            "system_prompt": system_prompt,
            "provider": provider,
            "temperature": 0.1,  # Very low temperature for consistent extraction
            "metadata": {"entity_types": entity_types}
        })
        
        return {
            "entities": result["response"],
            "entity_types": entity_types,
            "text_length": len(text),
            "provider": result["provider"]
        }

    @handle_errors(context="sentiment_analysis", reraise=True)
    async def _sentiment_analysis(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze sentiment of text."""
        text = payload.get("text", "")
        granularity = payload.get("granularity", "sentence")  # sentence, paragraph, document
        provider = payload.get("provider")
        
        if not text:
            raise ValueError("Text is required for sentiment analysis")
        
        system_prompt = f"""Analyze the sentiment of the following text at the {granularity} level.
        Return results as JSON:
        {{
            "overall_sentiment": "positive/negative/neutral",
            "confidence": 0.95,
            "sentiment_scores": {{"positive": 0.8, "negative": 0.1, "neutral": 0.1}},
            "detailed_analysis": ["sentence-level analysis if requested"]
        }}"""
        
        prompt = f"Analyze sentiment of this text:\n\n{text}"
        
        result = await self._generate_text({
            "prompt": prompt,
            "system_prompt": system_prompt,
            "provider": provider,
            "temperature": 0.2,
            "metadata": {"granularity": granularity}
        })
        
        return {
            "sentiment_analysis": result["response"],
            "granularity": granularity,
            "text_length": len(text),
            "provider": result["provider"]
        }

    async def _health_check(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Perform health check of the AI Agent service."""
        return {
            "status": "healthy",
            "service_id": self.service_id,
            "uptime": time.time() - self.start_time,
            "requests_processed": self.request_count,
            "successful_requests": self.successful_requests,
            "error_count": self.error_count,
            "success_rate": self.successful_requests / max(self.request_count, 1),
            "average_response_time": sum(self.response_times) / max(len(self.response_times), 1),
            "total_cost": self.ai_client_manager.get_total_cost(),
            "available_providers": list(self.ai_client_manager.clients.keys()),
            "timestamp": time.time()
        }

    async def _get_stats(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed statistics about the AI Agent service."""
        return {
            "service_stats": {
                "service_id": self.service_id,
                "uptime": time.time() - self.start_time,
                "requests_processed": self.request_count,
                "successful_requests": self.successful_requests,
                "error_count": self.error_count,
                "success_rate": self.successful_requests / max(self.request_count, 1)
            },
            "performance_stats": {
                "average_response_time": sum(self.response_times) / max(len(self.response_times), 1),
                "min_response_time": min(self.response_times) if self.response_times else 0,
                "max_response_time": max(self.response_times) if self.response_times else 0,
                "response_time_samples": len(self.response_times)
            },
            "cost_stats": {
                "total_cost": self.ai_client_manager.get_total_cost(),
                "cost_by_provider": self.ai_client_manager.get_cost_by_provider(),
                "cost_by_model": self.ai_client_manager.get_cost_by_model()
            },
            "provider_stats": {
                "available_providers": list(self.ai_client_manager.clients.keys()),
                "failed_providers": self.ai_client_manager.failed_providers
            },
            "timestamp": time.time()
        }

    # Convenience methods for direct access (bypassing MCP protocol)
    
    async def generate_text_direct(
        self,
        prompt: str,
        provider: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """Direct text generation bypassing MCP protocol."""
        result = await self._generate_text({
            "prompt": prompt,
            "provider": provider,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "system_prompt": system_prompt
        })
        return result["response"]

    async def get_embedding_direct(self, text: str, provider: Optional[str] = None) -> List[float]:
        """Direct embedding generation bypassing MCP protocol."""
        result = await self._get_embedding({
            "text": text,
            "provider": provider
        })
        return result["embedding"]

    def get_service_info(self) -> Dict[str, Any]:
        """Get basic service information."""
        return {
            "service_id": self.service_id,
            "service_type": "ai_agent",
            "version": "2.0.0",
            "description": "Centralized AI service abstraction",
            "capabilities": [
                "text_generation",
                "streaming_generation", 
                "embeddings",
                "text_analysis",
                "translation",
                "summarization",
                "entity_extraction",
                "sentiment_analysis"
            ],
            "providers": list(self.ai_client_manager.clients.keys()),
            "uptime": time.time() - self.start_time,
            "requests_processed": self.request_count
        }

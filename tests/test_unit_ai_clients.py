"""
Unit tests for AI client modules.

Tests the OpenAI and xAI client implementations including:
- Client initialization and configuration
- Message handling and response generation
- Error handling and logging
- Token estimation
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from typing import List

from src.ai_clients.openai_client import OpenAIClient
from src.ai_clients.xai_client import XAIClient
from src.models.data_models import Message, AIConfig


@pytest.fixture
def ai_config():
    """Create an AI configuration for testing."""
    return AIConfig(
        provider="openai",
        model="gpt-4o-mini",
        temperature=0.7,
        max_tokens=2000,
        system_prompt="You are a helpful assistant."
    )


@pytest.fixture
def sample_messages():
    """Create sample messages for testing."""
    conversation_id = "test-conversation-123"
    return [
        Message(
            id="1",
            conversation_id=conversation_id,
            participant="user",
            content="Hello, how are you?",
            timestamp=datetime.now()
        ),
        Message(
            id="2",
            conversation_id=conversation_id,
            participant="openai",
            content="I'm doing well, thank you!",
            timestamp=datetime.now()
        )
    ]


class TestOpenAIClient:
    """Test suite for OpenAI client."""
    
    def test_client_initialization(self, ai_config: AIConfig):
        """Test OpenAI client initialization."""
        api_key = "test-key"
        client = OpenAIClient(api_key, ai_config)
        
        assert client.config == ai_config
        assert client.client is not None
    
    @patch('openai.OpenAI')
    def test_get_response_success(self, mock_openai, ai_config: AIConfig, sample_messages: List[Message]):
        """Test successful response generation."""
        # Setup mock
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        client = OpenAIClient("test-key", ai_config)
        response = client.get_response(sample_messages)
        
        assert response == "Test response"
        mock_client.chat.completions.create.assert_called_once()
    
    @patch('openai.OpenAI')
    def test_get_response_with_system_prompt(self, mock_openai, ai_config: AIConfig, sample_messages: List[Message]):
        """Test response generation with custom system prompt."""
        # Setup mock
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Custom response"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        client = OpenAIClient("test-key", ai_config)
        system_prompt = "You are a specialized assistant."
        response = client.get_response(sample_messages, system_prompt)
        
        assert response == "Custom response"
        
        # Check that system prompt was included
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]['messages']
        assert messages[0]['role'] == 'system'
        assert messages[0]['content'] == system_prompt
    
    @patch('openai.OpenAI')
    def test_get_response_error_handling(self, mock_openai, ai_config: AIConfig, sample_messages: List[Message]):
        """Test error handling in response generation."""
        # Setup mock to raise an exception
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai.return_value = mock_client
        
        client = OpenAIClient("test-key", ai_config)
        
        with pytest.raises(Exception) as exc_info:
            client.get_response(sample_messages)
        
        assert "OpenAI API error" in str(exc_info.value)
    
    def test_convert_messages_to_openai_format(self, ai_config: AIConfig, sample_messages: List[Message]):
        """Test message format conversion."""
        client = OpenAIClient("test-key", ai_config)
        
        openai_messages = client._convert_messages_to_openai_format(sample_messages)
        
        # Should include system prompt + converted messages
        assert len(openai_messages) >= len(sample_messages)
        assert openai_messages[0]['role'] == 'system'
        assert openai_messages[1]['role'] == 'user'
        assert openai_messages[1]['content'] == "Hello, how are you?"
    
    def test_estimate_tokens(self, ai_config: AIConfig, sample_messages: List[Message]):
        """Test token estimation."""
        client = OpenAIClient("test-key", ai_config)
        
        estimated_tokens = client.estimate_tokens(sample_messages)
        
        # Should return a reasonable estimate
        assert estimated_tokens > 0
        assert isinstance(estimated_tokens, int)
    
    def test_update_config(self, ai_config: AIConfig):
        """Test configuration updates."""
        client = OpenAIClient("test-key", ai_config)
        
        client.update_config(temperature=0.8, max_tokens=1500)
        
        assert client.config.temperature == 0.8
        assert client.config.max_tokens == 1500


class TestXAIClient:
    """Test suite for xAI client."""
    
    def test_client_initialization(self, ai_config: AIConfig):
        """Test xAI client initialization."""
        api_key = "test-key"
        client = XAIClient(api_key, ai_config)
        
        assert client.config == ai_config
        assert client.client is not None
    
    @patch('xai_sdk.Client')
    @patch('src.ai_clients.xai_client.Client')
    def test_get_response_success(self, mock_client_class, sample_messages: List[Message]):
        """Test successful response generation."""
        # Create fresh config to avoid any mock interference
        test_config = AIConfig(
            provider="xai",
            model="grok-beta",
            temperature=0.7,
            max_tokens=2000,
            system_prompt="You are a helpful assistant."
        )
        
        # Setup mock instance
        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "xAI test response"
        mock_chat.sample.return_value = mock_response
        mock_client.chat.create.return_value = mock_chat
        mock_client_class.return_value = mock_client
        
        # Create client - the Client class will be mocked
        client = XAIClient("test-key", test_config)
        
        # Ensure config is still the real object, not a mock
        assert client.config == test_config
        assert client.config.model == "grok-beta"
        
        response = client.get_response(sample_messages)
        
        assert response == "xAI test response"
        mock_client.chat.create.assert_called_once_with(model="grok-beta")

    @patch('src.ai_clients.xai_client.Client')
    def test_get_response_with_system_prompt(self, mock_client_class, sample_messages: List[Message]):
        """Test response generation with system prompt."""
        # Create fresh config with xAI-specific model
        test_config = AIConfig(
            provider="xai",
            model="grok-beta",
            temperature=0.7,
            max_tokens=2000,
            system_prompt="Custom system prompt"
        )
        
        # Setup mock instance
        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Response with system prompt"
        mock_chat.sample.return_value = mock_response
        mock_client.chat.create.return_value = mock_chat
        mock_client_class.return_value = mock_client
        
        client = XAIClient("test-key", test_config)
        response = client.get_response(sample_messages)
        
        assert response == "Response with system prompt"
        mock_client.chat.create.assert_called_once_with(model="grok-beta")
    
    @patch('xai_sdk.Client')
    def test_get_response_error_handling(self, mock_xai, ai_config: AIConfig, sample_messages: List[Message]):
        """Test error handling in response generation."""
        # Setup mock to raise an exception
        mock_client = MagicMock()
        mock_client.chat.create.side_effect = Exception("xAI API Error")
        mock_xai.return_value = mock_client
        
        client = XAIClient("test-key", ai_config)
        
        with pytest.raises(Exception) as exc_info:
            client.get_response(sample_messages)
        
        assert "xAI API error" in str(exc_info.value)
    
    def test_estimate_tokens(self, ai_config: AIConfig, sample_messages: List[Message]):
        """Test token estimation."""
        client = XAIClient("test-key", ai_config)
        
        estimated_tokens = client.estimate_tokens(sample_messages)
        
        # Should return a reasonable estimate
        assert estimated_tokens > 0
        assert isinstance(estimated_tokens, int)
    
    def test_update_config(self, ai_config: AIConfig):
        """Test configuration updates."""
        client = XAIClient("test-key", ai_config)
        
        client.update_config(temperature=0.9, max_tokens=1800)
        
        assert client.config.temperature == 0.9
        assert client.config.max_tokens == 1800

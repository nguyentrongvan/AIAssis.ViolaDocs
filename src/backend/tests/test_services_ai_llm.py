"""
Tests for LLM Service.

Covers:
- LLMService class
- GeminiLLMProvider
- OpenAILLMProvider
- chat, classify_document, summarize_document, etc.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from src.app.services.ai.llm_service import (
    LLMService,
    GeminiLLMProvider,
    OpenAILLMProvider,
    LLMProvider
)


@pytest.mark.unit
class TestLLMService:
    """Tests for LLM service."""
    
    def test_llm_service_no_provider(self):
        """Test LLM service when no provider is configured."""
        with patch('src.app.services.ai.llm_service.settings') as mock_settings:
            mock_settings.gemini_api_keys = []
            mock_settings.openai_api_keys = []
            
            service = LLMService()
            
            assert service.provider is None
    
    def test_llm_service_with_gemini(self):
        """Test LLM service with Gemini provider."""
        with patch('src.app.services.ai.llm_service.settings') as mock_settings:
            mock_settings.gemini_api_keys = ["key1", "key2"]
            mock_settings.openai_api_keys = []
            
            service = LLMService()
            
            assert service.provider is not None
            assert isinstance(service.provider, GeminiLLMProvider)
    
    def test_llm_service_with_openai(self):
        """Test LLM service with OpenAI provider."""
        with patch('src.app.services.ai.llm_service.settings') as mock_settings:
            mock_settings.gemini_api_keys = []
            mock_settings.openai_api_keys = ["key1", "key2"]
            
            service = LLMService()
            
            assert service.provider is not None
            assert isinstance(service.provider, OpenAILLMProvider)
    
    def test_chat_with_context(self):
        """Test chat method with context."""
        mock_provider = MagicMock()
        mock_provider.generate_response.return_value = "Answer based on context"
        
        service = LLMService(provider=mock_provider)
        
        result = service.chat("Question?", context=["Context 1", "Context 2"])
        
        assert result == "Answer based on context"
        mock_provider.generate_response.assert_called_once()
    
    def test_chat_without_context(self):
        """Test chat method without context."""
        mock_provider = MagicMock()
        mock_provider.generate_response.return_value = "General answer"
        
        service = LLMService(provider=mock_provider)
        
        result = service.chat("Question?")
        
        assert result == "General answer"
    
    def test_chat_no_provider(self):
        """Test chat when provider is not configured."""
        service = LLMService(provider=None)
        
        result = service.chat("Question?")
        
        assert result == "LLM provider not configured"
    
    def test_classify_document(self):
        """Test document classification."""
        mock_provider = MagicMock()
        mock_provider.generate_response.return_value = "invoice"
        
        service = LLMService(provider=mock_provider)
        
        result = service.classify_document("Document content")
        
        assert result == "invoice"
    
    def test_summarize_document(self):
        """Test document summarization."""
        mock_provider = MagicMock()
        mock_provider.generate_response.return_value = "Summary text"
        
        service = LLMService(provider=mock_provider)
        
        result = service.summarize_document("Long document content")
        
        assert result == "Summary text"
    
    def test_rag_qa(self):
        """Test RAG question answering."""
        mock_provider = MagicMock()
        mock_provider.generate_response.return_value = "Answer from documents"
        
        service = LLMService(provider=mock_provider)
        
        result = service.rag_qa("Question?", ["Excerpt 1", "Excerpt 2"])
        
        assert result == "Answer from documents"


@pytest.mark.unit
class TestGeminiLLMProvider:
    """Tests for Gemini LLM provider."""
    
    def test_gemini_provider_initialization(self):
        """Test Gemini provider initialization."""
        with patch('google.generativeai') as mock_genai:
            provider = GeminiLLMProvider(["key1", "key2"])
            
            assert provider is not None
            assert len(provider.api_keys) == 2
    
    def test_gemini_generate_response(self):
        """Test Gemini response generation."""
        with patch('google.generativeai') as mock_genai:
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Generated response"
            mock_model.generate_content.return_value = mock_response
            
            provider = GeminiLLMProvider(["key1"])
            provider.models = {"key1": mock_model}
            
            result = provider.generate_response("Prompt text")
            
            assert result == "Generated response"
    
    def test_gemini_generate_response_no_model(self):
        """Test Gemini when no model is available."""
        provider = GeminiLLMProvider([])
        provider.models = {}
        
        result = provider.generate_response("Prompt text")
        
        assert "not available" in result.lower()


@pytest.mark.unit
class TestOpenAILLMProvider:
    """Tests for OpenAI LLM provider."""
    
    def test_openai_provider_initialization(self):
        """Test OpenAI provider initialization."""
        with patch('openai') as mock_openai:
            provider = OpenAILLMProvider(["key1", "key2"])
            
            assert provider is not None
            assert len(provider.api_keys) == 2
    
    def test_openai_generate_response(self):
        """Test OpenAI response generation."""
        with patch('openai') as mock_openai:
            mock_client = MagicMock()
            mock_choice = MagicMock()
            mock_choice.message.content = "Generated response"
            mock_response = MagicMock()
            mock_response.choices = [mock_choice]
            mock_client.chat.completions.create.return_value = mock_response
            
            provider = OpenAILLMProvider(["key1"])
            provider.clients = {"key1": mock_client}
            
            result = provider.generate_response("Prompt text")
            
            assert result == "Generated response"
    
    def test_openai_generate_response_no_client(self):
        """Test OpenAI when no client is available."""
        provider = OpenAILLMProvider([])
        provider.clients = {}
        
        result = provider.generate_response("Prompt text")
        
        assert "not available" in result.lower()


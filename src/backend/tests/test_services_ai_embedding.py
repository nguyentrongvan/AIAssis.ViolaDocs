"""
Tests for Embedding Service.

Covers:
- EmbeddingService class
- OpenAIEmbeddingProvider
- GeminiEmbeddingProvider
- generate_embedding
- generate_embeddings_batch
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from src.app.services.ai.embedding_service import (
    EmbeddingService,
    OpenAIEmbeddingProvider,
    GeminiEmbeddingProvider,
    EmbeddingProvider
)


@pytest.mark.unit
class TestEmbeddingService:
    """Tests for embedding service."""
    
    def test_embedding_service_no_provider(self):
        """Test embedding service when no provider is configured."""
        with patch('src.app.services.ai.embedding_service.settings') as mock_settings:
            mock_settings.openai_api_keys = []
            mock_settings.gemini_api_keys = []
            
            service = EmbeddingService()
            
            assert service.provider is None
    
    def test_embedding_service_with_openai(self):
        """Test embedding service with OpenAI provider."""
        with patch('src.app.services.ai.embedding_service.settings') as mock_settings:
            mock_settings.openai_api_keys = ["key1"]
            mock_settings.gemini_api_keys = []
            
            service = EmbeddingService()
            
            assert service.provider is not None
            assert isinstance(service.provider, OpenAIEmbeddingProvider)
    
    def test_embedding_service_with_gemini(self):
        """Test embedding service with Gemini provider."""
        with patch('src.app.services.ai.embedding_service.settings') as mock_settings:
            mock_settings.openai_api_keys = []
            mock_settings.gemini_api_keys = ["key1"]
            
            service = EmbeddingService()
            
            assert service.provider is not None
            assert isinstance(service.provider, GeminiEmbeddingProvider)
    
    def test_generate_embedding(self):
        """Test generating embedding."""
        mock_provider = MagicMock()
        mock_provider.generate_embedding.return_value = [0.1] * 1536
        
        service = EmbeddingService(provider=mock_provider)
        
        result = service.generate_embedding("Sample text")
        
        assert len(result) == 1536
        assert result[0] == 0.1
    
    def test_generate_embedding_no_provider(self):
        """Test generating embedding when provider is not configured."""
        service = EmbeddingService(provider=None)
        
        result = service.generate_embedding("Sample text")
        
        assert len(result) == 1536
        assert all(v == 0.0 for v in result)
    
    def test_generate_embeddings_batch(self):
        """Test generating embeddings for multiple texts."""
        mock_provider = MagicMock()
        mock_provider.generate_embeddings_batch.return_value = [[0.1] * 1536, [0.2] * 1536]
        
        service = EmbeddingService(provider=mock_provider)
        
        result = service.generate_embeddings_batch(["Text 1", "Text 2"])
        
        assert len(result) == 2
        assert len(result[0]) == 1536


@pytest.mark.unit
class TestOpenAIEmbeddingProvider:
    """Tests for OpenAI embedding provider."""
    
    def test_openai_embedding_provider_initialization(self):
        """Test OpenAI embedding provider initialization."""
        with patch('openai') as mock_openai:
            provider = OpenAIEmbeddingProvider(["key1", "key2"])
            
            assert provider is not None
            assert len(provider.api_keys) == 2
    
    def test_openai_generate_embedding(self):
        """Test OpenAI embedding generation."""
        with patch('openai') as mock_openai:
            mock_client = MagicMock()
            mock_data = MagicMock()
            mock_data.embedding = [0.1] * 1536
            mock_response = MagicMock()
            mock_response.data = [mock_data]
            mock_client.embeddings.create.return_value = mock_response
            
            provider = OpenAIEmbeddingProvider(["key1"])
            provider.clients = {"key1": mock_client}
            
            result = provider.generate_embedding("Sample text")
            
            assert len(result) == 1536
            assert result[0] == 0.1
    
    def test_openai_generate_embedding_no_client(self):
        """Test OpenAI when no client is available."""
        provider = OpenAIEmbeddingProvider([])
        provider.clients = {}
        
        result = provider.generate_embedding("Sample text")
        
        assert len(result) == 1536
        assert all(v == 0.0 for v in result)


@pytest.mark.unit
class TestGeminiEmbeddingProvider:
    """Tests for Gemini embedding provider."""
    
    def test_gemini_embedding_provider_initialization(self):
        """Test Gemini embedding provider initialization."""
        with patch('google.generativeai') as mock_genai:
            provider = GeminiEmbeddingProvider(["key1", "key2"])
            
            assert provider is not None
            assert len(provider.api_keys) == 2
    
    def test_gemini_generate_embedding(self):
        """Test Gemini embedding generation."""
        with patch('google.generativeai') as mock_genai:
            mock_model = MagicMock()
            mock_model.embed_content.return_value = {"embedding": [0.1] * 768}
            
            provider = GeminiEmbeddingProvider(["key1"])
            provider.models = {"key1": mock_model}
            
            result = provider.generate_embedding("Sample text")
            
            assert len(result) == 768
            assert result[0] == 0.1
    
    def test_gemini_generate_embedding_no_model(self):
        """Test Gemini when no model is available."""
        provider = GeminiEmbeddingProvider([])
        provider.models = {}
        
        result = provider.generate_embedding("Sample text")
        
        assert len(result) == 768
        assert all(v == 0.0 for v in result)

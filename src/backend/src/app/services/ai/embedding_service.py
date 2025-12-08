import random
from typing import List, Optional
from ...config import settings


class EmbeddingProvider:
    """Base class for embedding providers"""
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector from text"""
        raise NotImplementedError
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        return [self.generate_embedding(text) for text in texts]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embeddings with multiple key support"""
    
    def __init__(self, api_keys: List[str]):
        self.api_keys = api_keys
        self.clients = {}
        self._init_clients()
    
    def _init_clients(self):
        """Initialize clients for all API keys"""
        try:
            import openai
            for key in self.api_keys:
                try:
                    self.clients[key] = openai.OpenAI(api_key=key)
                except Exception as e:
                    print(f"Failed to initialize OpenAI embedding client with key: {e}")
        except ImportError:
            print("openai not installed")
    
    def _get_random_client(self):
        """Get a random client from available keys"""
        if not self.clients:
            return None
        key = random.choice(list(self.clients.keys()))
        return self.clients[key]
    
    def generate_embedding(self, text: str) -> List[float]:
        client = self._get_random_client()
        if not client:
            return [0.0] * 1536  # Default dimension
        
        try:
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            # Retry with another key if quota exceeded
            if "quota" in str(e).lower() or "429" in str(e) or "rate limit" in str(e).lower():
                if len(self.clients) > 1:
                    client = self._get_random_client()
                    if client:
                        try:
                            response = client.embeddings.create(
                                model="text-embedding-3-small",
                                input=text
                            )
                            return response.data[0].embedding
                        except:
                            pass
            print(f"Error generating embedding: {e}")
            return [0.0] * 1536


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Gemini embeddings with multiple key support"""
    
    def __init__(self, api_keys: List[str]):
        self.api_keys = api_keys
        self.models = {}
        self._init_models()
    
    def _init_models(self):
        """Initialize models for all API keys"""
        try:
            import google.generativeai as genai
            for key in self.api_keys:
                try:
                    genai.configure(api_key=key)
                    self.models[key] = genai.GenerativeModel('models/embedding-001')
                except Exception as e:
                    print(f"Failed to initialize Gemini embedding model with key: {e}")
        except ImportError:
            print("google-generativeai not installed")
    
    def _get_random_model(self):
        """Get a random model from available keys"""
        if not self.models:
            return None
        key = random.choice(list(self.models.keys()))
        return self.models[key]
    
    def generate_embedding(self, text: str) -> List[float]:
        model = self._get_random_model()
        if not model:
            return [0.0] * 768  # Default dimension
        
        try:
            result = model.embed_content(text)
            return result['embedding']
        except Exception as e:
            # Retry with another key if quota exceeded
            if "quota" in str(e).lower() or "429" in str(e):
                if len(self.models) > 1:
                    model = self._get_random_model()
                    if model:
                        try:
                            result = model.embed_content(text)
                            return result['embedding']
                        except:
                            pass
            print(f"Error generating embedding: {e}")
            return [0.0] * 768


class EmbeddingService:
    """Embedding Service with provider abstraction"""
    
    def __init__(self, provider: Optional[EmbeddingProvider] = None):
        self.provider = provider or self._get_default_provider()
    
    def _get_default_provider(self) -> Optional[EmbeddingProvider]:
        """Get default embedding provider"""
        openai_keys = settings.openai_api_keys
        gemini_keys = settings.gemini_api_keys
        
        if openai_keys:
            return OpenAIEmbeddingProvider(openai_keys)
        elif gemini_keys:
            return GeminiEmbeddingProvider(gemini_keys)
        else:
            return None
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        if not self.provider:
            return [0.0] * 1536  # Default dimension
        return self.provider.generate_embedding(text)
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        if not self.provider:
            return [[0.0] * 1536 for _ in texts]
        return self.provider.generate_embeddings_batch(texts)


def get_embedding_service() -> Optional[EmbeddingService]:
    """Factory to get embedding service"""
    service = EmbeddingService()
    if service.provider:
        return service
    return None




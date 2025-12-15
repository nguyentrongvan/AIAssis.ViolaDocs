import os
from typing import List, Optional, Dict, Any
from ...config import settings


class EmbeddingProvider:
    """Base class for embedding providers"""
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector from text"""
        raise NotImplementedError
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        return [self.generate_embedding(text) for text in texts]


class LocalEmbeddingProvider(EmbeddingProvider):
    """Local embedding provider using sentence-transformers (free, runs locally)"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize local embedding provider.
        
        Popular models:
        - all-MiniLM-L6-v2: Fast, lightweight (384 dims, ~80MB)
        - paraphrase-multilingual-MiniLM-L12-v2: Multilingual (384 dims, ~420MB)
        - all-mpnet-base-v2: Better quality (768 dims, ~420MB)
        """
        self.model_name = model_name
        self.model = None
        self.dimension = 384  # Default for MiniLM models
        self._init_model()
    
    def _init_model(self):
        """Initialize the sentence-transformers model"""
        try:
            from sentence_transformers import SentenceTransformer
            print(f"Loading local embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            # Get actual dimension from model
            self.dimension = self.model.get_sentence_embedding_dimension()
            print(f"Local embedding model loaded successfully (dimension: {self.dimension})")
        except ImportError:
            print("sentence-transformers not installed. Install with: pip install sentence-transformers")
            self.model = None
        except Exception as e:
            print(f"Failed to load local embedding model: {e}")
            self.model = None
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        if not self.model:
            return [0.0] * self.dimension
        
        try:
            # Normalize text
            if not text or not text.strip():
                return [0.0] * self.dimension
            
            # Generate embedding
            embedding = self.model.encode(text, normalize_embeddings=True, show_progress_bar=False)
            return embedding.tolist()
        except Exception as e:
            print(f"Error generating local embedding: {e}")
            return [0.0] * self.dimension
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts (optimized batch processing)"""
        if not self.model:
            return [[0.0] * self.dimension for _ in texts]
        
        try:
            # Filter empty texts
            valid_texts = [text if text and text.strip() else "" for text in texts]
            
            # Generate embeddings in batch (more efficient)
            embeddings = self.model.encode(
                valid_texts,
                normalize_embeddings=True,
                show_progress_bar=False,
                batch_size=32
            )
            return embeddings.tolist()
        except Exception as e:
            print(f"Error generating local embeddings batch: {e}")
            return [[0.0] * self.dimension for _ in texts]


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Ollama embedding provider using OpenAI-compatible API"""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None, model: str = "nomic-text-embedding"):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.client = None
        self.dimension = 768  # Default for nomic-text-embedding
        self._init_client()
    
    def _init_client(self):
        """Initialize OpenAI client with Ollama base URL"""
        try:
            import openai
            self.client = openai.OpenAI(
                base_url=self.base_url,
                api_key=self.api_key or "ollama"  # Ollama doesn't require key, but OpenAI client needs one
            )
        except ImportError:
            print("openai not installed")
            self.client = None
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        if not self.client:
            return [0.0] * self.dimension
        
        try:
            if not text or not text.strip():
                return [0.0] * self.dimension
            
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            embedding = response.data[0].embedding
            # Update dimension based on actual response
            if embedding:
                self.dimension = len(embedding)
            return embedding
        except Exception as e:
            print(f"Error generating Ollama embedding: {e}")
            return [0.0] * self.dimension
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        if not self.client:
            return [[0.0] * self.dimension for _ in texts]
        
        try:
            # Filter empty texts
            valid_texts = [text if text and text.strip() else "" for text in texts]
            
            response = self.client.embeddings.create(
                model=self.model,
                input=valid_texts
            )
            
            embeddings = [item.embedding for item in response.data]
            # Update dimension based on actual response
            if embeddings and embeddings[0]:
                self.dimension = len(embeddings[0])
            
            return embeddings
        except Exception as e:
            print(f"Error generating Ollama embeddings batch: {e}")
            return [[0.0] * self.dimension for _ in texts]


class ChromaVectorStore:
    """Chroma vector store wrapper (local persistent or HTTP server)"""
    
    def __init__(
        self,
        persist_dir: str,
        collection_name: str,
        server_host: str = "",
        server_port: int = 8000,
        server_ssl: bool = False
    ):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.server_host = server_host
        self.server_port = server_port
        self.server_ssl = server_ssl
        self.client = None
        self.collection = None
        self._init_store()
    
    def _init_store(self):
        try:
            import chromadb
            # If server_host is provided, use HTTP client; otherwise use local persistent
            if self.server_host:
                scheme = "https" if self.server_ssl else "http"
                self.client = chromadb.HttpClient(
                    host=self.server_host,
                    port=self.server_port,
                    ssl=self.server_ssl
                )
                print(f"Chroma HTTP client connected to {scheme}://{self.server_host}:{self.server_port}")
            else:
                os.makedirs(self.persist_dir, exist_ok=True)
                self.client = chromadb.PersistentClient(path=self.persist_dir)
                print(f"Chroma persistent client at {self.persist_dir}")
            
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            print(f"Chroma collection ready ({self.collection_name})")
        except ImportError:
            print("chromadb not installed. Install with: pip install chromadb")
            self.collection = None
        except Exception as e:
            print(f"Failed to init Chroma store: {e}")
            self.collection = None
    
    def upsert(self, ids: List[str], embeddings: List[List[float]], metadatas: List[Dict[str, Any]]):
        if not self.collection:
            return
        try:
            self.collection.upsert(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas
            )
        except Exception as e:
            print(f"Chroma upsert failed: {e}")
    
    def query(self, query_embeddings: List[List[float]], where: Optional[Dict[str, Any]], top_k: int):
        if not self.collection:
            return {"ids": [], "distances": [], "metadatas": []}
        try:
            return self.collection.query(
                query_embeddings=query_embeddings,
                n_results=top_k,
                where=where or {}
            )
        except Exception as e:
            print(f"Chroma query failed: {e}")
            return {"ids": [], "distances": [], "metadatas": []}


class EmbeddingService:
    """Embedding Service with encoder + vector store abstraction"""
    
    def __init__(
        self,
        embedder: Optional[EmbeddingProvider] = None,
        store: Optional[ChromaVectorStore] = None
    ):
        self.embedder = embedder or self._get_default_embedder()
        self.store = store or self._get_default_store()
    
    def _get_default_embedder(self) -> Optional[EmbeddingProvider]:
        """Get default embedding generator (prioritizes Ollama, then local, then cloud APIs)"""
        # Priority: Ollama > Local (free) > OpenAI > Gemini
        if settings.ollama_base_url:
            try:
                return OllamaEmbeddingProvider(
                    base_url=settings.ollama_base_url,
                    api_key=settings.ollama_api_key if settings.ollama_api_key else None,
                    model=settings.ollama_embedding_model
                )
            except Exception as e:
                print(f"Ollama embedding provider not available: {e}")
        
        # Fallback to local embedding provider
        try:
            model_name = getattr(settings, 'embedding_model_name', 'all-MiniLM-L6-v2')
            local_provider = LocalEmbeddingProvider(model_name=model_name)
            if local_provider.model is not None:
                return local_provider
        except Exception as e:
            print(f"Local embedding provider not available: {e}")
        
        # Last resort: try local again even if it failed before
        try:
            return LocalEmbeddingProvider()
        except:
            return None
    
    def _get_default_store(self) -> Optional[ChromaVectorStore]:
        """Get default vector store (Chroma local)"""
        try:
            return ChromaVectorStore(
                persist_dir=getattr(settings, "chroma_persist_dir", "./data/chroma"),
                collection_name=getattr(settings, "chroma_collection", "embeddings"),
                server_host=getattr(settings, "chroma_server_host", ""),
                server_port=getattr(settings, "chroma_server_port", 8000),
                server_ssl=getattr(settings, "chroma_server_ssl", False),
            )
        except Exception as e:
            print(f"Chroma store not available: {e}")
            return None
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        if not self.embedder:
            return [0.0] * 1536  # Default dimension if everything missing
        return self.embedder.generate_embedding(text)
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        if not self.embedder:
            return [[0.0] * 1536 for _ in texts]
        return self.embedder.generate_embeddings_batch(texts)
    
    def upsert_embeddings(self, ids: List[str], embeddings: List[List[float]], metadatas: List[Dict[str, Any]]):
        """Upsert embeddings into vector store"""
        if not self.store:
            print("Vector store not configured; skipping upsert")
            return
        self.store.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas)
    
    def query_embeddings(self, query_embedding: List[float], where: Optional[Dict[str, Any]], top_k: int = 10):
        """Query vector store for similar embeddings"""
        if not self.store:
            print("Vector store not configured; returning empty results")
            return {"ids": [], "distances": [], "metadatas": []}
        return self.store.query(query_embeddings=[query_embedding], where=where, top_k=top_k)


def get_embedding_service() -> Optional[EmbeddingService]:
    """Factory to get embedding service"""
    service = EmbeddingService()
    if service.embedder or service.store:
        return service
    return None




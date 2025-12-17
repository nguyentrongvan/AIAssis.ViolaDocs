import os
from typing import List, Optional, Dict, Any
from ...config import settings, get_ollama_base_url_from_db, get_ollama_embedding_model_from_db


class EmbeddingModelUnavailableError(Exception):
    """Exception raised when embedding model is not available"""
    pass

# Disable ChromaDB telemetry BEFORE importing chromadb
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"

# Monkey-patch posthog before chromadb imports it
# This must happen at module level, before any chromadb import
try:
    import sys
    import types
    
    # Create a mock posthog module before chromadb imports it
    class MockPosthogCapture:
        """Mock posthog capture that accepts any arguments but does nothing"""
        def __call__(self, *args, **kwargs):
            pass  # No-op
        def __getattr__(self, name):
            return self  # Return self for any attribute access
    
    # Inject mock into sys.modules before chromadb imports
    if 'posthog' not in sys.modules:
        mock_posthog = types.ModuleType('posthog')
        mock_posthog.capture = MockPosthogCapture()
        sys.modules['posthog'] = mock_posthog
    else:
        # If posthog already exists, patch it
        posthog = sys.modules['posthog']
        if hasattr(posthog, 'capture'):
            posthog.capture = MockPosthogCapture()
except Exception as e:
    # If patching fails, continue anyway - errors are non-critical
    pass


class EmbeddingProvider:
    """Base class for embedding providers"""
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector from text"""
        raise NotImplementedError
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        return [self.generate_embedding(text) for text in texts]


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Ollama embedding provider using native API"""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None, model: str = "nomic-text-embedding"):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.model = model
        self.http_client = None
        self.dimension = 1536  # Default for nomic-text-embedding (actual dimension)
        self._init_client()
        # Try to detect actual dimension from model
        self._detect_dimension()
    
    def _init_client(self):
        """Initialize HTTP client for Ollama native API"""
        try:
            import httpx
            self.http_client = httpx.Client(
                timeout=60.0,
                base_url=self.base_url
            )
        except ImportError:
            print("httpx not installed")
            self.http_client = None
        except Exception as e:
            print(f"Failed to initialize Ollama embedding HTTP client: {e}")
            self.http_client = None
    
    def is_model_available(self) -> bool:
        """Check if the embedding model is available"""
        if not self.http_client:
            return False
        
        # Try the configured model name first
        model_names_to_try = [self.model]
        
        # If model doesn't have :latest, also try with :latest
        if ":latest" not in self.model:
            model_names_to_try.append(f"{self.model}:latest")
        # If model has :latest, also try without it
        elif self.model.endswith(":latest"):
            model_names_to_try.append(self.model[:-7])  # Remove :latest
        
        for model_name in model_names_to_try:
            try:
                # Make a minimal test call to check if model exists using native API
                response = self.http_client.post(
                    "/api/embeddings",
                    json={
                        "model": model_name,
                        "prompt": "test"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    embedding = data.get("embedding", [])
                    if embedding:
                        # If we found a working model name that's different, update it
                        if model_name != self.model:
                            print(f"Info: Using model name '{model_name}' instead of '{self.model}'")
                            self.model = model_name
                        return True
                elif response.status_code == 404:
                    # Try next model name
                    continue
            except Exception as e:
                error_msg = str(e).lower()
                if "404" in error_msg or "not found" in error_msg:
                    # Try next model name
                    continue
                # For connection errors, log but don't fail - might be temporary
                if "connection" in error_msg or "timeout" in error_msg or "refused" in error_msg or "cannot connect" in error_msg:
                    print(f"Warning: Could not check model availability (connection issue): {e}")
                    return False
                # For other errors, try next model name
                continue
        
        # None of the model names worked
        return False
    
    def _detect_dimension(self):
        """Detect actual embedding dimension by making a test call"""
        if not self.http_client:
            return
        try:
            # Make a minimal test call to detect dimension using native API
            response = self.http_client.post(
                "/api/embeddings",
                json={
                    "model": self.model,
                    "prompt": "test"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                embedding = data.get("embedding", [])
                if embedding:
                    self.dimension = len(embedding)
                    print(f"Detected Ollama embedding dimension: {self.dimension}")
            elif response.status_code == 404:
                print(f"Ollama model '{self.model}' not available yet (404). Will use default dimension {self.dimension}.")
                print(f"  Make sure Ollama is running and model is pulled: ollama pull {self.model}")
        except Exception as e:
            error_msg = str(e).lower()
            # Don't log 404 errors as errors - Ollama might not be ready or model not pulled yet
            if "404" in error_msg or "not found" in error_msg:
                print(f"Ollama model '{self.model}' not available yet (404). Will use default dimension {self.dimension}.")
                print(f"  Make sure Ollama is running and model is pulled: ollama pull {self.model}")
            else:
                print(f"Could not detect embedding dimension: {e}, using default: {self.dimension}")
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        if not self.http_client:
            raise EmbeddingModelUnavailableError(
                f"Ollama embedding client not initialized. "
                f"Make sure Ollama is running at {self.base_url} and model '{self.model}' is available. "
                f"Run: ollama pull {self.model}"
            )
        
        if not self.is_model_available():
            raise EmbeddingModelUnavailableError(
                f"Ollama embedding model '{self.model}' is not available. "
                f"Make sure Ollama is running and model is pulled: ollama pull {self.model}"
            )
        
        try:
            if not text or not text.strip():
                raise ValueError("Cannot generate embedding for empty text")
            
            # Call Ollama native API
            response = self.http_client.post(
                "/api/embeddings",
                json={
                    "model": self.model,
                    "prompt": text
                }
            )
            
            if response.status_code != 200:
                if response.status_code == 404:
                    raise EmbeddingModelUnavailableError(
                        f"Ollama embedding model '{self.model}' is not available. "
                        f"Make sure Ollama is running and model is pulled: ollama pull {self.model}"
                    )
                raise RuntimeError(f"Ollama API error: HTTP {response.status_code} - {response.text}")
            
            data = response.json()
            embedding = data.get("embedding", [])
            
            # Update dimension based on actual response
            if embedding:
                self.dimension = len(embedding)
            
            return embedding
        except EmbeddingModelUnavailableError:
            raise
        except Exception as e:
            error_msg = str(e).lower()
            if "404" in error_msg or "not found" in error_msg:
                raise EmbeddingModelUnavailableError(
                    f"Ollama embedding model '{self.model}' is not available. "
                    f"Make sure Ollama is running and model is pulled: ollama pull {self.model}"
                ) from e
            raise RuntimeError(f"Error generating Ollama embedding: {e}") from e
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        if not self.http_client:
            raise EmbeddingModelUnavailableError(
                f"Ollama embedding client not initialized. "
                f"Make sure Ollama is running at {self.base_url} and model '{self.model}' is available. "
                f"Run: ollama pull {self.model}"
            )
        
        if not self.is_model_available():
            raise EmbeddingModelUnavailableError(
                f"Ollama embedding model '{self.model}' is not available. "
                f"Make sure Ollama is running and model is pulled: ollama pull {self.model}"
            )
        
        try:
            # Filter empty texts
            valid_texts = [text if text and text.strip() else "" for text in texts]
            if not valid_texts or all(not t for t in valid_texts):
                raise ValueError("Cannot generate embeddings for empty text list")
            
            # Ollama native API doesn't support batch, so call individually
            embeddings = []
            for text in valid_texts:
                if not text or not text.strip():
                    # Use zero vector for empty text
                    embeddings.append([0.0] * self.dimension)
                    continue
                
                response = self.http_client.post(
                    "/api/embeddings",
                    json={
                        "model": self.model,
                        "prompt": text
                    }
                )
                
                if response.status_code != 200:
                    if response.status_code == 404:
                        raise EmbeddingModelUnavailableError(
                            f"Ollama embedding model '{self.model}' is not available. "
                            f"Make sure Ollama is running and model is pulled: ollama pull {self.model}"
                        )
                    raise RuntimeError(f"Ollama API error: HTTP {response.status_code} - {response.text}")
                
                data = response.json()
                embedding = data.get("embedding", [])
                if embedding:
                    embeddings.append(embedding)
                    # Update dimension based on actual response
                    if len(embedding) != self.dimension:
                        self.dimension = len(embedding)
                else:
                    embeddings.append([0.0] * self.dimension)
            
            return embeddings
        except EmbeddingModelUnavailableError:
            raise
        except Exception as e:
            error_msg = str(e).lower()
            if "404" in error_msg or "not found" in error_msg:
                raise EmbeddingModelUnavailableError(
                    f"Ollama embedding model '{self.model}' is not available. "
                    f"Make sure Ollama is running and model is pulled: ollama pull {self.model}"
                ) from e
            raise RuntimeError(f"Error generating Ollama embeddings batch: {e}") from e


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
            # Ensure telemetry is disabled BEFORE importing chromadb
            os.environ["ANONYMIZED_TELEMETRY"] = "False"
            os.environ["CHROMA_TELEMETRY"] = "False"
            
            import chromadb
            
            # Try to monkey-patch posthog capture to prevent errors
            # This is a fallback in case module-level patching didn't work
            try:
                # Try multiple import paths
                import_paths = [
                    'chromadb.telemetry.posthog',
                    'chromadb.telemetry.events',
                ]
                for path in import_paths:
                    try:
                        module = __import__(path, fromlist=[''])
                        if hasattr(module, 'capture'):
                            def noop_capture(*args, **kwargs):
                                pass
                            module.capture = noop_capture
                    except:
                        continue
                
                # Also try to patch the posthog module directly if it exists
                try:
                    import posthog
                    if hasattr(posthog, 'capture'):
                        def noop_capture(*args, **kwargs):
                            pass
                        posthog.capture = noop_capture
                except:
                    pass
            except:
                # If we can't patch it, that's okay - errors are non-critical
                pass
            
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
            
            # Check if collection exists and get its dimension
            try:
                existing_collection = self.client.get_collection(name=self.collection_name)
                existing_dim = existing_collection.metadata.get("dimension") if hasattr(existing_collection, 'metadata') else None
                # Try to get dimension from collection count (if empty, we can recreate)
                count = existing_collection.count()
                if count == 0:
                    # Empty collection, can safely delete and recreate with new dimension
                    print(f"Collection '{self.collection_name}' is empty, will recreate with correct dimension")
                    self.client.delete_collection(name=self.collection_name)
                    self.collection = None
                else:
                    # Collection has data, check dimension
                    # Get dimension from first embedding if possible
                    try:
                        sample = existing_collection.peek(limit=1)
                        if sample.get("embeddings") and len(sample["embeddings"]) > 0:
                            existing_dim = len(sample["embeddings"][0])
                    except:
                        pass
                    self.collection = existing_collection
                    if existing_dim:
                        print(f"Existing collection dimension: {existing_dim}")
            except:
                # Collection doesn't exist, will create new one
                self.collection = None
            
            # Create or get collection
            if not self.collection:
                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
                print(f"Chroma collection ready ({self.collection_name})")
            else:
                print(f"Chroma collection ready ({self.collection_name})")
        except ImportError:
            print("chromadb not installed. Install with: pip install chromadb")
            self.collection = None
        except Exception as e:
            print(f"Failed to init Chroma store: {e}")
            import traceback
            traceback.print_exc()
            self.collection = None
    
    def upsert(self, ids: List[str], embeddings: List[List[float]], metadatas: List[Dict[str, Any]]):
        if not self.collection:
            return
        try:
            # Check dimension mismatch
            if embeddings and len(embeddings) > 0:
                embedding_dim = len(embeddings[0])
                # Try to get collection dimension
                try:
                    sample = self.collection.peek(limit=1)
                    if sample.get("embeddings") and len(sample["embeddings"]) > 0:
                        collection_dim = len(sample["embeddings"][0])
                        if embedding_dim != collection_dim:
                            print(f"Dimension mismatch: embedding={embedding_dim}, collection={collection_dim}")
                            print(f"Deleting and recreating collection '{self.collection_name}' with dimension {embedding_dim}")
                            # Delete and recreate collection
                            self.client.delete_collection(name=self.collection_name)
                            self.collection = self.client.create_collection(
                                name=self.collection_name,
                                metadata={"hnsw:space": "cosine"}
                            )
                            print(f"Collection recreated with dimension {embedding_dim}")
                except:
                    # Collection might be empty, proceed with upsert
                    pass
            
            self.collection.upsert(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas
            )
        except Exception as e:
            error_msg = str(e)
            if "dimension" in error_msg.lower():
                # Dimension mismatch - try to fix by recreating collection
                print(f"Chroma dimension mismatch detected: {e}")
                print(f"Attempting to recreate collection '{self.collection_name}'...")
                try:
                    self.client.delete_collection(name=self.collection_name)
                    if embeddings and len(embeddings) > 0:
                        embedding_dim = len(embeddings[0])
                        self.collection = self.client.create_collection(
                            name=self.collection_name,
                            metadata={"hnsw:space": "cosine"}
                        )
                        print(f"Collection recreated with dimension {embedding_dim}, retrying upsert...")
                        # Retry upsert
                        self.collection.upsert(
                            ids=ids,
                            embeddings=embeddings,
                            metadatas=metadatas
                        )
                        print("Upsert successful after collection recreation")
                except Exception as e2:
                    print(f"Failed to fix dimension mismatch: {e2}")
            else:
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
        """Get default embedding generator (Ollama only)"""
        if settings.ollama_base_url:
            try:
                provider = OllamaEmbeddingProvider(
                    base_url=settings.ollama_base_url,
                    api_key=settings.ollama_api_key if settings.ollama_api_key else None,
                    model=settings.ollama_embedding_model
                )
                # Verify client was initialized
                if provider.http_client is not None:
                    # Don't check model availability here - do it lazily when actually needed
                    # This allows the service to be created even if Ollama is temporarily unavailable
                    # The availability check will happen in is_available() or when generating embeddings
                    print(f"Ollama embedding provider initialized: {settings.ollama_base_url}, model: {settings.ollama_embedding_model}")
                    return provider
                else:
                    print(f"Warning: Ollama embedding provider client not initialized for {settings.ollama_base_url}")
                    return None
            except Exception as e:
                print(f"Ollama embedding provider not available: {e}")
                import traceback
                traceback.print_exc()
        
        # No fallback - return None if Ollama is not available
        print("Warning: No embedding provider available. Please configure Ollama.")
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
    
    def is_available(self) -> bool:
        """Check if embedding service is available and ready"""
        if not self.embedder:
            return False
        if isinstance(self.embedder, OllamaEmbeddingProvider):
            return self.embedder.is_model_available()
        # For other providers, assume available if embedder exists
        return True
    
    def get_availability_diagnostic(self) -> str:
        """Get detailed diagnostic information about why embedding service is not available"""
        if not self.embedder:
            # Try to create a new provider to get diagnostic info
            if not settings.ollama_base_url:
                return (
                    "Ollama base URL is not configured. "
                    f"Please set OLLAMA_BASE_URL in your .env file (current: {settings.ollama_base_url}). "
                    "Example: OLLAMA_BASE_URL=http://localhost:11434"
                )
            
            try:
                provider = OllamaEmbeddingProvider(
                    base_url=settings.ollama_base_url,
                    api_key=settings.ollama_api_key if settings.ollama_api_key else None,
                    model=settings.ollama_embedding_model
                )
                
                if provider.http_client is None:
                    return (
                        f"Failed to connect to Ollama at {settings.ollama_base_url}. "
                        "Please ensure Ollama is running and accessible. "
                        "Check: curl http://localhost:11434/api/tags"
                    )
                
                if not provider.is_model_available():
                    return (
                        f"Ollama embedding model '{settings.ollama_embedding_model}' is not available. "
                        f"Please pull the model: ollama pull {settings.ollama_embedding_model}. "
                        f"Ollama base URL: {settings.ollama_base_url}"
                    )
                
                return "Embedding provider should be available but is not initialized."
            except Exception as e:
                return (
                    f"Error initializing Ollama embedding provider: {str(e)}. "
                    f"Base URL: {settings.ollama_base_url}, Model: {settings.ollama_embedding_model}"
                )
        
        if isinstance(self.embedder, OllamaEmbeddingProvider):
            if self.embedder.http_client is None:
                return (
                    f"Ollama client not initialized. "
                    f"Base URL: {self.embedder.base_url}, Model: {self.embedder.model}"
                )
            if not self.embedder.is_model_available():
                return (
                    f"Ollama embedding model '{self.embedder.model}' is not available. "
                    f"Please ensure Ollama is running at {self.embedder.base_url} and pull the model: "
                    f"ollama pull {self.embedder.model}"
                )
        
        return "Unknown issue with embedding service availability."
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on embedding service"""
        status = {
            "available": False,
            "embedder": None,
            "store": None,
            "errors": []
        }
        
        # Check embedder
        if self.embedder:
            if isinstance(self.embedder, OllamaEmbeddingProvider):
                if self.embedder.http_client is None:
                    status["errors"].append("Ollama client not initialized")
                elif not self.embedder.is_model_available():
                    status["errors"].append(
                        f"Ollama model '{self.embedder.model}' is not available. "
                        f"Run: ollama pull {self.embedder.model}"
                    )
                else:
                    status["embedder"] = {
                        "type": "ollama",
                        "model": self.embedder.model,
                        "dimension": self.embedder.dimension,
                        "base_url": self.embedder.base_url
                    }
            else:
                status["embedder"] = {"type": "unknown"}
        else:
            status["errors"].append("No embedding provider configured")
        
        # Check store
        if self.store:
            if self.store.collection is not None:
                status["store"] = {
                    "type": "chroma",
                    "collection": self.store.collection_name,
                    "persist_dir": self.store.persist_dir if not self.store.server_host else None,
                    "server": f"{self.store.server_host}:{self.store.server_port}" if self.store.server_host else None
                }
            else:
                status["errors"].append("Chroma vector store not initialized")
        else:
            status["errors"].append("No vector store configured")
        
        status["available"] = (
            status["embedder"] is not None and 
            status["store"] is not None and 
            len(status["errors"]) == 0
        )
        
        return status
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        if not self.embedder:
            raise EmbeddingModelUnavailableError(
                "Embedding provider not configured. Please configure Ollama."
            )
        return self.embedder.generate_embedding(text)
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        if not self.embedder:
            raise EmbeddingModelUnavailableError(
                "Embedding provider not configured. Please configure Ollama."
            )
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




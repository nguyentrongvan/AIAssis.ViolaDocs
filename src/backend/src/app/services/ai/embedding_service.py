import os
from typing import List, Optional, Dict, Any
from ...config import settings

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
    """Ollama embedding provider using OpenAI-compatible API"""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None, model: str = "nomic-text-embedding"):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.client = None
        self.dimension = 1536  # Default for nomic-text-embedding (actual dimension)
        self._init_client()
        # Try to detect actual dimension from model
        self._detect_dimension()
    
    def _init_client(self):
        """Initialize OpenAI client with Ollama base URL"""
        try:
            import openai
            import httpx
            
            # The proxies error comes from httpx.Client being initialized with proxies parameter
            # We need to create httpx client WITHOUT base_url (OpenAI will handle that)
            # and explicitly exclude proxies parameter
            
            # Create httpx client without proxies
            # Don't pass base_url to httpx - OpenAI client will handle it
            http_client = httpx.Client(
                timeout=60.0,
                # Explicitly don't include proxies or base_url here
            )
            
            # Now initialize OpenAI client with the custom http_client
            # This should prevent proxies from being passed
            try:
                self.client = openai.OpenAI(
                    base_url=self.base_url,
                    api_key=self.api_key or "ollama",
                    http_client=http_client
                )
            except (TypeError, AttributeError) as e:
                # If http_client parameter not supported in this version
                if "http_client" in str(e) or "unexpected keyword" in str(e):
                    # Fallback: try without http_client
                    try:
                        self.client = openai.OpenAI(
                            base_url=self.base_url,
                            api_key=self.api_key or "ollama"
                        )
                    except TypeError as e2:
                        if "proxies" in str(e2):
                            # Last resort: try with just base_url
                            self.client = openai.OpenAI(base_url=self.base_url)
                        else:
                            raise e2
                elif "proxies" in str(e):
                    # If proxies error still occurs, try without http_client and api_key
                    self.client = openai.OpenAI(base_url=self.base_url)
                else:
                    raise
        except ImportError:
            print("openai or httpx not installed")
            self.client = None
        except Exception as e:
            error_msg = str(e)
            print(f"Failed to initialize Ollama embedding client: {error_msg}")
            # Try one more time with absolute minimal parameters
            if "proxies" in error_msg:
                try:
                    import openai
                    # Use inspect to only pass valid parameters
                    import inspect
                    sig = inspect.signature(openai.OpenAI.__init__)
                    params = {}
                    # Only add parameters that exist and are not proxies
                    for param_name, param in sig.parameters.items():
                        if param_name == 'base_url':
                            params['base_url'] = self.base_url
                        elif param_name == 'api_key' and (self.api_key or "ollama"):
                            params['api_key'] = self.api_key or "ollama"
                        # Skip proxies, http_client, and other optional params
                    self.client = openai.OpenAI(**params)
                    print("Successfully initialized with minimal parameters")
                except Exception as e2:
                    print(f"All initialization attempts failed. Last error: {e2}")
                    import traceback
                    traceback.print_exc()
                    self.client = None
            else:
                import traceback
                traceback.print_exc()
                self.client = None
    
    def _detect_dimension(self):
        """Detect actual embedding dimension by making a test call"""
        if not self.client:
            return
        try:
            # Make a minimal test call to detect dimension
            test_response = self.client.embeddings.create(
                model=self.model,
                input="test"
            )
            if test_response.data and test_response.data[0].embedding:
                self.dimension = len(test_response.data[0].embedding)
                print(f"Detected Ollama embedding dimension: {self.dimension}")
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
                if provider.client is not None:
                    return provider
                else:
                    print("Ollama embedding provider client not initialized")
            except Exception as e:
                print(f"Ollama embedding provider not available: {e}")
        
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




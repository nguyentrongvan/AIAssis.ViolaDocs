import os
from typing import List, Optional, Dict, Any
try:
    import httpx
except ImportError:
    httpx = None  # httpx not installed
from ...config import settings, get_ollama_base_url_from_db, get_ollama_embedding_model_from_db
from .qdrant_store import QdrantVectorStore


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
    
    async def generate_embedding_async(self, text: str) -> List[float]:
        """Generate embedding vector from text (async version)"""
        # Default implementation falls back to sync version
        return self.generate_embedding(text)
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        return [self.generate_embedding(text) for text in texts]
    
    async def generate_embeddings_batch_async(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts (async version)"""
        # Default implementation falls back to sync version
        return self.generate_embeddings_batch(texts)


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Ollama embedding provider using native API with async support"""
    
    # Class-level cache for async clients per base_url
    _async_clients: Dict[str, Any] = {}  # Use Any instead of httpx.AsyncClient to avoid type errors if httpx not installed
    
    def __init__(self, base_url: str, api_key: Optional[str] = None, model: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.model = model or settings.ollama_embedding_model  # Fallback to config if not provided
        self.http_client = None  # Keep sync client for backward compatibility
        self.dimension = 1536  # Default for nomic-text-embedding (actual dimension)
        self._init_client()
        # Try to detect actual dimension from model
        self._detect_dimension()
    
    def _init_client(self):
        """Initialize synchronous HTTP client for backward compatibility"""
        if httpx is None:
            print("httpx not installed")
            self.http_client = None
            return
        try:
            self.http_client = httpx.Client(
                timeout=60.0,
                base_url=self.base_url
            )
        except Exception as e:
            print(f"Failed to initialize Ollama embedding HTTP client: {e}")
            self.http_client = None
    
    async def _get_async_client(self) -> Optional[Any]:
        """Get or create async HTTP client with connection pooling"""
        if httpx is None:
            return None
        if self.base_url not in OllamaEmbeddingProvider._async_clients:
            try:
                OllamaEmbeddingProvider._async_clients[self.base_url] = httpx.AsyncClient(
                    timeout=30.0,  # Reduced timeout for faster responses
                    base_url=self.base_url,
                    limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
                    http2=True  # Enable HTTP/2 for better performance
                )
            except Exception as e:
                print(f"Failed to initialize Ollama embedding async HTTP client: {e}")
                return None
        return OllamaEmbeddingProvider._async_clients[self.base_url]
    
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
        """Generate embedding for text (synchronous, for backward compatibility)"""
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
    
    async def generate_embedding_async(self, text: str) -> List[float]:
        """Generate embedding for text (async version)"""
        # Load model and base_url from database settings
        try:
            db_base_url = await get_ollama_base_url_from_db()
            db_model = await get_ollama_embedding_model_from_db()
            
            # Update provider if model or base_url changed
            if db_model != self.model or db_base_url != self.base_url:
                self.model = db_model
                old_base_url = self.base_url
                self.base_url = db_base_url.rstrip('/')
                
                # Recreate async client if base_url changed
                if old_base_url != self.base_url:
                    # Close old client if exists
                    if old_base_url in OllamaEmbeddingProvider._async_clients:
                        try:
                            await OllamaEmbeddingProvider._async_clients[old_base_url].aclose()
                        except:
                            pass
                        del OllamaEmbeddingProvider._async_clients[old_base_url]
        except Exception as e:
            print(f"Warning: Failed to load embedding settings from DB, using current provider settings: {e}")
        
        async_client = await self._get_async_client()
        if not async_client:
            raise EmbeddingModelUnavailableError(
                f"Ollama embedding client not initialized. "
                f"Make sure Ollama is running at {self.base_url} and model '{self.model}' is available. "
                f"Run: ollama pull {self.model}"
            )
        
        # Check model availability (use sync check for now, can be optimized later)
        if not self.is_model_available():
            raise EmbeddingModelUnavailableError(
                f"Ollama embedding model '{self.model}' is not available. "
                f"Make sure Ollama is running and model is pulled: ollama pull {self.model}"
            )
        
        try:
            if not text or not text.strip():
                raise ValueError("Cannot generate embedding for empty text")
            
            # Call Ollama native API asynchronously
            response = await async_client.post(
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
    """
    Chroma vector store wrapper (local persistent or HTTP server)
    
    DEPRECATED: This class is kept temporarily for migration purposes only.
    Will be removed after migration from ChromaDB to Qdrant is complete.
    Use QdrantVectorStore instead.
    """
    
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
            
            # Detect Docker environment
            is_docker = os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER') == 'true'
            
            # Auto-detect ChromaDB server host if in Docker and not set
            server_host = self.server_host
            if not server_host and is_docker:
                server_host = "chroma"  # Docker service name
                print(f"WARNING: Detected Docker environment but CHROMA_SERVER_HOST not set. Auto-using '{server_host}'")
            
            # If server_host is provided, use HTTP client; otherwise use local persistent
            if server_host:
                scheme = "https" if self.server_ssl else "http"
                print(f"[ChromaVectorStore] Initializing HTTP client: {scheme}://{server_host}:{self.server_port}")
                self.client = chromadb.HttpClient(
                    host=server_host,
                    port=self.server_port,
                    ssl=self.server_ssl
                )
                print(f"[ChromaVectorStore] ✓ HTTP client connected to {scheme}://{server_host}:{self.server_port}")
            else:
                print(f"[ChromaVectorStore] Initializing persistent client at: {self.persist_dir}")
                os.makedirs(self.persist_dir, exist_ok=True)
                self.client = chromadb.PersistentClient(path=self.persist_dir)
                print(f"[ChromaVectorStore] ✓ Persistent client ready at {self.persist_dir}")
            
            # Check if collection exists and get its dimension
            print(f"[ChromaVectorStore] Checking collection: '{self.collection_name}'")
            try:
                existing_collection = self.client.get_collection(name=self.collection_name)
                existing_dim = existing_collection.metadata.get("dimension") if hasattr(existing_collection, 'metadata') else None
                
                # Get collection count and dimension from first embedding if possible
                collection_count = 0
                try:
                    collection_count = existing_collection.count()
                    print(f"[ChromaVectorStore] Collection exists with {collection_count} embeddings")
                except Exception as e:
                    print(f"[ChromaVectorStore] Warning: Could not get collection count: {e}")
                
                # Get dimension from first embedding if possible
                if collection_count > 0:
                    try:
                        sample = existing_collection.peek(limit=1)
                        if sample.get("embeddings") and len(sample["embeddings"]) > 0:
                            existing_dim = len(sample["embeddings"][0])
                            print(f"[ChromaVectorStore] Collection dimension: {existing_dim}")
                    except Exception as e:
                        print(f"[ChromaVectorStore] Warning: Could not get dimension from sample: {e}")
                
                # Use existing collection - don't delete even if empty
                # Empty collections are fine, they'll be populated when embeddings are added
                self.collection = existing_collection
                if existing_dim:
                    print(f"[ChromaVectorStore] ✓ Using existing collection (dimension: {existing_dim}, count: {collection_count})")
                else:
                    print(f"[ChromaVectorStore] ✓ Using existing collection (dimension unknown, count: {collection_count})")
            except Exception as e:
                # Collection doesn't exist, will create new one
                print(f"[ChromaVectorStore] Collection '{self.collection_name}' does not exist, will create new one: {e}")
                self.collection = None
            
            # Create or get collection
            if not self.collection:
                print(f"[ChromaVectorStore] Creating new collection: '{self.collection_name}'")
                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
                print(f"[ChromaVectorStore] ✓ Collection created/ready: '{self.collection_name}'")
            else:
                print(f"[ChromaVectorStore] ✓ Collection ready: '{self.collection_name}'")
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
            print("[ChromaVectorStore] ERROR: Collection is None, skipping upsert")
            return
        
        if not embeddings or len(embeddings) == 0:
            print("[ChromaVectorStore] ERROR: No embeddings provided, skipping upsert")
            return
        
        if not ids or len(ids) == 0:
            print("[ChromaVectorStore] ERROR: No IDs provided, skipping upsert")
            return
        
        try:
            embedding_dim = len(embeddings[0])
            
            # Get collection count before upsert
            collection_count_before = 0
            try:
                collection_count_before = self.collection.count()
            except Exception as e:
                print(f"[ChromaVectorStore] Warning: Could not get collection count before upsert: {e}")
            
            # Log before upsert
            metadata_sample = metadatas[0] if metadatas else {}
            print(f"[ChromaVectorStore] Upserting {len(ids)} embedding(s):")
            print(f"  - IDs: {ids[:3]}{'...' if len(ids) > 3 else ''}")
            print(f"  - Embedding dimension: {embedding_dim}")
            print(f"  - Metadata sample: doc_id={metadata_sample.get('doc_id')}, version_id={metadata_sample.get('version_id')}")
            print(f"  - Collection count before: {collection_count_before}")
            
            # Check dimension mismatch only if collection has data
            if collection_count_before > 0:
                try:
                    sample = self.collection.peek(limit=1)
                    if sample.get("embeddings") and len(sample["embeddings"]) > 0:
                        collection_dim = len(sample["embeddings"][0])
                        if embedding_dim != collection_dim:
                            print(f"[ChromaVectorStore] ERROR: Dimension mismatch: embedding={embedding_dim}, collection={collection_dim}")
                            print(f"[ChromaVectorStore] Deleting and recreating collection '{self.collection_name}' with dimension {embedding_dim}")
                            # Delete and recreate collection
                            self.client.delete_collection(name=self.collection_name)
                            self.collection = self.client.create_collection(
                                name=self.collection_name,
                                metadata={"hnsw:space": "cosine"}
                            )
                            print(f"[ChromaVectorStore] ✓ Collection recreated with dimension {embedding_dim}")
                            collection_count_before = 0  # Reset count after recreation
                except Exception as e:
                    print(f"[ChromaVectorStore] Warning: Error checking collection dimension: {e}, proceeding with upsert")
            
            # Perform upsert
            self.collection.upsert(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas
            )
            
            # Verify upsert success
            collection_count_after = 0
            try:
                collection_count_after = self.collection.count()
                print(f"[ChromaVectorStore] ✓ Upsert completed. Collection count after: {collection_count_after}")
                
                if collection_count_after <= collection_count_before:
                    print(f"[ChromaVectorStore] WARNING: Collection count did not increase! Before: {collection_count_before}, After: {collection_count_after}")
                else:
                    print(f"[ChromaVectorStore] ✓ Success: Collection count increased by {collection_count_after - collection_count_before}")
            except Exception as e:
                print(f"[ChromaVectorStore] Warning: Could not verify upsert success (count check failed): {e}")
        except Exception as e:
            error_msg = str(e)
            import traceback
            print(f"[ChromaVectorStore] ERROR: Upsert failed: {error_msg}")
            print(f"[ChromaVectorStore] Traceback:")
            traceback.print_exc()
            
            if "dimension" in error_msg.lower():
                # Dimension mismatch - try to fix by recreating collection
                print(f"[ChromaVectorStore] Dimension mismatch detected, attempting to recreate collection '{self.collection_name}'...")
                try:
                    self.client.delete_collection(name=self.collection_name)
                    if embeddings and len(embeddings) > 0:
                        embedding_dim = len(embeddings[0])
                        self.collection = self.client.create_collection(
                            name=self.collection_name,
                            metadata={"hnsw:space": "cosine"}
                        )
                        print(f"[ChromaVectorStore] Collection recreated with dimension {embedding_dim}, retrying upsert...")
                        # Retry upsert
                        self.collection.upsert(
                            ids=ids,
                            embeddings=embeddings,
                            metadatas=metadatas
                        )
                        print("[ChromaVectorStore] ✓ Upsert successful after collection recreation")
                except Exception as e2:
                    print(f"[ChromaVectorStore] ERROR: Failed to fix dimension mismatch: {e2}")
                    traceback.print_exc()
    
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
        store: Optional[QdrantVectorStore] = None
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
    
    def _get_default_store(self) -> Optional[QdrantVectorStore]:
        """Get default vector store (Qdrant)"""
        try:
            return QdrantVectorStore(
                host=getattr(settings, "qdrant_host", "localhost"),
                port=getattr(settings, "qdrant_port", 6333),
                grpc_port=getattr(settings, "qdrant_grpc_port", None),
                collection_name=getattr(settings, "qdrant_collection", "embeddings"),
                api_key=getattr(settings, "qdrant_api_key", None) or None,
            )
        except Exception as e:
            print(f"Qdrant store not available: {e}")
            import traceback
            traceback.print_exc()
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
            if self.store.client is not None:
                status["store"] = {
                    "type": "qdrant",
                    "collection": self.store.collection_name,
                    "host": self.store.host,
                    "port": self.store.port,
                    "grpc_port": self.store.grpc_port,
                    "web_ui": f"http://{self.store.host}:6333/dashboard" if self.store.host else None
                }
            else:
                status["errors"].append("Qdrant vector store not initialized")
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
    
    async def generate_embedding_async(self, text: str) -> List[float]:
        """Generate embedding for text (async version)"""
        if not self.embedder:
            raise EmbeddingModelUnavailableError(
                "Embedding provider not configured. Please configure Ollama."
            )
        if hasattr(self.embedder, 'generate_embedding_async'):
            return await self.embedder.generate_embedding_async(text)
        else:
            return self.embedder.generate_embedding(text)
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        if not self.embedder:
            raise EmbeddingModelUnavailableError(
                "Embedding provider not configured. Please configure Ollama."
            )
        return self.embedder.generate_embeddings_batch(texts)
    
    async def generate_embeddings_batch_async(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts (async version)"""
        if not self.embedder:
            raise EmbeddingModelUnavailableError(
                "Embedding provider not configured. Please configure Ollama."
            )
        if hasattr(self.embedder, 'generate_embeddings_batch_async'):
            return await self.embedder.generate_embeddings_batch_async(texts)
        else:
            return self.embedder.generate_embeddings_batch(texts)
    
    def upsert_embeddings(self, ids: List[str], embeddings: List[List[float]], metadatas: List[Dict[str, Any]]):
        """Upsert embeddings into vector store"""
        if not self.store:
            print("[EmbeddingService] ERROR: Vector store not configured; skipping upsert")
            return
        
        if not self.store.client:
            print("[EmbeddingService] ERROR: Vector store client is None; skipping upsert")
            return
        
        print(f"[EmbeddingService] Calling store.upsert() with {len(ids)} embedding(s)")
        try:
            self.store.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas)
            print(f"[EmbeddingService] ✓ store.upsert() completed successfully")
        except Exception as e:
            print(f"[EmbeddingService] ERROR: store.upsert() failed: {e}")
            import traceback
            traceback.print_exc()
            raise  # Re-raise to ensure error is not silently ignored
    
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




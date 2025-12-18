import os
import json
from typing import List, Optional, Dict, Any
from ...config import settings

# #region agent log
DEBUG_LOG_PATH = r"d:\TrongVan\VanDMS\AIAssis.ViolaDocs\.cursor\debug.log"
def _debug_log(location: str, message: str, data: dict, hypothesis_id: str = None):
    try:
        import time
        log_entry = {
            "sessionId": "qdrant-debug",
            "runId": "run1",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000)
        }
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except:
        pass
# #endregion


class QdrantVectorStore:
    """Qdrant vector store wrapper"""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        grpc_port: Optional[int] = None,
        collection_name: str = "embeddings",
        api_key: Optional[str] = None
    ):
        self.host = host
        self.port = port
        self.grpc_port = grpc_port
        self.collection_name = collection_name
        self.api_key = api_key
        self.client = None
        self.collection = None
        self._init_store()
    
    def _init_store(self):
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams
            
            # Detect Docker environment
            is_docker = os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER') == 'true'
            
            # Auto-detect Qdrant host if in Docker and not set
            host = self.host
            if host == "localhost" and is_docker:
                host = "qdrant"  # Docker service name
                print(f"[QdrantVectorStore] Detected Docker environment, using Qdrant service: '{host}'")
            
            # Initialize Qdrant client
            # Prefer gRPC for better performance if grpc_port is provided
            if self.grpc_port:
                print(f"[QdrantVectorStore] Initializing Qdrant client: gRPC at {host}:{self.grpc_port}")
                self.client = QdrantClient(
                    host=host,
                    grpc_port=self.grpc_port,
                    api_key=self.api_key,
                    prefer_grpc=True
                )
                print(f"[QdrantVectorStore] ✓ gRPC client connected to {host}:{self.grpc_port}")
            else:
                print(f"[QdrantVectorStore] Initializing Qdrant client: HTTP at {host}:{self.port}")
                self.client = QdrantClient(
                    url=f"http://{host}:{self.port}" if not host.startswith("http") else f"{host}:{self.port}",
                    api_key=self.api_key
                )
                print(f"[QdrantVectorStore] ✓ HTTP client connected to {host}:{self.port}")
            
            # Check if collection exists
            print(f"[QdrantVectorStore] Checking collection: '{self.collection_name}'")
            try:
                collection_info = self.client.get_collection(self.collection_name)
                collection_count = collection_info.points_count
                vector_size = collection_info.config.params.vectors.size
                print(f"[QdrantVectorStore] Collection exists with {collection_count} points, vector size: {vector_size}")
                self.collection = self.collection_name
            except Exception as e:
                error_msg = str(e)
                error_type = type(e).__name__
                # #region agent log
                _debug_log("qdrant_store.py:88", "Exception when getting collection", {
                    "error_type": error_type,
                    "error_msg": error_msg[:200]
                }, "A")
                # #endregion
                
                # Check if it's a validation error (collection exists but config has issues)
                # vs collection doesn't exist error
                is_validation_error = (
                    "validation error" in error_msg.lower() or 
                    "pydantic" in error_msg.lower() or
                    error_type == "ValidationError"
                )
                
                if is_validation_error:
                    # Collection exists but has config validation issue - check by listing collections
                    # Suppress error message - this is expected and handled gracefully
                    print(f"[QdrantVectorStore] Collection config has validation issue (using workaround)")
                    # #region agent log
                    _debug_log("qdrant_store.py:102", "Validation error detected, checking collections list", {
                        "error_type": error_type,
                        "error_msg": error_msg[:200]
                    }, "A")
                    # #endregion
                    try:
                        collections = self.client.get_collections().collections
                        collection_exists = any(col.name == self.collection_name for col in collections)
                        if collection_exists:
                            print(f"[QdrantVectorStore] ✓ Collection '{self.collection_name}' exists (using workaround)")
                            self.collection = self.collection_name
                        else:
                            print(f"[QdrantVectorStore] Collection '{self.collection_name}' does not exist, will create new one")
                            self.collection = None
                    except Exception as e2:
                        print(f"[QdrantVectorStore] Error checking collections list: {e2}")
                        self.collection = None
                else:
                    # Collection doesn't exist, will create new one
                    print(f"[QdrantVectorStore] Collection '{self.collection_name}' does not exist, will create new one: {e}")
                    self.collection = None
            
            # Create collection if it doesn't exist
            if not self.collection:
                print(f"[QdrantVectorStore] Creating new collection: '{self.collection_name}'")
                # We'll create it on first upsert with proper vector size
                # For now, just mark that we need to create it
                self.collection = self.collection_name
                print(f"[QdrantVectorStore] ✓ Collection will be created on first upsert")
            else:
                print(f"[QdrantVectorStore] ✓ Collection ready: '{self.collection_name}'")
        except ImportError:
            print("[QdrantVectorStore] ERROR: qdrant-client not installed. Install with: pip install qdrant-client")
            self.client = None
            self.collection = None
        except Exception as e:
            print(f"[QdrantVectorStore] ERROR: Failed to init Qdrant store: {e}")
            import traceback
            traceback.print_exc()
            self.client = None
            self.collection = None
    
    def upsert(self, ids: List[str], embeddings: List[List[float]], metadatas: List[Dict[str, Any]]):
        if not self.client:
            print("[QdrantVectorStore] ERROR: Client is None, skipping upsert")
            return
        
        if not embeddings or len(embeddings) == 0:
            print("[QdrantVectorStore] ERROR: No embeddings provided, skipping upsert")
            return
        
        if not ids or len(ids) == 0:
            print("[QdrantVectorStore] ERROR: No IDs provided, skipping upsert")
            return
        
        try:
            from qdrant_client.models import PointStruct, Distance, VectorParams
            from qdrant_client.http import models
            
            embedding_dim = len(embeddings[0])
            
            # Get collection count before upsert
            collection_count_before = 0
            try:
                collection_info = self.client.get_collection(self.collection_name)
                collection_count_before = collection_info.points_count
            except Exception as e:
                # Collection doesn't exist yet
                print(f"[QdrantVectorStore] Collection doesn't exist yet, will create: {e}")
            
            # Log before upsert
            metadata_sample = metadatas[0] if metadatas else {}
            print(f"[QdrantVectorStore] Upserting {len(ids)} point(s):")
            print(f"  - IDs: {ids[:3]}{'...' if len(ids) > 3 else ''}")
            print(f"  - Embedding dimension: {embedding_dim}")
            print(f"  - Payload sample: doc_id={metadata_sample.get('doc_id')}, version_id={metadata_sample.get('version_id')}")
            print(f"  - Collection count before: {collection_count_before}")
            
            # Create collection if it doesn't exist
            try:
                collection_info = self.client.get_collection(self.collection_name)
                existing_dim = collection_info.config.params.vectors.size
                if existing_dim != embedding_dim:
                    print(f"[QdrantVectorStore] ERROR: Dimension mismatch: embedding={embedding_dim}, collection={existing_dim}")
                    print(f"[QdrantVectorStore] Deleting and recreating collection '{self.collection_name}' with dimension {embedding_dim}")
                    self.client.delete_collection(self.collection_name)
                    self._create_collection(embedding_dim)
                    collection_count_before = 0
            except Exception as e:
                # Collection doesn't exist, create it
                print(f"[QdrantVectorStore] Creating collection '{self.collection_name}' with dimension {embedding_dim}")
                self._create_collection(embedding_dim)
            
            # Prepare points for upsert
            points = []
            for idx, (point_id, embedding, metadata) in enumerate(zip(ids, embeddings, metadatas)):
                # Convert point_id to int if it's numeric string, otherwise use as string
                try:
                    # Try to use numeric ID if possible (Qdrant prefers int IDs)
                    if point_id.startswith("embed-"):
                        # Extract numeric part from "embed-123"
                        numeric_id = int(point_id.split("-")[-1])
                    else:
                        numeric_id = int(point_id)
                    point_id_typed = numeric_id
                except (ValueError, IndexError):
                    # Use string ID if not numeric
                    point_id_typed = point_id
                
                points.append(
                    PointStruct(
                        id=point_id_typed,
                        vector=embedding,
                        payload=metadata
                    )
                )
            
            # Perform upsert
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            # Verify upsert success
            collection_count_after = 0
            try:
                collection_info = self.client.get_collection(self.collection_name)
                collection_count_after = collection_info.points_count
                print(f"[QdrantVectorStore] ✓ Upsert completed. Collection count after: {collection_count_after}")
                
                if collection_count_after <= collection_count_before:
                    print(f"[QdrantVectorStore] WARNING: Collection count did not increase! Before: {collection_count_before}, After: {collection_count_after}")
                else:
                    print(f"[QdrantVectorStore] ✓ Success: Collection count increased by {collection_count_after - collection_count_before}")
            except Exception as e:
                print(f"[QdrantVectorStore] Warning: Could not verify upsert success (count check failed): {e}")
        except Exception as e:
            error_msg = str(e)
            import traceback
            print(f"[QdrantVectorStore] ERROR: Upsert failed: {error_msg}")
            print(f"[QdrantVectorStore] Traceback:")
            traceback.print_exc()
    
    def _create_collection(self, vector_size: int):
        """Create Qdrant collection with specified vector size"""
        from qdrant_client.models import Distance, VectorParams
        
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE
            )
        )
        print(f"[QdrantVectorStore] ✓ Collection '{self.collection_name}' created with vector size {vector_size}")
    
    def query(self, query_embeddings: List[List[float]], where: Optional[Dict[str, Any]], top_k: int):
        """Query Qdrant collection"""
        if not self.client:
            return {"ids": [], "distances": [], "metadatas": []}
        
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny
            
            # Convert where filter to Qdrant Filter format
            qdrant_filter = None
            if where:
                filter_conditions = []
                for key, value in where.items():
                    if isinstance(value, list):
                        # Handle $in operator
                        filter_conditions.append(
                            FieldCondition(
                                key=key,
                                match=MatchAny(any=value)
                            )
                        )
                    else:
                        filter_conditions.append(
                            FieldCondition(
                                key=key,
                                match=MatchValue(value=value)
                            )
                        )
                
                if filter_conditions:
                    qdrant_filter = Filter(must=filter_conditions)
            
            # Query Qdrant
            query_vector = query_embeddings[0]  # Qdrant query takes single vector
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=qdrant_filter,
                limit=top_k,
                with_payload=True
            )
            
            # Transform results to match ChromaDB format
            # Qdrant returns scores (higher is better, 1.0 = identical for cosine)
            # ChromaDB returns distances (lower is better, 0.0 = identical for cosine)
            # Convert: distance = 1 - score
            ids = []
            distances = []
            metadatas = []
            
            for result in search_results:
                ids.append(str(result.id))
                # Convert Qdrant score to ChromaDB distance format
                # Qdrant score: 1.0 = identical, 0.0 = orthogonal
                # ChromaDB distance: 0.0 = identical, 1.0 = orthogonal
                distance = 1.0 - result.score if result.score is not None else 1.0
                distances.append(distance)  # Append single distance value, not list
                metadatas.append(result.payload if result.payload else {})
            
            return {
                "ids": [ids],  # ChromaDB format: list of lists
                "distances": [distances],  # distances is already a list of numbers
                "metadatas": [metadatas]
            }
        except Exception as e:
            print(f"[QdrantVectorStore] ERROR: Query failed: {e}")
            import traceback
            traceback.print_exc()
            return {"ids": [], "distances": [], "metadatas": []}
    
    def count(self):
        """Get collection point count"""
        if not self.client:
            return 0
        try:
            collection_info = self.client.get_collection(self.collection_name)
            return collection_info.points_count
        except Exception as e:
            error_msg = str(e)
            # Handle validation error (collection exists but config has issues)
            if "validation error" in error_msg.lower() or "pydantic" in error_msg.lower():
                # #region agent log
                _debug_log("qdrant_store.py:306", "Validation error detected, attempting HTTP API bypass", {
                    "error_msg": error_msg[:200],
                    "collection_name": self.collection_name
                }, "A")
                # #endregion
                
                # Try to get count using raw HTTP request (bypasses pydantic validation)
                try:
                    # #region agent log
                    _debug_log("qdrant_store.py:312", "Attempting raw HTTP request", {
                        "has_http": hasattr(self.client, 'http'),
                        "has_collections_api": hasattr(self.client, 'http') and hasattr(self.client.http, 'collections_api') if hasattr(self.client, 'http') else False
                    }, "B")
                    # #endregion
                    
                    # Get base URL from client
                    base_url = None
                    if hasattr(self.client, 'http') and hasattr(self.client.http, 'base_url'):
                        base_url = str(self.client.http.base_url).rstrip('/')
                        # #region agent log
                        _debug_log("qdrant_store.py:320", "Got base_url from client.http", {"base_url": base_url}, "B")
                        # #endregion
                    elif hasattr(self.client, '_client') and hasattr(self.client._client, 'base_url'):
                        base_url = str(self.client._client.base_url).rstrip('/')
                        # #region agent log
                        _debug_log("qdrant_store.py:323", "Got base_url from client._client", {"base_url": base_url}, "B")
                        # #endregion
                    else:
                        # Construct from host/port
                        scheme = "http"
                        host = self.host if self.host != "localhost" else "localhost"
                        base_url = f"{scheme}://{host}:{self.port}"
                        # #region agent log
                        _debug_log("qdrant_store.py:330", "Constructed base_url from host/port", {"base_url": base_url, "host": host, "port": self.port}, "B")
                        # #endregion
                    
                    # Make raw HTTP request using urllib to bypass pydantic
                    import urllib.request
                    import urllib.error
                    url = f"{base_url}/collections/{self.collection_name}"
                    # #region agent log
                    _debug_log("qdrant_store.py:337", "Making raw HTTP GET request", {"url": url}, "C")
                    # #endregion
                    
                    req = urllib.request.Request(url)
                    req.add_header('Content-Type', 'application/json')
                    with urllib.request.urlopen(req, timeout=5) as response:
                        raw_json = response.read().decode('utf-8')
                        # #region agent log
                        _debug_log("qdrant_store.py:343", "Got raw HTTP response", {
                            "status": response.status,
                            "json_length": len(raw_json),
                            "json_preview": raw_json[:500] if len(raw_json) > 500 else raw_json
                        }, "C")
                        # #endregion
                        
                        data = json.loads(raw_json)
                        # #region agent log
                        _debug_log("qdrant_store.py:349", "Parsed JSON response", {
                            "has_result": "result" in data,
                            "result_keys": list(data.get("result", {}).keys())[:10] if isinstance(data.get("result"), dict) else None
                        }, "C")
                        # #endregion
                        
                        if "result" in data and isinstance(data["result"], dict):
                            if "points_count" in data["result"]:
                                count = data["result"]["points_count"]
                                # #region agent log
                                _debug_log("qdrant_store.py:356", "Successfully extracted points_count", {"count": count}, "C")
                                # #endregion
                                print(f"[QdrantVectorStore] Got collection count via raw HTTP API: {count}")
                                return count
                except Exception as e2:
                    # #region agent log
                    _debug_log("qdrant_store.py:361", "Raw HTTP request failed", {
                        "error_type": type(e2).__name__,
                        "error_msg": str(e2)[:200]
                    }, "C")
                    # #endregion
                    # Don't print full error, just a brief warning
                    print(f"[QdrantVectorStore] Warning: Could not get count via raw HTTP API, will use scroll method")
                
                # Fallback: try scroll method (slower but works)
                try:
                    print(f"[QdrantVectorStore] Using scroll method to estimate count")
                    # Just check if collection has any points
                    scroll_result, _ = self.client.scroll(
                        collection_name=self.collection_name,
                        limit=1,
                        with_payload=False,
                        with_vectors=False
                    )
                    if scroll_result:
                        # Collection has points, but we can't get exact count easily
                        # Return a non-zero value to indicate collection has data
                        # For exact count, would need to scroll all (expensive)
                        print(f"[QdrantVectorStore] Collection has points but exact count unavailable due to config issue")
                        return -1  # Special value indicating "has data but count unknown"
                    else:
                        return 0
                except Exception as e3:
                    print(f"[QdrantVectorStore] Warning: Could not check collection via scroll: {e3}")
                    return 0
            else:
                print(f"[QdrantVectorStore] Warning: Could not get collection count: {e}")
                return 0
    
    def get(self, where: Optional[Dict[str, Any]] = None, limit: Optional[int] = None):
        """Get all points from collection (for migration)"""
        if not self.client:
            return {"ids": [], "vectors": [], "payloads": []}
        
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue, ScrollRequest
            
            # Convert where filter to Qdrant Filter format
            qdrant_filter = None
            if where:
                filter_conditions = []
                for key, value in where.items():
                    if isinstance(value, list):
                        from qdrant_client.models import MatchAny
                        filter_conditions.append(
                            FieldCondition(
                                key=key,
                                match=MatchAny(any=value)
                            )
                        )
                    else:
                        filter_conditions.append(
                            FieldCondition(
                                key=key,
                                match=MatchValue(value=value)
                            )
                        )
                
                if filter_conditions:
                    qdrant_filter = Filter(must=filter_conditions)
            
            # Scroll through all points
            scroll_limit = limit or 10000  # Default limit
            result, _ = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=qdrant_filter,
                limit=scroll_limit,
                with_payload=True,
                with_vectors=True
            )
            
            # Transform to ChromaDB-like format
            ids = []
            vectors = []
            payloads = []
            
            for point in result:
                ids.append(str(point.id))
                vectors.append(point.vector if point.vector else [])
                payloads.append(point.payload if point.payload else {})
            
            return {
                "ids": ids,
                "embeddings": vectors,
                "metadatas": payloads
            }
        except Exception as e:
            print(f"[QdrantVectorStore] ERROR: Get failed: {e}")
            import traceback
            traceback.print_exc()
            return {"ids": [], "embeddings": [], "metadatas": []}


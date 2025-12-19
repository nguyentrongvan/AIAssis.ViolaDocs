# Vector Database Architecture

## Overview

ViolaDocs uses **Qdrant** as the vector database for storing and querying document embeddings. Qdrant provides high-performance vector search with web UI for management and debugging.

## Qdrant Setup

### Docker Configuration

Qdrant runs as a Docker container with:
- **HTTP API**: Port 6333 (exposed as 6333:6333)
- **gRPC API**: Port 6334 (exposed as 6334:6334)
- **Web UI**: Available at http://localhost:6333/dashboard
- **Storage**: Persistent volume `qdrant_data`

### Configuration

Environment variables for Qdrant:
- `QDRANT_HOST`: Qdrant server host (default: "localhost", use "qdrant" in Docker)
- `QDRANT_PORT`: HTTP API port (default: 6333)
- `QDRANT_GRPC_PORT`: gRPC API port (default: 6334, optional)
- `QDRANT_COLLECTION`: Collection name (default: "embeddings")
- `QDRANT_API_KEY`: Optional API key for Qdrant Cloud

### Collection Structure

- **Collection Name**: `embeddings`
- **Vector Size**: 768 (nomic-embed-text model)
- **Distance Metric**: Cosine similarity
- **Payload Fields**:
  - `doc_id`: Document ID (integer)
  - `version_id`: Document version ID (integer)
  - `owner_id`: Document owner ID (integer)
  - `provider`: Embedding provider (string, e.g., "ollama")
  - `text_length`: Length of text used for embedding (integer)

## Features Used

### 1. Vector Search
- Cosine similarity search
- Top-K retrieval
- Filtering by metadata (doc_id, owner_id, group_id, etc.)

### 2. Filtering
Qdrant supports powerful filtering:
- **Field conditions**: Filter by exact match (`doc_id = 42`)
- **List matching**: Filter by list of values (`doc_id in [1, 2, 3]`)
- **Complex filters**: Combine multiple conditions with `must`, `should`, `must_not`

### 3. Web UI
- Access at http://localhost:6333/dashboard
- View collections and points
- Query and filter data
- Monitor collection statistics

## Integration

### Embedding Flow

1. **OCR/Text Extraction** → Extracts text from document
2. **Embedding Generation** → Ollama generates embedding vector (768 dimensions)
3. **Qdrant Upsert** → Stores embedding with metadata payload
4. **Collection Update** → Point count increases

### Query Flow

1. **User Query** → User asks question in chat
2. **Query Embedding** → Generate embedding for user query
3. **Vector Search** → Qdrant searches for similar vectors
4. **Filtering** → Apply ACL filters (doc_id, owner_id, group_id)
5. **Results** → Return top-K documents with scores

## Migration from ChromaDB

If migrating from ChromaDB, use the migration script:

```bash
cd src/backend
python migrate_chroma_to_qdrant.py
```

For dry-run:
```bash
python migrate_chroma_to_qdrant.py --dry-run
```

## Troubleshooting

### Check Qdrant Status

```bash
cd src/backend
python check_qdrant.py
```

Check specific document:
```bash
python check_qdrant.py 42
```

### Test Upsert

```bash
cd src/backend
python test_qdrant_upsert.py
```

### Web UI Access

Open browser to: http://localhost:6333/dashboard

## Performance Considerations

- **gRPC**: Use gRPC port (6334) for better performance in production
- **Batch Upsert**: Embeddings are upserted in batches for efficiency
- **Indexing**: Qdrant uses HNSW algorithm for fast approximate nearest neighbor search
- **Filtering**: Metadata filtering happens before vector search for better performance



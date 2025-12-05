# Extensibility: OCR/AI & Search

## Principles
- Provider interfaces with concrete adapters; no provider-specific code in business logic.
- Config-driven provider selection per task (ocr/embed/llm/classify).
- Health checks and graceful degradation (fallback provider).
- Idempotent jobs; retries with backoff; store inputs/outputs for auditability.

## Interfaces (sketch, Python)
- `class OcrProvider: def recognize(self, blob_uri, mime, options) -> OcrResult`
- `class EmbedProvider: def embed(self, texts|files, model) -> List[Vector]]`
- `class ClassifyProvider: def classify(self, text, schema) -> Labels`
- `class LlmProvider: def chat(self, messages, tools=None) -> Response`
- `class SearchAdapter: def keyword(self, query, filters); def vector(self, vector, k, filters)`
- Providers registered in a registry with name, type, priority, limits; selected at runtime via config or request hint.
- LLM registry supports multiple engines (e.g., Gemini, OpenAI, Azure OpenAI, local); selection by policy (default, per-tenant, per-task).
- Default OCR adapter: PaddleOCR with language packs for English and Vietnamese; options include `lang=["en","vi"]` and page-level configs. Additional OCR providers can be added via the same interface.

## Job Orchestration
- AI jobs represented by `AIJob` entries with status (queued/running/succeeded/failed), provider, payload refs.
- Workers pull jobs from queue; resolve provider; execute; store output refs (OCR text URI, embeddings ids).
- Emit events for progress; cap runtime/size; sanitize prompt/output.

## Adding a New Provider
1) Implement interface; map provider config (API key, endpoint, model).
2) Add health check method; register in provider registry.
3) Update settings to allow selection per task type (default + overrides).
4) No changes required in ingestion/search/business logic.

## Vector/Search Adapter
- Start with PostgreSQL + pgvector adapter; support HNSW index.
- Provide alternate adapter (Qdrant/Weaviate/OpenSearch k-NN) implementing same interface.
- Hybrid search: merge keyword + vector results; consistent scoring contract.

## OCR Pipelines
- Preprocessing hooks per source (scan: deskew/denoise; web upload: page split).
- Store OCR text and PDF rendition as separate objects; link by version.
- Multilingual support; configurable language packs; fall back to default.

## Governance & Audit
- Log provider, model, version, input refs, output refs, latency, cost (if external API).
- Allow provider-level quotas and disable/maintenance flags.


# Data Model & Storage

## Storage Mapping
- **Object Store (MinIO/S3)**: original files, thumbnails, OCR PDFs, extracted text, previews.
- **Relational DB (PostgreSQL)**: users, roles/permissions, devices, documents, versions, metadata, tags, folders, workflows, tasks, shares, audit refs, retention rules.
- **Vector Store**: embeddings per document/version/chunk; start with pgvector in PostgreSQL; scale to Qdrant/Weaviate for higher QPS/latency or multi-tenant isolation.
- **Search Index (optional)**: Postgres FTS or OpenSearch for keyword/facet search.

## Core Entities (simplified)
- **User**: id, name, email, status (active/inactive), locale, time zone, expires_at (short-term accounts), created_by.
- **Role**: id, name, permissions[]; mapping user_role.
- **Device**: id, name, location, capabilities, status, last_seen, allowed_users/groups, public_key/secret_ref.
- **Document**: id, title, source (web/scan/api), device_id, owner_id, folder_id, mime, size, checksum, status (processing/ready/failed), retention_policy_id, sensitivity, created_at, deleted_at, deleted_by, purge_at.
- **DocumentVersion**: id, document_id, version_no, blob_uri, ocr_uri, text_uri, thumbnail_uri, created_by, created_at, checksum, size, lineage (device_id, job_id), provider_info (ocr/embedding), metadata_snapshot (title, tags, folder, retention/sensitivity/custom fields).
- **Tag**: id, name; document_tag mapping.
- **Share**: id, document_id, target (user/role/link), expires_at, permissions scope.
- **DocumentGroup**: id, name, description, owners, allowed_roles/users; collection of documents/folders/tags used for scoped chatbot/search; `chatbot_policy` (allowed_sources: docs/reports/metrics, allow_previews, redaction rules, max_context_tokens).
- **Workflow**: id, document_id, template, state, assignees, due_at.
- **Task**: id, workflow_id, assignee, state, action, comment, timestamps.
- **AuditEvent**: id, actor, subject (doc/version/user/device), action, timestamp, metadata, ip/user_agent.
- **RetentionPolicy**: id, name, duration, disposition (delete/archive), legal_hold flag.
- **AIJob**: id, type (ocr/embed/classify/qa), target (doc/version/chunk), provider, status, input_ref, output_ref, error.
- **Embedding**: id, doc_id, version_id, chunk_id, vector, chunk_ref, provider, created_at. Stored in vector DB (or pgvector).

## Table/Storage Notes
- Keep blobs out of PostgreSQL; store URIs to MinIO objects with bucket/key/version.
- Use JSONB columns for flexible metadata (custom fields) with GIN indexes where needed.
- For embeddings in PostgreSQL: table with `vector` type + HNSW/IVFFlat index; size caution → migrate to dedicated vector DB when > few million vectors or low-latency needs.
- Partition large tables (audit events, embeddings) by time or tenant.
- Enable row-level security for multi-tenant or strict ACL enforcement.
- Maintain search index triggers or async jobs to update FTS/OpenSearch on metadata changes.

## Versioning & Retention
- New upload creates `DocumentVersion`; status transitions: uploading → processing → ready/failed.
- Keep lineage of source: web vs printer (device_id, job_id).
- Maintain per-version metadata snapshot (title/tags/folder/retention/custom fields) to support historical view and diff.
- ACL changes recorded in audit but referenced in version timeline for compare.
- Retention rules apply per document; prevent delete when legal hold active.
- Lifecycle rules in MinIO to tier old versions to cheaper storage; optional warm/cold buckets.
- On new version commit: re-run embeddings and search index updates for that version; mark previous version stable; ensure vector/index consistency via queued, idempotent jobs.

## Version Diff & History
- Store extracted text per version (`text_uri`) to enable text diff even for binary formats.
- Diff dimensions: content (text diff, image side-by-side), metadata (title/tags/retention/custom fields), ACL changes (from audit events).
- Checksums detect identical uploads; version timeline includes actor, timestamp, source, device/job, workflow state.

## Chatbot / RAG Scoping
- DocumentGroup defines the allowed corpus; a user must have access to both the group and underlying documents.
- Embedding index stores group_id/acl fields to filter at query time; vector search adapter applies ACL + group constraints before returning hits.
- Audit chatbot queries: who asked, group scope, docs/chunks returned, provider/model used.

## Indexing Strategy
- Metadata filters: BTREE/GIST on tags, owner, device_id, status, created_at.
- Text search: Postgres tsvector or external search.
- Vector search: HNSW/IVFFlat with approximate nearest neighbor; store chunk pointers.

## Backups/DR (data perspective)
- PostgreSQL: PITR with WAL archiving; replicas.
- MinIO: versioning enabled, cross-site replication optional, periodic object integrity checks.
- Vector DB: snapshot/backup schedule; reconstructable from embeddings jobs if needed.
- Soft delete policy: `deleted_at/purge_at`; purge job removes DB rows and MinIO objects after grace period (e.g., 30 days, configurable).


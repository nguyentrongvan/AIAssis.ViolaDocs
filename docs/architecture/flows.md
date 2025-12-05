# Architecture Flows

## Ingest via Web Upload
1) User selects file (pdf/docx/xlsx/img); client computes checksum, gets upload URL (pre-signed) + upload id.
2) Client uploads to MinIO (direct or via API passthrough), sends finalize call with metadata (title, tags, ACL scope, folder, retention, workflow).
3) Backend stores metadata row, version record, and enqueues jobs: virus scan, MIME/format sniff, thumbnail, OCR (if image/pdf), text extraction, embedding.
4) OCR/AI worker pulls job, runs provider (default PaddleOCR with en/vi language packs), stores extracted text as rendition, updates DB, pushes embeddings to vector store, updates search index.
5) Document service marks ingest complete and emits audit events; notifications for watchers/workflow assignees.

## Ingest via Printer/Scanner Connector
1) Device registered with key + allowed users/mailboxes; connector polls or pushes scan job with metadata (user, device id, job id, filename, duplex/color).
2) API validates device, issues upload URL or receives multipart stream; stores blob to MinIO with device/job tags.
3) Document service creates document entry (source=scan, device id) and enqueues OCR/AI jobs with scan-specific preprocessing (deskew/denoise).
4) OCR/AI workers process, store OCR PDF/text, embeddings, index.
5) Completion/audit events; optional routing to mailbox or workflow (e.g., AP invoices approval).

## Search (Keyword + Vector Hybrid)
1) User submits query + filters; frontend calls search service.
2) Search service runs keyword search (DB/index) and vector search (vector store); merges/reranks; applies ACL filters.
3) Returns hits with highlights, snippet, version, score, and signed URLs for previews.

## Document View & Actions
1) User opens document detail; backend authorizes; returns metadata, versions, renditions, activity.
2) User annotates/comments; actions stored in DB and audit log.
3) Sharing: create share link (time-bound, scope) or add collaborators; ACL enforced on subsequent requests.
4) Version history: list versions with lineage (source/device/job), actor, time, checksum; request diff between two versions (content via OCR/extracted text, metadata snapshot, ACL delta) and render side-by-side.
5) On new version: enqueue reindex/embedding jobs; ensure search/vector consistency before marking ready; stale reads mitigated via versioned signed URLs and status flags.

## Workflow (Review/Approve)
1) Document enters workflow (manual or auto-rule); tasks created for assignees.
2) Assignee acts (approve/reject/request changes); state transitions stored; notifications emitted.
3) Completion triggers retention policy or next process step.

## AI Assist (Summarize / Q&A / Classification)
1) User requests AI action; backend fetches text/embeddings.
2) For Q&A, RAG pipeline retrieves top-k chunks from vector store filtered by ACL and selected document groups; sends prompt to LLM provider.
3) Response stored as note/rendition; audit logged with prompt/output refs, group scope, and citations; provider abstracted via interface.
4) Chat session context cached (e.g., Redis) to maintain conversation state and short-term memory; history persisted for audit/forensics.
5) Agent can route to data sources: vector store (docs), reports/metrics (if authorized), and direct document retrieval (signed URLs) for preview.


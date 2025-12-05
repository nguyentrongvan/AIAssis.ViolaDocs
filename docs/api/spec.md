# API Spec (Draft)

- Style: REST/JSON, OAuth2/OIDC or username/password → JWT access/refresh. Device keys for printer/scanner.
- Versioning: `/api/v1`.
- Response envelope (all endpoints):
  - `is_success: bool`
  - `message: string` (human-friendly)
  - `status_code: int`
  - `data: object|null` (payload)
- Errors use same envelope with `is_success=false` and `data` containing `error:{code,message,details}` as needed.
- Pagination: `page/size` or `cursor/limit`; sorting; filtering via query params.

## Auth & Identity
- `POST /auth/login` – user login; returns tokens (no self-signup).
- `POST /auth/refresh` – refresh JWT.
- `POST /auth/device/login` – device key exchange; returns device token.
- `GET /me` – profile, roles, permissions, status.

## Users/Roles
- `GET/POST /users`, `PATCH /users/{id}`, `DELETE /users/{id}` (admin/staff only; no public registration).
- `GET/POST /roles`, `PATCH /roles/{id}`, `DELETE /roles/{id}`.
- `POST /roles/{id}/permissions` – set permissions.
- `POST /users/{id}/activate` / `POST /users/{id}/deactivate`.
- `PATCH /users/{id}/expiry` – set expires_at for short-term accounts.

## Devices (Printers/Scanners)
- `GET/POST /devices` – register device (name, location, allowed users/groups, capabilities).
- `PATCH /devices/{id}`, `DELETE /devices/{id}`.
- `POST /devices/{id}/issue-key` – create/revoke device key.
- `POST /devices/{id}/ping` – heartbeat.

## Upload (Web)
- `POST /uploads/init` – request upload id + pre-signed URLs (or direct upload endpoint). Payload: filename, size, checksum, mime.
- `PUT /uploads/{id}/chunk` – optional chunked upload passthrough.
- `POST /uploads/{id}/finalize` – metadata (title, tags, folder, retention, ACL, workflow), completes ingest and enqueues OCR/AI.

## Upload (Printer/Scanner)
- `POST /scan-jobs` – device uploads scan (multipart) or requests pre-signed URL; includes device token, user/mailbox, job metadata.
- `POST /scan-jobs/{jobId}/finalize` – confirm upload; metadata overrides; enqueue OCR/AI.
- `GET /scan-jobs/pending` – optional pull model for devices.

## Documents
- `GET /documents` – list with filters (type, tag, device, owner, status, retention).
- `POST /documents` – create (metadata-only, link to existing blob if needed).
- `GET /documents/{id}` – detail (metadata, ACL, versions, renditions).
- `PATCH /documents/{id}` – update metadata/ACL/retention.
- `DELETE /documents/{id}` – soft-delete respecting retention/legal holds; sets deleted_at/purge_at.
- `POST /documents/{id}/restore` – admin/staff restore within grace window.
- `POST /documents/{id}/share` – add collaborators or create time-bound link.
- `POST /documents/{id}/versions` – upload new version (init/finalize similar to upload).
- `GET /documents/{id}/versions` – list versions.
- `GET /documents/{id}/renditions/{type}` – signed URL for thumbnail/ocr/text.
- `GET /documents/{id}/versions/{v}/diff/{w}` – server-side diff (content via text rendition, metadata snapshot, ACL changes). Returns structured changes + rendition URLs for side-by-side.

## Search
- `POST /search` – body: query, mode (keyword/vector/hybrid), filters, pagination.
- `POST /search/vector` – embeddings query; returns matches with scores.
- `POST /search/index/reindex` – admin reindex job.
- `POST /search/index/reindex/{documentId}` – reindex single document (triggered on version updates to avoid stale data).

## Chatbot / RAG
- `POST /chat` – body: messages[], group_id (or allowed groups), mode (qa/summarize/agent), top_k, filters; enforces ACL + group scope; returns answer + citations; uses cached session context (e.g., Redis) for continuity.
- `GET /chat/history` – list past chats for user (filtered by group); supports session replay for audit.
- `POST /chat/session/{id}/feedback` – capture user feedback.
- `POST /chat/session/{id}/handoff` – optional escalate to human with context.
- `POST /chat/session/{id}/source-access` – allow agent to fetch allowed sources (docs via vector, reports/metrics if role permits); returns signed URLs for previews.

## Workflow & Tasks
- `POST /workflows` – start workflow on document with template/assignees.
- `GET /workflows/{id}` – status, history.
- `POST /tasks/{id}/action` – approve/reject/request changes/comment.
- `GET /tasks` – inbox list.

## OCR/AI Tasks
- `POST /ai/ocr` – enqueue OCR for doc/version/rendition; choose provider.
- `POST /ai/embed` – regenerate embeddings; provider selection.
- `POST /ai/classify` – run classifier; provider selection.
- `POST /ai/qa` – RAG Q&A over document(s); returns answer and references.
- `GET /ai/jobs/{id}` – job status/result.

## Audit & Logs
- `GET /audit` – filter by user, document, action, device, date.
- `POST /audit/export` – export within range (admin).

## Admin/Settings
- `GET/POST /settings/retention` – retention rules.
- `GET/POST /settings/providers` – OCR/AI/search provider configs; health checks.
- `GET/POST /document-groups` – manage document groups (name, description, members/roles, included docs/folders/tags).
- `POST /document-groups/{id}/reindex` – rebuild embeddings/index scoped to group if stored separately.
- `GET /reports/audit` – audit/export of user actions (upload/edit/delete/share/workflow/admin/AI). Filters: actor, action type, document, device, date range, status; formats: JSON/CSV; paginated.
- `GET /reports/usage` – usage metrics (uploads count/size, storage by bucket/folder/tag/group, search QPS, vector QPS, chatbot sessions, queue depth). Supports time ranges, rollups (hour/day/week), top-N breakdowns.
- `GET /reports/workflow` – workflow SLA: task durations, overdue counts, approval rates per template/assignee.
- `GET /reports/data-quality` – reindex/embedding job failures, stale index count, purge backlog, virus-scan failures.
- `GET/POST /settings/chatbot` – admin/staff configure chatbot policies per document group: allowed sources (docs, reports/metrics), allow previews/download links, redaction patterns, max tokens/context window, allowed LLM providers/models, rate limits.


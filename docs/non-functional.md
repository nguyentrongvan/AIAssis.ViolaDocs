# Non-Functional Considerations

## Security
- Auth via JWT/OIDC; short-lived access tokens, refresh rotation.
- RBAC enforced in API and queries; row-level security for multi-tenant/strict ACLs.
- Signed URLs for object access; avoid direct bucket exposure.
- Device auth with scoped keys; rate limit device endpoints.
- Input validation, virus scan on ingest, MIME sniff vs declared type.
- Audit everything: access, share, workflow, admin changes, AI actions.
- Encryption: TLS in transit; server-side encryption for MinIO; at-rest encryption for DB/vector.
- Account lifecycle: only admin/staff create users; enforce active/inactive flag and optional expires_at for short-term accounts; block login when inactive/expired.
- Soft delete grace: flag deleted_at/purge_at; only admin restore; purge after configurable days.
- OCR languages: default PaddleOCR with English & Vietnamese packs; allow admin to enable/disable language packs and fallback strategy.

## Performance & Scale
- Direct-to-object-store uploads with pre-signed URLs; chunked/resumable.
- Async pipeline for OCR/AI/thumbnail/index; backpressure via queues.
- Caching for auth/permissions and metadata lookups.
- Horizontal scale for API and workers; stateless app nodes.
- Vector/search adapters selected per workload; can shard/split by tenant.
- Reindex hooks on version updates to avoid stale vector/index; idempotent jobs.
- Scale paths: partition hot tables (audit, embeddings), move vector to dedicated DB, add read replicas for Postgres, tier MinIO storage, optional OpenSearch for heavy keyword/facet.

## Reliability & Ops
- Health endpoints per service/provider; circuit breakers/fallbacks.
- Observability: structured logs, metrics (ingest latency, OCR time, search QPS, queue depth), traces.
- Rate limits per user/device/IP; graceful degradation when AI unavailable.
- Reporting: audit exports and usage metrics dashboards for admin/staff.
- Reporting detail: time-windowed metrics (upload counts/sizes, storage by bucket/folder/tag/group, search/vector/chatbot QPS), workflow SLA (task durations/overdue), data quality (index/embedding failures, purge backlog, virus-scan failures); exports CSV/JSON; role-gated.

## Backup/DR
- PostgreSQL PITR, replicas; regular restore drills.
- MinIO versioning + replication optional; integrity checks.
- Vector DB snapshots; ability to rebuild from stored OCR text if embeddings lost.
- Scheduled purge job for soft-deleted items past grace period; alerts before purge.

## Compliance & Retention
- Retention policies enforced before delete; legal hold overrides.
- PII protection: redaction options in OCR/AI; access scoped by role.
- Data residency awareness when selecting providers/cloud storage.


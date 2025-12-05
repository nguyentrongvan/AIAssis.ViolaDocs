# Web UI (Vue) Design

## Key Journeys
- Upload from web: drag/drop, select files, progress, resumable, multi-file.
- Upload from scanner: manage devices, view incoming scans mailbox, claim/assign, complete metadata.
- Search & filter: keyword + semantic toggle, facets (type, tags, owner, device, date, status), saved searches.
- Document detail: preview, metadata, versions, annotations, comments, activity, share, workflow actions.
- Workflow: task inbox, approvals, reminders, SLA indicators.
- Chatbot: scoped Q&A over allowed document groups; show citations and access checks.
- Admin: users/roles, device registry, retention rules, audit viewer, OCR/AI provider settings, document groups, user activation/expiry.

## Screen Outline
- **Shell**: top nav (search bar, quick upload), left nav (library, tasks, admin), content area, user menu.
- **Upload Modal/Page**:
  - File picker/drag-drop, type badges; shows checksum/progress; pause/resume.
  - Metadata form: title, tags, folder, retention, sensitivity, workflow target, ACL (users/roles/team).
  - Post-upload status list with OCR/indexing state and link to detail.
- **Scan Inbox (from devices)**:
  - List of incoming scans with device, user/mailbox, time, thumbnails.
  - Actions: claim, assign to user/group, edit metadata, start workflow, delete/retry.
  - Device status widget (online, last seen).
- **Search Page**:
  - Combined search box; toggle keyword/vector; filters; result cards/table with highlights.
  - Bulk actions (share, move folder, start workflow).
- **Chatbot Panel**:
  - Select document group(s) (only those the user can access); optional filters (tag/type/date).
  - Conversation view with citations, source preview links; warnings when query hits restricted docs.
  - Feedback controls (thumbs up/down) and option to handoff to human with context bundle.
  - Shows session context indicator; can resume previous session; lets user request underlying document previews and report snippets when authorized.
- **Document Detail**:
  - Preview pane (PDF/image/office via viewer), toggles for OCR text, versions dropdown.
  - Metadata panel (editable with permission), tags, retention, workflow state, shares.
  - Comments/annotations panel, activity log.
  - Version history timeline with actor, time, source (web/scan), device/job, checksum; actions: open version, download, compare, restore.
  - Compare modal: side-by-side text diff (from extracted/OCR text), metadata diff (title/tags/retention/custom fields), ACL change highlights; for images, show dual view with optional heatmap.
- **Tasks / Workflow**:
  - Inbox with status chips; approve/reject/request changes; add notes; due dates.
- **Admin**:
  - Users/Roles/Permissions management.
  - Create users (no self-signup), set status active/inactive, set expiry for short-term accounts.
  - Devices: register/edit device, issue/revoke keys, test scan.
  - OCR/AI providers: select engine per task (OCR, embedding, LLM), health status, quotas.
  - Retention & audit: rules, export audit logs.
  - Document Groups: create/edit groups, assign members/roles, include docs/folders/tags, trigger reindex.
  - Chatbot Settings: per group policy for allowed sources (docs, reports/metrics), preview/download permissions, redaction patterns, allowed LLM/model selection, rate limits.

## UX Considerations
- Clear states: uploading, scanning, processing (OCR/AI), ready, failed.
- Show lineage: source (web/printer), device id, user, job id.
- Accessibility: keyboard-first uploads, status alerts; high-contrast for statuses.
- Offline/slow links: resumable uploads; optimistic metadata save with retries.
- Security: mask restricted docs, enforce signed URLs; least-privilege UI visibility based on role.
- Internationalization-ready labels and date/time locale formatting.


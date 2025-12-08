# Test-Driven Development (TDD) Plan

## Overview

This document lists all test cases that have been written and the features that need to be implemented to pass those tests. The goal is to implement code in priority order to ensure all test cases pass.

---

## Test Files Classification

### 1. Core Infrastructure & Utilities (High Priority)

#### ✅ `test_utils_response.py` - Response Utilities
**Status:** Needs implementation
**File to implement:** `src/app/utils/response.py`

**Test Cases:**
- `test_success_response_default` - Default success response
- `test_success_response_custom_message` - Response with custom message
- `test_success_response_custom_status_code` - Response with custom status code
- `test_success_response_no_data` - Response without data
- `test_error_response_default` - Default error response
- `test_error_response_custom_status_code` - Error response with custom status code
- `test_error_response_with_details` - Error response with details
- `test_error_response_unauthorized` - 401 Unauthorized response
- `test_error_response_forbidden` - 403 Forbidden response

**Features to implement:**
- `success_response()` - Create success response
- `error_response()` - Create error response

---

#### ✅ `test_services_auth.py` - Authentication Service
**Status:** Needs implementation
**File to implement:** `src/app/services/auth.py`

**Test Cases:**
- `test_verify_password_success` - Password verification success
- `test_verify_password_failure` - Password verification failure
- `test_get_password_hash` - Hash password
- `test_create_access_token_default` - Create access token with default settings
- `test_create_access_token_with_expires_delta` - Create access token with expiration time
- `test_create_refresh_token` - Create refresh token
- `test_decode_token_success` - Decode token success
- `test_decode_token_invalid` - Decode invalid token
- `test_decode_token_expired` - Decode expired token
- `test_authenticate_user_success` - Authenticate user success
- `test_authenticate_user_wrong_password` - Authenticate user with wrong password
- `test_authenticate_user_not_found` - Authenticate non-existent user
- `test_authenticate_user_inactive` - Authenticate inactive user
- `test_authenticate_user_expired` - Authenticate expired user
- `test_get_user_by_id_success` - Get user by ID success
- `test_get_user_by_id_not_found` - Get non-existent user

**Features to implement:**
- `verify_password()` - Verify password
- `get_password_hash()` - Hash password
- `create_access_token()` - Create JWT access token
- `create_refresh_token()` - Create JWT refresh token
- `decode_token()` - Decode and validate JWT token
- `authenticate_user()` - Authenticate user with email/password
- `get_user_by_id()` - Get user by ID

---

#### ✅ `test_services_storage.py` - Storage Service
**Status:** Needs implementation
**File to implement:** `src/app/services/storage.py`

**Test Cases:**
- `test_get_minio_client_success` - Connect to MinIO success
- `test_get_minio_client_creates_bucket` - Auto-create bucket if not exists
- `test_generate_presigned_upload_url` - Generate presigned URL for upload
- `test_generate_presigned_download_url` - Generate presigned URL for download
- `test_upload_file_to_minio_success` - Upload file success
- `test_upload_file_to_minio_failure` - Upload file failure
- `test_delete_file_from_minio_success` - Delete file success
- `test_delete_file_from_minio_failure` - Delete file failure
- `test_get_object_url_http` - Get object URL (HTTP)
- `test_get_object_url_https` - Get object URL (HTTPS)

**Features to implement:**
- `get_minio_client()` - Connect to MinIO client
- `generate_presigned_upload_url()` - Generate presigned upload URL
- `generate_presigned_download_url()` - Generate presigned download URL
- `upload_file_to_minio()` - Upload file to MinIO
- `delete_file_from_minio()` - Delete file from MinIO
- `get_object_url()` - Get public URL of object

---

### 2. Authentication & Identity APIs (High Priority)

#### ✅ `test_auth.py` - Authentication Endpoints
**Status:** Needs implementation
**File to implement:** `src/app/routers/auth.py`

**Test Cases:**

**POST /api/v1/auth/login:**
- `test_login_success` - Login success
- `test_login_invalid_email` - Login with non-existent email
- `test_login_invalid_password` - Login with wrong password
- `test_login_inactive_user` - Login with inactive user
- `test_login_expired_user` - Login with expired user
- `test_login_missing_email` - Login missing email
- `test_login_missing_password` - Login missing password
- `test_login_invalid_email_format` - Login with invalid email format

**POST /api/v1/auth/refresh:**
- `test_refresh_success` - Refresh token success
- `test_refresh_invalid_token` - Refresh with invalid token
- `test_refresh_access_token_instead_of_refresh` - Refresh with access token instead of refresh token
- `test_refresh_missing_token` - Refresh missing token

**POST /api/v1/auth/device/login:**
- `test_device_login_success` - Device login success
- `test_device_login_invalid_key` - Device login with invalid key
- `test_device_login_missing_key` - Device login missing key

**GET /api/v1/auth/me:**
- `test_get_me_success` - Get profile success
- `test_get_me_unauthorized` - Get profile without auth
- `test_get_me_invalid_token` - Get profile with invalid token
- `test_get_me_expired_token` - Get profile with expired token
- `test_get_me_admin_user` - Get admin profile
- `test_get_me_staff_user` - Get staff profile

**Features to implement:**
- `POST /auth/login` - Login endpoint
- `POST /auth/refresh` - Refresh token endpoint
- `POST /auth/device/login` - Device login endpoint
- `GET /auth/me` - Get current profile endpoint
- Dependency: `get_current_user()` - Get user from token

---

### 3. Health Check (High Priority - Simple)

#### ✅ `test_health.py` - Health Check Endpoint
**Status:** Needs implementation
**File to implement:** `src/app/routers/health.py`

**Test Cases:**
- `test_health_check` - Health check endpoint

**Features to implement:**
- `GET /health` - Health check endpoint

---

### 4. Background Workers (High Priority)

#### ✅ `test_workers.py` - Background Workers
**Status:** Needs implementation
**File to implement:** `src/app/workers/ocr_worker.py`

**Test Cases:**

**OCR Worker:**
- `test_process_ocr_job_success` - Process OCR job success
- `test_process_ocr_job_not_found` - Process non-existent job
- `test_process_ocr_job_already_processing` - Process job already in progress
- `test_process_ocr_job_failure` - Process OCR job failure
- `test_process_ocr_job_missing_version_id` - Process job missing version_id

**Embedding Worker:**
- `test_process_embedding_job_success` - Process embedding job success
- `test_process_embedding_job_no_ocr_text` - Process job without OCR text
- `test_process_embedding_job_provider_not_configured` - Process job without provider

**Features to implement:**
- `process_ocr_job(job_id)` - Process OCR job
- `process_embedding_job(job_id)` - Process embedding job
- `worker_loop()` - Worker loop to poll and process jobs
- Integration with OCR service and Embedding service
- Update job status (queued → processing → completed/failed)
- Save output (text_uri, embedding_uri) to job

---

### 5. AI Services (High Priority)

#### ✅ `test_services_ai_ocr.py` - OCR Service
**Status:** Needs implementation
**File to implement:** `src/app/services/ai/ocr_service.py`

**Test Cases:**
- `test_ocr_service_no_provider` - OCR service without provider
- `test_ocr_service_with_paddle` - OCR service with PaddleOCR
- `test_process_image_success` - Process image success
- `test_process_image_with_languages` - Process image with custom languages
- `test_process_pdf_success` - Process PDF success
- `test_paddle_ocr_provider_init` - Initialize PaddleOCR provider
- `test_paddle_ocr_provider_not_available` - PaddleOCR not available

**Features to implement:**
- `OcrService` class - Service to manage OCR providers
- `PaddleOcrProvider` class - PaddleOCR provider implementation
- `process_image()` - Process OCR for image
- `process_pdf()` - Process OCR for PDF
- Provider registry and selection logic

---

#### ✅ `test_services_ai_embedding.py` - Embedding Service
**Status:** Needs implementation
**File to implement:** `src/app/services/ai/embedding_service.py`

**Test Cases:**
- `test_embedding_service_no_provider` - Embedding service without provider
- `test_embedding_service_with_openai` - Embedding service with OpenAI
- `test_embedding_service_with_gemini` - Embedding service with Gemini
- `test_generate_embedding_success` - Generate embedding success
- `test_generate_embedding_no_provider` - Generate embedding without provider
- `test_generate_embeddings_batch` - Generate embeddings batch
- `test_openai_embedding_provider_init` - Initialize OpenAI provider
- `test_openai_embedding_provider_generate` - Generate embedding with OpenAI
- `test_gemini_embedding_provider_init` - Initialize Gemini provider
- `test_gemini_embedding_provider_generate` - Generate embedding with Gemini

**Features to implement:**
- `EmbeddingService` class - Service to manage embedding providers
- `OpenAIEmbeddingProvider` class - OpenAI embedding provider
- `GeminiEmbeddingProvider` class - Gemini embedding provider
- `generate_embedding()` - Generate embedding for text
- `generate_embeddings_batch()` - Generate embeddings for multiple texts
- Provider registry and selection logic

---

#### ✅ `test_services_ai_llm.py` - LLM Service
**Status:** Needs implementation
**File to implement:** `src/app/services/ai/llm_service.py`

**Test Cases:**
- `test_llm_service_no_provider` - LLM service without provider
- `test_llm_service_with_gemini` - LLM service with Gemini
- `test_llm_service_with_openai` - LLM service with OpenAI
- `test_chat_success` - Chat success
- `test_chat_with_context` - Chat with context
- `test_chat_no_provider` - Chat without provider
- `test_classify_document` - Classify document
- `test_summarize_document` - Summarize document
- `test_rag_qa` - RAG Q&A
- `test_gemini_llm_provider_init` - Initialize Gemini provider
- `test_gemini_llm_provider_chat` - Chat with Gemini
- `test_openai_llm_provider_init` - Initialize OpenAI provider
- `test_openai_llm_provider_chat` - Chat with OpenAI

**Features to implement:**
- `LLMService` class - Service to manage LLM providers
- `GeminiLLMProvider` class - Gemini LLM provider
- `OpenAILLMProvider` class - OpenAI LLM provider
- `chat()` - Chat with LLM
- `classify_document()` - Classify document
- `summarize_document()` - Summarize document
- `rag_qa()` - RAG Q&A
- Provider registry and selection logic

---

### 6. AI/OCR Task APIs (Medium Priority)

#### ✅ `test_ai.py` - AI Task Endpoints
**Status:** Needs implementation
**File to implement:** `src/app/routers/ai.py`

**Test Cases:**

**POST /api/v1/ai/ocr:**
- `test_enqueue_ocr_success` - Enqueue OCR job success
- `test_enqueue_ocr_with_version_id` - Enqueue with version_id
- `test_enqueue_ocr_with_document_id` - Enqueue with document_id
- `test_enqueue_ocr_missing_target` - Enqueue missing target
- `test_enqueue_ocr_default_provider` - Enqueue with default provider
- `test_enqueue_ocr_unauthorized` - Enqueue without auth

**POST /api/v1/ai/embed:**
- `test_enqueue_embed_success` - Enqueue embedding job success
- `test_enqueue_embed_unauthorized` - Enqueue without auth

**POST /api/v1/ai/classify:**
- `test_classify_success` - Classify success
- `test_classify_unauthorized` - Classify without auth

**POST /api/v1/ai/qa:**
- `test_qa_success` - Q&A success
- `test_qa_unauthorized` - Q&A without auth

**GET /api/v1/ai/jobs/{id}:**
- `test_get_job_status_success` - Get job status success
- `test_get_job_status_not_found` - Get non-existent job
- `test_get_job_status_completed` - Get completed job
- `test_get_job_status_failed` - Get failed job
- `test_get_job_status_unauthorized` - Get job without auth

**Features to implement:**
- `POST /ai/ocr` - Enqueue OCR job
- `POST /ai/embed` - Enqueue embedding job
- `POST /ai/classify` - Run classifier
- `POST /ai/qa` - RAG Q&A
- `GET /ai/jobs/{id}` - Get job status
- Create AIJob records in database
- Validation and error handling

---

### 7. Upload APIs (Medium Priority)

#### ✅ `test_uploads.py` - Upload Endpoints
**Status:** Needs implementation
**File to implement:** `src/app/routers/uploads.py`

**Test Cases:**

**POST /api/v1/uploads/init:**
- `test_init_upload_success` - Init upload success
- `test_init_upload_max_size` - Init upload with max size
- `test_init_upload_exceeds_max_size` - Init upload exceeding max size
- `test_init_upload_invalid_mime_type` - Init upload with invalid MIME type
- `test_init_upload_allowed_mime_types` - Init upload with allowed MIME types
- `test_init_upload_unauthorized` - Init upload without auth
- `test_init_upload_missing_fields` - Init upload missing fields

**POST /api/v1/uploads/{id}/finalize:**
- `test_finalize_upload_success` - Finalize upload success
- `test_finalize_upload_with_workflow` - Finalize with workflow
- `test_finalize_upload_not_found` - Finalize non-existent upload
- `test_finalize_upload_unauthorized` - Finalize another user's upload
- `test_finalize_upload_invalid_folder_id` - Finalize with invalid folder_id
- `test_finalize_upload_creates_ocr_job` - Finalize creates OCR job

**PUT /api/v1/uploads/{id}/chunk:**
- `test_upload_chunk_success` - Upload chunk success

**POST /api/v1/scan-jobs:**
- `test_create_scan_job_success` - Create scan job success

**POST /api/v1/scan-jobs/{jobId}/finalize:**
- `test_finalize_scan_job_success` - Finalize scan job success

**GET /api/v1/scan-jobs/pending:**
- `test_get_pending_scan_jobs` - Get pending scan jobs

**Features to implement:**
- `POST /uploads/init` - Initialize upload, create presigned URL
- `POST /uploads/{id}/finalize` - Finalize upload, create document
- `PUT /uploads/{id}/chunk` - Chunked upload (optional)
- `POST /scan-jobs` - Create scan job from device
- `POST /scan-jobs/{jobId}/finalize` - Finalize scan job
- `GET /scan-jobs/pending` - Get pending scan jobs
- Upload model/table to track uploads
- Validation file size, MIME type
- Auto-create OCR job after finalizing PDF/image

---

### 8. Users & Roles Management (Medium Priority)

#### ✅ `test_users.py` - Users & Roles Endpoints
**Status:** Needs implementation
**File to implement:** `src/app/routers/users.py`

**Test Cases:**

**GET /api/v1/users:**
- `test_list_users_success` - List users success
- `test_list_users_pagination` - List users with pagination
- `test_list_users_unauthorized` - List users without permission

**POST /api/v1/users:**
- `test_create_user_success` - Create user success
- `test_create_user_duplicate_email` - Create user with duplicate email
- `test_create_user_with_expiry` - Create user with expiry
- `test_create_user_unauthorized` - Create user without permission

**PATCH /api/v1/users/{id}:**
- `test_update_user_success` - Update user success
- `test_update_user_role_change` - Update user role
- `test_update_user_status_change` - Update user status
- `test_update_user_expiry` - Update user expiry
- `test_update_user_not_found` - Update non-existent user
- `test_update_user_unauthorized` - Update user without permission

**DELETE /api/v1/users/{id}:**
- `test_delete_user_success` - Delete user success
- `test_delete_user_self_delete_prevention` - Prevent self-deletion
- `test_delete_user_unauthorized` - Delete user without permission

**POST /api/v1/users/{id}/activate:**
- `test_activate_user_success` - Activate user success

**POST /api/v1/users/{id}/deactivate:**
- `test_deactivate_user_success` - Deactivate user success

**Features to implement:**
- `GET /users` - List users with pagination and filters
- `POST /users` - Create new user
- `PATCH /users/{id}` - Update user
- `DELETE /users/{id}` - Delete user (soft delete)
- `POST /users/{id}/activate` - Activate user
- `POST /users/{id}/deactivate` - Deactivate user
- Authorization checks (admin/staff only)
- Validation email, password, role

---

### 9. Devices Management (Medium Priority)

#### ✅ `test_devices.py` - Devices Endpoints
**Status:** Needs implementation
**File to implement:** `src/app/routers/devices.py`

**Test Cases:**

**GET /api/v1/devices:**
- `test_list_devices_success` - List devices success
- `test_list_devices_unauthorized` - List devices without permission

**POST /api/v1/devices:**
- `test_create_device_success` - Create device success
- `test_create_device_minimal_fields` - Create device with minimal fields
- `test_create_device_unauthorized` - Create device without permission

**PATCH /api/v1/devices/{id}:**
- `test_update_device_success` - Update device success
- `test_update_device_not_found` - Update non-existent device
- `test_update_device_unauthorized` - Update device without permission

**DELETE /api/v1/devices/{id}:**
- `test_delete_device_success` - Delete device success
- `test_delete_device_not_found` - Delete non-existent device
- `test_delete_device_unauthorized` - Delete device without permission

**POST /api/v1/devices/{id}/issue-key:**
- `test_issue_device_key_success` - Issue device key success
- `test_issue_device_key_revoke_previous` - Issue new key revokes old key
- `test_issue_device_key_multiple_times` - Issue key multiple times
- `test_issue_device_key_unauthorized` - Issue key without permission

**POST /api/v1/devices/{id}/ping:**
- `test_device_ping_success` - Device ping success
- `test_device_ping_updates_last_seen` - Ping updates last_seen

**Features to implement:**
- `GET /devices` - List devices
- `POST /devices` - Create device
- `PATCH /devices/{id}` - Update device
- `DELETE /devices/{id}` - Delete device
- `POST /devices/{id}/issue-key` - Issue device key
- `POST /devices/{id}/ping` - Device heartbeat
- Device model with key management
- Authorization checks

---

### 10. Documents APIs (Medium Priority)

#### ✅ `test_documents.py` - Documents Endpoints
**Status:** Needs implementation
**File to implement:** `src/app/routers/documents.py`

**Test Cases:**

**GET /api/v1/documents:**
- `test_list_documents_success` - List documents success
- `test_list_documents_pagination` - List with pagination
- `test_list_documents_search` - List with search
- `test_list_documents_filters_deleted` - Filter deleted documents

**GET /api/v1/documents/{id}:**
- `test_get_document_success` - Get document success
- `test_get_document_not_found` - Get non-existent document
- `test_get_document_access_denied` - Get document without permission
- `test_get_document_staff_access` - Staff access document

**PATCH /api/v1/documents/{id}:**
- `test_update_document_success` - Update document success
- `test_update_document_tags` - Update tags
- `test_update_document_not_found` - Update non-existent document
- `test_update_document_access_denied` - Update document without permission

**DELETE /api/v1/documents/{id}:**
- `test_delete_document_success` - Delete document success
- `test_delete_document_sets_purge_at` - Delete sets purge_at
- `test_delete_document_not_found` - Delete non-existent document
- `test_delete_document_unauthorized` - Delete document without permission

**POST /api/v1/documents/{id}/restore:**
- `test_restore_document_success` - Restore document success
- `test_restore_document_not_deleted` - Restore non-deleted document
- `test_restore_document_unauthorized` - Restore document without permission

**GET /api/v1/documents/{id}/versions:**
- `test_list_versions_success` - List versions success

**GET /api/v1/documents/{id}/versions/{v1}/diff/{v2}:**
- `test_compare_versions_success` - Compare versions success

**POST /api/v1/documents/{id}/versions:**
- `test_upload_new_version_success` - Upload new version success

**POST /api/v1/documents/{id}/share:**
- `test_share_document_with_user` - Share with user
- `test_share_document_with_role` - Share with role
- `test_share_document_with_link` - Share with link

**GET /api/v1/documents/{id}/renditions/{type}:**
- `test_get_rendition_thumbnail` - Get thumbnail
- `test_get_rendition_ocr_text` - Get OCR text

**Features to implement:**
- `GET /documents` - List documents with filters, pagination, search
- `GET /documents/{id}` - Get document detail
- `PATCH /documents/{id}` - Update document metadata
- `DELETE /documents/{id}` - Soft delete document
- `POST /documents/{id}/restore` - Restore deleted document
- `GET /documents/{id}/versions` - List versions
- `GET /documents/{id}/versions/{v1}/diff/{v2}` - Compare versions
- `POST /documents/{id}/versions` - Upload new version
- `POST /documents/{id}/share` - Share document
- `GET /documents/{id}/renditions/{type}` - Get rendition (thumbnail, OCR text)
- ACL/permission checks
- Soft delete with purge_at
- Version management

---

### 11. Search APIs (Low Priority)

#### ✅ `test_search.py` - Search Endpoints
**Status:** Needs implementation
**File to implement:** `src/app/routers/search.py`

**Test Cases:**

**POST /api/v1/search:**
- `test_search_keyword_mode` - Keyword search
- `test_search_vector_mode` - Vector search
- `test_search_hybrid_mode` - Hybrid search
- `test_search_with_filters` - Search with filters
- `test_search_with_group_id` - Search with group_id
- `test_search_empty_query` - Search with empty query

**POST /api/v1/search/vector:**
- `test_vector_search_success` - Vector search success
- `test_vector_search_with_filters` - Vector search with filters

**POST /api/v1/search/index/reindex:**
- `test_reindex_all_success` - Reindex all success
- `test_reindex_single_document` - Reindex single document

**Features to implement:**
- `POST /search` - Search with keyword/vector/hybrid mode
- `POST /search/vector` - Vector search
- `POST /search/index/reindex` - Reindex all
- `POST /search/index/reindex/{documentId}` - Reindex single document
- Integration with vector store (pgvector/Qdrant)
- Keyword search with full-text search
- Hybrid search merging results
- ACL filtering

---

### 12. Chatbot/RAG APIs (Low Priority)

#### ✅ `test_chatbot.py` - Chatbot Endpoints
**Status:** Needs implementation
**File to implement:** `src/app/routers/chat.py`

**Test Cases:**

**POST /api/v1/chat:**
- `test_chat_basic` - Basic chat
- `test_chat_with_group_id` - Chat with group_id
- `test_chat_with_session_id` - Chat with session_id
- `test_chat_empty_message` - Chat with empty message
- `test_chat_with_filters` - Chat with filters

**GET /api/v1/chat/history:**
- `test_get_chat_history_success` - Get chat history success
- `test_get_chat_history_with_group_filter` - Get history with group filter

**GET /api/v1/chat/session/{session_id}:**
- `test_get_session_history_success` - Get session history success

**POST /api/v1/chat/session/{id}/feedback:**
- `test_submit_feedback_positive` - Submit positive feedback
- `test_submit_feedback_negative` - Submit negative feedback

**POST /api/v1/chat/session/{id}/handoff:**
- `test_handoff_to_human_success` - Handoff to human success

**POST /api/v1/chat/session/{id}/source-access:**
- `test_request_source_access_success` - Request source access success

**Features to implement:**
- `POST /chat` - Chat with RAG
- `GET /chat/history` - Get chat history
- `GET /chat/session/{id}` - Get session history
- `POST /chat/session/{id}/feedback` - Submit feedback
- `POST /chat/session/{id}/handoff` - Handoff to human
- `POST /chat/session/{id}/source-access` - Request source access
- Session management
- Integration with LLM service and vector search
- Context management

---

### 13. Workflow & Tasks APIs (Low Priority)

#### ✅ `test_workflows.py` - Workflow Endpoints
**Status:** Needs implementation
**File to implement:** `src/app/routers/workflows.py`

**Test Cases:**

**POST /api/v1/workflows:**
- `test_start_workflow_success` - Start workflow success
- `test_start_workflow_with_assignees` - Start workflow with assignees
- `test_start_workflow_not_found_document` - Start workflow with non-existent document

**GET /api/v1/workflows/{id}:**
- `test_get_workflow_success` - Get workflow success
- `test_get_workflow_not_found` - Get non-existent workflow

**POST /api/v1/tasks/{id}/action:**
- `test_task_action_approve` - Approve task
- `test_task_action_reject` - Reject task
- `test_task_action_request_changes` - Request changes
- `test_task_action_not_found` - Action with non-existent task
- `test_task_action_unauthorized` - Action without permission
- `test_task_action_invalid_action` - Invalid action

**GET /api/v1/tasks:**
- `test_list_tasks_inbox` - List tasks in inbox
- `test_list_tasks_filtered_by_state` - List tasks with state filter

**Features to implement:**
- `POST /workflows` - Start workflow
- `GET /workflows/{id}` - Get workflow status
- `POST /tasks/{id}/action` - Action on task (approve/reject/request_changes)
- `GET /tasks` - List tasks (inbox)
- Workflow engine
- Task state management
- Notification system

---

### 14. Audit & Logs APIs (Low Priority)

#### ✅ `test_audit.py` - Audit Endpoints
**Status:** Needs implementation
**File to implement:** `src/app/routers/audit.py` (may not exist yet)

**Test Cases:**

**GET /api/v1/audit:**
- `test_list_audit_events_success` - List audit events success
- `test_list_audit_events_with_filters` - List with filters
- `test_list_audit_events_by_date_range` - List with date range
- `test_list_audit_events_by_subject` - List by subject

**POST /api/v1/audit/export:**
- `test_export_audit_csv` - Export CSV
- `test_export_audit_json` - Export JSON
- `test_export_audit_with_filters` - Export with filters

**Features to implement:**
- `GET /audit` - List audit events with filters
- `POST /audit/export` - Export audit logs
- Audit logging system
- Event storage and querying

---

### 15. Reports APIs (Low Priority)

#### ✅ `test_reports.py` - Reports Endpoints
**Status:** Needs implementation
**File to implement:** `src/app/routers/reports.py`

**Test Cases:**

**GET /api/v1/reports/audit:**
- `test_audit_report_success` - Audit report success
- `test_audit_report_with_filters` - Audit report with filters

**GET /api/v1/reports/usage:**
- `test_usage_report_success` - Usage report success
- `test_usage_report_with_time_range` - Usage report with time range
- `test_usage_report_with_rollup` - Usage report with rollup

**GET /api/v1/reports/workflow:**
- `test_workflow_report_success` - Workflow report success
- `test_workflow_report_with_filters` - Workflow report with filters

**GET /api/v1/reports/quality:**
- `test_data_quality_report_success` - Data quality report success

**Features to implement:**
- `GET /reports/audit` - Audit report
- `GET /reports/usage` - Usage metrics report
- `GET /reports/workflow` - Workflow SLA report
- `GET /reports/quality` - Data quality report
- Report generation logic
- Aggregation and statistics

---

### 16. Settings/Admin APIs (Low Priority)

#### ✅ `test_settings.py` - Settings Endpoints
**Status:** Needs implementation
**File to implement:** `src/app/routers/settings.py` or `src/app/routers/groups.py`

**Test Cases:**

**GET/POST /api/v1/settings/retention:**
- `test_get_retention_rules` - Get retention rules
- `test_create_retention_rule` - Create retention rule

**GET/POST /api/v1/settings/providers:**
- `test_get_provider_configs` - Get provider configs
- `test_create_provider_config` - Create provider config
- `test_provider_health_check` - Health check provider

**GET/POST /api/v1/document-groups:**
- `test_create_document_group` - Create document group
- `test_list_document_groups` - List document groups
- `test_get_document_group` - Get document group
- `test_update_document_group` - Update document group
- `test_delete_document_group` - Delete document group
- `test_reindex_document_group` - Reindex document group

**GET/POST /api/v1/settings/chatbot:**
- `test_get_chatbot_settings` - Get chatbot settings
- `test_update_chatbot_settings` - Update chatbot settings

**Features to implement:**
- `GET/POST /settings/retention` - Retention rules management
- `GET/POST /settings/providers` - Provider configs management
- `GET/POST /document-groups` - Document groups CRUD
- `POST /document-groups/{id}/reindex` - Reindex group
- `GET/POST /settings/chatbot` - Chatbot settings per group
- Settings storage and management

---

## Implementation Priority Order

### Phase 1: Core Infrastructure (Week 1)
1. ✅ `test_utils_response.py` - Response utilities
2. ✅ `test_services_auth.py` - Auth service
3. ✅ `test_services_storage.py` - Storage service
4. ✅ `test_auth.py` - Auth endpoints
5. ✅ `test_health.py` - Health check

### Phase 2: Workers & AI Services (Week 2)
6. ✅ `test_services_ai_ocr.py` - OCR service
7. ✅ `test_services_ai_embedding.py` - Embedding service
8. ✅ `test_services_ai_llm.py` - LLM service
9. ✅ `test_workers.py` - Background workers
10. ✅ `test_ai.py` - AI endpoints

### Phase 3: Core Features (Week 3-4)
11. ✅ `test_uploads.py` - Upload endpoints
12. ✅ `test_users.py` - Users management
13. ✅ `test_devices.py` - Devices management
14. ✅ `test_documents.py` - Documents CRUD

### Phase 4: Advanced Features (Week 5-6)
15. ✅ `test_search.py` - Search endpoints
16. ✅ `test_chatbot.py` - Chatbot/RAG
17. ✅ `test_workflows.py` - Workflows & Tasks
18. ✅ `test_audit.py` - Audit logs
19. ✅ `test_reports.py` - Reports
20. ✅ `test_settings.py` - Settings/Admin

---

## Implementation Checklist

### Core Infrastructure
- [ ] Response utilities (`utils/response.py`)
- [ ] Auth service (`services/auth.py`)
- [ ] Storage service (`services/storage.py`)
- [ ] Auth endpoints (`routers/auth.py`)
- [ ] Health check (`routers/health.py`)

### Workers & AI
- [ ] OCR service (`services/ai/ocr_service.py`)
- [ ] Embedding service (`services/ai/embedding_service.py`)
- [ ] LLM service (`services/ai/llm_service.py`)
- [ ] OCR worker (`workers/ocr_worker.py`)
- [ ] AI endpoints (`routers/ai.py`)

### Core Features
- [ ] Upload endpoints (`routers/uploads.py`)
- [ ] Users endpoints (`routers/users.py`)
- [ ] Devices endpoints (`routers/devices.py`)
- [ ] Documents endpoints (`routers/documents.py`)

### Advanced Features
- [ ] Search endpoints (`routers/search.py`)
- [ ] Chatbot endpoints (`routers/chat.py`)
- [ ] Workflows endpoints (`routers/workflows.py`)
- [ ] Audit endpoints (`routers/audit.py`)
- [ ] Reports endpoints (`routers/reports.py`)
- [ ] Settings endpoints (`routers/settings.py` or `routers/groups.py`)

---

## Notes

1. **Dependencies:** Some endpoints depend on each other. For example:
   - Upload endpoints need Storage service
   - AI endpoints need Workers and AI Services
   - Documents endpoints need Upload endpoints

2. **Database Models:** Ensure all models are defined in `src/app/models/`

3. **Testing:** Run tests after each feature is implemented:
   ```bash
   pytest tests/test_<feature>.py -v
   ```

4. **Coverage:** Target 80%+ test coverage for each module

5. **Documentation:** Update API documentation after implementing each endpoint

---

## Usage

1. Start with Phase 1 (Core Infrastructure)
2. Implement each test file in priority order
3. Run tests after each implementation to ensure they pass
4. Fix bugs and refactor if needed
5. Continue with the next phase

---

**Last Updated:** 2024
**Status:** In Progress

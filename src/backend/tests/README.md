# Test Suite for VanDMS Backend

## Test Structure

Test suite is organized by modules/features:

```
tests/
├── conftest.py                      # Shared fixtures and configuration
├── pytest.ini                      # Pytest configuration
├── test_health.py                  # Tests for Health check endpoint
├── test_auth.py                    # Tests for Authentication & Identity APIs
├── test_users.py                   # Tests for Users & Roles management APIs
├── test_devices.py                 # Tests for Devices (printers/scanners) APIs
├── test_uploads.py                 # Tests for Upload (Web & Scanner) APIs
├── test_documents.py               # Tests for Documents APIs (CRUD, versions, sharing)
├── test_search.py                  # Tests for Search APIs (keyword, vector, hybrid)
├── test_chatbot.py                 # Tests for Chatbot/RAG APIs
├── test_workflows.py               # Tests for Workflow & Tasks APIs
├── test_ai.py                      # Tests for AI/OCR Task APIs
├── test_audit.py                   # Tests for Audit & Logs APIs
├── test_reports.py                 # Tests for Reports APIs
├── test_settings.py                # Tests for Settings/Admin APIs
├── test_workers.py                 # Tests for Background Workers (OCR, Embedding)
├── test_services_storage.py        # Tests for Storage Service
├── test_services_auth.py           # Tests for Auth Service
├── test_services_ai_ocr.py        # Tests for OCR Service
├── test_services_ai_llm.py        # Tests for LLM Service
├── test_services_ai_embedding.py  # Tests for Embedding Service
└── test_utils_response.py          # Tests for Response Utils
```

## Running Tests

```bash
# Run all tests
pytest

# Run tests for a specific module
pytest tests/test_auth.py

# Run tests with coverage
pytest --cov=src --cov-report=html

# Run tests with markers
pytest -m unit          # Unit tests (services, utils, workers)
pytest -m integration  # Integration tests
pytest -m api          # API endpoint tests
pytest -m auth         # Authentication tests
```

## Naming Conventions

- Test file: `test_<module_name>.py`
- Test class: `Test<FeatureName>`
- Test function: `test_<scenario>_<expected_result>`

Examples:
- `test_auth_login_success`
- `test_auth_login_invalid_credentials`
- `test_documents_list_with_pagination`

## Test Coverage

Each test file includes:
- **Happy path scenarios** - Successful operations
- **Error cases** - Validation errors, authorization failures, not found
- **Edge cases** - Boundary values, empty data, null handling
- **Security cases** - Unauthorized access, privilege escalation, token validation

## Test Categories

### API Tests
- Test HTTP endpoints, request/response handling
- Test authentication and authorization
- Test input validation and error responses

### Service Tests
- Test business logic in services
- Test service integrations (MinIO, AI providers)
- Test error handling and fallbacks

### Worker Tests
- Test background job processing
- Test job status transitions
- Test error recovery

### Unit Tests
- Test individual functions and methods
- Test utility functions
- Test model validations

## Dependencies

Required packages (already in requirements.txt):
- pytest==7.4.3
- pytest-asyncio==0.21.1
- pytest-cov==4.1.0
- httpx==0.25.2
- aiosqlite==0.19.0

## Notes

1. Some endpoints may not be fully implemented yet - tests are written based on design and may need adjustment when code is implemented.

2. Tests use in-memory SQLite database for fast and independent testing.

3. Some AI/LLM endpoint tests may need mocked services or skip if API keys are not available.

4. Device authentication tests may need adjustment based on actual implementation.

5. Worker tests use mocks for external dependencies (MinIO, AI services) to avoid requiring actual services during testing.





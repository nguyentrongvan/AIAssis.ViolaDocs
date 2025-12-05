# ViolaDocs - Setup Guide

## Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Node.js 18+

## Quick Start

### 1. Start Infrastructure Services

Start all required services using Docker Compose:

```bash
docker-compose up -d
```

This starts:
- **PostgreSQL** (port 5432) with pgvector extension
- **MinIO** (ports 9000, 9001) - S3-compatible object storage
- **Redis** (port 6379) - Caching and message queue

Verify services are running:
```bash
docker-compose ps
```

### 2. Setup Backend

Navigate to the backend directory:

```bash
cd src/backend
```

#### Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

#### Install Dependencies

```bash
pip install -r requirements.txt
```

#### Configure Environment

Copy the example environment file:

```bash
# Windows
copy env.example .env

# Linux/Mac
cp env.example .env
```

Edit `.env` file with your configuration:

```env
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=viadocs
POSTGRES_PASSWORD=viadocs_pass
POSTGRES_DB=viadocs_db

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_SECURE=false
MINIO_BUCKET=documents

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# JWT
JWT_SECRET_KEY=your-secret-key-here-change-in-production-min-32-chars
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# LLM Providers - Support multiple keys (comma-separated) for quota distribution
GEMINI_API_KEY=your-gemini-api-key-1,your-gemini-api-key-2
OPENAI_API_KEY=your-openai-api-key-1,your-openai-api-key-2

# OCR
OCR_PROVIDER=paddle
OCR_LANGUAGES=en,vi

# App Settings
API_V1_PREFIX=/api/v1
DEBUG=true
LOG_LEVEL=INFO

# Retention & Purge
DEFAULT_RETENTION_DAYS=365
PURGE_GRACE_PERIOD_DAYS=30

# File Upload
MAX_UPLOAD_SIZE_MB=100
ALLOWED_MIME_TYPES=application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,image/jpeg,image/png,image/tiff
```

#### Run Database Migrations

```bash
# Create initial migration (if needed)
alembic revision --autogenerate -m "Initial schema"

# Apply migrations
alembic upgrade head
```

#### Start Backend Server

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or using Python module
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend API will be available at: **http://localhost:8000**

API Documentation (Swagger): **http://localhost:8000/docs**

### 3. Setup Frontend

Navigate to the frontend directory:

```bash
cd src/frontend
```

#### Install Dependencies

```bash
npm install
```

#### Configure Environment (Optional)

Create `.env` file if needed:

```env
VITE_API_BASE=http://localhost:8000/api/v1
```

#### Start Development Server

```bash
npm run dev
```

Frontend will be available at: **http://localhost:3000**

#### Build for Production

```bash
npm run build
```

Production files will be in `dist/` directory.

### 4. Create Initial Admin User

After starting the backend, create an admin user via API:

```bash
# Using curl
curl -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Admin",
    "email": "admin@example.com",
    "password": "admin123",
    "role": "admin"
  }'
```

Or use the API documentation at http://localhost:8000/docs to create a user.

### 5. Start Background Workers (Optional)

For processing OCR and embedding jobs, start the worker:

```bash
cd src/backend
python -m app.workers.ocr_worker
```

Or run in background:
```bash
python -m app.workers.ocr_worker &
```

## Verification

### Check Backend Health

```bash
curl http://localhost:8000/api/v1/health
```

Expected response:
```json
{
  "is_success": true,
  "message": "Success",
  "status_code": 200,
  "data": {
    "status": "ok"
  }
}
```

### Check Database Connection

```bash
# Using psql (if installed)
psql -h localhost -U viadocs -d viadocs_db

# Or check via Docker
docker exec -it viadocs_postgres psql -U viadocs -d viadocs_db
```

### Check MinIO

Access MinIO Console at: **http://localhost:9001**

Default credentials:
- Username: `minioadmin`
- Password: `minioadmin123`

### Check Redis

```bash
# Using redis-cli (if installed)
redis-cli -h localhost -p 6379 ping

# Or check via Docker
docker exec -it viadocs_redis redis-cli ping
```

Expected response: `PONG`

## Troubleshooting

### Port Already in Use

If ports are already in use, modify `docker-compose.yml` or stop conflicting services:

```bash
# Check what's using the port (Windows)
netstat -ano | findstr :8000

# Check what's using the port (Linux/Mac)
lsof -i :8000
```

### Database Connection Issues

1. Ensure PostgreSQL container is running:
   ```bash
   docker-compose ps postgres
   ```

2. Check database logs:
   ```bash
   docker-compose logs postgres
   ```

3. Verify connection string in `.env` file

### MinIO Access Issues

1. Check MinIO is running:
   ```bash
   docker-compose ps minio
   ```

2. Verify credentials in `.env` match docker-compose.yml

3. Check MinIO logs:
   ```bash
   docker-compose logs minio
   ```

### Frontend API Connection Issues

1. Verify `VITE_API_BASE` in frontend `.env` points to correct backend URL
2. Check CORS settings in backend `main.py`
3. Ensure backend is running on the specified port

### Migration Issues

1. Check Alembic configuration in `alembic.ini`
2. Verify database connection string
3. Review migration files in `migrations/versions/`

```bash
# Show migration history
alembic history

# Show current revision
alembic current
```

## Development Workflow

### Running Tests

```bash
# Backend tests
cd src/backend
pytest

# Frontend tests
cd src/frontend
npm run test
```

### Database Migrations

```bash
cd src/backend

# Create new migration
alembic revision --autogenerate -m "description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

### Code Formatting

```bash
# Backend (using black)
cd src/backend
black .

# Frontend (using prettier)
cd src/frontend
npm run format
```

## Production Deployment

### Backend

1. Set `DEBUG=false` in `.env`
2. Use production WSGI server:
   ```bash
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
   ```

### Frontend

1. Build production bundle:
   ```bash
   npm run build
   ```

2. Serve with nginx or similar web server

### Docker Production

Create `docker-compose.prod.yml` for production configuration with:
- Environment variables
- Volume mounts for persistent data
- Resource limits
- Health checks

## Additional Resources

- [API Documentation](http://localhost:8000/docs) - Interactive API docs
- [Architecture Documentation](docs/architecture/overview.md)
- [API Specification](docs/api/spec.md)


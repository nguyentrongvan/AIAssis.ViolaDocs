# ViolaDocs Docker Platform Guide

Complete guide to running ViolaDocs as a complete Docker platform with frontend, backend, and supporting services.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Environment Configuration](#environment-configuration)
- [Domain Configuration](#domain-configuration)
- [SSL/HTTPS Setup](#sslhttps-setup)
- [Production Deployment](#production-deployment)
- [Troubleshooting](#troubleshooting)
- [Scaling](#scaling)

## Overview

ViolaDocs Platform is fully containerized in Docker with:

- **Frontend**: Vue.js application served by Nginx
- **Backend**: FastAPI application with auto-migration
- **Nginx**: Reverse proxy with SSL/HTTPS support
- **Infrastructure**: PostgreSQL, MinIO, Redis, Qdrant, Ollama
- **Workers**: OCR worker and Purge worker

All services are managed via Docker Compose and can be started with a single command.

## Architecture

```
Internet
    │
    ├─ HTTP (80) ──────────────┐
    └─ HTTPS (443) ────────────┤
                               ▼
                        ┌─────────────┐
                        │    Nginx     │
                        │ Reverse Proxy│
                        └──────┬───────┘
                               │
                ┌──────────────┴──────────────┐
                │                             │
        ┌───────▼───────┐           ┌────────▼────────┐
        │   Frontend    │           │    Backend      │
        │   (Vue.js)    │           │   (FastAPI)     │
        └──────────────┘           └────────┬─────────┘
                                            │
                    ┌───────────────────────┼───────────────────────┐
                    │                       │                       │
            ┌───────▼──────┐      ┌────────▼──────┐      ┌────────▼──────┐
            │  PostgreSQL  │      │     MinIO      │      │     Redis     │
            │   (pgvector)  │      │  (S3 Storage)  │      │   (Cache)     │
            └──────────────┘      └────────────────┘      └───────────────┘
                    │
            ┌───────▼──────┐      ┌────────▼──────┐
            │   Qdrant     │      │    Ollama     │
            │ (Vector DB)  │      │     (LLM)     │
            └──────────────┘      └───────────────┘
```

## Quick Start

### 1. Prerequisites

Ensure you have installed:
- Docker (version 20.10+)
- Docker Compose (version 2.0+ or docker-compose 1.29+)

### 2. Environment Configuration

```bash
# Copy configuration template
cp .env.example .env

# Edit .env with your configuration
# At minimum, change:
# - JWT_SECRET_KEY (must be >= 32 characters)
# - POSTGRES_PASSWORD
# - MINIO_SECRET_KEY
```

### 3. Start Platform

ViolaDocs supports two modes: **Development** and **Production**.

#### Development Mode

For local development and testing:

**Linux/Mac:**
```bash
chmod +x start-dev.sh
./start-dev.sh
```

**Windows:**
```cmd
start-dev.bat
```

**Or use Docker Compose directly:**
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

**Access:**
- **Frontend**: http://localhost:3000 (direct access)
- **Backend API**: http://localhost:8000 (direct access)
- **API Documentation**: http://localhost:8000/api/v1/docs

**Features:**
- Direct port access for easy debugging
- No Nginx reverse proxy
- DEBUG mode enabled
- Hot reload support

#### Production Mode

For production deployment:

**Linux/Mac:**
```bash
chmod +x start-prod.sh
./start-prod.sh
```

**Windows:**
```cmd
start-prod.bat
```

**Or use Docker Compose directly:**
```bash
docker-compose --profile production up -d --build
```

**Access:**
- **Frontend**: http://localhost (via Nginx)
- **Backend API**: http://localhost/api/v1 (via Nginx)
- **API Documentation**: http://localhost/api/v1/docs

**Features:**
- Nginx reverse proxy
- SSL/HTTPS support
- Production-ready configuration
- Internal service communication only

#### Interactive Mode Selection

**Linux/Mac:**
```bash
chmod +x start.sh
./start.sh
# Will prompt for mode selection
```

**Windows:**
```cmd
start.bat
# Will prompt for mode selection
```

### 4. First Login

Root user is automatically created with information from `.env`:
- Email: `ROOT_USER_EMAIL` (default: admin@example.com)
- Password: `ROOT_USER_PASSWORD` (default: admin123)

**⚠️ Important**: Change password immediately after first login!

## Environment Configuration

The `.env` file contains all platform configuration. Important variables:

### Domain & SSL
```env
DOMAIN=yourdomain.com
ENABLE_SSL=false
VITE_API_BASE=/api/v1
```

### Database
```env
POSTGRES_HOST=postgres
POSTGRES_USER=viadocs
POSTGRES_PASSWORD=your-secure-password
POSTGRES_DB=viadocs_db
```

### JWT Security
```env
JWT_SECRET_KEY=your-secret-key-minimum-32-characters-long
```

### Storage
```env
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=your-secure-password
MINIO_BUCKET=documents
```

See `.env.example` for complete list of environment variables.

## Domain Configuration

### 1. DNS Configuration

Point your domain to the server IP:

```
Type: A
Name: @ (or subdomain like viadocs)
Value: YOUR_SERVER_IP
TTL: 3600
```

### 2. Update .env

```env
DOMAIN=yourdomain.com
VITE_API_BASE=https://yourdomain.com/api/v1
```

### 3. Update Nginx Config

Edit `nginx/conf.d/default.conf` and replace `server_name _;` with:

```nginx
server_name yourdomain.com www.yourdomain.com;
```

### 4. Restart

```bash
docker-compose restart nginx
```

## SSL/HTTPS Setup

There are 2 ways to setup SSL:

### Option 1: Let's Encrypt (Recommended - Automatic)

#### Step 1: Install Certbot

```bash
# On host (not in container)
sudo apt-get update
sudo apt-get install certbot
```

#### Step 2: Generate Certificate

```bash
# Temporarily stop nginx
docker-compose stop nginx

# Generate certificate
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Certificate will be saved at:
# /etc/letsencrypt/live/yourdomain.com/fullchain.pem
# /etc/letsencrypt/live/yourdomain.com/privkey.pem
```

#### Step 3: Mount Certificates into Container

Update `docker-compose.yml` for nginx service:

```yaml
nginx:
  volumes:
    - ./nginx/conf.d:/etc/nginx/conf.d:ro
    - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    - /etc/letsencrypt:/etc/letsencrypt:ro  # Mount Let's Encrypt certs
    - certbot_www:/var/www/certbot
```

#### Step 4: Configure SSL in Nginx

Copy template and edit:

```bash
cp nginx/conf.d/ssl.conf.template nginx/conf.d/ssl.conf
```

Edit `nginx/conf.d/ssl.conf`:
- Replace `YOUR_DOMAIN_HERE` with your domain
- Uncomment HTTPS server block in `default.conf`

#### Step 5: Restart

```bash
docker-compose up -d nginx
```

#### Step 6: Auto-renewal

Add cron job for automatic renewal:

```bash
# Open crontab
sudo crontab -e

# Add this line (runs daily at 2:30 AM)
30 2 * * * certbot renew --quiet --deploy-hook "docker-compose -f /path/to/docker-compose.yml restart nginx"
```

### Option 2: Custom SSL Certificate

#### Step 1: Copy Certificates

```bash
mkdir -p nginx/ssl
cp your-cert.pem nginx/ssl/cert.pem
cp your-key.pem nginx/ssl/key.pem
```

#### Step 2: Update .env

```env
ENABLE_SSL=true
SSL_CERT_PATH=/etc/nginx/ssl/cert.pem
SSL_KEY_PATH=/etc/nginx/ssl/key.pem
```

#### Step 3: Configure Nginx

Uncomment and edit HTTPS server block in `nginx/conf.d/default.conf`:

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    # ... rest of config
}
```

#### Step 4: Restart

```bash
docker-compose restart nginx
```

## Production Deployment

### Pre-deployment Checklist

- [ ] Change `JWT_SECRET_KEY` to a strong random value (>= 32 characters)
- [ ] Change `POSTGRES_PASSWORD` and `MINIO_SECRET_KEY`
- [ ] Set `DEBUG=false` in `.env`
- [ ] Configure domain and DNS
- [ ] Setup SSL/HTTPS
- [ ] Backup volumes before deployment
- [ ] Configure firewall (only open ports 80, 443)
- [ ] Setup monitoring and logging

### Optimization

#### 1. Resource Limits

Add to `docker-compose.yml`:

```yaml
backend:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 2G
      reservations:
        cpus: '1'
        memory: 1G
```

#### 2. Logging

Configure log rotation:

```yaml
backend:
  logging:
    driver: "json-file"
    options:
      max-size: "10m"
      max-file: "3"
```

#### 3. Health Checks

All services have health checks. Monitor with:

```bash
docker-compose ps
```

### Backup

#### Backup Database

```bash
docker-compose exec postgres pg_dump -U viadocs viadocs_db > backup_$(date +%Y%m%d).sql
```

#### Backup Volumes

```bash
# Backup all volumes
docker run --rm -v viadocs_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz /data
docker run --rm -v viadocs_minio_data:/data -v $(pwd):/backup alpine tar czf /backup/minio_backup.tar.gz /data
```

#### Restore

```bash
# Restore database
docker-compose exec -T postgres psql -U viadocs viadocs_db < backup_20240101.sql

# Restore volumes
docker run --rm -v viadocs_postgres_data:/data -v $(pwd):/backup alpine tar xzf /backup/postgres_backup.tar.gz -C /
```

## Troubleshooting

### Services Not Starting

```bash
# View logs
docker-compose logs [service-name]

# View real-time logs
docker-compose logs -f backend

# Check status
docker-compose ps
```

### Backend Cannot Connect to Database

```bash
# Check if database is ready
docker-compose exec postgres pg_isready -U viadocs

# Check connection from backend
docker-compose exec backend python -c "from app.config import settings; print(settings.postgres_dsn)"
```

### Frontend Not Loading

```bash
# Check frontend container
docker-compose logs frontend

# Check nginx routing
docker-compose exec nginx nginx -t

# Reload nginx config
docker-compose exec nginx nginx -s reload
```

### Migration Errors

```bash
# Run migration manually
docker-compose exec backend alembic upgrade head

# View migration history
docker-compose exec backend alembic history

# Rollback if needed
docker-compose exec backend alembic downgrade -1
```

### Port Already in Use

```bash
# Find process using port
# Linux/Mac
lsof -i :80
lsof -i :443

# Windows
netstat -ano | findstr :80

# Change port in docker-compose.yml or stop other process
```

### SSL Certificate Errors

```bash
# Check certificate
docker-compose exec nginx openssl x509 -in /etc/letsencrypt/live/yourdomain.com/fullchain.pem -text -noout

# Test SSL config
docker-compose exec nginx nginx -t

# View SSL logs
docker-compose logs nginx | grep ssl
```

### Out of Memory

```bash
# Check memory usage
docker stats

# Reduce number of workers
# Edit .env:
OCR_WORKER_MAX_CONCURRENT=1
MAX_CONCURRENT_OCR_JOBS=2
```

### Complete Reset (⚠️ Data Loss)

```bash
# Stop and remove all
docker-compose down -v

# Remove images
docker-compose down --rmi all

# Start fresh
./start.sh
```

## Scaling

### Scale Backend

```bash
# Scale backend to 3 instances
docker-compose up -d --scale backend=3

# Nginx will automatically load balance
```

### Scale Workers

```bash
# Scale OCR workers
docker-compose up -d --scale ocr-worker=3
```

### Load Balancing

Nginx is configured with upstream and automatically load balances when scaling backend.

## Monitoring

### Health Checks

All services have health checks. Check with:

```bash
docker-compose ps
```

### Logs

```bash
# All logs
docker-compose logs

# Specific service
docker-compose logs backend
docker-compose logs frontend
docker-compose logs nginx

# Follow logs
docker-compose logs -f
```

### Metrics

Can integrate with:
- Prometheus + Grafana
- ELK Stack
- Datadog

## Support

If you encounter issues:

1. Check logs: `docker-compose logs [service]`
2. Check health: `docker-compose ps`
3. See troubleshooting section above
4. Create issue on GitHub repository

## References

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [ViolaDocs API Documentation](http://localhost/api/v1/docs)

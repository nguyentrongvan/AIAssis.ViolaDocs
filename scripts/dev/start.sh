#!/bin/bash
set -e

echo "=========================================="
echo "ViolaDocs Platform - Development Mode"
echo "=========================================="

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "[WARN] .env file not found!"
    echo "[INFO] Creating .env from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "[OK] Created .env file. Please edit it with your configuration."
        echo "   Then run this script again."
        exit 1
    else
        echo "[ERROR] .env.example not found! Please create .env file manually."
        exit 1
    fi
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "[ERROR] Docker is not running. Please start Docker and try again."
    exit 1
fi

# Determine docker-compose command
if docker compose version > /dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

echo ""
echo "[START] Starting ViolaDocs Platform in DEVELOPMENT mode..."
echo ""
echo "[NOTE] Note: Frontend and Backend will be accessible directly on their ports"
echo "   Frontend: http://localhost:${FRONTEND_PORT:-3000}"
echo "   Backend API: http://localhost:${BACKEND_PORT:-8000}"
echo "   API Docs: http://localhost:${BACKEND_PORT:-8000}/api/v1/docs"
echo ""

# Build and start all services (without nginx)
$DOCKER_COMPOSE -f docker/docker-compose.base.yml -f docker/dev/docker-compose.yml up -d --build

echo ""
echo "[WAIT] Waiting for services to be healthy..."
sleep 10

# Check service status
echo ""
echo "[STATUS] Service Status:"
$DOCKER_COMPOSE -f docker/docker-compose.base.yml -f docker/dev/docker-compose.yml ps

echo ""
echo "[OK] ViolaDocs Platform is running in DEVELOPMENT mode!"
echo ""
echo "[WEB] Access the application:"
echo "   Frontend: http://localhost:${FRONTEND_PORT:-3000}"
echo "   Backend API: http://localhost:${BACKEND_PORT:-8000}"
echo "   API Docs: http://localhost:${BACKEND_PORT:-8000}/api/v1/docs"
echo ""
echo "[NOTE] View logs: docker-compose -f docker/docker-compose.base.yml -f docker/dev/docker-compose.yml logs -f"
echo "[STOP] Stop services: ./scripts/dev/stop.sh"
echo ""


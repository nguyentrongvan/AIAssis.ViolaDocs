#!/bin/bash
set -e

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
cd "$PROJECT_ROOT"

echo "=========================================="
echo "ViolaDocs Platform - Startup Script"
echo "=========================================="

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
echo "[START] Starting ViolaDocs Platform..."
echo ""
echo "Select mode:"
echo "  1) Development (direct ports, no nginx)"
echo "  2) Production (nginx reverse proxy)"
echo ""
read -p "Enter choice [1-2] (default: 2): " mode
mode=${mode:-2}

if [ "$mode" = "1" ]; then
    echo ""
    echo "[NOTE] Starting in DEVELOPMENT mode..."
    echo "   Frontend: http://localhost:${FRONTEND_PORT:-3000}"
    echo "   Backend: http://localhost:${BACKEND_PORT:-8000}"
    echo ""
    $DOCKER_COMPOSE -f docker/docker-compose.base.yml -f docker/dev/docker-compose.yml up -d --build
else
    echo ""
    echo "[NOTE] Starting in PRODUCTION mode..."
    echo "   Access via: http://localhost"
    echo ""
    $DOCKER_COMPOSE -f docker/docker-compose.base.yml -f docker/prod/docker-compose.yml up -d --build
fi

echo ""
echo "[WAIT] Waiting for services to be healthy..."
sleep 10

# Check service status
echo ""
echo "[STATUS] Service Status:"
if [ "$mode" = "1" ]; then
    $DOCKER_COMPOSE -f docker/docker-compose.base.yml -f docker/dev/docker-compose.yml ps
else
    $DOCKER_COMPOSE -f docker/docker-compose.base.yml -f docker/prod/docker-compose.yml ps
fi

echo ""
echo "[OK] ViolaDocs Platform is starting!"
echo ""
if [ "$mode" = "1" ]; then
    echo "[WEB] Access the application:"
    echo "   Frontend: http://localhost:${FRONTEND_PORT:-3000}"
    echo "   Backend API: http://localhost:${BACKEND_PORT:-8000}"
    echo "   API Docs: http://localhost:${BACKEND_PORT:-8000}/api/v1/docs"
    echo ""
    echo "[NOTE] View logs: docker-compose -f docker/docker-compose.base.yml -f docker/dev/docker-compose.yml logs -f"
    echo "[STOP] Stop services: ./stop.sh or docker-compose -f docker/docker-compose.base.yml -f docker/dev/docker-compose.yml down"
else
    echo "[WEB] Access the application:"
    echo "   Frontend: http://localhost"
    echo "   Backend API: http://localhost/api/v1"
    echo "   API Docs: http://localhost/api/v1/docs"
    echo ""
    echo "[NOTE] View logs: docker-compose -f docker/docker-compose.base.yml -f docker/prod/docker-compose.yml logs -f"
    echo "[STOP] Stop services: ./stop.sh or docker-compose -f docker/docker-compose.base.yml -f docker/prod/docker-compose.yml down"
fi
echo ""


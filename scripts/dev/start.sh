#!/bin/bash
set -e

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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
        if cp .env.example .env; then
            echo -e "${GREEN}[✓ OK]${NC} Created .env file. Please edit it with your configuration."
            echo "   Then run this script again."
        else
            echo -e "${RED}[✗ ERROR]${NC} Failed to create .env file."
            exit 1
        fi
        exit 1
    else
        echo -e "${RED}[✗ ERROR]${NC} .env.example not found! Please create .env file manually."
        exit 1
    fi
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}[✗ ERROR]${NC} Docker is not running. Please start Docker and try again."
    exit 1
fi
echo -e "${GREEN}[✓ OK]${NC} Docker is running."
echo "[✓ OK] Docker is running."

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
if $DOCKER_COMPOSE -f docker/docker-compose.base.yml -f docker/dev/docker-compose.yml up -d --build; then
    echo -e "${GREEN}[✓ OK]${NC} Services started successfully."
else
    echo -e "${RED}[✗ ERROR]${NC} Failed to start services in DEVELOPMENT mode."
    exit 1
fi

echo ""
echo "[WAIT] Waiting for services to be healthy..."
sleep 10

# Check service status
echo ""
echo "[STATUS] Service Status:"
$DOCKER_COMPOSE -f docker/docker-compose.base.yml -f docker/dev/docker-compose.yml ps

echo ""
echo "[✓ OK] ViolaDocs Platform is running in DEVELOPMENT mode!"
echo ""
echo "[WEB] Access the application:"
echo "   Frontend: http://localhost:${FRONTEND_PORT:-3000}"
echo "   Backend API: http://localhost:${BACKEND_PORT:-8000}"
echo "   API Docs: http://localhost:${BACKEND_PORT:-8000}/api/v1/docs"
echo ""
echo "[NOTE] View logs: docker-compose -f docker/docker-compose.base.yml -f docker/dev/docker-compose.yml logs -f"
echo "[STOP] Stop services: ./scripts/dev/stop.sh"
echo ""


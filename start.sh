#!/bin/bash
set -e

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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

echo ""
echo "Build options:"
echo "  1) Normal build (use cache)"
echo "  2) Force rebuild (no cache - slower but ensures fresh build)"
echo ""
read -p "Enter build option [1-2] (default: 1): " build_option
build_option=${build_option:-1}

BUILD_FLAGS="--build"
if [ "$build_option" = "2" ]; then
    BUILD_FLAGS="--build --no-cache"
    echo -e "${YELLOW}[INFO]${NC} Force rebuild enabled (no cache)"
fi

if [ "$mode" = "1" ]; then
    echo ""
    echo "[NOTE] Starting in DEVELOPMENT mode..."
    echo "   Frontend: http://localhost:${FRONTEND_PORT:-3000}"
    echo "   Backend: http://localhost:${BACKEND_PORT:-8000}"
    echo ""
    if $DOCKER_COMPOSE -f docker/docker-compose.base.yml -f docker/dev/docker-compose.yml up -d $BUILD_FLAGS; then
        echo -e "${GREEN}[✓ OK]${NC} Services started successfully in DEVELOPMENT mode."
    else
        echo -e "${RED}[✗ ERROR]${NC} Failed to start services in DEVELOPMENT mode."
        exit 1
    fi
else
    echo ""
    echo "[NOTE] Starting in PRODUCTION mode..."
    echo "   Access via: http://localhost"
    echo ""
    if $DOCKER_COMPOSE -f docker/docker-compose.base.yml -f docker/prod/docker-compose.yml up -d $BUILD_FLAGS; then
        echo -e "${GREEN}[✓ OK]${NC} Services started successfully in PRODUCTION mode."
    else
        echo -e "${RED}[✗ ERROR]${NC} Failed to start services in PRODUCTION mode."
        exit 1
    fi
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
echo -e "${GREEN}[✓ OK]${NC} ViolaDocs Platform is starting!"
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


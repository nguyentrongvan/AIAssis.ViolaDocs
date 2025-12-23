#!/bin/bash
set -e

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "ViolaDocs Platform - Stop Production Mode"
echo "=========================================="

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# Determine docker-compose command
if docker compose version > /dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

echo ""
echo "[STOP] Stopping ViolaDocs Platform (Production mode)..."
echo ""

# Stop all services
if $DOCKER_COMPOSE -f docker/docker-compose.base.yml -f docker/prod/docker-compose.yml down; then
    echo -e "${GREEN}[✓ OK]${NC} All services stopped successfully!"
else
    echo -e "${RED}[✗ ERROR]${NC} Failed to stop services."
    exit 1
fi

echo ""
echo -e "${GREEN}[✓ OK]${NC} All services stopped!"
echo ""


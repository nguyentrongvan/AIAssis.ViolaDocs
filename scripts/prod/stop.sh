#!/bin/bash
set -e

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
$DOCKER_COMPOSE -f docker/docker-compose.base.yml -f docker/prod/docker-compose.yml down

echo ""
echo "[OK] All services stopped!"
echo ""


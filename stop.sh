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
echo "ViolaDocs Platform - Stop Script"
echo "=========================================="

# Determine docker-compose command
if docker compose version > /dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

echo ""
echo "[STOP] Stopping ViolaDocs Platform..."
echo ""
echo "Select mode to stop:"
echo "  1) Development"
echo "  2) Production"
echo "  3) Both (all running containers)"
echo ""
read -p "Enter choice [1-3] (default: 3): " mode
mode=${mode:-3}

if [ "$mode" = "1" ]; then
    echo "Stopping Development mode..."
    if $DOCKER_COMPOSE -f docker/docker-compose.base.yml -f docker/dev/docker-compose.yml down; then
        echo -e "${GREEN}[✓ OK]${NC} Development services stopped successfully."
    else
        echo -e "${RED}[✗ ERROR]${NC} Failed to stop Development services."
        exit 1
    fi
elif [ "$mode" = "2" ]; then
    echo "Stopping Production mode..."
    if $DOCKER_COMPOSE -f docker/docker-compose.base.yml -f docker/prod/docker-compose.yml down; then
        echo -e "${GREEN}[✓ OK]${NC} Production services stopped successfully."
    else
        echo -e "${RED}[✗ ERROR]${NC} Failed to stop Production services."
        exit 1
    fi
else
    echo "Stopping all containers..."
    $DOCKER_COMPOSE -f docker/docker-compose.base.yml -f docker/dev/docker-compose.yml down 2>/dev/null || true
    $DOCKER_COMPOSE -f docker/docker-compose.base.yml -f docker/prod/docker-compose.yml down 2>/dev/null || true
    echo -e "${GREEN}[✓ OK]${NC} All services stopped successfully."
fi

echo ""
echo -e "${GREEN}[✓ OK]${NC} All services stopped!"
echo ""
echo "[TIP] To remove volumes (data will be lost):"
echo "   docker-compose -f docker/docker-compose.base.yml -f docker/dev/docker-compose.yml down -v"
echo "   docker-compose -f docker/docker-compose.base.yml -f docker/prod/docker-compose.yml down -v"
echo ""


#!/bin/bash
set -e

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
echo "🛑 Stopping ViolaDocs Platform..."
echo ""

# Stop all services
$DOCKER_COMPOSE down

echo ""
echo "✅ All services stopped!"
echo ""
echo "💡 To remove volumes (data will be lost):"
echo "   docker-compose down -v"
echo ""


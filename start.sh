#!/bin/bash
set -e

echo "=========================================="
echo "ViolaDocs Platform - Startup Script"
echo "=========================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "📋 Creating .env from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ Created .env file. Please edit it with your configuration."
        echo "   Then run this script again."
        exit 1
    else
        echo "❌ .env.example not found! Please create .env file manually."
        exit 1
    fi
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose > /dev/null 2>&1 && ! docker compose version > /dev/null 2>&1; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose."
    exit 1
fi

# Determine docker-compose command
if docker compose version > /dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

echo ""
echo "🚀 Starting ViolaDocs Platform..."
echo ""

# Build and start all services
$DOCKER_COMPOSE up -d --build

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service status
echo ""
echo "📊 Service Status:"
$DOCKER_COMPOSE ps

echo ""
echo "✅ ViolaDocs Platform is starting!"
echo ""
echo "🌐 Access the application:"
echo "   Frontend: http://localhost"
echo "   Backend API: http://localhost/api/v1"
echo "   API Docs: http://localhost/api/v1/docs"
echo ""
echo "📝 View logs: docker-compose logs -f"
echo "🛑 Stop services: ./stop.sh or docker-compose down"
echo ""


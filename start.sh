#!/bin/bash
# ============================================================================
# Local Audit Agent - Docker Startup Script
# ============================================================================
# Usage: ./start.sh [dev|prod]
# Default: dev (development mode)

set -e

ENVIRONMENT=${1:-dev}
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "============================================================================"
echo "  🐳 Local Audit Agent - Docker Startup"
echo "============================================================================"
echo ""
echo "Environment: $ENVIRONMENT"
echo "Project Directory: $PROJECT_DIR"
echo ""

# Change to project directory
cd "$PROJECT_DIR"

# Check Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Compose first."
    echo "   Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✓ Docker and Docker Compose found"
echo ""

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ .env created (update with your values)"
    echo ""
fi

# Start services based on environment
if [ "$ENVIRONMENT" = "prod" ]; then
    echo "🚀 Starting production environment..."
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
else
    echo "🚀 Starting development environment..."
    docker-compose up -d
fi

echo ""
echo "✓ All containers started!"
echo ""

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service status
echo ""
echo "============================================================================"
echo "  📊 Service Status"
echo "============================================================================"
docker-compose ps

echo ""
echo "============================================================================"
echo "  🌐 Access Points"
echo "============================================================================"
echo ""
echo "  Frontend:     http://localhost:3000"
echo "  Backend API:  http://localhost:8000"
echo "  API Docs:     http://localhost:8000/docs"
echo "  pgAdmin:      http://localhost:5050"
echo "  Ollama:       http://localhost:11434"
echo ""
echo "  Default Login: admin@example.com / password"
echo ""

echo "============================================================================"
echo "  📚 Useful Commands"
echo "============================================================================"
echo ""
echo "  View logs:        docker-compose logs -f [service]"
echo "  Stop services:    docker-compose down"
echo "  Restart service:  docker-compose restart [service]"
echo "  Access bash:      docker-compose exec [service] bash"
echo ""

echo "✅ Local Audit Agent is ready!"
echo ""

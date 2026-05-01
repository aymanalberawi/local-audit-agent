#!/bin/bash
# ============================================================================
# Local Audit Agent - Docker Shutdown Script
# ============================================================================
# Usage: ./stop.sh [--full]
# --full: Also removes all volumes (DELETES DATA!)

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FULL_RESET=${1:-}

echo "============================================================================"
echo "  🛑 Local Audit Agent - Docker Shutdown"
echo "============================================================================"
echo ""

cd "$PROJECT_DIR"

if [ "$FULL_RESET" = "--full" ]; then
    echo "⚠️  WARNING: This will DELETE ALL DATA (audits, database, uploads)"
    read -p "Are you sure? Type 'yes' to continue: " confirm
    
    if [ "$confirm" = "yes" ]; then
        echo ""
        echo "🗑️  Removing all containers and volumes..."
        docker-compose down -v
        echo "✓ All data deleted"
    else
        echo "Cancelled"
        exit 0
    fi
else
    echo "🛑 Stopping all containers (data preserved)..."
    docker-compose down
    echo "✓ All containers stopped"
fi

echo ""
echo "✅ Shutdown complete"
echo ""
echo "To restart: ./start.sh"
echo ""

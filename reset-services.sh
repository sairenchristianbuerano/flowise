#!/bin/bash

# Script to reset and restart Flowise Component Factory services
# Use this if you encounter startup issues with Docker volumes/permissions
#
# Usage:
#   ./reset-services.sh           # Standard reset (uses cache)
#   ./reset-services.sh --no-cache # Full rebuild from scratch

set -e

# Parse arguments
NO_CACHE_FLAG=""
if [ "$1" == "--no-cache" ]; then
    NO_CACHE_FLAG="--no-cache"
    echo "Running with --no-cache (full rebuild)"
fi

echo "=========================================="
echo "Flowise Component Factory - Reset Script"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ ERROR: .env file not found!"
    echo "Please create .env file with your ANTHROPIC_API_KEY"
    echo "You can copy from .env.example:"
    echo "  cp .env.example .env"
    echo ""
    exit 1
fi

echo "✓ .env file found"
echo ""

# Step 1: Stop and remove containers
echo "📦 Step 1: Stopping and removing containers..."
docker-compose down -v 2>/dev/null || true
echo "✓ Containers stopped"
echo ""

# Step 2: Clean up volumes
echo "🗑️  Step 2: Cleaning up volumes..."
docker volume rm flowise_component_data 2>/dev/null || true
docker volume rm flowise_index_data 2>/dev/null || true
echo "✓ Volumes cleaned"
echo ""

# Step 3: Rebuild services
echo "🔨 Step 3: Rebuilding services (this may take a few minutes)..."
if [ -n "$NO_CACHE_FLAG" ]; then
    docker-compose build --no-cache
else
    docker-compose build
fi
echo "✓ Services rebuilt"
echo ""

# Step 4: Start services
echo "🚀 Step 4: Starting services..."
docker-compose up -d
echo "✓ Services started"
echo ""

# Step 5: Wait for services to be healthy
echo "⏳ Step 5: Waiting for services to become healthy..."
echo "   (This may take 2-3 minutes on first startup while downloading embedding models)"
sleep 5

MAX_WAIT=180
ELAPSED=0
ALL_HEALTHY=false

while [ $ELAPSED -lt $MAX_WAIT ]; do
    COMPONENT_INDEX_HEALTH=$(docker-compose ps component-index 2>/dev/null | grep -c "healthy" || echo "0")
    COMPONENT_GEN_HEALTH=$(docker-compose ps component-generator 2>/dev/null | grep -c "healthy" || echo "0")

    if [ "$COMPONENT_INDEX_HEALTH" -eq "1" ] && [ "$COMPONENT_GEN_HEALTH" -eq "1" ]; then
        echo "✓ All services are healthy!"
        ALL_HEALTHY=true
        break
    fi

    echo "  Waiting... ($ELAPSED seconds elapsed)"
    sleep 5
    ELAPSED=$((ELAPSED + 5))
done

if [ "$ALL_HEALTHY" = false ]; then
    echo "⚠️  Services did not become healthy within $MAX_WAIT seconds"
    echo "   They may still be initializing. Check status below and logs if needed."
fi

echo ""
echo "=========================================="
echo "Status Check"
echo "=========================================="
docker-compose ps
echo ""

# Test endpoints
echo "=========================================="
echo "Testing Endpoints"
echo "=========================================="

echo "Component Index Health:"
curl -s http://localhost:8086/api/flowise/component-index/health | jq '.' 2>/dev/null || echo "❌ Service not responding"
echo ""

echo "Component Generator Health:"
curl -s http://localhost:8085/api/flowise/component-generator/health | jq '.' 2>/dev/null || echo "❌ Service not responding"
echo ""

echo "=========================================="
echo "✅ Reset Complete!"
echo "=========================================="
echo ""
echo "Services are available at:"
echo "  - Component Index:     http://localhost:8086"
echo "  - Component Generator: http://localhost:8085"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f"
echo ""

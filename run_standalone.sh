#!/bin/bash
# Flowise Services - Standalone Run Script
# Starts both component-index and component-generator services

set -e

echo "=============================================="
echo "Flowise Services - Standalone Mode"
echo "=============================================="
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# PID files
INDEX_PID_FILE="$SCRIPT_DIR/.component-index.pid"
GENERATOR_PID_FILE="$SCRIPT_DIR/.component-generator.pid"

# Log files
INDEX_LOG="$SCRIPT_DIR/component-index.log"
GENERATOR_LOG="$SCRIPT_DIR/component-generator.log"

# Check if services are already running
if [ -f "$INDEX_PID_FILE" ] && kill -0 $(cat "$INDEX_PID_FILE") 2>/dev/null; then
    echo "⚠ Component Index is already running (PID: $(cat $INDEX_PID_FILE))"
    echo "  Run ./stop_standalone.sh first to stop existing services"
    exit 1
fi

if [ -f "$GENERATOR_PID_FILE" ] && kill -0 $(cat "$GENERATOR_PID_FILE") 2>/dev/null; then
    echo "⚠ Component Generator is already running (PID: $(cat $GENERATOR_PID_FILE))"
    echo "  Run ./stop_standalone.sh first to stop existing services"
    exit 1
fi

# Load environment variables
if [ -f ".env.standalone" ]; then
    echo "✓ Loading environment from .env.standalone"
    export $(grep -v '^#' .env.standalone | xargs)
elif [ -f ".env" ]; then
    echo "✓ Loading environment from .env"
    export $(grep -v '^#' .env | xargs)
else
    echo "⚠ No .env.standalone or .env file found"
fi

# Set default environment variables
export COMPONENT_RAG_URL="${COMPONENT_RAG_URL:-http://localhost:8086}"
export PORT_INDEX="${PORT_INDEX:-8086}"
export PORT_GENERATOR="${PORT_GENERATOR:-8085}"

# Check required dependencies
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo ""
    echo "❌ ERROR: ANTHROPIC_API_KEY is required"
    echo ""
    echo "Set it in .env.standalone:"
    echo "  ANTHROPIC_API_KEY=your_key_here"
    echo ""
    exit 1
fi

# Check if venvs exist
if [ ! -d "component-index/venv" ]; then
    echo "❌ ERROR: component-index/venv not found"
    echo "   Run ./setup_standalone.sh first"
    exit 1
fi

if [ ! -d "component-generator/venv" ]; then
    echo "❌ ERROR: component-generator/venv not found"
    echo "   Run ./setup_standalone.sh first"
    exit 1
fi

echo ""
echo "Configuration:"
echo "  Component Index Port: $PORT_INDEX"
echo "  Component Generator Port: $PORT_GENERATOR"
echo "  RAG URL: $COMPONENT_RAG_URL"
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo "Shutting down services..."
    ./stop_standalone.sh
}

trap cleanup EXIT INT TERM

# Start Component Index
echo "=============================================="
echo "Starting Component Index Service"
echo "=============================================="
echo ""

cd component-index
if [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate  # Windows
else
    source venv/bin/activate  # Linux/Mac
fi

export PORT=$PORT_INDEX
export STORAGE_PATH=./data/components
export FLOWISE_COMPONENTS_DIR=./data/flowise_components
export CHROMADB_DIR=./data/chromadb

echo "Starting on port $PORT_INDEX..."
nohup python src/service.py > "$INDEX_LOG" 2>&1 &
INDEX_PID=$!
echo $INDEX_PID > "$INDEX_PID_FILE"

deactivate
cd "$SCRIPT_DIR"

echo "✓ Component Index started (PID: $INDEX_PID)"
echo "  Logs: $INDEX_LOG"
echo ""

# Wait for component-index to be healthy
echo "Waiting for Component Index to become healthy..."
for i in {1..30}; do
    if curl -s http://localhost:$PORT_INDEX/api/flowise/component-index/health > /dev/null 2>&1; then
        echo "✓ Component Index is healthy"
        break
    fi

    if [ $i -eq 30 ]; then
        echo "❌ Component Index failed to start within 30 seconds"
        echo "   Check logs: tail -f $INDEX_LOG"
        exit 1
    fi

    sleep 1
    echo -n "."
done

echo ""

# Start Component Generator
echo "=============================================="
echo "Starting Component Generator Service"
echo "=============================================="
echo ""

cd component-generator
if [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate  # Windows
else
    source venv/bin/activate  # Linux/Mac
fi

export PORT=$PORT_GENERATOR
export COMPONENT_RAG_URL=$COMPONENT_RAG_URL

echo "Starting on port $PORT_GENERATOR..."
nohup python src/service.py > "$GENERATOR_LOG" 2>&1 &
GENERATOR_PID=$!
echo $GENERATOR_PID > "$GENERATOR_PID_FILE"

deactivate
cd "$SCRIPT_DIR"

echo "✓ Component Generator started (PID: $GENERATOR_PID)"
echo "  Logs: $GENERATOR_LOG"
echo ""

# Wait for component-generator to be healthy
echo "Waiting for Component Generator to become healthy..."
for i in {1..30}; do
    if curl -s http://localhost:$PORT_GENERATOR/api/flowise/component-generator/health > /dev/null 2>&1; then
        echo "✓ Component Generator is healthy"
        break
    fi

    if [ $i -eq 30 ]; then
        echo "❌ Component Generator failed to start within 30 seconds"
        echo "   Check logs: tail -f $GENERATOR_LOG"
        exit 1
    fi

    sleep 1
    echo -n "."
done

echo ""
echo "=============================================="
echo "All Services Running!"
echo "=============================================="
echo ""
echo "Component Index:      http://localhost:$PORT_INDEX"
echo "Component Generator:  http://localhost:$PORT_GENERATOR"
echo ""
echo "Logs:"
echo "  Component Index:     tail -f $INDEX_LOG"
echo "  Component Generator: tail -f $GENERATOR_LOG"
echo ""
echo "To stop services: ./stop_standalone.sh"
echo ""
echo "Press Ctrl+C to stop all services and exit..."
echo ""

# Keep script running and tail logs
trap cleanup EXIT INT TERM
tail -f "$INDEX_LOG" -f "$GENERATOR_LOG"

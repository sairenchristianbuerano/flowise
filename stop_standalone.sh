#!/bin/bash
# Flowise Services - Standalone Stop Script
# Stops both component-index and component-generator services

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# PID files
INDEX_PID_FILE="$SCRIPT_DIR/.component-index.pid"
GENERATOR_PID_FILE="$SCRIPT_DIR/.component-generator.pid"

echo "=============================================="
echo "Stopping Flowise Services"
echo "=============================================="
echo ""

# Stop Component Generator
if [ -f "$GENERATOR_PID_FILE" ]; then
    GENERATOR_PID=$(cat "$GENERATOR_PID_FILE")

    if kill -0 "$GENERATOR_PID" 2>/dev/null; then
        echo "Stopping Component Generator (PID: $GENERATOR_PID)..."
        kill "$GENERATOR_PID"

        # Wait for process to stop
        for i in {1..10}; do
            if ! kill -0 "$GENERATOR_PID" 2>/dev/null; then
                break
            fi
            sleep 1
        done

        # Force kill if still running
        if kill -0 "$GENERATOR_PID" 2>/dev/null; then
            echo "  Force killing..."
            kill -9 "$GENERATOR_PID" 2>/dev/null || true
        fi

        echo "✓ Component Generator stopped"
    else
        echo "⚠ Component Generator not running (stale PID file)"
    fi

    rm -f "$GENERATOR_PID_FILE"
else
    echo "⚠ Component Generator PID file not found"
fi

# Stop Component Index
if [ -f "$INDEX_PID_FILE" ]; then
    INDEX_PID=$(cat "$INDEX_PID_FILE")

    if kill -0 "$INDEX_PID" 2>/dev/null; then
        echo "Stopping Component Index (PID: $INDEX_PID)..."
        kill "$INDEX_PID"

        # Wait for process to stop
        for i in {1..10}; do
            if ! kill -0 "$INDEX_PID" 2>/dev/null; then
                break
            fi
            sleep 1
        done

        # Force kill if still running
        if kill -0 "$INDEX_PID" 2>/dev/null; then
            echo "  Force killing..."
            kill -9 "$INDEX_PID" 2>/dev/null || true
        fi

        echo "✓ Component Index stopped"
    else
        echo "⚠ Component Index not running (stale PID file)"
    fi

    rm -f "$INDEX_PID_FILE"
else
    echo "⚠ Component Index PID file not found"
fi

echo ""
echo "✓ All services stopped"
echo ""

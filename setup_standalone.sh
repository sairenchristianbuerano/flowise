#!/bin/bash
# Flowise Services - Standalone Setup Script
# Creates virtual environments and installs dependencies for both services

set -e

echo "=============================================="
echo "Flowise Services - Standalone Setup"
echo "=============================================="
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ ERROR: Python 3 is not installed"
    echo "   Please install Python 3.11 or higher"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

echo "✓ Found Python $PYTHON_VERSION"

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
    echo "⚠ WARNING: Python 3.11+ is recommended (you have $PYTHON_VERSION)"
    echo ""
fi

# Check pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ ERROR: pip3 is not installed"
    exit 1
fi

echo "✓ Found pip $(pip3 --version | awk '{print $2}')"
echo ""

# Setup Component Index
echo "=============================================="
echo "Setting up Component Index Service"
echo "=============================================="
echo ""

cd component-index

if [ -d "venv" ]; then
    echo "⚠ venv already exists, removing..."
    rm -rf venv
fi

echo "Creating virtual environment..."
python3 -m venv venv

echo "Activating virtual environment..."
if [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate  # Windows
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate  # Linux/Mac
else
    echo "❌ ERROR: Could not find venv activation script"
    exit 1
fi

echo "Upgrading pip..."
pip install --upgrade pip --quiet || echo "⚠ Pip upgrade skipped"

echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

# Pre-download sentence transformer model
echo "Pre-downloading sentence transformer model (this may take a minute)..."
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')" 2>/dev/null || echo "⚠ Model download skipped"

deactivate
echo "✓ Component Index setup complete"
echo ""

cd "$SCRIPT_DIR"

# Setup Component Generator
echo "=============================================="
echo "Setting up Component Generator Service"
echo "=============================================="
echo ""

cd component-generator

if [ -d "venv" ]; then
    echo "⚠ venv already exists, removing..."
    rm -rf venv
fi

echo "Creating virtual environment..."
python3 -m venv venv

echo "Activating virtual environment..."
if [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate  # Windows
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate  # Linux/Mac
else
    echo "❌ ERROR: Could not find venv activation script"
    exit 1
fi

echo "Upgrading pip..."
pip install --upgrade pip --quiet || echo "⚠ Pip upgrade skipped"

echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

deactivate
echo "✓ Component Generator setup complete"
echo ""

cd "$SCRIPT_DIR"

# Create data directories
echo "=============================================="
echo "Creating data directories"
echo "=============================================="
echo ""

mkdir -p component-index/data/components
mkdir -p component-index/data/chromadb
mkdir -p component-index/data/flowise_components
mkdir -p component-generator/data
echo "✓ Data directories created"
echo ""

# Create .env.standalone if it doesn't exist
if [ ! -f ".env.standalone" ]; then
    if [ -f ".env.standalone.example" ]; then
        echo "Creating .env.standalone from example..."
        cp .env.standalone.example .env.standalone
        echo "⚠ IMPORTANT: Edit .env.standalone and add your ANTHROPIC_API_KEY"
    else
        echo "⚠ No .env.standalone.example found, skipping .env creation"
    fi
else
    echo "✓ .env.standalone already exists"
fi

echo ""
echo "=============================================="
echo "Setup Complete!"
echo "=============================================="
echo ""
echo "Next steps:"
echo "  1. Edit .env.standalone and add your ANTHROPIC_API_KEY"
echo "  2. Run: ./run_standalone.sh"
echo ""
echo "Virtual environments created at:"
echo "  - component-index/venv"
echo "  - component-generator/venv"
echo ""

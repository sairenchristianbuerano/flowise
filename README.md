# Flowise Component Generator & Index

Backend services for generating and managing custom Flowise components.

## 📋 Overview

This repository contains two microservices specifically for Flowise platform:

1. **Component Generator** - Generates custom Flowise component code from YAML specifications
2. **Component Index** - Tracks and manages generated components

Both services are **separate from the main teamsflow** multi-agent system and focus exclusively on Flowise component development.

---

## 🏗️ Architecture

```
flowise/
├── component-generator/      # Code generation service
│   ├── src/
│   │   ├── service.py        # FastAPI endpoints
│   │   ├── flowise_agent.py  # Core generator logic
│   │   ├── flowise_validator.py
│   │   └── flowise_feasibility_checker.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── component-index/          # Component registry service
│   ├── src/
│   │   ├── service.py        # FastAPI endpoints
│   │   ├── models.py         # Data models
│   │   └── storage.py        # JSON-based storage
│   ├── Dockerfile
│   └── requirements.txt
│
└── docker-compose.yml        # Service orchestration
```

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Anthropic API key (for Claude)

### 1. Set Environment Variables

Create a `.env` file:

```bash
# Required: Claude API key for code generation
ANTHROPIC_API_KEY=your_api_key_here

# Optional: Claude model selection
CLAUDE_MODEL=claude-sonnet-4-20250514

# Optional: RAG service URL (if available)
COMPONENT_RAG_URL=http://rag-service:8088
```

### 2. Start Services

```bash
# Build and start both services
docker-compose up -d

# Check logs
docker-compose logs -f

# Verify services are healthy
curl http://localhost:8085/api/flowise/component-generator/health
curl http://localhost:8086/api/flowise/component-index/health
```

### 3. Stop Services

```bash
docker-compose down
```

---

## 📡 API Endpoints

### Component Generator (Port 8085)

#### Health Check
```bash
GET /api/flowise/component-generator/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "flowise-component-generator",
  "version": "1.0.0"
}
```

#### Generate Component
```bash
POST /api/flowise/generate
Content-Type: application/json

{
  "spec_yaml": "<YAML specification string>"
}
```

**Example Request:**
```bash
curl -X POST http://localhost:8085/api/flowise/generate \
  -H "Content-Type: application/json" \
  -d '{
    "spec_yaml": "name: CalculatorTool\ndisplay_name: Calculator\ndescription: Perform basic calculations\ncategory: tools\nplatforms:\n  - flowise\nrequirements:\n  - Evaluate mathematical expressions"
  }'
```

**Response:**
```json
{
  "component_code": "import { INode, INodeData... }",
  "component_config": {
    "name": "CalculatorTool",
    "label": "Calculator",
    "category": "Tools"
  },
  "dependencies": [],
  "validation": {
    "is_valid": true,
    "errors": [],
    "warnings": []
  },
  "deployment_instructions": { ... }
}
```

#### Assess Feasibility
```bash
POST /api/flowise/assess
Content-Type: application/json

{
  "spec_yaml": "<YAML specification string>"
}
```

**Response:**
```json
{
  "feasible": true,
  "confidence": "high",
  "complexity": "medium",
  "issues": [],
  "suggestions": ["Good pattern matches found in knowledge base"]
}
```

---

### Component Index (Port 8086)

#### Health Check
```bash
GET /api/flowise/component-index/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "flowise-component-index",
  "version": "1.0.0",
  "stats": {
    "total_components": 15,
    "by_platform": {"flowise": 15},
    "by_category": {"tools": 10, "utilities": 5}
  }
}
```

#### Register Component
```bash
POST /api/flowise/components/register
Content-Type: application/json

{
  "name": "CalculatorTool",
  "display_name": "Calculator",
  "description": "Perform basic calculations",
  "category": "tools",
  "platform": "flowise",
  "version": "1.0.0",
  "author": "Component Factory",
  "code_size": 2048,
  "dependencies": [],
  "validation_passed": true,
  "deployment_status": null
}
```

**Response:**
```json
{
  "component_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "CalculatorTool",
  "display_name": "Calculator",
  "created_at": "2025-11-26T10:00:00.000Z",
  "status": "generated",
  ...
}
```

#### List Components
```bash
GET /api/flowise/components?platform=flowise&category=tools&limit=10&offset=0
```

**Response:**
```json
{
  "total": 15,
  "components": [
    {
      "component_id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "CalculatorTool",
      "display_name": "Calculator",
      "created_at": "2025-11-26T10:00:00.000Z",
      ...
    }
  ]
}
```

#### Get Component by ID
```bash
GET /api/flowise/components/{component_id}
```

#### Get Component by Name
```bash
GET /api/flowise/components/name/{name}
```

#### Update Deployment Status
```bash
PATCH /api/flowise/components/{component_id}/deployment?status=deployed
```

#### Delete Component
```bash
DELETE /api/flowise/components/{component_id}
```

#### Get Statistics
```bash
GET /api/flowise/components/stats
```

---

## 📝 YAML Specification Format

Component specifications use YAML format:

```yaml
# Required fields
name: ComponentName              # PascalCase
display_name: "Component Name"
description: "What the component does"
category: tools                  # tools, utilities, agents, etc.

# Platform specification
platforms:
  - flowise

# Functional requirements
requirements:
  - "Requirement 1"
  - "Requirement 2"

# Optional fields
dependencies:
  - "expr-eval"

inputs:
  - name: inputParam
    label: "Input Parameter"
    type: string
    placeholder: "Enter value..."

outputs:
  - name: result
    type: string

# Component metadata
author: "Component Factory"
version: "1.0.0"
icon: "tool.svg"
```

---

## 🔧 Development

### Running Locally (Without Docker)

#### Component Generator

```bash
cd component-generator

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export ANTHROPIC_API_KEY=your_key_here

# Run service
python src/service.py
```

Service runs on http://localhost:8085

#### Component Index

```bash
cd component-index

# Install dependencies
pip install -r requirements.txt

# Run service
python src/service.py
```

Service runs on http://localhost:8086

---

## 🔗 Integration with teamsflow

While this repository is separate from teamsflow, it can integrate with:

- **tf-flowise-dev-env**: Optional deployment target for generated components
- **RAG Service**: For retrieving similar component patterns
- **Deployment scripts**: Located in teamsflow repo (`scripts/deploy_component.py`)

---

## 📦 Deployment to Flowise

Generated components can be **optionally** deployed to `tf-flowise-dev-env` (from teamsflow repo):

### Option 1: Manual Deployment

1. Generate component using `POST /api/flowise/generate`
2. Copy `component_code` from response
3. Save to `teamsflow/data/flowise-custom-components/ComponentName/ComponentName.js`
4. Restart tf-flowise-dev-env: `docker restart tf-flowise-dev-env`

### Option 2: Using Deployment Script

```bash
# From teamsflow repository
python scripts/deploy_component.py component_spec.yaml
```

---

## 🧪 Testing

### Test Component Generation

```bash
# Create test spec file
cat > test_spec.yaml << 'EOF'
name: TestTool
display_name: "Test Tool"
description: "Simple test tool"
category: tools
platforms:
  - flowise
requirements:
  - "Echo input back to user"
EOF

# Convert to JSON with spec_yaml field
curl -X POST http://localhost:8085/api/flowise/generate \
  -H "Content-Type: application/json" \
  -d "{\"spec_yaml\": \"$(cat test_spec.yaml | sed 's/$/\\n/' | tr -d '\n')\"}"
```

### Test Component Index

```bash
# Register a component
curl -X POST http://localhost:8086/api/flowise/components/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "TestComponent",
    "display_name": "Test",
    "description": "Test component",
    "category": "tools",
    "platform": "flowise",
    "author": "Test",
    "code_size": 1024,
    "validation_passed": true
  }'

# List all components
curl http://localhost:8086/api/flowise/components

# Get stats
curl http://localhost:8086/api/flowise/components/stats
```

---

## 📊 Monitoring

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f component-generator
docker-compose logs -f component-index
```

### Check Health

```bash
# Component Generator
curl http://localhost:8085/api/flowise/component-generator/health

# Component Index (includes stats)
curl http://localhost:8086/api/flowise/component-index/health
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart component-generator
docker-compose restart component-index
```

---

## 🗂️ Data Storage

### Component Index Storage

- **Location**: Docker volume `index_data`
- **Format**: JSON file (`/app/data/components/index.json`)
- **Backup**: Copy from container or mount local directory

```bash
# Backup index
docker cp flowise-component-index:/app/data/components/index.json ./backup_index.json

# Restore index
docker cp ./backup_index.json flowise-component-index:/app/data/components/index.json
```

---

## 🛠️ Troubleshooting

### Component Generator Not Responding

```bash
# Check logs
docker-compose logs component-generator

# Common issues:
# - Missing ANTHROPIC_API_KEY
# - Invalid Claude API key
# - RAG service not accessible (warning, not error)
```

### Component Index Errors

```bash
# Check logs
docker-compose logs component-index

# Verify storage
docker exec flowise-component-index ls -la /app/data/components/
```

### Port Conflicts

```bash
# Change ports in docker-compose.yml if 8085 or 8086 are in use
ports:
  - "9085:8085"  # Use port 9085 instead
```

---

## 📚 Related Documentation

- [Flowise Documentation](https://docs.flowiseai.com)
- [teamsflow Repository](../ian/teamsflow) - Multi-agent system
- [Phase 2A Findings](../ian/teamsflow/PHASE_2A_FINDINGS.md) - Component development insights

---

## 🆘 Support

For issues or questions:

1. Check logs: `docker-compose logs -f`
2. Verify health endpoints
3. Ensure API keys are set correctly
4. Review YAML specification format

---

## 📄 License

MIT

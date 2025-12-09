# Flowise Services - API Documentation

Complete API reference for Component Generator and Component Index services.

**Services:**
- **Component Generator**: Port 8085
- **Component Index**: Port 8086

📖 **[Back to README](README.md)**

---

## Table of Contents

- [Component Generator API](#component-generator-api)
- [Component Index API](#component-index-api)
- [YAML Specification Format](#yaml-specification-format)
- [Testing Examples](#testing-examples)

---

## Component Generator API

**Base URL:** `http://localhost:8085`

### Health Check

**Endpoint:** `GET /api/flowise/component-generator/health`

**Response:**
```json
{
  "status": "healthy",
  "service": "flowise-component-generator",
  "version": "1.0.0"
}
```

---

### Generate Component

**Endpoint:** `POST /api/flowise/component-generator/generate`

**Request Body:**
```json
{
  "spec": "<YAML specification string>"
}
```

**Example Request:**
```bash
curl -X POST http://localhost:8085/api/flowise/component-generator/generate \
  -H "Content-Type: application/json" \
  -d '{
    "spec": "name: CalculatorTool\ndisplay_name: Calculator\ndescription: Perform basic calculations\ncategory: tools\nplatforms:\n  - flowise\nrequirements:\n  - Evaluate mathematical expressions"
  }'
```

**Response:**
```json
{
  "code": "import { INode, INodeData, INodeParams } from '../../../src/Interface'...",
  "documentation": "# Calculator Tool\n\nA tool for performing basic calculations..."
}
```

**Response Fields:**
- `code` (string): Generated TypeScript/JavaScript component code
- `documentation` (string): Component usage documentation in Markdown format

---

### Generate Sample Component

**Endpoint:** `POST /api/flowise/component-generator/generate/sample`

Generates a sample component using built-in specification file. No request body required.

**Example Request:**
```bash
curl -X POST http://localhost:8085/api/flowise/component-generator/generate/sample \
  -H "Content-Type: application/json"
```

**Response:** Same format as `/generate` endpoint

---

### Assess Feasibility

**Endpoint:** `POST /api/flowise/component-generator/assess`

Assess whether a component can be generated before attempting generation.

**Request Body:**
```json
{
  "spec": "<YAML specification string>"
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

**Response Fields:**
- `feasible` (boolean): Whether generation is feasible
- `confidence` (string): Confidence level - "high", "medium", "low", or "blocked"
- `complexity` (string): Estimated complexity - "low", "medium", or "high"
- `issues` (array): List of potential issues
- `suggestions` (array): Suggestions for improvement

---

## Component Index API

**Base URL:** `http://localhost:8086`

### Health Check

**Endpoint:** `GET /api/flowise/component-index/health`

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
  },
  "pattern_engine": {
    "total_components": 36,
    "collection_name": "flowise_components"
  }
}
```

---

### Register Component

**Endpoint:** `POST /api/flowise/component-index/components/register`

**Request Body:**
```json
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
  "description": "Perform basic calculations",
  "category": "tools",
  "platform": "flowise",
  "version": "1.0.0",
  "author": "Component Factory",
  "code_size": 2048,
  "dependencies": [],
  "validation_passed": true,
  "deployment_status": null,
  "created_at": "2025-12-04T10:00:00.000Z",
  "updated_at": "2025-12-04T10:00:00.000Z",
  "status": "generated"
}
```

---

### List Components

**Endpoint:** `GET /api/flowise/component-index/components`

**Query Parameters:**
- `platform` (optional): Filter by platform (e.g., "flowise")
- `category` (optional): Filter by category (e.g., "tools")
- `limit` (optional): Number of results per page (default: 50)
- `offset` (optional): Offset for pagination (default: 0)

**Example:**
```bash
GET /api/flowise/component-index/components?platform=flowise&category=tools&limit=10&offset=0
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
      "created_at": "2025-12-04T10:00:00.000Z",
      "category": "tools",
      "platform": "flowise"
    }
  ]
}
```

---

### Get Component by ID

**Endpoint:** `GET /api/flowise/component-index/components/{component_id}`

**Example:**
```bash
GET /api/flowise/component-index/components/550e8400-e29b-41d4-a716-446655440000
```

---

### Get Component by Name

**Endpoint:** `GET /api/flowise/component-index/components/name/{name}`

**Example:**
```bash
GET /api/flowise/component-index/components/name/CalculatorTool
```

---

### Update Deployment Status

**Endpoint:** `PATCH /api/flowise/component-index/components/{component_id}/deployment`

**Query Parameters:**
- `status` (required): New deployment status (e.g., "deployed", "pending", "failed")

**Example:**
```bash
PATCH /api/flowise/component-index/components/550e8400-e29b-41d4-a716-446655440000/deployment?status=deployed
```

---

### Delete Component

**Endpoint:** `DELETE /api/flowise/component-index/components/{component_id}`

**Example:**
```bash
DELETE /api/flowise/component-index/components/550e8400-e29b-41d4-a716-446655440000
```

---

### Get Statistics

**Endpoint:** `GET /api/flowise/component-index/components/stats`

**Response:**
```json
{
  "total_components": 15,
  "by_platform": {"flowise": 15},
  "by_category": {"tools": 10, "utilities": 5},
  "by_status": {"generated": 12, "deployed": 3},
  "total_code_size": 45678
}
```

---

### Pattern Search

**Endpoint:** `POST /api/flowise/component-index/patterns/search`

Search for similar component patterns using semantic search.

**Request Body:**
```json
{
  "query": "text processing tool",
  "n_results": 3
}
```

---

### Find Similar Patterns

**Endpoint:** `POST /api/flowise/component-index/patterns/similar`

Find patterns similar to a component description.

**Request Body:**
```json
{
  "description": "A component that formats JSON data",
  "category": "utilities",
  "n_results": 5
}
```

---

### Pattern Statistics

**Endpoint:** `GET /api/flowise/component-index/patterns/stats`

Get statistics about indexed patterns.

---

### Reindex Patterns

**Endpoint:** `POST /api/flowise/component-index/patterns/index`

Force reindexing of all component patterns.

**Request Body:**
```json
{
  "force_reindex": true
}
```

---

## YAML Specification Format

Component specifications use YAML format. Here's the complete schema:

### Required Fields

```yaml
name: ComponentName              # PascalCase, no spaces
display_name: "Component Name"   # Human-readable name
description: "What the component does"
category: tools                  # tools, utilities, agents, etc.

# Platform specification
platforms:
  - flowise

# Functional requirements
requirements:
  - "Requirement 1"
  - "Requirement 2"
```

### Optional Fields

```yaml
# Package dependencies
dependencies:
  - "expr-eval"
  - "axios"

# Input specifications
inputs:
  - name: inputParam
    label: "Input Parameter"
    type: string
    placeholder: "Enter value..."
    required: true
    default: ""

# Output specifications
outputs:
  - name: result
    type: string

# Component metadata
author: "Component Factory"
version: "1.0.0"
icon: "tool.svg"
```

### Complete Example

```yaml
name: CalculatorTool
display_name: "Calculator Tool"
description: "Perform mathematical calculations"
category: tools

platforms:
  - flowise

requirements:
  - "Evaluate mathematical expressions"
  - "Support basic operations: +, -, *, /"
  - "Handle parentheses and operator precedence"

dependencies:
  - "expr-eval"

inputs:
  - name: expression
    label: "Math Expression"
    type: string
    placeholder: "2 + 2 * 3"
    required: true

outputs:
  - name: result
    type: number

author: "Component Factory"
version: "1.0.0"
icon: "calculator.svg"
```

---

## Testing Examples

### Test Component Generation

Create a test specification and generate a component:

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

# Generate component
curl -X POST http://localhost:8085/api/flowise/component-generator/generate \
  -H "Content-Type: application/json" \
  -d "{\"spec\": \"$(cat test_spec.yaml | sed 's/$/\\n/' | tr -d '\n')\"}"
```

### Test Component Registry

```bash
# Register a component
curl -X POST http://localhost:8086/api/flowise/component-index/components/register \
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
curl http://localhost:8086/api/flowise/component-index/components

# Get stats
curl http://localhost:8086/api/flowise/component-index/components/stats
```

### Test Pattern Search

```bash
# Search for patterns
curl -X POST http://localhost:8086/api/flowise/component-index/patterns/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "text processing tool",
    "n_results": 3
  }'

# Find similar patterns
curl -X POST http://localhost:8086/api/flowise/component-index/patterns/similar \
  -H "Content-Type: application/json" \
  -d '{
    "description": "A component that formats JSON data",
    "category": "utilities",
    "n_results": 5
  }'
```

### Automated Testing

An automated test script is provided to validate all service endpoints:

```bash
# Run all endpoint tests
./test_endpoints.sh
```

**What Gets Tested:**
- ✅ Component Generator health check
- ✅ Sample component generation
- ✅ Component Index health & statistics
- ✅ Component registry CRUD operations
- ✅ Pattern search functionality
- ✅ CORS headers validation

**Test Output:**
- Console output with color-coded results
- `test_results.log` file with detailed results
- Summary report showing pass/fail count

---

## Error Responses

All endpoints return standard HTTP status codes and error messages:

### 400 Bad Request
```json
{
  "detail": "Invalid YAML: ..."
}
```

### 404 Not Found
```json
{
  "detail": "Component not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Component generation failed: ..."
}
```

### 503 Service Unavailable
```json
{
  "detail": "Generator not initialized"
}
```

---

## Rate Limiting

Currently, there are no rate limits enforced. However, component generation uses Claude API which has its own rate limits based on your Anthropic API key tier.

---

## CORS Configuration

Both services support CORS for cross-origin requests. Configure allowed origins via `CORS_ORIGINS` environment variable:

```bash
CORS_ORIGINS='["http://localhost:3000","http://localhost:8085","http://localhost:8086"]'
```

---

📖 **[Back to README](README.md)**

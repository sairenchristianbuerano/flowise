# Flowise Component Generator Service

Generates custom Flowise component code from YAML specifications using Claude AI.

## 📋 Overview

This service generates production-ready JavaScript code for Flowise custom components based on YAML specifications. It uses Claude AI to create components that follow Flowise best practices and patterns.

## 🏗️ Architecture

```
component-generator/
├── src/
│   ├── service.py                      # FastAPI application & endpoints
│   ├── flowise_agent.py                # Core component generator
│   ├── flowise_validator.py            # Code validation & security checks
│   ├── flowise_feasibility_checker.py  # Assess generation feasibility
│   └── base_classes.py                 # Shared base classes
├── Dockerfile                          # Container definition
└── requirements.txt                    # Python dependencies
```

## 🔧 Core Components

### service.py
FastAPI application with two main endpoints:

- `POST /api/flowise/generate` - Generate component from YAML spec
- `POST /api/flowise/assess` - Assess feasibility before generation
- `GET /api/flowise/component-generator/health` - Health check

### flowise_agent.py
**CustomComponentGenerator** class that:

- Retrieves similar components from RAG for pattern matching
- Generates component structure using Claude AI
- Creates TypeScript/JavaScript implementation code
- Validates generated code
- Applies automatic fixes for common issues
- Returns complete component with metadata

**Key Features:**
- Template-based generation (Tools, Utilities, Custom classes)
- Official Flowise validation utilities integration
- Forbidden library detection (mathjs, lodash, etc.)
- Auto-retry with fixes on validation errors
- RAG-powered pattern learning

### flowise_validator.py
**FlowiseValidator** class that validates:

- TypeScript syntax
- Flowise INode interface compliance
- Required methods and properties
- Module export format
- Security practices (using official Flowise validators)
- Forbidden imports

**FeasibilityAssessment** class that checks:
- Component complexity
- Similar patterns availability
- Unsupported features
- Confidence level

### base_classes.py
Shared Pydantic models:

- `ComponentSpec` - Input specification
- `GeneratedComponent` - Output with code and metadata
- `BaseCodeGenerator` - Abstract base class

## 📡 API Endpoints

### Generate Component

```bash
POST /api/flowise/generate
Content-Type: application/json

{
  "spec_yaml": "<YAML specification string>"
}
```

**Response:**
```json
{
  "component_code": "import { INode...",
  "component_config": {...},
  "dependencies": [],
  "validation": {
    "is_valid": true,
    "errors": [],
    "warnings": []
  },
  "deployment_instructions": {...}
}
```

### Assess Feasibility

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
  "suggestions": []
}
```

## 🚀 Running the Service

### With Docker (Recommended)

```bash
# From flowise root directory
docker-compose up -d component-generator

# View logs
docker-compose logs -f component-generator
```

### Standalone

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export ANTHROPIC_API_KEY=your_key_here
export CLAUDE_MODEL=claude-sonnet-4-20250514

# Run service
python src/service.py
```

Service will be available at http://localhost:8085

## 🔑 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes | - | Claude API key for code generation |
| `CLAUDE_MODEL` | No | `claude-sonnet-4-20250514` | Claude model to use |
| `PORT` | No | `8085` | Service port |
| `COMPONENT_RAG_URL` | No | `http://rag-service:8088` | RAG service for patterns |

## 📝 YAML Specification Format

```yaml
name: ComponentName
display_name: "Component Display Name"
description: "What the component does"
category: tools
platforms:
  - flowise

requirements:
  - "Requirement 1"
  - "Requirement 2"

dependencies:
  - "expr-eval"  # Optional npm packages

inputs:
  - name: param1
    label: "Parameter 1"
    type: string

author: "Your Name"
version: "1.0.0"
icon: "tool.svg"
```

## 🧪 Testing

```bash
# Test generation with curl
curl -X POST http://localhost:8085/api/flowise/generate \
  -H "Content-Type: application/json" \
  -d '{"spec_yaml": "name: TestTool\ndisplay_name: Test\ndescription: Test tool\ncategory: tools\nplatforms:\n  - flowise\nrequirements:\n  - Echo input"}'

# Test health endpoint
curl http://localhost:8085/api/flowise/component-generator/health
```

## 🔍 Generated Component Structure

The generator creates components following Flowise 3.0.8 patterns:

### For Tools Category:
Uses **Custom Tool Class** pattern (user's proven best practice):

```javascript
const { getBaseClasses } = require('../../../../src/utils')
const { Tool } = require('@langchain/core/tools')

class ComponentName implements INode {
    constructor() {
        this.label = 'Display Name'
        this.baseClasses = ['Tool', 'StructuredTool']
        // ...
    }

    async init(nodeData: INodeData): Promise<Tool> {
        return new ComponentNameCustomTool({...})
    }
}

class ComponentNameCustomTool extends Tool {
    async _call(input: string): Promise<string> {
        // Business logic here
    }
}

module.exports = { nodeClass: ComponentName }
```

### For Other Categories:
Uses standard INode pattern.

## ⚠️ Important Notes

### Forbidden Libraries
The generator automatically prevents use of unsupported libraries:

- ❌ mathjs (use native JavaScript Math)
- ❌ lodash (use native array/object methods)
- ❌ moment (use native Date)
- ❌ axios (use native fetch)

### Validation & Security
Uses official Flowise validation utilities:

- `isValidUUID` - Validate UUIDs
- `isValidURL` - Validate URLs
- `isPathTraversal` - Prevent path traversal attacks
- `isUnsafeFilePath` - Prevent unsafe file paths
- `handleErrorMessage` - Consistent error formatting

## 🛠️ Troubleshooting

### Claude API Errors

```bash
# Check API key is set
docker exec flowise-component-generator env | grep ANTHROPIC

# View detailed logs
docker-compose logs -f component-generator
```

### Validation Failures

The generator auto-retries with fixes, but check logs for:
- Missing required properties
- Invalid TypeScript syntax
- Forbidden imports

### RAG Service Unavailable

RAG is optional - service will work without it but with reduced pattern matching.

## 📚 Related Files

- [flowise_agent.py](src/flowise_agent.py) - Core generator logic
- [flowise_validator.py](src/flowise_validator.py) - Validation rules
- [base_classes.py](src/base_classes.py) - Shared models
- [Phase 2A Findings](../../ian/teamsflow/PHASE_2A_FINDINGS.md) - Research findings

## 🆘 Support

Check logs for errors:
```bash
docker-compose logs -f component-generator
```

Common issues:
- Missing API key → Set ANTHROPIC_API_KEY
- Invalid YAML → Check spec format
- Validation errors → Review Flowise patterns

---

**Service Status:** Port 8085 | Health: `/api/flowise/component-generator/health`

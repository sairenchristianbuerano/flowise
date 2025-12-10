# Flowise Component Generator & Index

Backend services for generating and managing custom Flowise components.

**Flowise Version:** Component generator targets [Flowise v3.0.8](https://github.com/FlowiseAI/Flowise/blob/flowise%403.0.8/package.json) component architecture

📖 **[API Documentation](API.md)** - Complete endpoint reference

---

## 📋 Overview

This repository contains two microservices specifically for Flowise platform:

1. **Component Generator** (Port 8085) - Generates custom Flowise component code from YAML specifications using Claude AI
2. **Component Index** (Port 8086) - Tracks and manages generated components with semantic pattern search (RAG)

The Component Index provides both component registry functionality and semantic search over Flowise component patterns to help generate better, more consistent code.

All services are **separate from the main teamsflow** multi-agent system and focus exclusively on Flowise component development.

---

## 🏗️ Architecture

```
flowise/
├── component-generator/      # Code generation service (Port 8085)
│   ├── src/
│   │   ├── service.py        # FastAPI endpoints
│   │   ├── flowise_agent.py  # Core generator with Claude AI
│   │   └── flowise_validator.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── component-index/          # Component registry & RAG (Port 8086)
│   ├── src/
│   │   ├── service.py        # FastAPI endpoints
│   │   ├── storage.py        # JSON-based component registry
│   │   └── flowise_rag_engine.py  # Pattern search engine
│   ├── data/
│   │   └── flowise_components/   # Component knowledge base
│   ├── Dockerfile
│   └── requirements.txt
│
└── docker-compose.yml        # Service orchestration
```

---

## 🚀 Quick Start - Docker

### Prerequisites

- Docker & Docker Compose
- Anthropic API key (for Claude)

### 1. Set Environment Variables

Create a `.env` file:

```bash
# Required: Claude API key for code generation
ANTHROPIC_API_KEY=your_api_key_here

# Optional: Claude model selection (default shown)
CLAUDE_MODEL=claude-sonnet-4-20250514

# Optional: Pattern search URL (served by component-index)
COMPONENT_RAG_URL=http://component-index:8086
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

## 🖥️ Quick Start - Standalone Mode (No Docker)

For users without Docker or for local development.

### Prerequisites

- Python 3.11+ (3.13 recommended)
- pip
- Anthropic API key

### 1. One-Time Setup

```bash
# Run setup script to create virtual environments and install dependencies
./setup_standalone.sh
```

This will:
- Create isolated virtual environments for both services
- Install all Python dependencies
- Pre-download required ML models
- Create data directories
- Generate `.env.standalone` configuration file

### 2. Configure Environment

Edit `.env.standalone` and add your API key:

```bash
# Required
ANTHROPIC_API_KEY=your_api_key_here

# Optional (defaults shown)
CLAUDE_MODEL=claude-sonnet-4-20250514
PORT_INDEX=8086
PORT_GENERATOR=8085
COMPONENT_RAG_URL=http://localhost:8086
```

### 3. Start Services

```bash
# Start both services together
./run_standalone.sh
```

This will:
- Start component-index on port 8086
- Wait for component-index to become healthy
- Start component-generator on port 8085
- Display live logs from both services

Services will continue running until you press Ctrl+C.

### 4. Stop Services

```bash
# In another terminal, or after pressing Ctrl+C
./stop_standalone.sh
```

### Standalone vs Docker Comparison

| Feature | Docker | Standalone |
|---------|--------|------------|
| **Setup** | Docker required | Python 3.11+ required |
| **Isolation** | Container-level | venv-level |
| **Startup Time** | ~30 seconds | ~20 seconds |
| **Memory Usage** | Higher (containers) | Lower (native) |
| **Best For** | Production, CI/CD | Local development, debugging |

---

## 📡 API Endpoints

Both services provide REST APIs for component generation and management.

📖 **See [API.md](API.md) for complete endpoint documentation** including:
- Component Generator API (health, generate, assess feasibility)
- Component Index API (register, list, search, CRUD operations)
- Pattern Search API (semantic search over component patterns)
- YAML specification format
- Request/response examples
- Error handling

### Quick Examples

**Generate a Component:**
```bash
curl -X POST http://localhost:8085/api/flowise/component-generator/generate \
  -H "Content-Type: application/json" \
  -d '{"spec": "name: CalculatorTool\ndisplay_name: Calculator\ndescription: Perform calculations\ncategory: tools\nplatforms:\n  - flowise\nrequirements:\n  - Evaluate math expressions"}'
```

**List Components:**
```bash
curl http://localhost:8086/api/flowise/component-index/components
```

**Search for Patterns:**
```bash
curl -X POST http://localhost:8086/api/flowise/component-index/patterns/search \
  -H "Content-Type: application/json" \
  -d '{"query": "text processing tool", "n_results": 3}'
```

---

## 🧪 Testing

An automated test script validates all service endpoints:

```bash
./test_endpoints.sh
```

**What Gets Tested:**
- ✅ Component Generator health check
- ✅ Sample component generation (uses cached sample)
- ✅ Component Index health & statistics
- ✅ Component registry CRUD operations
- ✅ Pattern search functionality
- ✅ CORS headers validation

**Test Output:**
- Console output with color-coded results
- `test_results.log` file with detailed results
- Summary report showing pass/fail count

---

## 🛠️ Troubleshooting

### Docker Mode

**Services won't start:**
```bash
# Check logs
docker-compose logs -f

# Verify .env file has ANTHROPIC_API_KEY
cat .env | grep ANTHROPIC_API_KEY
```

**Port conflicts:**
```bash
# Change ports in docker-compose.yml if needed
ports:
  - "9085:8085"  # Use port 9085 instead
  - "9086:8086"  # Use port 9086 instead
```

### Standalone Mode

**Services won't start:**
```bash
# Check if venvs exist
ls component-index/venv component-generator/venv

# If missing, run setup again
./setup_standalone.sh
```

**API key error:**
```bash
# Verify .env.standalone has your key
cat .env.standalone | grep ANTHROPIC_API_KEY
```

**Port conflicts:**
```bash
# Check if ports are in use
netstat -ano | findstr "8085"
netstat -ano | findstr "8086"

# Change ports in .env.standalone if needed
PORT_INDEX=9086
PORT_GENERATOR=9085
```

**View logs:**
```bash
# Component Index logs
tail -f component-index.log

# Component Generator logs
tail -f component-generator.log
```

---

## 🔗 Integration with teamsflow

While this repository is separate from teamsflow, it can integrate with:

- **tf-flowise-dev-env**: Optional deployment target for generated components
- **Deployment scripts**: Located in teamsflow repo (`scripts/deploy_component.py`)

Pattern search functionality is built into the component-index service.

---

## 📚 Related Documentation

### Service Documentation
- [API.md](API.md) - Complete API reference with endpoint details for both services

### External Resources
- [Flowise Documentation](https://docs.flowiseai.com) - Official Flowise docs
- [teamsflow Repository](../ian/teamsflow) - Multi-agent system
- [Phase 2A Findings](../ian/teamsflow/PHASE_2A_FINDINGS.md) - Component development insights

---

## 🆘 Support

For issues or questions:

1. Check logs: `docker-compose logs -f` or `tail -f *.log`
2. Verify health endpoints: `curl http://localhost:8085/health` and `curl http://localhost:8086/health`
3. Ensure API keys are set correctly in `.env` or `.env.standalone`
4. Review [API.md](API.md) for YAML specification format

---

## 📄 License

MIT

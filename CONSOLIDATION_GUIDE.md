# RAG Service → Component-Index Consolidation Guide

## Overview
Consolidate RAG service functionality into component-index for a simpler 2-service architecture.

## Changes Required

### 1. Component-Index Service (service.py)

**Add to imports:**
```python
from flowise_rag_engine import FlowiseRAGEngine
```

**Add to globals:**
```python
pattern_engine: Optional[FlowiseRAGEngine] = None
```

**Update startup() to initialize RAG:**
```python
# Add after storage initialization:
flowise_components_dir = os.getenv("FLOWISE_COMPONENTS_DIR", "/app/data/flowise_components")
chromadb_dir = os.getenv("CHROMADB_DIR", "/app/data/chromadb")

pattern_engine = FlowiseRAGEngine(
    flowise_components_dir=flowise_components_dir,
    persist_directory=chromadb_dir
)

pattern_count = pattern_engine.index_components()
logger.info(f"Indexed {pattern_count} component patterns")
```

**Update health check to include pattern stats:**
```python
@app.get("/api/flowise/component-index/health")
async def health_check():
    registry_stats = storage.get_stats() if storage else {}
    pattern_stats = pattern_engine.get_stats() if pattern_engine else {}
    
    return {
        "status": "healthy",
        "service": "flowise-component-index",
        "version": "2.0.0",
        "registry": registry_stats,
        "patterns": pattern_stats
    }
```

**Add new Pattern Search endpoints:**
```python
# Add Pydantic models:
class PatternSearchRequest(BaseModel):
    query: str
    n_results: int = 5
    category: Optional[str] = None

class SimilarPatternsRequest(BaseModel):
    description: str
    category: Optional[str] = None
    input_types: Optional[List[str]] = None
    n_results: int = 5

# Add endpoints:
@app.post("/api/flowise/patterns/search")
async def search_patterns(request: PatternSearchRequest):
    ...pattern_engine.search()...

@app.post("/api/flowise/patterns/similar")
async def find_similar_patterns(request: SimilarPatternsRequest):
    ...pattern_engine.find_similar_components()...

@app.get("/api/flowise/patterns/{pattern_name}")
async def get_pattern(pattern_name: str):
    ...pattern_engine.get_component_by_name()...

@app.post("/api/flowise/patterns/index")
async def reindex_patterns(request: ReindexRequest):
    ...pattern_engine.index_components()...

@app.get("/api/flowise/patterns/stats")
async def get_pattern_stats():
    ...pattern_engine.get_stats()...
```

### 2. Docker-compose.yml

**Remove `rag-service` section entirely**

**Update `component-index`:**
```yaml
component-index:
  build:
    context: ./component-index
  container_name: flowise-component-index
  ports:
    - "8086:8086"
  environment:
    - PORT=8086
    - STORAGE_PATH=/app/data/components
    - FLOWISE_COMPONENTS_DIR=/app/data/flowise_components  # ADD
    - CHROMADB_DIR=/app/data/chromadb                      # ADD
  volumes:
    - index_data:/app/data
    - ./data/flowise_components:/app/data/flowise_components:ro  # ADD
  networks:
    - flowise-network
  restart: unless-stopped
  healthcheck:                                              # ADD
    test: ["CMD", "curl", "-f", "http://localhost:8086/api/flowise/component-index/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s
```

**Update `component-generator` depends_on:**
```yaml
component-generator:
  ...
  depends_on:
    component-index:                    # CHANGE from rag-service
      condition: service_healthy
```

**Update `component-generator` environment:**
```yaml
- COMPONENT_RAG_URL=${COMPONENT_RAG_URL:-http://component-index:8086}  # CHANGE port from 8088
```

**Remove `rag_data` volume** - keep only:
```yaml
volumes:
  component_data:
  index_data:
```

### 3. Component-Index Dockerfile

**Update to pre-download embeddings model:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the embeddings model (same as RAG service)
RUN python -c "\
import chromadb; \
from chromadb.utils import embedding_functions; \
client = chromadb.Client(); \
ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name='sentence-transformers/all-MiniLM-L6-v2'); \
collection = client.create_collection(name='test', embedding_function=ef); \
collection.add(documents=['test'], ids=['1']); \
print('Model downloaded and cached successfully')"

# Copy source code
COPY src/ ./src/

# Expose port
EXPOSE 8086

# Run service
CMD ["python", "-m", "uvicorn", "src.service:app", "--host", "0.0.0.0", "--port", "8086"]
```

### 4. Component-Generator Flowise Agent

**Update RAG URL in flowise_agent.py:**
```python
# Change from:
rag_url = os.getenv("COMPONENT_RAG_URL", "http://rag-service:8088")

# To:
rag_url = os.getenv("COMPONENT_RAG_URL", "http://component-index:8086")
```

**Update endpoint calls:**
```python
# Change from:
response = httpx.post(f"{rag_url}/flowise/components/similar", ...)

# To:
response = httpx.post(f"{rag_url}/api/flowise/patterns/similar", ...)
```

### 5. .env.example

**Update:**
```bash
# Component services
COMPONENT_RAG_URL=http://component-index:8086  # Changed from rag-service:8088

# Component-Index configuration
STORAGE_PATH=/app/data/components
FLOWISE_COMPONENTS_DIR=/app/data/flowise_components
CHROMADB_DIR=/app/data/chromadb
```

### 6. Clean Up

**Remove:**
- `rag-service/` directory entirely
- References to port 8088
- rag-service from all documentation

## New API Structure

### Registry Endpoints (port 8086):
- `POST /api/flowise/components/register` - Register generated component
- `GET /api/flowise/components` - List generated components
- `GET /api/flowise/components/{id}` - Get component by ID
- `GET /api/flowise/components/stats` - Registry statistics

### Pattern Search Endpoints (port 8086):
- `POST /api/flowise/patterns/search` - Search knowledge base
- `POST /api/flowise/patterns/similar` - Find similar patterns
- `GET /api/flowise/patterns/{name}` - Get pattern by name
- `GET /api/flowise/patterns/stats` - Pattern statistics
- `POST /api/flowise/patterns/index` - Reindex patterns

## Testing After Consolidation

```bash
# Rebuild and start services
docker-compose down
docker-compose build
docker-compose up -d

# Test health
curl http://localhost:8086/api/flowise/component-index/health

# Should show both registry AND patterns stats

# Test pattern search
curl -X POST http://localhost:8086/api/flowise/patterns/search \
  -H "Content-Type: application/json" \
  -d '{"query": "calculator tool", "n_results": 3}'

# Test component generation (should use patterns)
curl -X POST http://localhost:8085/api/flowise/generate \
  -H "Content-Type: application/json" \
  -d '{"spec_yaml": "name: TestCalc\ndisplay_name: Calculator\n..."}'
```

## Benefits

- ✅ Single service (8086) instead of two (8086 + 8088)
- ✅ Unified storage (index_data contains both registry JSON + ChromaDB)
- ✅ Single health check
- ✅ Simpler deployment
- ✅ Clear API separation (/components/ vs /patterns/)

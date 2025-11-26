# Flowise Component Index Service

Component registry and tracking system for generated Flowise components, with integrated pattern search.

## 📋 Overview

This service provides two main functions:

1. **Component Registry** - Tracks metadata, deployment status, and statistics for generated components
2. **Pattern Search** - Semantic search over reference component patterns using RAG (Retrieval-Augmented Generation)

The pattern search functionality helps the component generator create better, more consistent code by learning from existing component patterns.

## 🏗️ Architecture

```
component-index/
├── src/
│   ├── service.py           # FastAPI application & endpoints (registry + patterns)
│   ├── models.py            # Pydantic data models
│   ├── storage.py           # JSON-based storage layer
│   └── flowise_rag_engine.py # Pattern search engine (ChromaDB + embeddings)
├── Dockerfile               # Container definition
└── requirements.txt         # Python dependencies (includes ChromaDB)
```

## 🔧 Core Components

### service.py
FastAPI application with RESTful endpoints for:

**Component Registry (`/api/flowise/components/*`)**:
- Component registration
- Component retrieval (by ID or name)
- Component listing with filters
- Deployment status tracking
- Component deletion
- Statistics

**Pattern Search (`/api/flowise/patterns/*`)**:
- Semantic search for patterns
- Find similar component patterns
- Pattern retrieval by name
- Pattern reindexing
- Pattern statistics

### models.py
**Pydantic models:**

- `ComponentMetadata` - Full component metadata with timestamps
- `ComponentRegistrationRequest` - Registration payload
- `ComponentListResponse` - Paginated list response

**Fields tracked:**
- component_id (UUID)
- name, display_name, description
- category, platform, version
- author, created_at, updated_at
- code_size, dependencies
- validation_passed, deployment_status
- status

### storage.py
**ComponentStorage** class:

- JSON-based persistence (`/app/data/components/index.json`)
- CRUD operations for components
- Filtering by platform/category
- Pagination support
- Statistics generation

**Storage features:**
- Atomic file operations
- UUID generation
- Timestamp management
- Search by ID or name

### flowise_rag_engine.py
**FlowiseRAGEngine** class:

- ChromaDB vector database integration
- Sentence-transformers embedding model (`all-MiniLM-L6-v2`)
- Semantic search over component patterns
- Component indexing from knowledge base (`/app/data/flowise_components`)

**Pattern search features:**
- Search by query string
- Find similar components by description
- Category filtering
- Similarity scoring
- Statistics generation

## 📡 API Endpoints

The service provides two sets of endpoints:

### Health Check

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

### Register Component

```bash
POST /api/flowise/components/register
Content-Type: application/json

{
  "name": "CalculatorTool",
  "display_name": "Calculator",
  "description": "Perform calculations",
  "category": "tools",
  "platform": "flowise",
  "version": "1.0.0",
  "author": "Component Factory",
  "code_size": 2048,
  "dependencies": ["expr-eval"],
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
  "description": "Perform calculations",
  "category": "tools",
  "platform": "flowise",
  "version": "1.0.0",
  "created_at": "2025-11-26T10:00:00.000Z",
  "updated_at": "2025-11-26T10:00:00.000Z",
  "author": "Component Factory",
  "status": "generated",
  "code_size": 2048,
  "dependencies": ["expr-eval"],
  "validation_passed": true,
  "deployment_status": null
}
```

### List Components

```bash
GET /api/flowise/components?platform=flowise&category=tools&limit=10&offset=0
```

**Query Parameters:**
- `platform` - Filter by platform (optional)
- `category` - Filter by category (optional)
- `limit` - Max results (1-1000, default: 100)
- `offset` - Pagination offset (default: 0)

**Response:**
```json
{
  "total": 15,
  "components": [
    {
      "component_id": "550e8400-...",
      "name": "CalculatorTool",
      "created_at": "2025-11-26T10:00:00.000Z",
      ...
    }
  ]
}
```

### Get Component by ID

```bash
GET /api/flowise/components/{component_id}
```

**Response:** Single ComponentMetadata object

### Get Component by Name

```bash
GET /api/flowise/components/name/{name}
```

Returns latest version of component with given name.

**Response:** Single ComponentMetadata object

### Update Deployment Status

```bash
PATCH /api/flowise/components/{component_id}/deployment?status=deployed
```

**Response:**
```json
{
  "component_id": "550e8400-...",
  "deployment_status": "deployed",
  "updated": true
}
```

### Delete Component

```bash
DELETE /api/flowise/components/{component_id}
```

**Response:**
```json
{
  "component_id": "550e8400-...",
  "deleted": true
}
```

### Get Statistics

```bash
GET /api/flowise/components/stats
```

**Response:**
```json
{
  "total_components": 15,
  "by_platform": {
    "flowise": 15
  },
  "by_category": {
    "tools": 10,
    "utilities": 5
  },
  "by_status": {
    "generated": 12,
    "deployed": 3
  },
  "total_code_size": 30720
}
```

---

## 🔍 Pattern Search Endpoints

### Search Patterns

```bash
POST /api/flowise/patterns/search
Content-Type: application/json

{
  "query": "component that processes text",
  "n_results": 5,
  "category": "utilities"
}
```

**Response:**
```json
{
  "query": "component that processes text",
  "results_count": 5,
  "results": [
    {
      "name": "TextProcessor",
      "description": "Process and transform text",
      "code": "...",
      "similarity": 0.85
    }
  ],
  "platform": "flowise"
}
```

### Find Similar Patterns

```bash
POST /api/flowise/patterns/similar
Content-Type: application/json

{
  "description": "A tool that calculates mathematical expressions",
  "category": "tools",
  "n_results": 3
}
```

**Response:**
```json
{
  "description": "A tool that calculates...",
  "results_count": 3,
  "results": [
    {
      "name": "CalculatorTool",
      "category": "tools",
      "code": "...",
      "inputs": [...],
      "outputs": [...]
    }
  ],
  "platform": "flowise"
}
```

### Get Pattern by Name

```bash
GET /api/flowise/patterns/{pattern_name}
```

**Response:** Single component pattern object

### Reindex Patterns

```bash
POST /api/flowise/patterns/index
Content-Type: application/json

{
  "force_reindex": true
}
```

**Response:**
```json
{
  "status": "success",
  "components_indexed": 15,
  "force_reindex": true,
  "platform": "flowise"
}
```

### Get Pattern Statistics

```bash
GET /api/flowise/patterns/stats
```

**Response:**
```json
{
  "total_components": 15,
  "has_embeddings": true
}
```

---

## 🚀 Running the Service

### With Docker (Recommended)

```bash
# From flowise root directory
docker-compose up -d component-index

# View logs
docker-compose logs -f component-index
```

### Standalone

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables (optional)
export PORT=8086
export STORAGE_PATH=/app/data/components

# Run service
python src/service.py
```

Service will be available at http://localhost:8086

## 🔑 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PORT` | No | `8086` | Service port |
| `STORAGE_PATH` | No | `/app/data/components` | JSON storage directory for registry |
| `FLOWISE_COMPONENTS_DIR` | No | `/app/data/flowise_components` | Component pattern knowledge base directory |
| `CHROMADB_DIR` | No | `/app/data/chromadb` | ChromaDB vector database directory |

## 💾 Data Storage

The service stores both component registry data and pattern search data:

### Component Registry Storage

Components are stored in JSON format at:
```
/app/data/components/index.json
```

### Pattern Search Storage

- **ChromaDB**: Vector embeddings at `/app/data/chromadb`
- **Knowledge Base**: Component patterns at `/app/data/flowise_components` (read-only)

**Structure:**
```json
{
  "550e8400-e29b-41d4-a716-446655440000": {
    "component_id": "550e8400-...",
    "name": "CalculatorTool",
    "display_name": "Calculator",
    "created_at": "2025-11-26T10:00:00.000Z",
    ...
  }
}
```

### Backup & Restore

```bash
# Backup index
docker cp flowise-component-index:/app/data/components/index.json ./backup_index.json

# Restore index
docker cp ./backup_index.json flowise-component-index:/app/data/components/index.json

# Restart service after restore
docker-compose restart component-index
```

### Clear All Data

```bash
# Stop service
docker-compose down component-index

# Remove volume
docker volume rm flowise_index_data

# Start fresh
docker-compose up -d component-index
```

## 🧪 Testing

### Register a Component

```bash
curl -X POST http://localhost:8086/api/flowise/components/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "TestComponent",
    "display_name": "Test Component",
    "description": "Test component for demo",
    "category": "tools",
    "platform": "flowise",
    "author": "Test User",
    "code_size": 1024,
    "validation_passed": true
  }'
```

### List All Components

```bash
curl http://localhost:8086/api/flowise/components
```

### Get Statistics

```bash
curl http://localhost:8086/api/flowise/components/stats
```

### Filter by Category

```bash
curl "http://localhost:8086/api/flowise/components?category=tools&limit=5"
```

## 📊 Use Cases

### Workflow Integration

1. **After Generation:**
   ```bash
   # Component generator creates component
   POST /api/flowise/component-generator/generate

   # Register in index
   POST /api/flowise/components/register
   ```

2. **Track Deployment:**
   ```bash
   # Update status after deployment
   PATCH /api/flowise/components/{id}/deployment?status=deployed
   ```

3. **Component Discovery:**
   ```bash
   # Find existing components
   GET /api/flowise/components?category=tools

   # Check if component exists
   GET /api/flowise/components/name/CalculatorTool
   ```

### Statistics & Analytics

```bash
# Get overview
GET /api/flowise/components/stats

# Response shows:
# - Total components generated
# - Distribution by platform
# - Distribution by category
# - Deployment status breakdown
# - Total code size
```

## 🔍 Search & Filtering

### By Platform

```bash
curl "http://localhost:8086/api/flowise/components?platform=flowise"
```

### By Category

```bash
curl "http://localhost:8086/api/flowise/components?category=tools"
```

### Combined Filters

```bash
curl "http://localhost:8086/api/flowise/components?platform=flowise&category=tools&limit=20"
```

### Pagination

```bash
# First 10 results
curl "http://localhost:8086/api/flowise/components?limit=10&offset=0"

# Next 10 results
curl "http://localhost:8086/api/flowise/components?limit=10&offset=10"
```

## 🛠️ Troubleshooting

### Storage Errors

```bash
# Check storage directory
docker exec flowise-component-index ls -la /app/data/components/

# Check index file
docker exec flowise-component-index cat /app/data/components/index.json

# View logs
docker-compose logs -f component-index
```

### Corrupted Index

```bash
# Backup current index
docker cp flowise-component-index:/app/data/components/index.json ./corrupted_index.json

# Reset index (creates empty index)
docker exec flowise-component-index sh -c 'echo "{}" > /app/data/components/index.json'

# Restart service
docker-compose restart component-index
```

### Port Conflicts

Change port in docker-compose.yml:
```yaml
component-index:
  ports:
    - "9086:8086"  # Use different external port
```

## 📈 Performance Notes

- **JSON Storage:** Suitable for 100s-1000s of components
- **In-Memory:** Index loaded per request (fast for small datasets)
- **Scalability:** For production with 10K+ components, consider database upgrade

## 🔄 Future Enhancements

Potential improvements:
- Database backend (PostgreSQL, MongoDB)
- Full-text search
- Component versioning
- Duplicate detection
- Batch operations
- Export/import functionality

## 📚 Related Files

- [models.py](src/models.py) - Data models
- [storage.py](src/storage.py) - Storage implementation
- [service.py](src/service.py) - API endpoints

## 🆘 Support

Check logs for errors:
```bash
docker-compose logs -f component-index
```

Common issues:
- Storage permission errors → Check volume mounts
- Corrupted JSON → Reset index file
- Port conflicts → Change external port

---

**Service Status:** Port 8086 | Health: `/api/flowise/component-index/health`

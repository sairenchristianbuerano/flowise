# Flowise Component Index Service

Component registry and tracking system for generated Flowise components.

## 📋 Overview

This service maintains a searchable index of all generated Flowise components. It tracks metadata, deployment status, and provides statistics about component generation history.

## 🏗️ Architecture

```
component-index/
├── src/
│   ├── service.py    # FastAPI application & endpoints
│   ├── models.py     # Pydantic data models
│   └── storage.py    # JSON-based storage layer
├── Dockerfile        # Container definition
└── requirements.txt  # Python dependencies
```

## 🔧 Core Components

### service.py
FastAPI application with RESTful endpoints for:

- Component registration
- Component retrieval (by ID or name)
- Component listing with filters
- Deployment status tracking
- Component deletion
- Statistics

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

## 📡 API Endpoints

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
| `STORAGE_PATH` | No | `/app/data/components` | JSON storage directory |

## 💾 Data Storage

### Storage Format

Components are stored in JSON format at:
```
/app/data/components/index.json
```

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
   POST /api/flowise/generate

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

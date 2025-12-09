"""
FastAPI service for Flowise Component Index

REST API service for component registry and tracking.
Endpoint prefix: /flowise/*
"""

import os
import uuid
from typing import Optional, List
import structlog
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from models import ComponentMetadata, ComponentRegistrationRequest, ComponentListResponse
from storage import ComponentStorage
from flowise_rag_engine import FlowiseRAGEngine

logger = structlog.get_logger()

# FastAPI app
app = FastAPI(
    title="Flowise Component Index",
    version="1.0.0",
    description="Component registry and tracking for Flowise components"
)

# CORS Configuration
cors_origins = os.getenv("CORS_ORIGINS", '["http://localhost:8085", "http://localhost:3000"]')
# Parse JSON string to list
import json
allowed_origins = json.loads(cors_origins) if isinstance(cors_origins, str) else cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Storage instance
storage: Optional[ComponentStorage] = None

# RAG Pattern Engine
pattern_engine: Optional[FlowiseRAGEngine] = None


@app.on_event("startup")
async def startup():
    """Initialize storage and RAG pattern engine"""
    global storage, pattern_engine

    logger.info("Starting Flowise Component Index service")

    # Initialize storage
    storage_path = os.getenv("STORAGE_PATH", "/app/data/components")
    storage = ComponentStorage(storage_path=storage_path)

    logger.info("Component storage initialized", path=storage_path)

    # Initialize RAG pattern engine
    flowise_components_dir = os.getenv("FLOWISE_COMPONENTS_DIR", "/app/data/flowise_components")
    chromadb_dir = os.getenv("CHROMADB_DIR", "/app/data/chromadb")

    try:
        pattern_engine = FlowiseRAGEngine(
            flowise_components_dir=flowise_components_dir,
            persist_directory=chromadb_dir
        )

        pattern_count = pattern_engine.index_components()
        logger.info("Pattern engine initialized", patterns_indexed=pattern_count)
    except Exception as e:
        logger.warning("Pattern engine initialization failed", error=str(e))
        logger.warning("Pattern search endpoints will not be available")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup"""
    logger.info("Shutting down Flowise Component Index")


@app.get("/api/flowise/component-index/health")
async def health_check():
    """Health check endpoint"""
    stats = storage.get_stats() if storage else {}

    # Include pattern engine status
    pattern_stats = None
    if pattern_engine:
        try:
            pattern_stats = pattern_engine.get_stats()
        except Exception as e:
            logger.warning("Failed to get pattern stats", error=str(e))

    return {
        "status": "healthy",
        "service": "flowise-component-index",
        "version": "1.0.0",
        "stats": stats,
        "pattern_engine": pattern_stats
    }


@app.post("/api/flowise/component-index/components/register", response_model=ComponentMetadata)
async def register_component(request: ComponentRegistrationRequest):
    """
    Register a generated component in the index

    This endpoint stores metadata about generated components for tracking purposes.
    """
    if not storage:
        raise HTTPException(status_code=503, detail="Storage not initialized")

    try:
        # Create metadata with generated ID
        metadata = ComponentMetadata(
            component_id=str(uuid.uuid4()),
            name=request.name,
            display_name=request.display_name,
            description=request.description,
            category=request.category,
            platform=request.platform,
            version=request.version,
            author=request.author,
            code_size=request.code_size,
            dependencies=request.dependencies,
            validation_passed=request.validation_passed,
            deployment_status=request.deployment_status
        )

        # Register in storage
        registered = storage.register_component(metadata)

        logger.info("Component registered", component_id=registered.component_id, name=registered.name)

        return registered
    except Exception as e:
        logger.error("Component registration failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/flowise/component-index/components", response_model=ComponentListResponse)
async def list_components(
    platform: Optional[str] = Query(None, description="Filter by platform"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """
    List all registered components with optional filters

    Query parameters:
    - platform: Filter by platform (e.g., 'flowise')
    - category: Filter by category (e.g., 'tools')
    - limit: Maximum number of results (default: 100)
    - offset: Pagination offset (default: 0)
    """
    if not storage:
        raise HTTPException(status_code=503, detail="Storage not initialized")

    try:
        components = storage.list_components(
            platform=platform,
            category=category,
            limit=limit,
            offset=offset
        )

        # Get total count (without pagination)
        all_components = storage.list_components(platform=platform, category=category, limit=10000)
        total = len(all_components)

        return ComponentListResponse(
            total=total,
            components=components
        )
    except Exception as e:
        logger.error("Component listing failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/flowise/component-index/components/stats")
async def get_stats():
    """
    Get component index statistics
    """
    if not storage:
        raise HTTPException(status_code=503, detail="Storage not initialized")

    try:
        stats = storage.get_stats()
        return stats
    except Exception as e:
        logger.error("Stats retrieval failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/flowise/component-index/components/name/{name}", response_model=ComponentMetadata)
async def get_component_by_name(name: str):
    """
    Get component metadata by name (returns latest version)
    """
    if not storage:
        raise HTTPException(status_code=503, detail="Storage not initialized")

    try:
        component = storage.get_component_by_name(name)

        if not component:
            raise HTTPException(status_code=404, detail=f"Component not found: {name}")

        return component
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Component retrieval failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/flowise/component-index/components/{component_id}", response_model=ComponentMetadata)
async def get_component(component_id: str):
    """
    Get component metadata by ID
    """
    if not storage:
        raise HTTPException(status_code=503, detail="Storage not initialized")

    try:
        component = storage.get_component(component_id)

        if not component:
            raise HTTPException(status_code=404, detail=f"Component not found: {component_id}")

        return component
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Component retrieval failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/flowise/component-index/components/{component_id}/deployment")
async def update_deployment_status(
    component_id: str,
    status: str = Query(..., description="Deployment status")
):
    """
    Update deployment status of a component
    """
    if not storage:
        raise HTTPException(status_code=503, detail="Storage not initialized")

    try:
        success = storage.update_deployment_status(component_id, status)

        if not success:
            raise HTTPException(status_code=404, detail=f"Component not found: {component_id}")

        return {"component_id": component_id, "deployment_status": status, "updated": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Deployment status update failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/flowise/component-index/components/{component_id}")
async def delete_component(component_id: str):
    """
    Delete a component from the index
    """
    if not storage:
        raise HTTPException(status_code=503, detail="Storage not initialized")

    try:
        success = storage.delete_component(component_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Component not found: {component_id}")

        return {"component_id": component_id, "deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Component deletion failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PATTERN SEARCH ENDPOINTS (RAG)
# ============================================================================

class PatternSearchRequest(BaseModel):
    """Request for pattern search"""
    query: str
    n_results: int = 5
    category: Optional[str] = None


class PatternSimilarRequest(BaseModel):
    """Request for finding similar patterns"""
    description: str
    category: Optional[str] = None
    input_types: Optional[List[str]] = None
    n_results: int = 3


class PatternIndexRequest(BaseModel):
    """Request for reindexing patterns"""
    force_reindex: bool = False


@app.post("/api/flowise/component-index/patterns/search")
async def search_patterns(request: PatternSearchRequest):
    """
    Search component patterns using semantic search

    This endpoint searches the knowledge base of reference component patterns
    to help guide code generation with similar examples.
    """
    if not pattern_engine:
        raise HTTPException(status_code=503, detail="Pattern engine not initialized")

    try:
        # Build filters if category specified
        filters = {'category': request.category} if request.category else None

        results = pattern_engine.search(
            query=request.query,
            n_results=request.n_results,
            filters=filters
        )

        return {
            "query": request.query,
            "results_count": len(results),
            "results": results,
            "platform": "flowise"
        }
    except Exception as e:
        logger.error("Pattern search failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/flowise/component-index/patterns/similar")
async def find_similar_patterns(request: PatternSimilarRequest):
    """
    Find component patterns similar to a description

    Used by the component generator to find reference implementations
    that match the specification being generated.
    """
    if not pattern_engine:
        raise HTTPException(status_code=503, detail="Pattern engine not initialized")

    try:
        results = pattern_engine.find_similar_components(
            description=request.description,
            category=request.category,
            input_types=request.input_types,
            n_results=request.n_results
        )

        return {
            "description": request.description,
            "results_count": len(results),
            "results": results,
            "platform": "flowise"
        }
    except Exception as e:
        logger.error("Similar pattern search failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/flowise/component-index/patterns/index")
async def reindex_patterns(request: PatternIndexRequest):
    """
    Reindex component patterns from the knowledge base
    """
    if not pattern_engine:
        raise HTTPException(status_code=503, detail="Pattern engine not initialized")

    try:
        count = pattern_engine.index_components(force_reindex=request.force_reindex)

        return {
            "status": "success",
            "components_indexed": count,
            "force_reindex": request.force_reindex,
            "platform": "flowise"
        }
    except Exception as e:
        logger.error("Pattern reindexing failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/flowise/component-index/patterns/stats")
async def get_pattern_stats():
    """
    Get pattern knowledge base statistics
    """
    if not pattern_engine:
        raise HTTPException(status_code=503, detail="Pattern engine not initialized")

    try:
        stats = pattern_engine.get_stats()
        return stats
    except Exception as e:
        logger.error("Pattern stats retrieval failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/flowise/component-index/patterns/{pattern_name}")
async def get_pattern_by_name(pattern_name: str):
    """
    Get a specific component pattern by name
    """
    if not pattern_engine:
        raise HTTPException(status_code=503, detail="Pattern engine not initialized")

    try:
        pattern = pattern_engine.get_component_by_name(pattern_name)

        if not pattern:
            raise HTTPException(status_code=404, detail=f"Pattern not found: {pattern_name}")

        return pattern
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Pattern retrieval failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8086"))

    uvicorn.run(
        "service:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )

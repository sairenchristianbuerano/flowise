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
from pydantic import BaseModel

from models import ComponentMetadata, ComponentRegistrationRequest, ComponentListResponse
from storage import ComponentStorage

logger = structlog.get_logger()

# FastAPI app
app = FastAPI(
    title="Flowise Component Index",
    version="1.0.0",
    description="Component registry and tracking for Flowise components"
)

# Storage instance
storage: Optional[ComponentStorage] = None


@app.on_event("startup")
async def startup():
    """Initialize storage"""
    global storage

    logger.info("Starting Flowise Component Index service")

    # Initialize storage
    storage_path = os.getenv("STORAGE_PATH", "/app/data/components")
    storage = ComponentStorage(storage_path=storage_path)

    logger.info("Component storage initialized", path=storage_path)


@app.on_event("shutdown")
async def shutdown():
    """Cleanup"""
    logger.info("Shutting down Flowise Component Index")


@app.get("/api/flowise/component-index/health")
async def health_check():
    """Health check endpoint"""
    stats = storage.get_stats() if storage else {}

    return {
        "status": "healthy",
        "service": "flowise-component-index",
        "version": "1.0.0",
        "stats": stats
    }


@app.post("/api/flowise/components/register", response_model=ComponentMetadata)
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


@app.get("/api/flowise/components", response_model=ComponentListResponse)
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


@app.get("/api/flowise/components/{component_id}", response_model=ComponentMetadata)
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


@app.get("/api/flowise/components/name/{name}", response_model=ComponentMetadata)
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


@app.patch("/api/flowise/components/{component_id}/deployment")
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


@app.delete("/api/flowise/components/{component_id}")
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


@app.get("/api/flowise/components/stats")
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


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8086"))

    uvicorn.run(
        "service:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )

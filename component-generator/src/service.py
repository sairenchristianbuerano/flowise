"""
FastAPI service for Flowise Custom Component Generator

REST API service for Flowise custom component generation.
Endpoint prefix: /flowise/*
"""

import os
import yaml
from typing import Optional
import structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from flowise_agent import CustomComponentGenerator, ComponentSpec, GeneratedComponent
from flowise_feasibility_checker import FlowiseFeasibilityChecker

logger = structlog.get_logger()

# FastAPI app
app = FastAPI(
    title="Flowise Component Generator",
    version="1.0.0",
    description="Generate custom Flowise components from specifications"
)

# Agent instances
generator: Optional[CustomComponentGenerator] = None
feasibility_checker: Optional[FlowiseFeasibilityChecker] = None


class GenerateRequest(BaseModel):
    """Request model for component generation"""
    spec_yaml: str


@app.on_event("startup")
async def startup():
    """Initialize agent"""
    global generator, feasibility_checker

    logger.info("Starting Flowise Component Generator service")

    # Initialize agent
    generator = CustomComponentGenerator()
    feasibility_checker = FlowiseFeasibilityChecker()
    logger.info("Flowise Component Generator and Feasibility Checker initialized")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup"""
    logger.info("Shutting down Flowise Component Generator")


@app.get("/api/flowise/component-generator/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "flowise-component-generator",
        "version": "1.0.0"
    }


@app.post("/api/flowise/component-generator/generate")
async def generate_component_endpoint(request: GenerateRequest):
    """
    Generate custom Flowise component from YAML specification

    Request body:
    {
        "spec_yaml": "<YAML specification string>"
    }

    This endpoint generates JavaScript code for Flowise custom components.
    Deployment to tf-flowise-dev-env is optional and handled separately.
    """
    if not generator:
        raise HTTPException(status_code=503, detail="Generator not initialized")

    try:
        # Parse YAML specification
        logger.info("Parsing component specification from YAML")
        spec_dict = yaml.safe_load(request.spec_yaml)

        # Convert to ComponentSpec
        spec = ComponentSpec(**spec_dict)

        logger.info("Generating Flowise component", component=spec.name)
        result = await generator.generate_component(spec)

        logger.info(
            "Component generated successfully",
            component=spec.name,
            code_size=len(result.component_code)
        )

        return result.dict()
    except yaml.YAMLError as e:
        logger.error("YAML parsing failed", error=str(e))
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {str(e)}")
    except Exception as e:
        logger.error("Flowise component generation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/flowise/component-generator/assess")
async def assess_feasibility_endpoint(request: GenerateRequest):
    """
    Assess feasibility of generating a Flowise component before attempting generation

    Request body:
    {
        "spec_yaml": "<YAML specification string>"
    }

    Returns feasibility analysis including:
    - Whether generation is feasible
    - Confidence level (high/medium/low/blocked)
    - Issues found
    - Suggestions for improvement
    - Missing information needed
    """
    if not feasibility_checker or not generator:
        raise HTTPException(status_code=503, detail="Services not initialized")

    try:
        # Parse YAML specification
        logger.info("Parsing component specification from YAML for assessment")
        spec_dict = yaml.safe_load(request.spec_yaml)

        # Convert to ComponentSpec
        spec = ComponentSpec(**spec_dict)

        # Get RAG context for pattern matching
        rag_context = await generator._retrieve_similar_components(spec)

        # Run feasibility assessment
        assessment = await feasibility_checker.assess(
            spec.dict(),
            rag_context=rag_context
        )

        return assessment.to_dict()
    except yaml.YAMLError as e:
        logger.error("YAML parsing failed", error=str(e))
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {str(e)}")
    except Exception as e:
        logger.error("Feasibility assessment failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8085"))

    uvicorn.run(
        "service:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )

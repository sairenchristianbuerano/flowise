"""
Data models for Component Index
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ComponentMetadata(BaseModel):
    """Metadata for a generated component"""
    component_id: str = Field(..., description="Unique component identifier")
    name: str = Field(..., description="Component name (PascalCase)")
    display_name: str = Field(..., description="Human-readable display name")
    description: str = Field(..., description="Component description")
    category: str = Field(..., description="Component category")
    platform: str = Field(default="flowise", description="Target platform")
    version: str = Field(default="1.0.0", description="Component version")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    author: str = Field(..., description="Component author")
    status: str = Field(default="generated", description="Component status")
    code_size: int = Field(..., description="Size of generated code in bytes")
    dependencies: List[str] = Field(default_factory=list)
    validation_passed: bool = Field(default=False)
    deployment_status: Optional[str] = Field(None, description="Deployment status")


class ComponentRegistrationRequest(BaseModel):
    """Request to register a generated component"""
    name: str
    display_name: str
    description: str
    category: str
    platform: str = "flowise"
    version: str = "1.0.0"
    author: str
    code_size: int
    dependencies: List[str] = []
    validation_passed: bool = False
    deployment_status: Optional[str] = None


class ComponentListResponse(BaseModel):
    """Response for component list"""
    total: int
    components: List[ComponentMetadata]

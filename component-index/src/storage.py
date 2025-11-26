"""
JSON-based storage for component registry
"""

import json
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import structlog

from models import ComponentMetadata

logger = structlog.get_logger()


class ComponentStorage:
    """JSON-based component storage"""

    def __init__(self, storage_path: str = "/app/data/components"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.index_file = self.storage_path / "index.json"
        self.logger = logger.bind(storage="component_index")

        # Initialize index if not exists
        if not self.index_file.exists():
            self._save_index({})
            self.logger.info("Initialized new component index")

    def _load_index(self) -> Dict[str, Any]:
        """Load component index from JSON"""
        try:
            with open(self.index_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error("Failed to load index", error=str(e))
            return {}

    def _save_index(self, index: Dict[str, Any]):
        """Save component index to JSON"""
        try:
            with open(self.index_file, 'w') as f:
                json.dump(index, f, indent=2)
        except Exception as e:
            self.logger.error("Failed to save index", error=str(e))
            raise

    def register_component(self, metadata: ComponentMetadata) -> ComponentMetadata:
        """Register a new component"""
        index = self._load_index()

        # Generate unique ID if not provided
        if not metadata.component_id:
            metadata.component_id = str(uuid.uuid4())

        # Add to index
        index[metadata.component_id] = metadata.dict()

        self._save_index(index)
        self.logger.info("Component registered", component_id=metadata.component_id, name=metadata.name)

        return metadata

    def get_component(self, component_id: str) -> Optional[ComponentMetadata]:
        """Get component by ID"""
        index = self._load_index()

        if component_id not in index:
            return None

        return ComponentMetadata(**index[component_id])

    def get_component_by_name(self, name: str) -> Optional[ComponentMetadata]:
        """Get component by name (latest version)"""
        index = self._load_index()

        # Find all components with this name
        matching = [
            ComponentMetadata(**data)
            for cid, data in index.items()
            if data.get("name") == name
        ]

        if not matching:
            return None

        # Return most recently created
        return sorted(matching, key=lambda x: x.created_at, reverse=True)[0]

    def list_components(
        self,
        platform: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ComponentMetadata]:
        """List components with optional filters"""
        index = self._load_index()

        components = [ComponentMetadata(**data) for data in index.values()]

        # Apply filters
        if platform:
            components = [c for c in components if c.platform == platform]

        if category:
            components = [c for c in components if c.category == category]

        # Sort by created_at (newest first)
        components.sort(key=lambda x: x.created_at, reverse=True)

        # Apply pagination
        return components[offset:offset + limit]

    def update_deployment_status(self, component_id: str, status: str) -> bool:
        """Update deployment status of a component"""
        index = self._load_index()

        if component_id not in index:
            return False

        index[component_id]["deployment_status"] = status
        index[component_id]["updated_at"] = datetime.utcnow().isoformat()

        self._save_index(index)
        self.logger.info("Deployment status updated", component_id=component_id, status=status)

        return True

    def delete_component(self, component_id: str) -> bool:
        """Delete a component from index"""
        index = self._load_index()

        if component_id not in index:
            return False

        del index[component_id]
        self._save_index(index)

        self.logger.info("Component deleted", component_id=component_id)
        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        index = self._load_index()

        components = [ComponentMetadata(**data) for data in index.values()]

        stats = {
            "total_components": len(components),
            "by_platform": {},
            "by_category": {},
            "by_status": {},
            "total_code_size": sum(c.code_size for c in components)
        }

        for comp in components:
            # Count by platform
            stats["by_platform"][comp.platform] = stats["by_platform"].get(comp.platform, 0) + 1

            # Count by category
            stats["by_category"][comp.category] = stats["by_category"].get(comp.category, 0) + 1

            # Count by status
            stats["by_status"][comp.status] = stats["by_status"].get(comp.status, 0) + 1

        return stats

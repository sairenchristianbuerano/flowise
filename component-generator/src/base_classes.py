"""
Base Classes for Flowise Code Generator

Local implementation of shared base classes until proper shared-libs configuration.
"""

import asyncio
import json
import os
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import structlog
import aiohttp
from pydantic import BaseModel, Field

logger = structlog.get_logger()


class ComponentSpec(BaseModel):
    """Universal specification for a custom component to generate"""
    name: str = Field(..., description="Component class name (PascalCase)")
    display_name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="What the component does")
    category: str = Field(default="custom", description="Component category")
    platform: str = Field(default="flowise", description="Target platform")
    inputs: List[Dict[str, Any]] = Field(default_factory=list, description="Input specifications")
    outputs: List[Dict[str, Any]] = Field(default_factory=list, description="Output specifications")
    requirements: List[str] = Field(default_factory=list, description="Functional requirements")
    dependencies: List[str] = Field(default_factory=list, description="Package dependencies")
    test_data: Optional[Dict[str, Any]] = Field(None, description="Test data for validation")
    
    # Company branding and publishing metadata
    author: str = Field(default="Custom Component Developer", description="Component author/company")
    version: str = Field(default="1.0.0", description="Component version (semver)")
    license: str = Field(default="MIT", description="Component license")
    icon: str = Field(default="code", description="Component icon identifier")
    keywords: List[str] = Field(default_factory=list, description="Keywords for marketplace search")
    homepage: Optional[str] = Field(None, description="Homepage or repository URL")
    repository: Optional[str] = Field(None, description="Source code repository URL")


class GeneratedComponent(BaseModel):
    """Generated component code and metadata"""
    component_code: str = Field(..., description="Source code for the component")
    component_config: Dict[str, Any] = Field(..., description="Platform component configuration")
    dependencies: List[str] = Field(default_factory=list, description="Required packages")
    test_code: Optional[str] = Field(None, description="Unit tests for the component")
    documentation: Optional[str] = Field(None, description="Component usage documentation")
    validation: Optional[Dict[str, Any]] = Field(None, description="Component validation results")
    deployment_instructions: Optional[Dict[str, Any]] = Field(None, description="Step-by-step deployment guide")
    platform: str = Field(default="flowise", description="Target platform")
    
    # Packaging and distribution metadata
    package_json: Optional[Dict[str, Any]] = Field(None, description="NPM package.json for distribution")
    readme: Optional[str] = Field(None, description="README.md content for the component")
    changelog: Optional[str] = Field(None, description="CHANGELOG.md for version history")
    marketplace_metadata: Optional[Dict[str, Any]] = Field(None, description="Marketplace listing information")


class BaseCodeGenerator(ABC):
    """Base class for platform-specific code generators"""

    def __init__(
        self,
        agent_id: str,
        platform: str = "flowise",
        rag_url: str = None,
        platform_url: str = None
    ):
        self.agent_id = agent_id
        self.platform = platform
        self.rag_url = rag_url or os.getenv("COMPONENT_RAG_URL", "http://component-index:8086")
        self.platform_url = platform_url
        self.logger = logger.bind(agent_id=agent_id, platform=platform)
        self.max_validation_retries = 2

    async def _retrieve_similar_components(
        self,
        spec: ComponentSpec,
        n_results: int = 3
    ) -> Dict[str, Any]:
        """
        Retrieve similar components from RAG service for pattern learning.
        """
        self.logger.info(
            "Retrieving similar components from RAG",
            component=spec.name,
            description=spec.description[:100],
            platform=self.platform
        )

        try:
            # Use platform-specific RAG endpoint
            if self.platform == "flowise":
                endpoint = f"{self.rag_url}/api/flowise/component-index/patterns/similar"
            else:
                endpoint = f"{self.rag_url}/api/flowise/component-index/patterns/similar"

            # Determine input/output types from spec
            input_types = []
            output_types = []

            for inp in spec.inputs:
                if inp.get("type"):
                    input_types.append(inp["type"])

            for out in spec.outputs:
                if out.get("type"):
                    output_types.append(out["type"])

            payload = {
                "description": f"{spec.description}. {' '.join(spec.requirements[:3])}",
                "category": spec.category if spec.category != "custom" else None,
                "input_types": input_types if input_types else None,
                "output_types": output_types if output_types else None,
                "n_results": n_results,
                "platform": self.platform
            }

            timeout_config = aiohttp.ClientTimeout(total=30)

            async with aiohttp.ClientSession(timeout=timeout_config) as session:
                async with session.post(endpoint, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()

                        similar_components = result.get("results", [])

                        self.logger.info(
                            "Retrieved similar components",
                            count=len(similar_components),
                            components=[c.get("type") for c in similar_components[:3]]
                        )

                        # Extract patterns from similar components
                        if similar_components:
                            patterns = self._extract_patterns_from_similar(similar_components)

                            return {
                                "similar_components": similar_components,
                                "patterns": patterns,
                                "has_rag_context": True
                            }

                        return {"has_rag_context": False}

                    else:
                        self.logger.warning(
                            "RAG service returned error",
                            status=response.status
                        )
                        return {"has_rag_context": False}

        except Exception as e:
            self.logger.warning(
                "Failed to retrieve similar components from RAG",
                error=str(e)
            )
            return {"has_rag_context": False}

    def _extract_patterns_from_similar(
        self,
        similar_components: List[Dict]
    ) -> Dict[str, Any]:
        """Extract useful patterns from similar components - platform agnostic"""

        patterns = {
            "common_imports": set(),
            "input_examples": [],
            "output_examples": [],
            "code_snippets": []
        }

        for comp in similar_components[:2]:  # Use top 2 most similar
            # Collect imports
            for imp in comp.get("imports", [])[:5]:
                patterns["common_imports"].add(imp)

            # Collect input patterns
            for inp in comp.get("input_patterns", [])[:3]:
                patterns["input_examples"].append({
                    "name": inp.get("name"),
                    "type": inp.get("type"),
                    "display_name": inp.get("display_name")
                })

            # Collect output patterns
            for out in comp.get("output_patterns", [])[:2]:
                patterns["output_examples"].append({
                    "name": out.get("name"),
                    "type": out.get("type"),
                    "method": out.get("method")
                })

            # Get code snippet (first 40 lines)
            code = comp.get("code", "")
            if code:
                snippet_lines = code.splitlines()[:40]
                patterns["code_snippets"].append({
                    "source": comp.get("type"),
                    "snippet": "\n".join(snippet_lines)
                })

        patterns["common_imports"] = list(patterns["common_imports"])

        return patterns

    async def _call_llm(
        self,
        prompt: str,
        temperature: float = 0.3,
        timeout: int = 300
    ) -> str:
        """Call Claude API for code generation"""

        claude_model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

        self.logger.info(
            "Claude API Request",
            model=claude_model,
            temperature=temperature,
            timeout=timeout,
            platform=self.platform,
            prompt_length=len(prompt)
        )

        # Check for API key or Claude Code OAuth
        claude_api_key = os.getenv("ANTHROPIC_API_KEY")
        claude_code_token = self._load_claude_code_token()

        if claude_api_key or claude_code_token:
            return await self._call_claude(prompt, temperature, timeout)
        else:
            error_msg = (
                f"Claude API is required for {self.platform} component generation. "
                "Please set ANTHROPIC_API_KEY environment variable."
            )
            self.logger.error("Claude API not configured", error=error_msg)
            raise Exception(error_msg)

    def _load_claude_code_token(self) -> Optional[str]:
        """Load OAuth access token from Claude Code credentials"""
        import json
        from pathlib import Path

        creds_path = Path.home() / ".claude" / ".credentials.json"

        if not creds_path.exists():
            return None

        try:
            with open(creds_path, 'r') as f:
                creds = json.load(f)

            oauth_data = creds.get("claudeAiOauth", {})
            access_token = oauth_data.get("accessToken")

            if access_token:
                self.logger.info("Loaded Claude Code OAuth token")
                return access_token

        except Exception as e:
            self.logger.error("Failed to load Claude Code credentials", error=str(e))

        return None

    async def _call_claude(
        self,
        prompt: str,
        temperature: float = 0.3,
        timeout: int = 300
    ) -> str:
        """Call Claude API for code generation"""

        try:
            from anthropic import AsyncAnthropic
        except ImportError:
            raise Exception(
                "anthropic package not installed. Run: pip install anthropic"
            )

        # Check for API key first
        api_key = os.getenv("ANTHROPIC_API_KEY")

        # If no API key, try to load Claude Code OAuth tokens
        if not api_key:
            api_key = self._load_claude_code_token()

        if not api_key:
            raise Exception(
                "No authentication found. Either set ANTHROPIC_API_KEY or log in to Claude Code"
            )

        claude_model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

        client = AsyncAnthropic(api_key=api_key, timeout=float(timeout))

        try:
            message = await client.messages.create(
                model=claude_model,
                max_tokens=8192,
                temperature=temperature,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            response_text = message.content[0].text

            self.logger.info(
                "Claude Response",
                model=claude_model,
                platform=self.platform,
                response_length=len(response_text)
            )

            return response_text

        except Exception as e:
            self.logger.error("Claude API call failed", error=str(e))
            raise Exception(f"Claude API call failed: {str(e)}")

    # Abstract methods that must be implemented by platform-specific generators
    @abstractmethod
    async def generate_component(
        self,
        spec: ComponentSpec,
        context: Optional[Dict[str, Any]] = None
    ) -> GeneratedComponent:
        """Generate a custom component from specification"""
        pass

    @abstractmethod
    def _generate_platform_config(self, spec: ComponentSpec) -> Dict[str, Any]:
        """Generate platform-specific component configuration"""
        pass

    @abstractmethod
    async def _ai_generate_implementation(
        self,
        spec: ComponentSpec,
        structure: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Use LLM to generate platform-specific implementation code"""
        pass
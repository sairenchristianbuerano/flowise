"""
Custom Component Generator Agent

Generates TypeScript code for custom Flowise components when no existing component fits requirements.
Uses a coding-specialized LLM (Claude) for better code generation.
"""

import asyncio
import json
import os
import time
from typing import Dict, Any, Optional
import structlog
import aiohttp
from pydantic import BaseModel, Field

from flowise_validator import FlowiseValidator

logger = structlog.get_logger()


class ComponentSpec(BaseModel):
    """Specification for a custom component to generate"""
    name: str = Field(..., description="Component class name (PascalCase)")
    display_name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="What the component does")
    category: str = Field(default="custom", description="Component category")
    inputs: list[Dict[str, Any]] = Field(
        default_factory=list, description="Input specifications")
    outputs: list[Dict[str, Any]] = Field(
        default_factory=list, description="Output specifications")
    requirements: list[str] = Field(
        default_factory=list, description="Functional requirements")
    dependencies: list[str] = Field(
        default_factory=list, description="Package dependencies")
    test_data: Optional[Dict[str, Any]] = Field(
        None, description="Test data for validation")


class GeneratedComponent(BaseModel):
    """Generated component code and metadata"""
    component_code: str = Field(...,
                                description="TypeScript code for the component")
    core_code: Optional[str] = Field(
        None, description="Optional core.ts file for complex tool implementations")
    component_config: Dict[str,
                           Any] = Field(..., description="Flowise component configuration")
    dependencies: list[str] = Field(
        default_factory=list, description="Required packages")
    test_code: Optional[str] = Field(
        None, description="Unit tests for the component")
    documentation: Optional[str] = Field(
        None, description="Component usage documentation")
    validation: Optional[Dict[str, Any]] = Field(
        None, description="Component validation results")
    deployment_instructions: Optional[Dict[str, Any]] = Field(
        None, description="Step-by-step deployment guide")


class CustomComponentGenerator:
    """Agent for generating custom Flowise components"""

    def __init__(
        self,
        agent_id: str = "flowise_codegen",
        rag_url: str = None,
        flowise_url: str = None
    ):
        self.agent_id = agent_id
        self.rag_url = rag_url or os.getenv(
            "COMPONENT_RAG_URL", "http://component-index:8086")
        self.flowise_url = flowise_url or os.getenv(
            "FLOWISE_URL", "http://flowise:3000")
        self.logger = logger.bind(agent_id=agent_id)

        # Initialize component validator with Flowise URL
        self.validator = FlowiseValidator(flowise_url=self.flowise_url)
        self.max_validation_retries = 0  # Disabled validation retries to save credits

        # Load component generation templates
        self._load_templates()

    def _load_templates(self):
        """Load Flowise TypeScript component generation templates"""
        self.base_component_template = '''
import {{ INode, INodeData, INodeParams }} from '../../../src/Interface'
{additional_imports}

class {component_name} implements INode {{
    label: string
    name: string
    version: number
    type: string
    icon: string
    category: string
    description: string
    baseClasses: string[]
    author: string
    inputs: INodeParams[]
    
    constructor() {{
        this.label = '{display_name}'
        this.name = '{component_name_lower}'
        this.version = {version}
        this.type = '{component_name}'
        this.icon = '{icon}'
        this.category = '{category}'
        this.description = `{description}`
        this.baseClasses = [this.type]
        this.author = '{author}'
        this.inputs = [
{input_definitions}
        ]
    }}
    
    async init(nodeData: INodeData, _: string, options: {{ componentNodes: any }}): Promise<{return_type}> {{
        /**
         * {method_description}
         */
{implementation}
        
        return result
    }}
}}

module.exports = {{ nodeClass: {component_name} }}
'''

        # Tools-specific template for category: "Tools"
        # Returns Flowise's custom DynamicStructuredTool for AgentFlow compatibility
        self.tools_component_template = '''
import {{ INode, INodeData, INodeParams }} from '../../../src/Interface'
import {{ DynamicStructuredTool }} from '../CustomTool/core'
import {{ z }} from 'zod'
{additional_imports}

const code = `
{implementation}
`

class {component_name} implements INode {{
    label: string
    name: string
    version: number
    type: string
    icon: string
    category: string
    description: string
    baseClasses: string[]
    author: string
    inputs: INodeParams[]

    constructor() {{
        this.label = '{display_name}'
        this.name = '{component_name_lower}'
        this.version = {version}
        this.type = '{component_name}'
        this.icon = '{icon}'
        this.category = '{category}'
        this.description = `{description}`
        this.baseClasses = [this.type, 'Tool']
        this.author = '{author}'
        this.inputs = [
{input_definitions}
        ]
    }}

    async init(nodeData: INodeData): Promise<any> {{
        // Extract configuration from nodeData
{input_extractions}

        return new DynamicStructuredTool({{
            name: '{component_name_lower}',
            description: `{description}`,
            schema: z.object({{
{schema_definitions}
            }}),
            code: code
        }})
    }}
{helper_methods}
}}

module.exports = {{ nodeClass: {component_name} }}
'''

        # Custom Tool Class template (USER'S PROVEN PATTERN - PRIMARY for complex tools)
        # Extends Tool from @langchain/core/tools with proper OOP structure
        self.custom_tool_class_template = '''
import {{ INode, INodeData, INodeParams }} from '../../../src/Interface'
import {{ Tool }} from '@langchain/core/tools'
import {{ handleErrorMessage }} from '../../../src/utils'
{validation_imports}
{additional_imports}

class {component_name} implements INode {{
    label: string
    name: string
    version: number
    type: string
    icon: string
    category: string
    description: string
    author: string
    baseClasses: string[]
    inputs: INodeParams[]

    constructor() {{
        this.label = '{display_name}'
        this.name = '{component_name_lower}'
        this.version = {version}
        this.type = '{component_name}'
        this.icon = '{icon}'
        this.category = 'Tools'
        this.author = '{author}'
        this.description = `{description}`
        this.baseClasses = ['Tool', 'StructuredTool']
        this.inputs = [
{input_definitions}
        ]
    }}

    async init(nodeData: INodeData): Promise<Tool> {{
        try {{
{input_extractions}

            const tool = new {component_name}CustomTool({{
                name: '{component_name_lower}',
                description: `{description}`{constructor_params}
            }})

            return tool
        }} catch (error) {{
            throw new Error(`Failed to initialize {display_name}: ${{error.message}}`)
        }}
    }}
}}

class {component_name}CustomTool extends Tool {{
    name: string
    description: string
{tool_properties}

    constructor(fields: {{ name: string; description: string{constructor_fields} }}) {{
        super()
        this.name = fields.name
        this.description = fields.description
{property_assignments}
    }}

{helper_methods}

    async _call(input: string): Promise<string> {{
        try {{
{implementation}
        }} catch (error) {{
            if (error instanceof Error) {{
                throw new Error(`{display_name} error: ${{error.message}}`)
            }}
            throw new Error('An unexpected error occurred')
        }}
    }}
}}

module.exports = {{ nodeClass: {component_name} }}
'''

        self.logger.info("Loaded component generation templates")

    def _get_custom_tool_class_guidance(self) -> str:
        """Get guidance for Custom Tool Class pattern (user's proven best example)"""
        return '''
**PATTERN: Custom Tool Class** (USER'S PROVEN PATTERN - Works in production Flowise & AgentFlow)

This pattern extends Tool from @langchain/core/tools for proper OOP structure.

✅ REQUIRED IMPORTS:
```typescript
import { INode, INodeData, INodeParams } from '../../../src/Interface'
import { Tool } from '@langchain/core/tools'
// Add external library imports if needed:
// import { Parser } from 'expr-eval'
```

✅ REQUIRED STRUCTURE (Two classes):

**Class 1: INode Wrapper** (Flowise integration)
```typescript
class ComponentName implements INode {
    label: string
    name: string
    version: number
    type: string
    icon: string
    category: string
    description: string
    author: string
    baseClasses: string[]  // CRITICAL: Use ['Tool', 'StructuredTool']
    inputs: INodeParams[]

    constructor() {
        this.label = 'Display Name'
        this.name = 'componentName'
        this.version = 1.0
        this.type = 'ComponentName'
        this.icon = 'icon.svg'
        this.category = 'Tools'
        this.author = 'Component Factory'
        this.description = 'What it does'
        this.baseClasses = ['Tool', 'StructuredTool']  // MUST be static array
        this.inputs = [  // Configuration inputs (optional)
            {
                label: 'Tool Name',
                name: 'name',
                type: 'string',
                default: 'tool_name'
            }
        ]
    }

    async init(nodeData: INodeData): Promise<Tool> {
        try {
            // Extract configuration from nodeData.inputs
            const name = nodeData.inputs?.name as string
            const description = nodeData.inputs?.description as string

            // Validate inputs if needed
            if (name && typeof name !== 'string') {
                throw new Error('Name must be a string')
            }

            // Return instance of custom tool class
            const tool = new ComponentNameCustomTool({
                name: name || 'default_name',
                description: description || 'Default description'
            })

            return tool
        } catch (error) {
            throw new Error(`Failed to initialize: ${error.message}`)
        }
    }
}
```

**Class 2: Custom Tool Implementation** (Business logic)
```typescript
class ComponentNameCustomTool extends Tool {
    name: string
    description: string
    // Add other properties as needed (e.g., parser, config, state)

    constructor(fields: { name: string; description: string }) {
        super()
        this.name = fields.name
        this.description = fields.description
        // Initialize other properties
    }

    // Private helper methods for organization
    private _validateInput(input: string): boolean {
        if (!input || typeof input !== 'string') {
            return false
        }
        // Add validation logic
        return true
    }

    private _sanitizeInput(input: string): string {
        return input.trim()
    }

    // Main execution method - REQUIRED
    async _call(input: string): Promise<string> {
        try {
            // Validate input
            if (!this._validateInput(input)) {
                throw new Error('Invalid input')
            }

            // Sanitize input
            const sanitized = this._sanitizeInput(input)

            // Business logic here
            const result = // ... your logic ...

            // Return string result
            return result.toString()
        } catch (error) {
            if (error instanceof Error) {
                throw new Error(`ComponentName error: ${error.message}`)
            }
            throw new Error('An unexpected error occurred')
        }
    }
}
```

**CRITICAL RULES:**
1. baseClasses MUST be ['Tool', 'StructuredTool'] (static array, not dynamic)
2. category MUST ALWAYS be 'Tools' (hardcoded, not variable)
3. init() returns Promise<Tool> (not Promise<any>)
4. Custom class extends Tool (not DynamicTool, not StructuredTool)
5. Custom class MUST implement async _call(input: string): Promise<string>
6. Use private helper methods for organization
7. Add proper error handling in _call method
8. Can import and use external libraries (e.g., expr-eval, but NOT mathjs)
9. Full TypeScript - compile-time type checking

**When to use this pattern:**
- Component has external dependencies
- Complex validation or parsing logic needed
- Multiple helper methods required
- Advanced error handling needed
- Better code organization desired

---

**✅ OFFICIAL FLOWISE VALIDATION UTILITIES**

Import validators from official Flowise repository (proven in production):

```typescript
// Validation utilities from Flowise
import { isValidUUID, isValidURL, isPathTraversal, isUnsafeFilePath } from '../../../src/validator'
// Utility functions from Flowise
import { handleErrorMessage, parseJsonBody, getCredentialData, getCredentialParam } from '../../../src/utils'
```

**UUID Validation Example:**
```typescript
async init(nodeData: INodeData): Promise<Tool> {
    try {
        const chatflowId = nodeData.inputs?.chatflowId as string

        // Validate UUID format
        if (chatflowId && !isValidUUID(chatflowId)) {
            throw new Error('Invalid chatflow ID format - must be a valid UUID')
        }

        const tool = new MyCustomTool({ chatflowId })
        return tool
    } catch (error) {
        throw new Error(`Failed to initialize: ${handleErrorMessage(error)}`)
    }
}
```

**URL Validation Example:**
```typescript
async init(nodeData: INodeData): Promise<Tool> {
    try {
        const endpoint = nodeData.inputs?.endpoint as string

        // Validate URL format
        if (!endpoint) {
            throw new Error('Endpoint URL is required')
        }
        if (!isValidURL(endpoint)) {
            throw new Error('Invalid endpoint URL format')
        }

        const tool = new APICallerTool({ endpoint })
        return tool
    } catch (error) {
        throw new Error(`Failed to initialize: ${handleErrorMessage(error)}`)
    }
}
```

**File Path Security Example:**
```typescript
private _validateFilePath(filePath: string): void {
    if (!filePath) {
        throw new Error('File path is required')
    }

    // Check for unsafe file path patterns
    if (isUnsafeFilePath(filePath)) {
        throw new Error('Unsafe file path detected - potential security risk')
    }

    // Check for path traversal attempts
    if (isPathTraversal(filePath)) {
        throw new Error('Path traversal attempt detected')
    }
}
```

**Input Validation & Sanitization Example:**
```typescript
class MyCustomTool extends Tool {
    // ...

    private _validateAndSanitizeInput(input: string): string {
        // Basic validation
        if (!input || typeof input !== 'string') {
            throw new Error('Input must be a non-empty string')
        }

        // Trim and normalize
        const sanitized = input.trim()

        if (sanitized.length === 0) {
            throw new Error('Input cannot be empty after trimming')
        }

        // Check for potential injection attempts
        if (sanitized.includes('<script') || sanitized.includes('javascript:')) {
            throw new Error('Invalid input detected - potential XSS attempt')
        }

        return sanitized
    }

    async _call(input: string): Promise<string> {
        try {
            // Validate and sanitize
            const validated = this._validateAndSanitizeInput(input)

            // Process validated input
            const result = await this._processInput(validated)

            return result.toString()
        } catch (error) {
            // Use official error handler for consistent formatting
            throw new Error(`Tool error: ${handleErrorMessage(error)}`)
        }
    }
}
```

**Complete Example with Multiple Validations:**
```typescript
import { INode, INodeData, INodeParams } from '../../../src/Interface'
import { Tool } from '@langchain/core/tools'
import { handleErrorMessage } from '../../../src/utils'
import { isValidURL, isValidUUID } from '../../../src/validator'

class APICaller implements INode {
    label: string
    name: string
    version: number
    type: string
    icon: string
    category: string
    description: string
    author: string
    baseClasses: string[]
    inputs: INodeParams[]

    constructor() {
        this.label = 'API Caller'
        this.name = 'apiCaller'
        this.version = 1.0
        this.type = 'APICaller'
        this.icon = 'api.svg'
        this.category = 'Tools'  // MUST ALWAYS be 'Tools'
        this.author = 'Component Factory'
        this.description = 'Call external API endpoints'
        this.baseClasses = ['Tool', 'StructuredTool']
        this.inputs = [
            {
                label: 'API Endpoint',
                name: 'endpoint',
                type: 'string',
                placeholder: 'https://api.example.com'
            },
            {
                label: 'Chatflow ID',
                name: 'chatflowId',
                type: 'string',
                optional: true
            }
        ]
    }

    async init(nodeData: INodeData): Promise<Tool> {
        try {
            const endpoint = nodeData.inputs?.endpoint as string
            const chatflowId = nodeData.inputs?.chatflowId as string

            // Validate required inputs
            if (!endpoint) {
                throw new Error('API endpoint is required')
            }

            // Validate URL format
            if (!isValidURL(endpoint)) {
                throw new Error('Invalid API endpoint URL')
            }

            // Validate optional UUID if provided
            if (chatflowId && !isValidUUID(chatflowId)) {
                throw new Error('Invalid chatflow ID format')
            }

            const tool = new APICallerCustomTool({
                endpoint,
                chatflowId: chatflowId || null
            })

            return tool
        } catch (error) {
            throw new Error(`Failed to initialize API Caller: ${handleErrorMessage(error)}`)
        }
    }
}

class APICallerCustomTool extends Tool {
    endpoint: string
    chatflowId: string | null

    constructor(fields: { endpoint: string; chatflowId: string | null }) {
        super()
        this.name = 'api_caller'
        this.description = 'Call external API endpoints'
        this.endpoint = fields.endpoint
        this.chatflowId = fields.chatflowId
    }

    private _validateInput(input: string): boolean {
        return input && typeof input === 'string' && input.trim().length > 0
    }

    async _call(input: string): Promise<string> {
        try {
            if (!this._validateInput(input)) {
                throw new Error('Invalid input: must be a non-empty string')
            }

            // Make API call
            const response = await fetch(this.endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: input.trim() })
            })

            if (!response.ok) {
                throw new Error(`API request failed: ${response.statusText}`)
            }

            return await response.text()
        } catch (error) {
            throw new Error(`API Caller error: ${handleErrorMessage(error)}`)
        }
    }
}

module.exports = { nodeClass: APICaller }
```

**VALIDATION CHECKLIST:**
☑ Import validators from '../../../src/validator'
☑ Import handleErrorMessage from '../../../src/utils'
☑ Validate all external inputs (URLs, UUIDs, file paths)
☑ Sanitize user input before processing
☑ Use handleErrorMessage() for consistent error formatting
☑ Add private validation methods (_validateX, _sanitizeX)
☑ Validate in both init() and _call() where appropriate
☑ Throw descriptive errors with context
☑ Wrap init() and _call() in try-catch blocks
☑ Check for null/undefined before processing

---

**❌ FORBIDDEN IMPORTS - DO NOT USE**

These libraries are NOT supported in Flowise and MUST NOT be imported:

```typescript
// ❌ FORBIDDEN - These will cause runtime errors in Flowise
import { evaluate } from 'mathjs'           // NOT SUPPORTED
import * as math from 'mathjs'              // NOT SUPPORTED
import mathjs from 'mathjs'                 // NOT SUPPORTED
import { create, all } from 'mathjs'        // NOT SUPPORTED
```

**For mathematical operations, use native JavaScript instead:**

```typescript
// ✅ CORRECT - Use native JavaScript Math
class CalculatorCustomTool extends Tool {
    private _evaluateExpression(expression: string): number {
        // Use native eval with validation (safe for mathematical expressions only)
        // Validate input first to prevent code injection
        if (!/^[0-9+\\-*/().\\s]+$/.test(expression)) {
            throw new Error('Invalid expression - only numbers and operators allowed')
        }

        try {
            const result = eval(expression)
            return Number(result)
        } catch (error) {
            throw new Error(`Calculation error: ${handleErrorMessage(error)}`)
        }
    }

    // Or use Math object for specific operations
    private _calculate(operation: string, value: number): number {
        switch (operation) {
            case 'sqrt':
                return Math.sqrt(value)
            case 'abs':
                return Math.abs(value)
            case 'round':
                return Math.round(value)
            case 'floor':
                return Math.floor(value)
            case 'ceil':
                return Math.ceil(value)
            default:
                throw new Error(`Unknown operation: ${operation}`)
        }
    }
}
```

**Other unsupported libraries to avoid:**
- ❌ `mathjs` - Use native JavaScript Math
- ❌ `moment` - Use native Date or import from '@langchain/community' if needed
- ❌ `lodash` - Use native JavaScript array/object methods
- ❌ `jquery` - Not applicable in Node.js backend
- ❌ `axios` - Use native fetch() instead

**Supported external libraries (safe to use):**
- ✅ `expr-eval` - Expression parser (SUPPORTED in Flowise)
- ✅ Libraries from `@langchain/core`
- ✅ Libraries from `@langchain/community`
- ✅ Native Node.js modules (fs, path, crypto, etc.)
- ✅ Libraries already in Flowise dependencies

**CRITICAL: Always check if a library is available in Flowise before importing!**

'''

    def _get_dynamic_tool_guidance(self) -> str:
        """Get guidance for DynamicStructuredTool pattern (simple tools only)"""
        return '''
**PATTERN: DynamicStructuredTool** (For SIMPLE tools only - no dependencies)

Only use this pattern for trivial cases (string manipulation, basic formatting).

✅ REQUIRED IMPORTS:
```typescript
import { DynamicStructuredTool } from '../CustomTool/core'
import { z } from 'zod'
```

✅ PATTERN:
```typescript
const code = `
// JavaScript code as string
const result = $input + " processed"
return result
`

class MyTool_Tools implements INode {
    baseClasses = [this.type, 'Tool']

    async init(nodeData: INodeData): Promise<any> {
        return new DynamicStructuredTool({
            name: 'tool_name',
            description: 'What it does',
            schema: z.object({
                input: z.string().describe('Input description')
            }),
            code: code
        })
    }
}
```

**Use only when:**
- No external dependencies
- Simple string manipulation
- Less than 10 lines of logic
- No complex validation needed

**Otherwise, use Custom Tool Class pattern above.**
'''

    def _should_use_custom_tool_class(self, spec: ComponentSpec) -> bool:
        """
        Determine if component should use Custom Tool Class pattern (user's proven pattern)
        or simpler DynamicStructuredTool pattern.

        Custom Tool Class is PREFERRED for most cases, especially:
        - Components with external dependencies
        - Complex validation/parsing logic
        - Multiple helper methods needed
        - Advanced error handling

        Returns True to use Custom Tool Class (recommended for 90% of cases)
        Returns False to use DynamicStructuredTool (only for trivial cases)
        """

        # Use Custom Tool Class if has external dependencies
        if spec.dependencies and len(spec.dependencies) > 0:
            self.logger.info("Using Custom Tool Class pattern: has dependencies",
                           deps=spec.dependencies)
            return True

        # Calculate complexity score
        complexity_score = 0

        # Check requirements complexity
        requirements_text = " ".join(spec.requirements).lower()

        # Keywords indicating complexity (need Custom Tool Class)
        complex_keywords = [
            "validate", "validation", "parse", "parser", "sanitize",
            "format", "transform", "convert", "calculate", "process",
            "library", "external", "api", "http", "database",
            "error handling", "try-catch", "exception"
        ]

        for keyword in complex_keywords:
            if keyword in requirements_text:
                complexity_score += 1

        # Multiple requirements suggest complexity
        complexity_score += len(spec.requirements)

        # Multiple inputs suggest structured tool
        complexity_score += len(spec.inputs) * 2

        # Decision logic - PREFER Custom Tool Class
        if complexity_score >= 3:
            self.logger.info("Using Custom Tool Class pattern: complexity score high",
                           score=complexity_score)
            return True

        # Only use DynamicStructuredTool for trivial cases
        if complexity_score <= 2 and len(spec.requirements) <= 1 and not spec.inputs:
            self.logger.info("Using DynamicStructuredTool pattern: trivial case",
                           score=complexity_score)
            return False

        # Default to Custom Tool Class (user's proven pattern)
        self.logger.info("Using Custom Tool Class pattern: default choice",
                       score=complexity_score)
        return True

    def _detect_validation_needs(self, spec: ComponentSpec) -> Dict[str, bool]:
        """
        Detect which official Flowise validators are needed based on component spec.

        Analyzes requirements and inputs to determine which validation utilities
        from the official Flowise repository should be imported.

        Returns:
            Dict mapping validator names to boolean indicating if needed
        """
        # Combine requirements and inputs for analysis
        requirements_text = " ".join(spec.requirements).lower() if spec.requirements else ""
        inputs_text = json.dumps(spec.inputs).lower() if spec.inputs else ""
        combined = requirements_text + " " + inputs_text

        self.logger.debug("Detecting validation needs",
                         requirements=spec.requirements,
                         inputs_count=len(spec.inputs))

        validation_needs = {
            # UUID validation - for chatflow IDs, agent IDs, flow IDs
            'isValidUUID': any(term in combined for term in [
                'uuid', 'chatflow id', 'flow id', 'agent id', 'flowid',
                'chatflowid', 'agentid', 'id'
            ]) and 'uuid' in combined,

            # URL validation - for endpoints, webhooks, APIs
            'isValidURL': any(term in combined for term in [
                'url', 'endpoint', 'api', 'webhook', 'http', 'https',
                'uri', 'link', 'web'
            ]),

            # Path traversal detection - for file operations
            'isPathTraversal': any(term in combined for term in [
                'path', 'file path', 'directory', 'folder'
            ]) and any(term in combined for term in ['file', 'path']),

            # Unsafe file path detection - for file uploads/downloads
            'isUnsafeFilePath': any(term in combined for term in [
                'file path', 'upload', 'download', 'read file', 'write file',
                'file system', 'filepath'
            ]),

            # Error message handler - always useful for consistent error formatting
            'handleErrorMessage': True  # Always include for professional error handling
        }

        # Log detected needs
        needed_validators = [name for name, needed in validation_needs.items() if needed and name != 'handleErrorMessage']
        if needed_validators:
            self.logger.info("Detected validation needs", validators=needed_validators)

        return validation_needs

    async def _retrieve_similar_components(
        self,
        spec: ComponentSpec,
        n_results: int = 3
    ) -> Dict[str, Any]:
        """
        Retrieve similar components from RAG service for pattern learning.

        Args:
            spec: Component specification
            n_results: Number of similar components to retrieve

        Returns:
            Dictionary with similar components and extracted patterns
        """
        self.logger.info(
            "Retrieving similar components from RAG",
            component=spec.name,
            description=spec.description[:100]
        )

        try:
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
                "platform": "flowise"
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
                            components=[c.get("type")
                                        for c in similar_components[:3]]
                        )

                        # Extract patterns from similar components
                        if similar_components:
                            patterns = self._extract_patterns_from_similar(
                                similar_components)

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
        similar_components: list
    ) -> Dict[str, Any]:
        """Extract useful patterns from similar components"""

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

    async def generate_component(
        self,
        spec: ComponentSpec,
        context: Optional[Dict[str, Any]] = None
    ) -> GeneratedComponent:
        """
        Generate a custom Flowise component from specification

        Args:
            spec: Component specification
            context: Additional context (existing components, patterns, etc.)

        Returns:
            GeneratedComponent with TypeScript component code, config, and metadata
        """
        start_time = time.time()
        self.logger.info("Starting Flowise component generation",
                         component_name=spec.name)

        try:
            # Step 0: Retrieve similar components from RAG for pattern learning
            rag_context = await self._retrieve_similar_components(spec)

            # Merge RAG context with provided context
            if context is None:
                context = {}
            context["rag"] = rag_context

            # Step 1: Generate component structure
            component_structure = await self._ai_generate_structure(spec, context)

            # Step 2: Generate implementation code
            self.logger.info("=" * 80)
            self.logger.info("Generating component implementation...")
            self.logger.info("=" * 80)

            component_code = await self._ai_generate_implementation(
                spec, component_structure, context
            )

            # Log the generated component code
            self.logger.info("=" * 80)
            self.logger.info(f"Generated {spec.name}.ts:")
            self.logger.info("=" * 80)
            print(component_code)  # Print to stdout for docker logs
            print("=" * 80)

            # Step 2.5: Apply automatic fixes BEFORE validation
            self.logger.info("Applying automatic fixes to generated code...")
            component_code = self._auto_fix_component_issues(component_code)

            # Step 3: Generate component configuration
            component_config = self._generate_flowise_config(spec)

            # Step 4: Generate tests (DISABLED TO SAVE CREDITS)
            # test_code = await self._ai_generate_tests(spec, component_code)
            test_code = "# Test generation disabled to save Claude API credits"

            # Step 5: Generate documentation
            documentation = await self._ai_generate_documentation(spec, component_code)
            # documentation = "# Documentation generation disabled to save Claude API credits"  # DISABLED TO SAVE CREDITS

            # Step 6: Validate generated code with comprehensive validation
            component_code, validation_details = await self._validate_and_fix_component(
                component_code,
                spec
            )

            # Step 7: Run functional tests with test data if provided (DISABLED TO SAVE CREDITS)
            # if spec.test_data:
            #     test_results = await self._run_functional_tests(
            #         component_code,
            #         spec
            #     )
            #     validation_details["functional_tests"] = test_results

            execution_time = time.time() - start_time
            self.logger.info(
                "Component generation completed",
                component_name=spec.name,
                execution_time=execution_time,
                validation_passed=validation_details.get("is_valid", False)
            )

            # Step 7: Generate deployment instructions
            deployment_instructions = self._generate_flowise_deployment_instructions(
                spec)

            return GeneratedComponent(
                component_code=component_code,
                core_code=None,  # TODO: Generate core.ts for complex tools if needed
                component_config=component_config,
                dependencies=spec.dependencies,
                test_code=test_code,
                documentation=documentation,
                validation=validation_details,
                deployment_instructions=deployment_instructions
            )

        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(
                "Component generation failed",
                component_name=spec.name,
                error=str(e),
                execution_time=execution_time
            )
            raise

    async def _ai_generate_structure(
        self,
        spec: ComponentSpec,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Use LLM to generate component structure"""

        prompt = f"""
You are an expert at designing Flowise custom components.

Component Specification:
- Name: {spec.name}
- Description: {spec.description}
- Category: {spec.category}
- Inputs: {json.dumps(spec.inputs, indent=2)}
- Outputs: {json.dumps(spec.outputs, indent=2)}
- Requirements: {json.dumps(spec.requirements, indent=2)}

Design the Flowise component structure:
1. Determine required imports and dependencies
2. Define input parameters (INodeParams)
3. Define expected return type
4. Plan the init() method logic
5. Identify helper methods needed
6. Specify branding information (author, version, license)

Return ONLY a JSON object with this structure:
{{
  "imports": ["axios", "fs", "path"],
  "input_fields": [
    {{"name": "inputText", "label": "Input Text", "type": "string", "placeholder": "Enter text..."}}
  ],
  "return_type": "string",
  "helper_methods": ["_parseInput", "_validateData"],
  "implementation_steps": ["step 1", "step 2"],
  "branding": {{
    "author": "Company Name",
    "version": "1.0.0",
    "license": "MIT",
    "icon": "code"
  }}
}}
"""

        response = await self._call_llm(prompt, temperature=0.2)

        try:
            # Clean and parse response
            response_clean = response.strip()
            if "```json" in response_clean:
                response_clean = response_clean.split(
                    "```json")[1].split("```")[0].strip()
            elif "```" in response_clean:
                response_clean = response_clean.split(
                    "```")[1].split("```")[0].strip()

            structure = json.loads(response_clean)
            return structure

        except json.JSONDecodeError as e:
            self.logger.error("Failed to parse structure JSON", error=str(e))
            # Fallback structure
            return {
                "imports": ["axios"],
                "input_fields": [
                    {"name": "inputData", "label": "Input Data",
                        "type": "string", "placeholder": "Enter data..."}
                ],
                "return_type": "string",
                "helper_methods": [],
                "implementation_steps": ["Process input", "Return result"],
                "branding": {
                    "author": "Custom Component",
                    "version": "1.0.0",
                    "license": "MIT",
                    "icon": "code"
                }
            }

    async def _ai_generate_implementation(
        self,
        spec: ComponentSpec,
        structure: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Use LLM to generate complete component implementation"""

        # Detect if this is a Tool component
        is_tool_component = spec.category.lower() == "tools"

        # Determine which pattern to use (Custom Tool Class vs DynamicStructuredTool)
        use_custom_tool_class = False
        if is_tool_component:
            use_custom_tool_class = self._should_use_custom_tool_class(spec)

        # Detect validation needs and build imports for official Flowise validators
        validation_imports_str = ""
        if is_tool_component and use_custom_tool_class:
            validation_needs = self._detect_validation_needs(spec)

            # Build list of validators to import (excluding handleErrorMessage which is in utils)
            validators_to_import = [
                name for name, needed in validation_needs.items()
                if needed and name != 'handleErrorMessage'
            ]

            if validators_to_import:
                validation_imports_str = f"import {{ {', '.join(validators_to_import)} }} from '../../../src/validator'"
                self.logger.info("Adding official Flowise validators",
                               validators=validators_to_import)

        self.logger.info(
            "Generating implementation",
            component=spec.name,
            category=spec.category,
            is_tool=is_tool_component,
            pattern="CustomToolClass" if use_custom_tool_class else "DynamicStructuredTool" if is_tool_component else "Standard"
        )

        # Build RAG context section if available
        rag_context_section = ""
        if context and context.get("rag", {}).get("has_rag_context"):
            rag_data = context["rag"]
            patterns = rag_data.get("patterns", {})

            rag_context_section = "\n**SIMILAR FLOWISE TOOL PATTERNS (for reference):**\n\n"

            # Add common imports
            if patterns.get("common_imports"):
                rag_context_section += "Common imports found in similar tools:\n"
                for imp in patterns["common_imports"][:5]:
                    rag_context_section += f"- {imp}\n"
                rag_context_section += "\n"

            # Add input examples
            if patterns.get("input_examples"):
                rag_context_section += "Input pattern examples:\n"
                for inp in patterns["input_examples"][:3]:
                    rag_context_section += f"- {inp.get('name')}: {inp.get('type')} ({inp.get('display_name')})\n"
                rag_context_section += "\n"

            # Add code snippet from most similar component
            if patterns.get("code_snippets") and len(patterns["code_snippets"]) > 0:
                snippet_data = patterns["code_snippets"][0]
                rag_context_section += f"Example component structure (from {snippet_data['source']}):\n"
                rag_context_section += f"```typescript\n{snippet_data['snippet']}\n```\n\n"

        # Build category-specific guidance for Tools
        category_guidance = ""
        if is_tool_component:
            # Choose guidance based on complexity
            if use_custom_tool_class:
                category_guidance = self._get_custom_tool_class_guidance()
            else:
                category_guidance = self._get_dynamic_tool_guidance()

        # OLD GUIDANCE BELOW - KEEPING FOR REFERENCE THEN WILL DELETE
        if False:  # DISABLED - using new guidance methods above
            category_guidance_old = """
**CRITICAL: This is a TOOLS component - You MUST use Flowise's custom DynamicStructuredTool pattern:**

⚠️ ABSOLUTELY FORBIDDEN:
- NEVER use `import {{ Tool }} from '@langchain/core/tools'` - Tool is ABSTRACT
- NEVER use `import {{ DynamicStructuredTool }} from '@langchain/core/tools'` - this is LangChain's version, NOT Flowise's
- NEVER use `new Tool({{...}})` - this will FAIL at runtime
- NEVER use `func: async (input) => {{}}` pattern - that's LangChain, not Flowise

✅ REQUIRED IMPORTS for Flowise custom tools:
```typescript
import {{ DynamicStructuredTool }} from '../CustomTool/core'
import {{ z }} from 'zod'
```

✅ REQUIRED PATTERN (this is the ONLY valid pattern for Flowise custom tools):
```typescript
// 1. Define code as a string OUTSIDE the class
const code = `
// STANDARDIZED PATTERN: Always use $input for the primary input parameter
// Example: if schema has "input", access it as $input
const result = $input + " processed"

// Add your business logic here
// You can use JavaScript, not TypeScript

return result  // MUST return a value
`

class MyTool_Tools implements INode {{
    label: string
    name: string
    type: string
    baseClasses: string[]  // REQUIRED property
    // ... other properties ...

    constructor() {{
        this.label = 'My Tool'
        this.name = 'myTool'
        this.type = 'MyTool'
        this.baseClasses = [this.type, 'Tool']  // CRITICAL: MUST include this line!
        // ... other assignments ...
    }}

    async init(nodeData: INodeData): Promise<any> {{
        try {{
            // Extract any configuration from nodeData if needed (optional)
            const someConfig = nodeData.inputs?.configParam as string

            // Validate configuration if needed
            if (someConfig && typeof someConfig !== 'string') {{
                throw new Error('Invalid configuration: configParam must be a string')
            }}

            return new DynamicStructuredTool({{
                name: 'tool_name',
                description: 'Clear description of what this tool does',
                schema: z.object({{
                    input: z.string().describe('Semantic description of what this input represents')
                }}),
                code: code  // Pass the code string, NOT a function
            }})
        }} catch (error) {{
            throw new Error(`Failed to initialize tool: ${{error.message}}`)
        }}
    }}
}}
```

**CRITICAL RULES for Flowise Tools:**
1. Import from '../CustomTool/core', NOT from '@langchain/core/tools'
2. **MANDATORY**: Constructor MUST include `this.baseClasses = [this.type, 'Tool']` assignment
3. Business logic goes in a `code` string (JavaScript), NOT in a `func` function
4. **STANDARDIZED NAMING**: For simple tools with one main input, ALWAYS use `input` as the parameter name in schema
5. Access input parameter as `$input` in the code string (e.g., schema field `input` becomes `$input`)
6. The parameter's `.describe()` should explain WHAT the input represents semantically (e.g., 'Mathematical expression to evaluate', 'Text to transform', 'URL to fetch')
7. The code string is executed in a sandbox at runtime
8. The code MUST return a value (string or object that will be JSON.stringify'd)
9. Use JavaScript syntax in code string, NOT TypeScript
10. Define the code string OUTSIDE the class, then pass it to DynamicStructuredTool constructor
11. **MANDATORY ERROR HANDLING**: Wrap init() method body in try-catch block
12. **MANDATORY VALIDATION**: If component has inputs, validate them with throw new Error() for invalid values
13. **MANDATORY INPUT ACCESS**: If component defines inputs in constructor, MUST access them via nodeData.inputs

**Example - Calculator Tool with standardized input:**
```typescript
const code = `
// Access the input using $input (standardized parameter name)
const result = eval($input)
return String(result)
`

class Calculator_Tools implements INode {{
    constructor() {{
        this.label = 'Calculator'
        this.name = 'calculator'
        this.type = 'Calculator'
        this.baseClasses = [this.type, 'Tool']
        // ... other properties
    }}

    async init(nodeData: INodeData): Promise<any> {{
        try {{
            // Access nodeData.inputs if you have configuration inputs
            // const someInput = nodeData.inputs?.someInput as string

            return new DynamicStructuredTool({{
                name: 'calculator',
                description: 'Evaluate mathematical expressions',
                schema: z.object({{
                    input: z.string().describe('Mathematical expression to evaluate using standard operators')
                }}),
                code: code
            }})
        }} catch (error) {{
            throw new Error(`Failed to initialize calculator: ${{error.message}}`)
        }}
    }}
}}
```

**Example - Text Transformer Tool:**
```typescript
const code = `
// Access the input using $input (standardized parameter name)
const transformed = $input.toUpperCase()
return transformed
`

// In init():
return new DynamicStructuredTool({{
    name: 'text_transformer',
    description: 'Transform text to uppercase',
    schema: z.object({{
        input: z.string().describe('Text to transform to uppercase')
    }}),
    code: code
}})
```

**Example from Flowise's CurrentDateTime tool (no inputs):**
```typescript
const code = `
const now = new Date();
const date = now.toISOString().split('T')[0];
return {{
    date: date,
    time: now.toTimeString().split(' ')[0]
}};
`

// Then in init():
return new DynamicStructuredTool({{
    name: 'current_date_time',
    description: 'Get current date and time',
    schema: z.object({{}}),  // No inputs needed
    code: code
}})
```

NOTE: Pre-built tools like Calculator use direct imports from @langchain/community (e.g., `new Calculator()`).
For CUSTOM tools with your own logic, you MUST use Flowise's DynamicStructuredTool with code-as-string pattern.

"""

        # Build calculator pattern section (before f-string to avoid backslash issues)
        is_calculator = 'calculat' in spec.name.lower() or 'calculat' in spec.description.lower() or any('calculat' in str(r).lower() or 'math' in str(r).lower() for r in spec.requirements)

        calculator_pattern_section = ""
        if is_calculator:
            calculator_pattern_section = r'''
**VALIDATED CALCULATOR PATTERN (USE THIS FOR CALCULATOR COMPONENTS):**
If this is a calculator or mathematical operations component, use this proven pattern as your basis:

Key features of the validated pattern:
- Extends Tool from '@langchain/core/tools'
- Has a `mathFunction` input to support different operation modes (default, add, subtract, multiply, divide, power, sqrt, sin, cos, tan)
- Uses simple validation regex: `/^[0-9+\-*/().\s]+$/` (CRITICAL - no complex character classes)
- Implements `_sanitizeExpression()` for security (checks for <script, javascript:, eval)
- Implements `_validateMathExpression()` for input validation
- Implements `_convertDegreesToRadians()` for trig functions
- Implements `_applyMathFunction()` for specific operations (switch/case based on mathFunction)
- Implements `_evaluateSafeExpression()` that replaces sin/cos/tan/sqrt/pow/abs/floor/ceil with Math equivalents
- Implements `_formatResult()` to format numbers (integers as-is, decimals rounded to 6 places)
- Main `_call()` method routes to either expression evaluation or specific function based on mathFunction

CRITICAL options input structure (use 'name' NOT 'value'):
```typescript
{
    label: 'Math Function Mode',
    name: 'mathFunction',
    type: 'options',
    options: [
        { label: 'Default (Expression Evaluation)', name: 'default' },  // Use 'name' NOT 'value'!
        { label: 'Addition', name: 'add' },
        { label: 'Subtraction', name: 'subtract' },
        // etc...
    ],
    default: 'default',
    optional: true
}
```

CRITICAL validation approach:
```typescript
private _validateMathExpression(expression: string): boolean {
    if (!expression || typeof expression !== 'string') {
        return false
    }
    const allowedPattern = /^[0-9+\-*/().\s]+$/  // SIMPLE pattern - no complex char classes
    return allowedPattern.test(expression)
}
```
'''

        prompt = f"""
You are an expert TypeScript developer specializing in Flowise component development.

{category_guidance}

Generate a complete, working TypeScript component for Flowise with this specification:

**Component Name:** {spec.name}
**Description:** {spec.description}
**Requirements:** {json.dumps(spec.requirements, indent=2)}

**Component Structure (from analysis):**
{json.dumps(structure, indent=2)}
{rag_context_section}
{f'''
**OFFICIAL FLOWISE VALIDATORS TO INCLUDE:**
The following import statement should be added based on this component's needs:
```typescript
{validation_imports_str}
```
These are official Flowise validation utilities from the repository. Use them to validate inputs.
''' if validation_imports_str else ''}
{calculator_pattern_section}

**REQUIREMENTS:**
1. **CRITICAL FOR VALIDATION REGEX**: When validating mathematical expressions or similar input, use SIMPLE regex patterns like `/^[0-9+\-*/().\s]+$/` - DO NOT use complex character classes like `[sincotan√sqrtpowabsfloorceiltrig]` as they cause validation failures and Unicode encoding issues. Keep validation patterns minimal and only include essential characters. THIS OVERRIDES ANY PATTERNS SEEN IN REFERENCE COMPONENTS ABOVE.
2. Follow the patterns shown in the similar components above (EXCEPT for validation regex patterns - see requirement #1)
3. Implement INode interface with all required properties
4. **CRITICAL**: Constructor MUST include `this.baseClasses = [this.type, 'Tool']` - component will fail without this
5. Use proper TypeScript syntax and types for class structure
6. **REQUIRED**: If component has inputs in constructor, MUST access them in init() via `nodeData.inputs?.inputName as Type`
7. **REQUIRED**: Add input validation in init() method with `throw new Error()` for invalid inputs
8. **REQUIRED**: Wrap init() method body in try-catch block for error handling
9. End with `module.exports = {{ nodeClass: ComponentName }}`
{f"10. Include these dependencies if needed: {', '.join(spec.dependencies)}" if spec.dependencies else ""}
{f"11. **CRITICAL FOR TOOLS**: Import from '../CustomTool/core', define code as string OUTSIDE class, use code property NOT func" if is_tool_component else ""}
{f"12. **CRITICAL FOR TOOLS**: ALWAYS use 'input' as the parameter name in schema for simple single-input tools, access it as $input in code string" if is_tool_component else ""}
{f"13. **CRITICAL FOR TOOLS**: The 'input' parameter's .describe() should contain the semantic meaning (e.g., 'Mathematical expression to evaluate')" if is_tool_component else ""}
{f"14. **CRITICAL FOR TOOLS**: Use JavaScript syntax in code string (NOT TypeScript), MUST return a value" if is_tool_component else ""}
{f"15. **FORBIDDEN FOR TOOLS**: NEVER import from '@langchain/core/tools', NEVER use func property, NEVER use custom parameter names like 'expression' or 'text'" if is_tool_component else ""}

**Key Points:**
- Learn from the similar component patterns provided above
- Follow Flowise conventions for component structure
- Ensure all TypeScript syntax is valid
- Handle errors gracefully with meaningful messages

Generate the COMPLETE Flowise component code. Return ONLY the TypeScript code, no markdown blocks, no explanation.
"""

        response = await self._call_llm(prompt, temperature=0.3)

        # Clean response - extract code if wrapped
        code = response.strip()
        if "```typescript" in code:
            code = code.split("```typescript")[1].split("```")[0].strip()
        elif "```ts" in code:
            code = code.split("```ts")[1].split("```")[0].strip()
        elif "```" in code:
            code = code.split("```")[1].split("```")[0].strip()

        return code

    async def _ai_generate_tests(
        self,
        spec: ComponentSpec,
        component_code: str
    ) -> str:
        """Generate unit tests for the Flowise component"""

        prompt = f"""
Generate Jest unit tests for this Flowise component:

```typescript
{component_code}
```

Create comprehensive tests that:
1. Test the init() method with valid inputs
2. Test error handling for missing inputs
3. Test edge cases and boundary conditions
4. Mock external dependencies if needed
5. Use Jest testing framework

Return ONLY the test code, no markdown, no explanation.
"""

        response = await self._call_llm(prompt, temperature=0.3)

        code = response.strip()
        if "```typescript" in code:
            code = code.split("```typescript")[1].split("```")[0].strip()
        elif "```javascript" in code:
            code = code.split("```javascript")[1].split("```")[0].strip()
        elif "```" in code:
            code = code.split("```")[1].split("```")[0].strip()

        return code

    async def _ai_generate_documentation(
        self,
        spec: ComponentSpec,
        component_code: str
    ) -> str:
        """Generate usage documentation"""

        prompt = f"""
Create user documentation for this Flowise component:

Component: {spec.name}
Description: {spec.description}

Code:
```typescript
{component_code}
```

Create markdown documentation with:
1. Overview (what it does)
2. Inputs (what parameters it accepts)
3. Outputs (what it returns)
4. Usage example in Flowise
5. Common use cases
6. Troubleshooting tips

Return markdown documentation.
"""

        response = await self._call_llm(prompt, temperature=0.5)
        return response.strip()

    def _generate_flowise_config(self, spec: ComponentSpec) -> Dict[str, Any]:
        """Generate Flowise component configuration"""
        return {
            "name": spec.name,
            "label": spec.display_name,
            "description": spec.description,
            "category": spec.category,
            "icon": "code",
            "version": 1.0,
            "type": spec.name,
            "inputs": spec.inputs,
            "outputs": spec.outputs,
            "is_custom": True,
            "dependencies": spec.dependencies,
            "platform": "flowise"
        }

    async def _validate_and_fix_component(
        self,
        code: str,
        spec: ComponentSpec
    ) -> tuple[str, Dict[str, Any]]:
        """
        Validate component and auto-retry with fixes if validation fails.

        Uses comprehensive ComponentValidator with auto-retry logic.

        Returns:
            tuple: (fixed_code, validation_details)
        """
        current_code = code
        attempt = 0

        while attempt <= self.max_validation_retries:
            self.logger.info(
                "Validating component code",
                attempt=attempt + 1,
                max_retries=self.max_validation_retries + 1
            )

            # Run comprehensive validation
            validation_result = self.validator.validate(current_code)

            # Log validation results
            if validation_result.is_valid:
                self.logger.info(
                    "Component validation PASSED",
                    component_name=validation_result.component_name,
                    display_name=getattr(
                        validation_result, 'display_name', 'Unknown'),
                    inputs=getattr(validation_result, 'input_count', 0),
                    outputs=getattr(validation_result, 'output_count', 0),
                    warnings=len(validation_result.warnings),
                    attempt=attempt + 1
                )

                # Log warnings if any
                if validation_result.warnings:
                    for warning in validation_result.warnings:
                        self.logger.warning(
                            "Component warning", warning=warning)

                return current_code, validation_result.to_dict()

            else:
                # Validation failed
                self.logger.error(
                    "Component validation FAILED",
                    attempt=attempt + 1,
                    errors=validation_result.errors,
                    warnings=validation_result.warnings
                )

                # Apply automatic fixes for common issues
                current_code = self._auto_fix_component_issues(current_code)

                # If we have retries left, ask LLM to fix
                if attempt < self.max_validation_retries:
                    self.logger.info(
                        "Attempting to fix validation errors with LLM",
                        retry_attempt=attempt + 1
                    )

                    current_code = await self._ai_fix_validation_errors(
                        current_code,
                        validation_result.errors,
                        spec
                    )

                    attempt += 1
                else:
                    # Out of retries - return with final validation
                    self.logger.warning(
                        "Validation failed after max retries",
                        errors=validation_result.errors
                    )

                    final_validation = self.validator.validate(current_code)
                    return current_code, final_validation.to_dict()

        # Should not reach here, but return current code just in case
        return current_code, {}

    def _auto_fix_component_issues(self, code: str) -> str:
        """
        Automatically fix common component issues.
        """
        import re

        self.logger.info("Running auto-fixes")

        # Fix missing module.exports
        if "module.exports" not in code:
            # Extract class name
            class_match = re.search(
                r'class\s+(\w+)\s+implements\s+INode', code)
            if class_match:
                class_name = class_match.group(1)
                code += f"\n\nmodule.exports = {{ nodeClass: {class_name} }}"
                self.logger.info("Auto-fixed: Added module.exports")

        # Fix missing imports
        if "import {" not in code and "import(" not in code:
            code = "import { INode, INodeData, INodeParams } from '../../../src/Interface'\n\n" + code
            self.logger.info("Auto-fixed: Added missing Interface imports")

        # Fix missing baseClasses property assignment (CRITICAL for Flowise)
        if "this.baseClasses" not in code:
            self.logger.info("Detected missing baseClasses - attempting auto-fix")

            # Strategy 1: Find after this.description (most reliable)
            # Handle backticks, single quotes, double quotes
            description_match = re.search(
                r"this\.description\s*=\s*(`[^`]*`|'[^']*'|\"[^\"]*\")",
                code,
                re.DOTALL  # Allow multiline strings
            )

            if description_match:
                insert_pos = description_match.end()
                code = code[:insert_pos] + f"\n        this.baseClasses = [this.type, 'Tool']" + code[insert_pos:]
                self.logger.info("Auto-fixed: Added missing this.baseClasses assignment after description")
            else:
                # Strategy 2: Find after this.category
                category_match = re.search(r"this\.category\s*=\s*['\"]([^'\"]+)['\"]", code)
                if category_match:
                    insert_pos = category_match.end()
                    code = code[:insert_pos] + f"\n        this.baseClasses = [this.type, 'Tool']" + code[insert_pos:]
                    self.logger.info("Auto-fixed: Added missing this.baseClasses assignment after category")
                else:
                    # Strategy 3: Find after this.type
                    type_match = re.search(r"this\.type\s*=\s*['\"](\w+)['\"]", code)
                    if type_match:
                        insert_pos = type_match.end()
                        code = code[:insert_pos] + f"\n        this.baseClasses = [this.type, 'Tool']" + code[insert_pos:]
                        self.logger.info("Auto-fixed: Added missing this.baseClasses assignment after type")
                    else:
                        self.logger.warning("Could not auto-fix baseClasses - no suitable insertion point found")

        # Fix common TypeScript syntax errors
        # Remove trailing commas in object literals
        code = re.sub(r',(\s*[}\]])', r'\1', code)

        # Note: Removed automatic semicolon addition for property assignments
        # as it was causing issues with array/object literals (e.g., this.inputs = [...])
        # TypeScript is forgiving about missing semicolons in most cases

        # Fix missing semicolons after statements
        code = re.sub(
            r'(\}|\w+|\]|\))\s*\n(\s*(?:const|let|var|if|for|while|return|throw))', r'\1;\n\2', code)

        self.logger.info("Auto-fixed: Common TypeScript syntax issues")

        return code

    async def _ai_fix_validation_errors(
        self,
        code: str,
        errors: list[str],
        spec: ComponentSpec
    ) -> str:
        """Use LLM to fix Flowise validation errors"""

        error_list = "\n".join(f"- {error}" for error in errors)

        prompt = f"""
You are a Flowise component code fixer. Fix the following validation errors in this TypeScript component:

**Validation Errors:**
{error_list}

**Component Specification:**
- Name: {spec.name}
- Description: {spec.description}

**Current Code:**
```typescript
{code}
```

**Fix these specific issues:**
{error_list}

**Critical Rules for Flowise:**
1. Must implement INode interface
2. Must have proper constructor with all required properties
3. Must have async init() method with correct signature
4. Must end with: module.exports = {{ nodeClass: ComponentName }}
5. Must import from '../../../src/Interface'
6. Handle errors gracefully with meaningful messages
7. Access inputs via nodeData.inputs?.inputName

Return the FIXED code. Return ONLY the TypeScript code, no markdown, no explanation.
"""

        response = await self._call_llm(prompt, temperature=0.2)

        fixed_code = response.strip()
        if "```typescript" in fixed_code:
            fixed_code = fixed_code.split("```typescript")[
                1].split("```")[0].strip()
        elif "```" in fixed_code:
            fixed_code = fixed_code.split("```")[1].split("```")[0].strip()

        return fixed_code

    async def _run_functional_tests(
        self,
        code: str,
        spec: ComponentSpec
    ) -> Dict[str, Any]:
        """
        Run functional tests with actual test data.

        This executes the component with real inputs and verifies the outputs.
        """
        self.logger.info(
            "Running functional tests with test data", component=spec.name)

        test_results = {
            "passed": False,
            "test_cases": [],
            "errors": [],
            "warnings": []
        }

        try:
            # For now, return placeholder - full implementation would require Node.js runtime
            test_results["warnings"].append(
                "Functional testing requires Node.js runtime - not implemented yet")
            test_results["passed"] = True

        except Exception as e:
            test_results["errors"].append(f"Test execution failed: {str(e)}")
            self.logger.error("Functional test execution failed", error=str(e))

        return test_results

    def _generate_flowise_deployment_instructions(self, spec: ComponentSpec) -> Dict[str, Any]:
        """
        Generate step-by-step deployment instructions for Flowise repository

        Args:
            spec: Component specification

        Returns:
            Detailed deployment instructions for Flowise source code
        """
        # Determine category directory
        category_map = {
            "tools": "tools",
            "text_processing": "tools",
            "utilities": "utilities",
            "chatmodels": "chatmodels",
            "vectorstores": "vectorstores",
            "documentloaders": "documentloaders",
            "embeddings": "embeddings",
            "memory": "memory",
            "chains": "chains",
            "agents": "agents",
            "custom": "tools"  # Default for custom components
        }

        category_dir = category_map.get(spec.category.lower(), "tools")
        component_dir = f"{category_dir}/{spec.name}"
        file_name = f"{spec.name}.ts"
        relative_path = f"packages/components/nodes/{component_dir}/{file_name}"

        return {
            "method": "flowise_repository_deployment",
            "requires_restart": True,
            "requires_build": True,
            "summary": "Deploy TypeScript component to Flowise source repository",
            "prerequisites": [
                "Clone Flowise repository: git clone https://github.com/FlowiseAI/Flowise.git",
                "Install dependencies: npm install",
                "Ensure Node.js >= 18 and npm >= 9"
            ],
            "steps": [
                {
                    "step": 1,
                    "title": "Navigate to Flowise Repository",
                    "description": "Change to your Flowise repository directory",
                    "command": "cd /path/to/Flowise",
                    "note": "Replace with your actual Flowise repository path"
                },
                {
                    "step": 2,
                    "title": "Create Component Directory",
                    "description": f"Create directory structure for the component",
                    "command": f"mkdir -p packages/components/nodes/{component_dir}",
                    "note": f"Creates the {spec.category} category directory"
                },
                {
                    "step": 3,
                    "title": "Save Component Code",
                    "description": f"Save the generated TypeScript code to the component file",
                    "file_path": relative_path,
                    "action": "Copy the 'component_code' from this response into the file",
                    "note": "Ensure the file has .ts extension for TypeScript"
                },
                {
                    "step": 4,
                    "title": "Install Dependencies (if any)",
                    "description": "Install any additional npm dependencies",
                    "command": f"npm install {' '.join(spec.dependencies)}" if spec.dependencies else "# No additional dependencies needed",
                    "note": "Only run if dependencies are specified"
                },
                {
                    "step": 5,
                    "title": "Build Components",
                    "description": "Compile all TypeScript components",
                    "command": "npm run build",
                    "note": "This compiles the entire project including your new component",
                    "expected_output": "Build completed successfully"
                },
                {
                    "step": 6,
                    "title": "Start Development Server",
                    "description": "Start Flowise in development mode",
                    "command": "npm run dev",
                    "note": "Server will start on http://localhost:3000",
                    "alternative": "Use 'npm start' for production mode"
                },
                {
                    "step": 7,
                    "title": "Verify Component in UI",
                    "description": "Check that your component appears in Flowise",
                    "action": f"Look for '{spec.display_name}' in the '{spec.category}' category",
                    "ui_location": f"Flowise UI > Component Panel > {spec.category.title()} > {spec.display_name}",
                    "verification": "Component should appear in the left sidebar"
                },
                {
                    "step": 8,
                    "title": "Test Component",
                    "description": "Create a test flow to verify component functionality",
                    "action": "Drag the component to canvas and configure inputs",
                    "note": "Test with sample data to ensure it works correctly"
                }
            ],
            "file_locations": {
                "source_file": relative_path,
                "compiled_file": f"packages/components/dist/nodes/{component_dir}/{spec.name}.js",
                "category": category_dir,
                "ui_category": spec.category
            },
            "requirements": {
                "nodejs": "Node.js >= 18.0.0",
                "npm": "npm >= 9.0.0",
                "typescript": "TypeScript compilation via npm run build",
                "flowise_source": "Access to Flowise source repository"
            },
            "troubleshooting": {
                "component_not_visible": [
                    "Ensure build completed without errors: npm run build",
                    "Verify server restarted successfully: npm run dev",
                    "Check browser cache (hard refresh: Ctrl+F5)",
                    "Look in browser console for JavaScript errors",
                    "Verify file was saved in correct directory structure"
                ],
                "build_errors": [
                    "Check TypeScript syntax in generated code",
                    "Verify all imports are correct and available",
                    "Ensure file is saved with .ts extension",
                    "Check for missing dependencies in package.json",
                    "Run npm install to ensure all dependencies are installed"
                ],
                "runtime_errors": [
                    "Check server logs for component loading errors",
                    "Verify component implements required interfaces",
                    "Ensure no syntax errors in component code",
                    "Check that all required properties are defined",
                    "Test with simple inputs first"
                ]
            },
            "quick_reference": [
                f"mkdir -p packages/components/nodes/{component_dir}",
                f"# Save code to packages/components/nodes/{component_dir}/{file_name}",
                "npm run build",
                "npm run dev",
                f"# Look for '{spec.display_name}' in {spec.category} category"
            ],
            "estimated_time": "5-10 minutes",
            "difficulty": "intermediate",
            "notes": [
                "Always backup your Flowise repository before adding custom components",
                "Test components thoroughly before deploying to production",
                "Consider creating a separate branch for custom components",
                "Document your custom components for team members"
            ]
        }

    def _load_claude_code_token(self) -> Optional[str]:
        """Load OAuth access token from Claude Code credentials"""
        import json
        from pathlib import Path

        # Claude Code stores credentials in ~/.claude/.credentials.json
        creds_path = Path.home() / ".claude" / ".credentials.json"

        if not creds_path.exists():
            self.logger.info("No Claude Code credentials found",
                             path=str(creds_path))
            return None

        try:
            with open(creds_path, 'r') as f:
                creds = json.load(f)

            oauth_data = creds.get("claudeAiOauth", {})
            access_token = oauth_data.get("accessToken")

            if access_token:
                self.logger.info(
                    "Loaded Claude Code OAuth token",
                    subscription=oauth_data.get("subscriptionType", "unknown"),
                    token_preview=access_token[:20] + "..."
                )
                return access_token
            else:
                self.logger.warning(
                    "No access token found in Claude Code credentials")
                return None

        except Exception as e:
            self.logger.error(
                "Failed to load Claude Code credentials", error=str(e))
            return None

    async def _call_llm(
        self,
        prompt: str,
        temperature: float = 0.3,
        timeout: int = 300
    ) -> str:
        """Call Claude API for code generation (Ollama fallback removed for quality assurance)"""

        claude_model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

        self.logger.info(
            "Claude API Request",
            model=claude_model,
            temperature=temperature,
            timeout=timeout,
            prompt_length=len(prompt),
            prompt_preview=prompt[:300] +
            "..." if len(prompt) > 300 else prompt
        )

        # Check if using Claude API (API key or Claude Code OAuth)
        claude_api_key = os.getenv("ANTHROPIC_API_KEY")
        claude_code_token = self._load_claude_code_token()

        if claude_api_key or claude_code_token:
            return await self._call_claude(prompt, temperature, timeout)
        else:
            # Fail explicitly instead of falling back to Ollama
            # This ensures we always use high-quality Claude API for component generation
            error_msg = (
                "Claude API is required for component generation. "
                "Please set ANTHROPIC_API_KEY environment variable. "
                "Get your API key from: https://console.anthropic.com/settings/keys"
            )
            self.logger.error("Claude API not configured", error=error_msg)
            raise Exception(error_msg)

    async def _call_claude(
        self,
        prompt: str,
        temperature: float = 0.3,
        timeout: int = 300
    ) -> str:
        """Call Claude API for code generation (supports API key or OAuth tokens)"""

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
                "No authentication found. Either set ANTHROPIC_API_KEY or log in to Claude Code with /login"
            )

        # Use Claude model specified in env or default to Sonnet
        claude_model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

        client = AsyncAnthropic(api_key=api_key, timeout=float(timeout))

        try:
            message = await client.messages.create(
                model=claude_model,
                max_tokens=8192,  # Claude can generate longer responses
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
                response_length=len(response_text),
                response_preview=response_text[:300] +
                "..." if len(response_text) > 300 else response_text
            )

            return response_text

        except Exception as e:
            self.logger.error("Claude API call failed", error=str(e))
            raise Exception(f"Claude API call failed: {str(e)}")

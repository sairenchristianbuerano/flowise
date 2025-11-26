"""
Flowise Component Validator

Validates generated Flowise components for:
- TypeScript syntax
- Flowise interface compliance
- Required methods and properties
- Module export format
"""

import re
import structlog
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

logger = structlog.get_logger()


class ValidationResult(BaseModel):
    """Validation result for a Flowise component"""
    is_valid: bool
    component_name: Optional[str] = None
    errors: List[str] = []
    warnings: List[str] = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "component_name": self.component_name,
            "errors": self.errors,
            "warnings": self.warnings,
            "validation_type": "flowise"
        }


class FlowiseValidator:
    """Validator for Flowise TypeScript components"""
    
    def __init__(self, flowise_url: str = None):
        self.flowise_url = flowise_url
        self.logger = logger.bind(validator="flowise")
        
    def validate(self, component_code: str) -> ValidationResult:
        """
        Comprehensive validation of Flowise component code
        
        Args:
            component_code: TypeScript code to validate
            
        Returns:
            ValidationResult with validation details
        """
        result = ValidationResult(is_valid=True)
        
        try:
            # Basic structure validation
            self._validate_structure(component_code, result)
            
            # TypeScript syntax validation (basic)
            self._validate_typescript_syntax(component_code, result)
            
            # Flowise interface compliance
            self._validate_flowise_interface(component_code, result)
            
            # Required methods validation
            self._validate_required_methods(component_code, result)
            
            # Module export validation
            self._validate_module_export(component_code, result)

            # Security and validation practices (using official Flowise utilities)
            self._validate_security_practices(component_code, result)

            # Extract component name if valid
            if result.is_valid:
                result.component_name = self._extract_component_name(component_code)
                
            self.logger.info(
                "Flowise validation completed",
                is_valid=result.is_valid,
                component_name=result.component_name,
                error_count=len(result.errors),
                warning_count=len(result.warnings)
            )
            
        except Exception as e:
            result.is_valid = False
            result.errors.append(f"Validation failed with exception: {str(e)}")
            self.logger.error("Flowise validation exception", error=str(e))
            
        return result
    
    def _validate_structure(self, code: str, result: ValidationResult):
        """Validate basic code structure"""
        
        # Check for class declaration
        class_pattern = r'class\s+(\w+)\s+implements\s+INode'
        class_match = re.search(class_pattern, code)
        
        if not class_match:
            result.is_valid = False
            result.errors.append("Missing class declaration implementing INode interface")
            return
            
        # Check for constructor
        if 'constructor()' not in code and 'constructor(' not in code:
            result.is_valid = False
            result.errors.append("Missing constructor method")
            
        # Check for required properties in constructor
        # CRITICAL: baseClasses is absolutely required - component will fail without it
        critical_props = ['baseClasses']
        required_props = ['label', 'name', 'version', 'type', 'icon', 'category', 'description', 'inputs']

        # Critical properties are ERRORS (will fail validation)
        for prop in critical_props:
            if f'this.{prop}' not in code:
                result.is_valid = False
                result.errors.append(f"Missing CRITICAL required property assignment: this.{prop}")

        # Other required properties are warnings
        for prop in required_props:
            if f'this.{prop}' not in code:
                result.warnings.append(f"Missing required property assignment: this.{prop}")
    
    def _validate_typescript_syntax(self, code: str, result: ValidationResult):
        """Basic TypeScript syntax validation"""
        
        # Check for proper type annotations
        if 'async init(nodeData: INodeData' not in code:
            result.is_valid = False
            result.errors.append("Invalid init method signature - must be: async init(nodeData: INodeData, ...)")
            
        # Check for proper imports
        if 'import {' not in code and 'import(' not in code:
            result.is_valid = False
            result.errors.append("Missing import statements")
            
        # Check for interface import
        if 'INode' not in code or 'INodeData' not in code:
            result.is_valid = False
            result.errors.append("Missing required interface imports (INode, INodeData)")
            
        # Check for balanced braces (basic)
        open_braces = code.count('{')
        close_braces = code.count('}')
        
        if open_braces != close_braces:
            result.is_valid = False
            result.errors.append(f"Unbalanced braces: {open_braces} open, {close_braces} close")
            
        # Check for async/await usage
        if 'async init(' in code and 'await' not in code:
            result.warnings.append("Async method declared but no await usage found")
    
    def _validate_flowise_interface(self, code: str, result: ValidationResult):
        """Validate Flowise INode interface compliance"""
        
        # Required interface methods
        required_methods = ['init']
        
        for method in required_methods:
            if f'async {method}(' not in code:
                result.is_valid = False
                result.errors.append(f"Missing required async method: {method}")
                
        # Check init method signature
        init_pattern = r'async\s+init\s*\(\s*nodeData:\s*INodeData[^)]*\)\s*:\s*Promise<[^>]+>'
        if not re.search(init_pattern, code):
            result.is_valid = False
            result.errors.append("Invalid init method signature - must return Promise<T>")
            
        # Check for input access pattern
        if 'nodeData.inputs' not in code:
            result.warnings.append("No nodeData.inputs access found - ensure inputs are being used")
    
    def _validate_required_methods(self, code: str, result: ValidationResult):
        """Validate required method implementations"""
        
        # Check for error handling
        if 'try' not in code and 'catch' not in code:
            result.warnings.append("No error handling found - consider adding try-catch blocks")
            
        if 'throw new Error' not in code and 'throw' not in code:
            result.warnings.append("No error throwing found - consider validating inputs and throwing meaningful errors")
            
        # Check for input validation
        if '!' not in code or 'if (' not in code:
            result.warnings.append("Limited input validation detected - ensure required inputs are checked")

    def _check_forbidden_imports(self, code: str, result: ValidationResult):
        """Check for unsupported/forbidden library imports"""

        # Define forbidden imports that are NOT supported in Flowise
        forbidden_imports = {
            'mathjs': 'mathjs is NOT supported in Flowise. Use native JavaScript Math or expr-eval instead.',
            'moment': 'moment is NOT supported. Use native Date or import from @langchain/community if needed.',
            'lodash': 'lodash is NOT supported. Use native JavaScript array/object methods.',
            'jquery': 'jquery is NOT applicable in Node.js backend.',
            'axios': 'axios should be avoided. Use native fetch() instead.'
        }

        # Check each forbidden import
        for lib, message in forbidden_imports.items():
            # Check various import patterns
            import_patterns = [
                f"from '{lib}'",
                f'from "{lib}"',
                f"import {lib}",
                f"import * as",
                f"import {{",
                "} from"
            ]

            # Check if any forbidden import pattern exists
            code_lower = code.lower()
            if f"from '{lib}'" in code_lower or f'from "{lib}"' in code_lower:
                result.is_valid = False
                result.errors.append(
                    f"FORBIDDEN IMPORT: {lib} - {message}"
                )
            elif f"import {{{lib}" in code or f"import * as {lib}" in code or f"import {lib}" in code:
                result.is_valid = False
                result.errors.append(
                    f"FORBIDDEN IMPORT: {lib} - {message}"
                )

    def _validate_security_practices(self, code: str, result: ValidationResult):
        """Validate security and validation practices using official Flowise utilities"""

        # Check for forbidden/unsupported imports first
        self._check_forbidden_imports(code, result)

        # Check for external data handling (URLs, UUIDs, file paths)
        has_external_inputs = any(keyword in code.lower() for keyword in [
            'url', 'endpoint', 'api', 'uuid', 'id', 'chatflow', 'agent',
            'path', 'file', 'filepath', 'directory', 'folder'
        ])

        if has_external_inputs:
            # Should import official Flowise validators
            if '../../../src/validator' not in code:
                result.warnings.append(
                    "Component handles external data but doesn't import official Flowise validation utilities. "
                    "Consider importing: isValidUUID, isValidURL, isPathTraversal, isUnsafeFilePath from '../../../src/validator'"
                )

            # Check for specific validator usage based on detected patterns
            code_lower = code.lower()

            # UUID validation check
            if any(term in code_lower for term in ['uuid', 'chatflow id', 'flow id', 'agent id', 'chatflowid']):
                if 'isValidUUID' not in code:
                    result.warnings.append(
                        "Component uses UUIDs but doesn't validate with isValidUUID. "
                        "Import from '../../../src/validator' and use: if (!isValidUUID(uuid)) throw new Error('Invalid UUID')"
                    )

            # URL validation check
            if any(term in code_lower for term in ['url', 'endpoint', 'api', 'webhook', 'http']):
                if 'isValidURL' not in code:
                    result.warnings.append(
                        "Component uses URLs but doesn't validate with isValidURL. "
                        "Import from '../../../src/validator' and use: if (!isValidURL(url)) throw new Error('Invalid URL')"
                    )

            # File path security check
            if any(term in code_lower for term in ['path', 'file path', 'filepath', 'directory', 'folder']):
                if 'isUnsafeFilePath' not in code and 'isPathTraversal' not in code:
                    result.warnings.append(
                        "Component handles file paths but doesn't validate with isUnsafeFilePath or isPathTraversal. "
                        "Import from '../../../src/validator' for security: if (isUnsafeFilePath(path)) throw new Error('Unsafe path')"
                    )

        # Check for error handling with official handleErrorMessage utility
        if 'try' in code and 'catch' in code:
            if 'handleErrorMessage' not in code:
                result.warnings.append(
                    "Component has error handling but doesn't use handleErrorMessage utility. "
                    "Import from '../../../src/utils' for consistent error formatting: handleErrorMessage(error)"
                )

        # Check for credentials handling
        if any(term in code.lower() for term in ['credential', 'api key', 'apikey', 'token', 'secret']):
            if 'getCredentialData' not in code and 'getCredentialParam' not in code:
                result.warnings.append(
                    "Component references credentials but doesn't use official Flowise credential utilities. "
                    "Consider importing getCredentialData or getCredentialParam from '../../../src/utils'"
                )

    def _validate_module_export(self, code: str, result: ValidationResult):
        """Validate proper module export format"""
        
        export_pattern = r'module\.exports\s*=\s*{\s*nodeClass:\s*\w+\s*}'
        
        if not re.search(export_pattern, code):
            result.is_valid = False
            result.errors.append("Missing or invalid module.exports - must be: module.exports = { nodeClass: ComponentName }")
            
        # Check if exported class matches defined class
        class_match = re.search(r'class\s+(\w+)\s+implements\s+INode', code)
        export_match = re.search(r'module\.exports\s*=\s*{\s*nodeClass:\s*(\w+)\s*}', code)
        
        if class_match and export_match:
            class_name = class_match.group(1)
            export_name = export_match.group(1)
            
            if class_name != export_name:
                result.is_valid = False
                result.errors.append(f"Class name '{class_name}' doesn't match exported name '{export_name}'")
    
    def _extract_component_name(self, code: str) -> Optional[str]:
        """Extract component name from class declaration"""
        
        class_match = re.search(r'class\s+(\w+)\s+implements\s+INode', code)
        if class_match:
            return class_match.group(1)
            
        return None
    
    async def validate_with_flowise_api(self, component_code: str) -> ValidationResult:
        """
        Validate component against Flowise API (if available)
        
        This would test the component in a real Flowise environment,
        but requires Flowise to be running and accessible.
        """
        result = ValidationResult(is_valid=True)
        
        if not self.flowise_url:
            result.warnings.append("Flowise URL not configured - skipping API validation")
            return result
            
        try:
            # TODO: Implement actual Flowise API validation
            # This would involve:
            # 1. Submitting component to Flowise
            # 2. Testing component initialization
            # 3. Validating component in workflow context
            
            result.warnings.append("Flowise API validation not yet implemented")
            
        except Exception as e:
            result.warnings.append(f"Flowise API validation failed: {str(e)}")
            
        return result


class FlowiseFeasibilityChecker:
    """Assess feasibility of generating Flowise components"""
    
    def __init__(self):
        self.logger = logger.bind(checker="flowise_feasibility")
        
    async def assess(self, spec_dict: Dict[str, Any], rag_context: Dict[str, Any] = None) -> 'FeasibilityAssessment':
        """
        Assess feasibility of generating a Flowise component
        
        Args:
            spec_dict: Component specification dictionary
            rag_context: RAG context with similar components
            
        Returns:
            FeasibilityAssessment with analysis
        """
        assessment = FeasibilityAssessment()
        
        try:
            # Analyze component requirements
            self._assess_complexity(spec_dict, assessment)
            
            # Check for similar patterns in RAG
            if rag_context and rag_context.get("has_rag_context"):
                self._assess_rag_support(rag_context, assessment)
            else:
                assessment.confidence = "medium"
                assessment.issues.append("No similar components found in knowledge base")
                
            # Check for unsupported features
            self._assess_unsupported_features(spec_dict, assessment)
            
            # Final feasibility determination
            self._determine_feasibility(assessment)
            
            self.logger.info(
                "Flowise feasibility assessment completed",
                feasible=assessment.feasible,
                confidence=assessment.confidence,
                issues=len(assessment.issues)
            )
            
        except Exception as e:
            assessment.feasible = False
            assessment.confidence = "blocked"
            assessment.issues.append(f"Assessment failed: {str(e)}")
            self.logger.error("Flowise feasibility assessment failed", error=str(e))
            
        return assessment
    
    def _assess_complexity(self, spec_dict: Dict[str, Any], assessment: 'FeasibilityAssessment'):
        """Assess component complexity"""
        
        requirements = spec_dict.get("requirements", [])
        dependencies = spec_dict.get("dependencies", [])
        
        # Simple complexity scoring
        complexity_score = 0
        complexity_score += len(requirements)
        complexity_score += len(dependencies) * 2
        complexity_score += len(spec_dict.get("inputs", [])) * 1
        
        if complexity_score <= 5:
            assessment.complexity = "simple"
            assessment.confidence = "high"
        elif complexity_score <= 15:
            assessment.complexity = "medium"  
            assessment.confidence = "medium"
        else:
            assessment.complexity = "complex"
            assessment.confidence = "low"
            assessment.issues.append("High complexity component may require manual review")
    
    def _assess_rag_support(self, rag_context: Dict[str, Any], assessment: 'FeasibilityAssessment'):
        """Assess RAG context support"""
        
        similar_components = rag_context.get("similar_components", [])
        
        if len(similar_components) >= 2:
            assessment.confidence = "high"
            assessment.suggestions.append("Good pattern matches found in knowledge base")
        elif len(similar_components) == 1:
            assessment.confidence = "medium"
            assessment.suggestions.append("Limited pattern matches - may need additional validation")
        else:
            assessment.confidence = "low"
            assessment.issues.append("No similar components found for pattern matching")
    
    def _assess_unsupported_features(self, spec_dict: Dict[str, Any], assessment: 'FeasibilityAssessment'):
        """Check for unsupported Flowise features"""
        
        # Check for complex requirements that might not be feasible
        requirements = spec_dict.get("requirements", [])
        
        for req in requirements:
            req_lower = req.lower()
            
            # Features that might be challenging in Flowise
            if "real-time" in req_lower or "streaming" in req_lower:
                assessment.issues.append("Real-time/streaming features may be limited in Flowise")
                
            if "database" in req_lower and "connection" in req_lower:
                assessment.issues.append("Database connections require careful configuration in Flowise")
                
            if "file system" in req_lower or "file write" in req_lower:
                assessment.issues.append("File system operations may have security restrictions")
    
    def _determine_feasibility(self, assessment: 'FeasibilityAssessment'):
        """Make final feasibility determination"""
        
        if assessment.confidence == "blocked":
            assessment.feasible = False
        elif len(assessment.issues) > 3:
            assessment.feasible = False
            assessment.confidence = "blocked"
        elif assessment.complexity == "complex" and assessment.confidence == "low":
            assessment.feasible = False
        else:
            assessment.feasible = True


class FeasibilityAssessment(BaseModel):
    """Feasibility assessment result"""
    feasible: bool = True
    confidence: str = "medium"  # high|medium|low|blocked
    complexity: str = "medium"  # simple|medium|complex
    issues: List[str] = []
    suggestions: List[str] = []
    missing_info: List[str] = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "feasible": self.feasible,
            "confidence": self.confidence,
            "complexity": self.complexity,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "missing_info": self.missing_info,
            "platform": "flowise"
        }
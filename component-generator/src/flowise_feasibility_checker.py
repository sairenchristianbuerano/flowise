"""
Flowise Feasibility Checker

Assess feasibility of generating Flowise components before attempting generation.
"""

import structlog
from typing import Dict, Any, List
from pydantic import BaseModel

logger = structlog.get_logger()


class FeasibilityAssessment(BaseModel):
    """Feasibility assessment result for Flowise components"""
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


class FlowiseFeasibilityChecker:
    """Assess feasibility of generating Flowise components"""
    
    def __init__(self):
        self.logger = logger.bind(checker="flowise_feasibility")
        
    async def assess(self, spec_dict: Dict[str, Any], rag_context: Dict[str, Any] = None) -> FeasibilityAssessment:
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
                assessment.issues.append("No similar Flowise components found in knowledge base")
                
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
    
    def _assess_complexity(self, spec_dict: Dict[str, Any], assessment: FeasibilityAssessment):
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
    
    def _assess_rag_support(self, rag_context: Dict[str, Any], assessment: FeasibilityAssessment):
        """Assess RAG context support"""
        
        similar_components = rag_context.get("similar_components", [])
        
        if len(similar_components) >= 2:
            assessment.confidence = "high"
            assessment.suggestions.append("Good pattern matches found in Flowise knowledge base")
        elif len(similar_components) == 1:
            assessment.confidence = "medium"
            assessment.suggestions.append("Limited pattern matches - may need additional validation")
        else:
            assessment.confidence = "low"
            assessment.issues.append("No similar Flowise components found for pattern matching")
    
    def _assess_unsupported_features(self, spec_dict: Dict[str, Any], assessment: FeasibilityAssessment):
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
                
            if "browser" in req_lower or "dom" in req_lower:
                assessment.issues.append("Browser/DOM manipulation not available in Flowise backend")
    
    def _determine_feasibility(self, assessment: FeasibilityAssessment):
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
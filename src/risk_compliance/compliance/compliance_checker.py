"""
Compliance checker module for risk compliance.
"""
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class ComplianceChecker:
    """Checks compliance with regulations and internal policies."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the compliance checker.
        
        Args:
            config: Configuration dictionary for the checker
        """
        self.config = config or {}
        self.rules = []
        logger.info("ComplianceChecker initialized")
    
    def register_rule(self, rule_id: str, rule_func: callable, description: str) -> None:
        """
        Register a new compliance rule.
        
        Args:
            rule_id: Unique identifier for the rule
            rule_func: Function that implements the rule check
            description: Human-readable description of the rule
        """
        self.rules.append({
            "id": rule_id,
            "function": rule_func,
            "description": description
        })
        logger.info(f"Registered compliance rule: {rule_id}")
    
    def check_compliance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check compliance against all registered rules.
        
        Args:
            data: Data to check for compliance
            
        Returns:
            Compliance check results
        """
        results = []
        for rule in self.rules:
            try:
                result = rule["function"](data)
                results.append({
                    "rule_id": rule["id"],
                    "compliant": result,
                    "description": rule["description"]
                })
            except Exception as e:
                logger.error(f"Error checking rule {rule['id']}: {str(e)}")
                results.append({
                    "rule_id": rule["id"],
                    "error": str(e),
                    "description": rule["description"]
                })
        
        return {
            "overall_compliant": all(r.get("compliant", False) for r in results),
            "results": results
        }

# Create a default compliance checker instance
compliance_checker = ComplianceChecker()

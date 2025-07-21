"""
Parallel qualification checks for Carlos using Send API
"""
from typing import Dict, Any, List
from langgraph.types import Send
from app.state.conversation_state import ConversationState
from app.utils.simple_logger import get_logger

logger = get_logger("carlos_parallel")


def carlos_qualification_dispatcher(state: ConversationState) -> List[Send]:
    """
    Dispatch parallel qualification checks for Carlos
    
    This runs multiple checks simultaneously:
    - Budget verification
    - Timeline assessment  
    - Authority confirmation
    - Business validation
    """
    lead_info = state.get("extracted_data", {})
    contact_id = state.get("contact_id", "unknown")
    
    # Only dispatch if we have info to check
    if not lead_info:
        return []
    
    checks = []
    
    # Budget check if we have budget info
    if lead_info.get("budget"):
        checks.append(
            Send(
                "budget_verification", 
                {
                    "budget": lead_info["budget"],
                    "contact_id": contact_id,
                    "threshold": 300
                }
            )
        )
    
    # Timeline check if we have urgency/timeline info
    if lead_info.get("urgency_level") or lead_info.get("timeline"):
        checks.append(
            Send(
                "timeline_assessment",
                {
                    "urgency": lead_info.get("urgency_level", "NO_EXPRESADO"),
                    "timeline": lead_info.get("timeline"),
                    "contact_id": contact_id
                }
            )
        )
    
    # Authority check if we have role/position info
    if lead_info.get("role") or lead_info.get("is_decision_maker"):
        checks.append(
            Send(
                "authority_confirmation",
                {
                    "role": lead_info.get("role"),
                    "is_decision_maker": lead_info.get("is_decision_maker"),
                    "contact_id": contact_id
                }
            )
        )
    
    # Business validation if we have business type
    if lead_info.get("business_type"):
        checks.append(
            Send(
                "business_validation",
                {
                    "business_type": lead_info["business_type"],
                    "business_size": lead_info.get("business_size"),
                    "contact_id": contact_id
                }
            )
        )
    
    logger.info(f"Dispatching {len(checks)} parallel qualification checks for {contact_id}")
    return checks


# Individual check nodes
async def budget_verification_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Verify budget meets threshold"""
    budget = state.get("budget", "")
    threshold = state.get("threshold", 300)
    
    # Extract numeric value
    try:
        budget_value = int(
            str(budget)
            .replace("$", "")
            .replace("+", "")
            .replace(",", "")
            .split("/")[0]
        )
        meets_threshold = budget_value >= threshold
    except:
        meets_threshold = False
    
    return {
        "budget_verified": meets_threshold,
        "budget_value": budget_value if 'budget_value' in locals() else 0,
        "check_complete": True
    }


async def timeline_assessment_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Assess urgency and timeline"""
    urgency = state.get("urgency", "NO_EXPRESADO")
    timeline = state.get("timeline", "")
    
    # Score urgency
    urgency_score = {
        "ALTA": 3,
        "MEDIA": 2,
        "BAJA": 1,
        "NO_EXPRESADO": 0
    }.get(urgency, 0)
    
    # Check for immediate timeline indicators
    immediate_indicators = ["now", "ahora", "today", "hoy", "asap", "urgente"]
    is_immediate = any(ind in str(timeline).lower() for ind in immediate_indicators)
    
    return {
        "urgency_score": urgency_score,
        "is_immediate": is_immediate,
        "timeline_assessed": True,
        "check_complete": True
    }


async def authority_confirmation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Confirm decision-making authority"""
    role = state.get("role", "")
    is_decision_maker = state.get("is_decision_maker", None)
    
    # Check role indicators
    decision_roles = ["owner", "dueño", "propietario", "ceo", "director", "gerente", "manager"]
    has_authority = any(role_ind in str(role).lower() for role_ind in decision_roles)
    
    # Use explicit decision maker flag if available
    if is_decision_maker is not None:
        has_authority = is_decision_maker
    
    return {
        "has_authority": has_authority,
        "role_verified": bool(role),
        "check_complete": True
    }


async def business_validation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Validate business type and size"""
    business_type = state.get("business_type", "")
    business_size = state.get("business_size", "")
    
    # Valid business types for our services
    valid_types = [
        "restaurante", "restaurant",
        "salon", "salón", "barbería", "barberia",
        "clinica", "clínica", "consultorio",
        "tienda", "boutique", "shop",
        "gimnasio", "gym", "fitness"
    ]
    
    is_valid_business = any(btype in str(business_type).lower() for btype in valid_types)
    
    # Size scoring
    size_score = 0
    if business_size:
        if "small" in business_size.lower() or "pequeño" in business_size.lower():
            size_score = 1
        elif "medium" in business_size.lower() or "mediano" in business_size.lower():
            size_score = 2
        elif "large" in business_size.lower() or "grande" in business_size.lower():
            size_score = 3
    
    return {
        "is_valid_business": is_valid_business,
        "business_size_score": size_score,
        "business_validated": True,
        "check_complete": True
    }


def aggregate_qualification_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate results from parallel qualification checks
    
    Returns:
        Combined qualification score and recommendations
    """
    total_score = 0
    max_score = 0
    recommendations = []
    
    # Process each result
    for result in results:
        if result.get("budget_verified"):
            total_score += 3
            max_score += 3
        elif "budget_value" in result:
            max_score += 3
            if result["budget_value"] > 0:
                recommendations.append(f"Budget ${result['budget_value']} is below $300 threshold")
        
        if result.get("urgency_score", 0) > 0:
            total_score += result["urgency_score"]
            max_score += 3
        
        if result.get("is_immediate"):
            total_score += 1
            recommendations.append("Customer has immediate need - prioritize")
        
        if result.get("has_authority"):
            total_score += 2
            max_score += 2
        elif result.get("role_verified"):
            max_score += 2
            recommendations.append("Confirm decision-making authority")
        
        if result.get("is_valid_business"):
            total_score += 2
            max_score += 2
        elif result.get("business_validated"):
            max_score += 2
            recommendations.append("Business type may need clarification")
    
    # Calculate percentage
    qualification_percentage = (total_score / max_score * 100) if max_score > 0 else 0
    
    return {
        "qualification_score": total_score,
        "max_possible_score": max_score,
        "qualification_percentage": qualification_percentage,
        "is_qualified": qualification_percentage >= 70,
        "recommendations": recommendations
    }


# Export functions
__all__ = [
    "carlos_qualification_dispatcher",
    "budget_verification_node",
    "timeline_assessment_node", 
    "authority_confirmation_node",
    "business_validation_node",
    "aggregate_qualification_results"
]
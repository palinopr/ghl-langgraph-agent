"""
Base Agent Utilities - Low Risk Consolidation
Only contains truly duplicate code shared by ALL agents
"""
from typing import Dict, Any, List, Optional, Tuple
from app.utils.simple_logger import get_logger


def get_current_message(messages: List[Any]) -> str:
    """
    Extract current message from messages list
    This exact logic is duplicated in all three agents
    """
    for msg in reversed(messages):
        if hasattr(msg, '__class__') and msg.__class__.__name__ == 'HumanMessage':
            return msg.content
    return ""


def check_score_boundaries(
    lead_score: int, 
    min_score: int, 
    max_score: int,
    agent_name: str,
    logger: Any
) -> Optional[Dict[str, Any]]:
    """
    Check if lead score is within agent's range
    Returns escalation response if out of bounds
    """
    if lead_score < min_score:
        logger.info(f"Score {lead_score} too low for {agent_name} (handles {min_score}-{max_score})")
        return {
            "needs_rerouting": True,
            "escalation_reason": "wrong_agent",
            "escalation_details": f"Score {lead_score} too low for {agent_name}",
            "current_agent": agent_name.lower()
        }
    elif lead_score > max_score:
        logger.info(f"Score {lead_score} too high for {agent_name} (handles {min_score}-{max_score})")
        return {
            "needs_rerouting": True,
            "escalation_reason": "needs_next_agent", 
            "escalation_details": f"Score {lead_score} ready for next agent",
            "current_agent": agent_name.lower()
        }
    return None


def extract_data_status(extracted_data: Dict[str, Any]) -> Dict[str, bool]:
    """
    Extract data collection status
    This exact pattern is used in all agents
    """
    return {
        "has_name": bool(extracted_data.get("name")),
        "has_business": bool(extracted_data.get("business_type") and 
                           extracted_data.get("business_type") != "NO_MENCIONADO"),
        "has_budget": bool(extracted_data.get("budget")),
        "has_email": bool(extracted_data.get("email"))
    }


def create_error_response(agent_name: str, error: Exception, state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create standardized error response
    This exact error handling is duplicated in all agents
    """
    return {
        "error": str(error),
        "current_agent": agent_name.lower(),
        "messages": state.get("messages", [])
    }


def get_base_contact_info(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract basic contact information from state
    Common pattern across all agents
    """
    return {
        "contact_id": state.get("contact_id", ""),
        "lead_score": state.get("lead_score", 0),
        "extracted_data": state.get("extracted_data", {}),
        "messages": state.get("messages", [])
    }
"""
Simplified State Schema using MessagesState
Reduces from 50+ fields to essential 15 fields
"""
from typing import List, Optional, Dict, Any, Literal
from typing_extensions import TypedDict
from langgraph.graph import MessagesState


class SimplifiedState(MessagesState):
    """
    Simplified state schema extending MessagesState.
    Reduces complexity while maintaining essential functionality.
    
    Total fields: 15 (including messages from MessagesState)
    """
    
    # Core identification (2 fields)
    contact_id: str  # GHL contact ID
    contact_info: Optional[Dict[str, Any]]  # Full contact data from GHL
    
    # Lead scoring (3 fields)
    lead_score: int  # 1-10 scale
    extracted_data: Dict[str, Any]  # All extracted information
    
    # Agent routing (4 fields)
    current_agent: Optional[Literal["maria", "carlos", "sofia"]]
    next_agent: Optional[Literal["maria", "carlos", "sofia"]]
    agent_task: Optional[str]  # Task description for handoffs
    
    # Workflow control (3 fields)
    needs_rerouting: bool = False
    should_end: bool = False
    
    # Context (2 fields)
    webhook_data: Dict[str, Any]  # Original webhook data
    agent_context: Optional[Dict[str, Any]]  # Context for current agent


def create_initial_simplified_state(webhook_data: Dict[str, Any]) -> SimplifiedState:
    """
    Create initial state from webhook data
    
    Args:
        webhook_data: Raw webhook data from GoHighLevel
        
    Returns:
        Initial simplified state
    """
    from langchain_core.messages import HumanMessage
    
    # Extract message
    message_content = webhook_data.get("body", webhook_data.get("message", ""))
    
    # Create initial human message
    initial_message = HumanMessage(
        content=message_content,
        metadata={
            "contact_id": webhook_data.get("contactId", webhook_data.get("id")),
            "source": "webhook"
        }
    )
    
    return SimplifiedState(
        # Messages from MessagesState
        messages=[initial_message],
        
        # Core identification
        contact_id=webhook_data.get("contactId", webhook_data.get("id", "")),
        contact_info=None,  # Will be loaded by receptionist
        
        # Lead scoring
        lead_score=0,  # Will be set by intelligence
        extracted_data={},  # Will be populated by intelligence
        
        # Agent routing
        current_agent=None,
        next_agent=None,
        agent_task=None,
        
        # Workflow control
        needs_rerouting=False,
        should_end=False,
        
        # Context
        webhook_data=webhook_data,
        agent_context=None
    )


# Helper functions for common state operations
def get_contact_name(state: SimplifiedState) -> Optional[str]:
    """Extract contact name from state"""
    # Check extracted data first
    if state.get("extracted_data", {}).get("name"):
        return state["extracted_data"]["name"]
    
    # Check contact info
    if state.get("contact_info"):
        return (state["contact_info"].get("name") or 
                state["contact_info"].get("firstName") or
                state["contact_info"].get("fullName"))
    
    return None


def get_contact_email(state: SimplifiedState) -> Optional[str]:
    """Extract contact email from state"""
    if state.get("extracted_data", {}).get("email"):
        return state["extracted_data"]["email"]
    
    if state.get("contact_info", {}).get("email"):
        return state["contact_info"]["email"]
    
    return None


def get_business_info(state: SimplifiedState) -> Optional[str]:
    """Extract business type from state"""
    return state.get("extracted_data", {}).get("business_type")


def get_budget_info(state: SimplifiedState) -> Optional[str]:
    """Extract budget from state"""
    return state.get("extracted_data", {}).get("budget")


def is_qualified_for_appointment(state: SimplifiedState) -> bool:
    """Check if contact is qualified for appointment booking"""
    name = get_contact_name(state)
    email = get_contact_email(state)
    budget = get_budget_info(state)
    
    # Must have name, email, and $300+ budget
    has_budget_300 = budget and ("300" in str(budget) or 
                                  (budget.replace("$", "").replace("+", "").isdigit() and 
                                   int(budget.replace("$", "").replace("+", "")) >= 300))
    
    return bool(name and email and has_budget_300)


def get_lead_category(score: int) -> Literal["cold", "warm", "hot"]:
    """Get lead category from score"""
    if score <= 4:
        return "cold"
    elif score <= 7:
        return "warm"
    else:
        return "hot"


def determine_agent_from_score(score: int) -> Literal["maria", "carlos", "sofia"]:
    """Determine agent based on lead score"""
    category = get_lead_category(score)
    return {
        "cold": "maria",
        "warm": "carlos",
        "hot": "sofia"
    }[category]


# State update helpers
def mark_for_rerouting(
    state: SimplifiedState, 
    reason: str, 
    task: str
) -> Dict[str, Any]:
    """Create update dict to mark state for rerouting"""
    return {
        "needs_rerouting": True,
        "agent_task": task,
        "agent_context": {
            "escalation_reason": reason,
            "from_agent": state.get("current_agent")
        }
    }


def mark_conversation_end(state: SimplifiedState, reason: str) -> Dict[str, Any]:
    """Create update dict to end conversation"""
    return {
        "should_end": True,
        "agent_context": {
            **state.get("agent_context", {}),
            "end_reason": reason
        }
    }


# Export all
__all__ = [
    "SimplifiedState",
    "create_initial_simplified_state",
    "get_contact_name",
    "get_contact_email",
    "get_business_info",
    "get_budget_info",
    "is_qualified_for_appointment",
    "get_lead_category",
    "determine_agent_from_score",
    "mark_for_rerouting",
    "mark_conversation_end"
]
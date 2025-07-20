"""
Simplified Conversation State V2 - Only Essential Fields
Reduced from 50+ fields to 15 essential fields
"""
from typing import Dict, Any, List, Optional, Literal, Annotated
from datetime import datetime
from langchain_core.messages import AnyMessage
from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages

class ConversationStateV2(MessagesState):
    """
    Simplified state with only essential fields for the conversation flow
    """
    # Core identification
    contact_id: str
    contact_info: Dict[str, Any]  # Name, email, phone from GHL
    
    # Lead scoring (from intelligence layer)
    lead_score: int = 0
    extracted_data: Dict[str, Any] = {}  # Name, business, budget, etc.
    
    # Routing control
    current_agent: Optional[Literal["maria", "carlos", "sofia"]] = None
    next_agent: Optional[Literal["maria", "carlos", "sofia"]] = None
    agent_context: Dict[str, Any] = {}  # Context from AI supervisor
    routing_attempts: int = 0
    
    # Flow control
    needs_rerouting: bool = False
    escalation_reason: str = ""
    should_end: bool = False
    
    # GHL integration
    previous_custom_fields: Dict[str, Any] = {}  # Score, business, etc from GHL
    webhook_data: Dict[str, Any] = {}  # Original webhook payload
    
    # Optional fields (only when needed)
    appointment_booked: bool = False
    available_slots: List[Dict[str, Any]] = []


# For backward compatibility, keep the original name pointing to V2
ConversationState = ConversationStateV2

__all__ = ["ConversationStateV2", "ConversationState"]
"""
Enhanced Conversation State with Proper Tracking
This solves the conversation repetition issue by tracking what's been asked and answered
"""
from typing import Dict, Any, List, Optional, Set, Annotated
from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage
from enum import Enum
from typing_extensions import TypedDict


class ConversationStage(Enum):
    """Exact conversation stages"""
    GREETING = "greeting"
    COLLECTING_NAME = "collecting_name"
    COLLECTING_BUSINESS = "collecting_business"
    COLLECTING_CHALLENGE = "collecting_challenge"
    COLLECTING_BUDGET = "collecting_budget"
    COLLECTING_EMAIL = "collecting_email"
    OFFERING_APPOINTMENT = "offering_appointment"
    BOOKING_APPOINTMENT = "booking_appointment"
    COMPLETED = "completed"


def merge_collected_data(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    """Merge new collected data with existing, never losing information"""
    merged = left.copy()
    for key, value in right.items():
        if value is not None and value != "":
            merged[key] = value
    return merged


def merge_questions_asked(left: Set[str], right: Set[str]) -> Set[str]:
    """Merge sets of questions asked"""
    return left.union(right)


class EnhancedConversationState(MessagesState):
    """
    Enhanced state that tracks conversation progress and prevents repetition
    """
    # Basic info
    contact_id: str
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    
    # Collected data with smart merging
    collected_data: Annotated[Dict[str, Any], merge_collected_data] = {
        "name": None,
        "business_type": None,
        "challenge": None,
        "budget_confirmed": False,
        "budget_amount": None,
        "email": None,
        "preferred_time": None
    }
    
    # Track what we've asked to prevent repetition
    questions_asked: Annotated[Set[str], merge_questions_asked] = set()
    
    # Track what we're waiting for
    expecting_answer_for: Optional[str] = None
    
    # Current conversation stage
    current_stage: ConversationStage = ConversationStage.GREETING
    
    # Lead scoring
    lead_score: int = 1
    lead_category: str = "cold"
    
    # Routing
    current_agent: str = "receptionist"
    next_agent: Optional[str] = None
    needs_rerouting: bool = False
    escalation_reason: Optional[str] = None
    
    # Workflow control
    routing_attempts: int = 0
    interaction_count: int = 0
    should_end: bool = False
    
    # Response tracking
    response_sent: bool = False
    last_ai_response: Optional[str] = None
    
    # Context summary for agents
    conversation_summary: Optional[str] = None
    
    # Error handling
    error: Optional[str] = None
    
    # Additional context from webhook/GHL
    contact_info: Optional[Dict[str, Any]] = None
    conversation_history: Optional[List[Dict[str, Any]]] = None
    previous_custom_fields: Optional[Dict[str, str]] = None


class ConversationAnalysis(TypedDict):
    """Analysis result from conversation enforcer"""
    current_stage: ConversationStage
    collected_data: Dict[str, Any]
    questions_asked: Set[str]
    expecting_answer_for: Optional[str]
    next_question_to_ask: Optional[str]
    can_skip_to: Optional[str]
    language: str
    last_human_message: Optional[str]
    last_ai_question: Optional[str]
    conversation_summary: str
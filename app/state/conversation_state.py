"""
Conversation state definition for LangGraph workflow
"""
from typing import List, Literal, Optional, Dict, Any, Annotated
from typing_extensions import TypedDict
from datetime import datetime
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph.message import add_messages


class ConversationState(TypedDict):
    """
    Main state object for the conversation workflow.
    This tracks all information needed throughout the conversation lifecycle.
    """
    
    # Message history - using add_messages reducer for proper message handling
    messages: Annotated[List[BaseMessage], add_messages]
    
    # Contact Information
    # Using operator.add for contact_id to handle parallel updates
    # This allows multiple nodes to update contact_id without conflicts
    contact_id: Annotated[str, lambda x, y: y if y else x]  # Keep latest non-empty value
    thread_id: Optional[str]  # Current conversation thread ID for history filtering
    contact_name: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    
    # Lead Information
    lead_score: int  # 1-10
    previous_score: int  # For tracking score changes
    route: Literal["cold", "warm", "hot"]  # Current routing
    intent: Literal[
        "LISTO_COMPRAR",
        "BUSCANDO_INFO", 
        "COMPARANDO_OPCIONES",
        "SOLO_PREGUNTANDO",
        "NO_INTERESADO"
    ]
    
    # Collected Information
    business_type: Optional[str]
    goal: Optional[str]
    budget: Optional[str]
    preferred_day: Optional[str]
    preferred_time: Optional[str]
    
    # Agent Assignment
    current_agent: Literal["maria", "carlos", "sofia"]
    agent_history: List[Dict[str, Any]]  # Track agent handoffs
    
    # Appointment Information
    appointment_booked: bool
    appointment_id: Optional[str]
    appointment_datetime: Optional[datetime]
    
    # Workflow Control
    current_step: Literal[
        "receive_message",
        "analyze_lead", 
        "route_to_agent",
        "collect_name",
        "collect_business",
        "collect_goal",
        "collect_budget",
        "collect_email",
        "check_calendar",
        "book_appointment",
        "send_response",
        "end"
    ]
    next_action: Optional[str]
    
    # Response Management
    pending_response: Optional[str]  # Response to be sent
    last_response_sent: Optional[str]  # Last message sent to user
    response_sent: bool  # Whether response has been sent
    
    # Error Handling
    error: Optional[str]
    retry_count: int
    
    # Metadata
    conversation_started_at: datetime
    last_updated_at: datetime
    language: Literal["en", "es"]  # Detected language
    
    # Raw webhook data (for reference)
    webhook_data: Dict[str, Any]
    
    # Data loaded by receptionist
    contact_info: Optional[Dict[str, Any]]  # Full contact details from GHL
    previous_custom_fields: Optional[Dict[str, Any]]  # Custom fields from GHL
    conversation_history: Optional[List[Dict[str, Any]]]  # Previous messages
    
    # Analysis Results
    ai_analysis: Optional[Dict[str, Any]]  # Store full AI analysis
    extracted_data: Dict[str, Any]  # Extracted information from messages
    
    # Intelligence Layer Results (new fields for structured analysis)
    score_history: List[Dict[str, Any]]  # Track score changes over time
    lead_category: Optional[Literal["cold", "warm", "hot"]]  # Explicit category
    suggested_agent: Optional[Literal["maria", "carlos", "sofia"]]  # Routing suggestion
    analysis_metadata: Optional[Dict[str, Any]]  # Analysis details and confidence
    score_reasoning: Optional[str]  # Explanation for current score
    
    # Loop Prevention Fields (to prevent expensive agent loops)
    interaction_count: int  # Number of agent interactions in this conversation
    should_end: bool  # Explicit flag to end the conversation
    
    # Required by create_react_agent for internal loop management
    remaining_steps: int  # Steps remaining for agent execution
    
    # Workflow-specific fields for node coordination
    next_agent: Optional[Literal["sofia", "carlos", "maria"]]  # Next agent to route to
    supervisor_complete: Optional[bool]  # Whether supervisor has completed analysis
    data_loaded: Optional[bool]  # Whether receptionist loaded all data
    receptionist_complete: Optional[bool]  # Whether receptionist completed
    
    # Responder tracking fields
    responder_status: Optional[str]  # Status of message sending
    messages_sent_count: Optional[int]  # Number of messages sent
    messages_failed_count: Optional[int]  # Number of failed messages
    failed_messages: Optional[List[str]]  # List of failed message details
    
    # Appointment booking
    available_slots: Optional[List[Dict[str, Any]]]  # Available calendar slots
    
    # LINEAR FLOW: Escalation fields
    escalation_reason: Optional[str]  # Why agent escalated
    escalation_details: Optional[str]  # Details about escalation
    escalation_from: Optional[str]  # Which agent escalated
    needs_rerouting: Optional[bool]  # Flag for supervisor to re-route
    routing_attempts: Optional[int]  # Track routing attempts to prevent loops


def create_initial_state(webhook_data: Dict[str, Any]) -> ConversationState:
    """
    Create initial state from webhook data
    
    Args:
        webhook_data: Raw webhook data from GoHighLevel
        
    Returns:
        Initial conversation state
    """
    now = datetime.utcnow()
    
    # Create initial human message
    initial_message = HumanMessage(
        content=webhook_data.get("message", ""),
        additional_kwargs={
            "contact_id": webhook_data.get("contactId", webhook_data.get("id")),
            "timestamp": now.isoformat()
        }
    )
    
    return ConversationState(
        # Messages
        messages=[initial_message],
        
        # Contact Info
        contact_id=webhook_data.get("contactId", webhook_data.get("id", "")),
        contact_name=webhook_data.get("name"),
        contact_email=webhook_data.get("email"),
        contact_phone=webhook_data.get("phone"),
        
        # Lead Info (defaults)
        lead_score=0,
        previous_score=0,
        route="cold",
        intent="BUSCANDO_INFO",
        
        # Collected Info
        business_type=None,
        goal=None,
        budget=None,
        preferred_day=None,
        preferred_time=None,
        
        # Agent
        current_agent="maria",  # Default to cold agent
        agent_history=[],
        
        # Appointment
        appointment_booked=False,
        appointment_id=None,
        appointment_datetime=None,
        
        # Workflow
        current_step="receive_message",
        next_action=None,
        
        # Response
        pending_response=None,
        last_response_sent=None,
        response_sent=False,
        
        # Error Handling
        error=None,
        retry_count=0,
        
        # Metadata
        conversation_started_at=now,
        last_updated_at=now,
        language="es",  # Default to Spanish
        
        # Raw Data
        webhook_data=webhook_data,
        ai_analysis=None,
        extracted_data={},
        
        # Intelligence Layer
        score_history=[],
        lead_category="cold",
        suggested_agent="maria",
        analysis_metadata=None,
        score_reasoning=None,
        
        # Loop Prevention
        interaction_count=0,
        should_end=False,
        remaining_steps=10,  # Default steps for create_react_agent
        
        # Workflow coordination
        next_agent=None,
        supervisor_complete=False,
        data_loaded=False,
        receptionist_complete=False,
        
        # Responder tracking
        responder_status=None,
        messages_sent_count=0,
        messages_failed_count=0,
        failed_messages=[],
        
        # Appointment booking
        available_slots=None,
        
        # LINEAR FLOW: Escalation fields
        escalation_reason=None,
        escalation_details=None,
        escalation_from=None,
        needs_rerouting=False,
        routing_attempts=0
    )


def update_state_timestamp(state: ConversationState) -> ConversationState:
    """Update the last_updated_at timestamp"""
    state["last_updated_at"] = datetime.utcnow()
    return state


def add_message_to_state(
    state: ConversationState, 
    content: str, 
    is_human: bool = True,
    **kwargs
) -> ConversationState:
    """
    Add a message to the conversation state
    
    Args:
        state: Current conversation state
        content: Message content
        is_human: Whether this is a human message (vs AI)
        **kwargs: Additional message metadata
        
    Returns:
        Updated state
    """
    message_class = HumanMessage if is_human else AIMessage
    message = message_class(
        content=content,
        additional_kwargs={
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
    )
    
    # Messages will be appended due to Annotated[List[BaseMessage], operator.add]
    state["messages"] = [message]
    
    return update_state_timestamp(state)


def determine_route_from_score(score: int) -> Literal["cold", "warm", "hot"]:
    """Determine route based on lead score"""
    if score <= 4:
        return "cold"
    elif score <= 7:
        return "warm"
    else:
        return "hot"


def determine_agent_from_route(route: Literal["cold", "warm", "hot"]) -> Literal["maria", "carlos", "sofia"]:
    """Determine which agent should handle based on route"""
    agent_map = {
        "cold": "maria",
        "warm": "carlos",
        "hot": "sofia"
    }
    return agent_map[route]


def should_handoff_agent(state: ConversationState) -> bool:
    """
    Determine if agent handoff is needed based on score change
    
    Args:
        state: Current conversation state
        
    Returns:
        True if handoff needed
    """
    current_route = determine_route_from_score(state["lead_score"])
    previous_route = determine_route_from_score(state["previous_score"])
    
    return current_route != previous_route


def get_missing_required_data(state: ConversationState) -> List[str]:
    """
    Get list of missing required data fields
    
    Args:
        state: Current conversation state
        
    Returns:
        List of missing field names
    """
    required_fields = {
        "contact_name": state["contact_name"],
        "business_type": state["business_type"],
        "goal": state["goal"],
        "budget": state["budget"],
        "contact_email": state["contact_email"]
    }
    
    missing = []
    for field, value in required_fields.items():
        if not value:
            missing.append(field)
            
    return missing


def can_book_appointment(state: ConversationState) -> bool:
    """
    Check if all requirements are met for booking an appointment
    
    Args:
        state: Current conversation state
        
    Returns:
        True if can book appointment
    """
    # Must be hot lead
    if state["route"] != "hot":
        return False
        
    # Must have all required data
    if get_missing_required_data(state):
        return False
        
    # Must not already have appointment
    if state["appointment_booked"]:
        return False
        
    # Must have confirmed intent to buy
    if state["intent"] not in ["LISTO_COMPRAR"]:
        return False
        
    return True
"""
Minimal conversation state - only what we ACTUALLY use in production
Reduced from 100+ fields to essential 23 fields
"""
from typing import List, Literal, Optional, Dict, Any, Annotated
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class MinimalState(TypedDict):
    """
    Minimal state for the conversation workflow.
    Only includes fields that are actively used in production.
    """
    
    # Core fields (always used)
    messages: Annotated[List[BaseMessage], add_messages]  # Message history with reducer
    contact_id: str  # Primary identifier
    thread_id: Optional[str]  # Conversation thread ID
    webhook_data: Dict[str, Any]  # Raw webhook data
    
    # Lead scoring (intelligence layer)
    lead_score: int  # 1-10 score
    lead_category: Literal["cold", "warm", "hot"]  # Score-based category
    extracted_data: Dict[str, Any]  # All extracted information
    score_reasoning: Optional[str]  # Why this score was given
    score_history: List[Dict[str, Any]]  # Track score changes
    
    # Agent routing
    current_agent: Literal["maria", "carlos", "sofia"]  # Active agent
    next_agent: Optional[Literal["maria", "carlos", "sofia"]]  # Next routing
    suggested_agent: Optional[Literal["maria", "carlos", "sofia"]]  # Intelligence suggestion
    agent_task: Optional[str]  # Task description for handoffs
    
    # Workflow control
    supervisor_complete: bool  # Supervisor finished analysis
    should_end: bool  # Explicit end flag
    routing_attempts: int  # Prevent infinite loops
    interaction_count: int  # Total agent interactions
    
    # Escalation (LINEAR FLOW)
    needs_rerouting: bool  # Agent requests new routing
    needs_escalation: bool  # Agent needs supervisor help
    escalation_reason: Optional[str]  # Why escalating
    
    # Response tracking
    response_sent: bool  # Message sent to customer
    last_sent_message: Optional[str]  # Track duplicates
    
    # Optional contact info (loaded by receptionist)
    contact_info: Optional[Dict[str, Any]]  # Full GHL contact
    previous_custom_fields: Optional[Dict[str, Any]]  # GHL custom fields
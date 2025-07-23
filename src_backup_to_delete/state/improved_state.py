"""
Improved state definition using LangGraph best practices
Uses reducers for automatic state merging and proper message handling
"""
from typing import TypedDict, Annotated, List, Dict, Any, Optional
from langgraph.graph.message import add_messages
from operator import add
from datetime import datetime


def merge_extracted_data(left: dict, right: dict) -> dict:
    """Custom reducer to merge extracted data dictionaries"""
    # Create a copy of left to avoid mutations
    result = left.copy()
    
    # Merge right into result, preferring non-None values
    for key, value in right.items():
        if value is not None:  # Only update if new value is not None
            result[key] = value
    
    return result


def update_score_history(left: list, right: list) -> list:
    """Custom reducer to append score history entries"""
    # Combine both lists
    combined = left + right
    
    # Sort by timestamp to maintain chronological order
    # Assumes each entry has a 'timestamp' field
    try:
        sorted_history = sorted(
            combined,
            key=lambda x: x.get('timestamp', ''),
            reverse=False  # Oldest first
        )
        return sorted_history
    except:
        # If sorting fails, just return combined list
        return combined


class ImprovedState(TypedDict):
    """
    Improved state using LangGraph reducers for automatic state management
    
    Key improvements:
    1. Messages use add_messages reducer for proper deduplication and merging
    2. Lead score uses add reducer for automatic summing
    3. Extracted data uses custom merger to preserve and update fields
    4. Score history uses custom reducer to maintain chronological order
    """
    
    # Message handling with built-in reducer
    messages: Annotated[List[Any], add_messages]
    """Messages are automatically merged, deduplicated by ID"""
    
    # Webhook and identification
    webhook_data: Dict[str, Any]
    """Raw webhook data from GoHighLevel"""
    
    contact_id: str
    """Primary contact identifier"""
    
    thread_id: str
    """Thread identifier for checkpoint persistence"""
    
    conversation_id: Optional[str]
    """GHL conversation ID if available"""
    
    # Lead scoring with automatic addition
    lead_score: Annotated[int, add]
    """Lead score automatically sums when updated"""
    
    lead_category: str
    """Lead category: cold, warm, hot"""
    
    # Data extraction with smart merging
    extracted_data: Annotated[Dict[str, Any], merge_extracted_data]
    """Extracted data automatically merges, preserving non-None values"""
    
    # Score history with chronological ordering
    score_history: Annotated[List[Dict], update_score_history]
    """Score history automatically maintains chronological order"""
    
    # Agent routing
    next_agent: Optional[str]
    """Next agent to route to"""
    
    suggested_agent: Optional[str]
    """Suggested agent from supervisor"""
    
    agent_task: Optional[str]
    """Task description for the agent"""
    
    # Workflow control
    supervisor_complete: bool
    """Whether supervisor has completed routing"""
    
    should_end: bool
    """Whether workflow should end"""
    
    needs_escalation: bool
    """Whether current agent needs to escalate"""
    
    escalation_reason: Optional[str]
    """Reason for escalation"""
    
    # Conversation context
    is_new_conversation: bool
    """Whether this is a new conversation"""
    
    conversation_stage: str
    """Current stage of conversation"""
    
    # Response tracking
    last_sent_message: Optional[str]
    """Last message sent to contact"""
    
    message_sent: bool
    """Whether a message was sent in this workflow"""
    
    # Additional metadata
    contact_info: Dict[str, Any]
    """Contact information from GHL"""
    
    location_id: str
    """GHL location ID"""
    
    # Timestamps
    workflow_started_at: str
    """When this workflow execution started"""
    
    last_updated_at: str
    """When state was last updated"""


# Example usage showing the benefits:
"""
# OLD WAY - Manual state management:
def agent_node(state):
    # Had to manually handle messages
    messages = state.get("messages", [])
    messages.append(AIMessage(content="Hello"))
    
    # Had to manually update score
    score = state.get("lead_score", 0)
    score += 5
    
    return {
        "messages": messages,
        "lead_score": score,
        # ... other updates
    }

# NEW WAY - Automatic state management:
def agent_node(state):
    return {
        "messages": [AIMessage(content="Hello")],  # Automatically appended
        "lead_score": 5,  # Automatically added to existing score
        "extracted_data": {"name": "John"},  # Automatically merged
        # ... other updates
    }
"""

# Migration guide:
"""
1. Update imports in workflow.py:
   from app.state.improved_state import ImprovedState

2. Replace MinimalState with ImprovedState:
   workflow_graph = StateGraph(ImprovedState)

3. Update agents to return partial state updates:
   - Don't manually append to lists
   - Don't manually calculate new scores
   - Just return the values to add/merge

4. Benefits:
   - Cleaner agent code
   - Automatic deduplication of messages
   - No more manual state merging
   - Thread-safe operations
"""
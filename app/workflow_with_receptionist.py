"""
Complete Workflow with Receptionist Pattern
Matches n8n flow exactly:
1. Webhook → Receptionist (loads all data)
2. Intelligence (analyzes and scores)
3. Supervisor (routes with context)
4. Agents → Responder
"""
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

# Import state
from app.state.conversation_state import ConversationState

# Import nodes in order
from app.agents.receptionist_agent import receptionist_node
from app.intelligence.analyzer import intelligence_node
from app.intelligence.ghl_updater import ghl_update_node
from app.agents.supervisor import supervisor_node
from app.agents.sofia_agent_v2 import sofia_node_v2
from app.agents.carlos_agent_v2 import carlos_node_v2
from app.agents.maria_agent_v2 import maria_node_v2
from app.agents.responder_agent import responder_node

# Import utilities
from app.utils.simple_logger import get_logger

logger = get_logger("workflow_with_receptionist")


# Routing function from supervisor
def route_from_supervisor(state: ConversationState) -> Literal["sofia", "carlos", "maria", "end"]:
    """Route based on supervisor decision"""
    # Check end conditions
    if state.get("should_end", False):
        return "end"
    
    if state.get("interaction_count", 0) >= 3:
        return "end"
    
    # Get routing decision
    next_agent = state.get("next_agent")
    
    if next_agent in ["sofia", "carlos", "maria"]:
        logger.info(f"Routing to: {next_agent}")
        return next_agent
    
    # Default to end
    return "end"


def create_complete_workflow():
    """
    Create workflow matching n8n pattern:
    
    1. Receptionist - Loads all GHL data
    2. Intelligence - Analyzes and scores
    3. GHL Update - Persists changes
    4. Supervisor - Routes with context
    5. Agents - Handle conversation
    6. Responder - Sends messages
    """
    # Create workflow
    workflow = StateGraph(ConversationState)
    
    # Add all nodes
    workflow.add_node("receptionist", receptionist_node)
    workflow.add_node("intelligence", intelligence_node)
    workflow.add_node("ghl_update", ghl_update_node)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("sofia", sofia_node_v2)
    workflow.add_node("carlos", carlos_node_v2)
    workflow.add_node("maria", maria_node_v2)
    workflow.add_node("responder", responder_node)
    
    # Set entry point - receptionist first!
    workflow.set_entry_point("receptionist")
    
    # Linear flow for data preparation
    workflow.add_edge("receptionist", "intelligence")
    workflow.add_edge("intelligence", "ghl_update")
    workflow.add_edge("ghl_update", "supervisor")
    
    # Conditional routing from supervisor
    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "sofia": "sofia",
            "carlos": "carlos",
            "maria": "maria",
            "end": END
        }
    )
    
    # All agents go to responder
    workflow.add_edge("sofia", "responder")
    workflow.add_edge("carlos", "responder")
    workflow.add_edge("maria", "responder")
    
    # Responder ends
    workflow.add_edge("responder", END)
    
    # Add memory and store
    checkpointer = MemorySaver()
    store = InMemoryStore()
    
    # Compile
    app = workflow.compile(
        checkpointer=checkpointer,
        store=store
    )
    
    logger.info("""
    ✅ Complete workflow created matching n8n:
    1. Receptionist loads all GHL data first
    2. Intelligence analyzes and scores
    3. GHL Update persists changes
    4. Supervisor routes with full context
    5. Agents process with complete information
    6. Responder ensures delivery
    
    Flow: Webhook → Receptionist → Intelligence → Update → Supervisor → Agent → Responder
    """)
    
    return app


# Create and export
complete_workflow = create_complete_workflow()

__all__ = ["complete_workflow"]
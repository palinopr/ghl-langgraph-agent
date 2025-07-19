"""
Complete Workflow with Supervisor Brain
Consolidated pattern matching n8n flow:
1. Webhook → Receptionist (loads all data)
2. Supervisor Brain (analyzes, scores, updates GHL, routes)
3. Agents → Responder
"""
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

# Import state
from app.state.conversation_state import ConversationState

# Import nodes
from app.agents.receptionist_simple import receptionist_simple_node
from app.agents.supervisor_brain_simple import supervisor_brain_simple_node
from app.agents.sofia_agent_v2 import sofia_node_v2
from app.agents.carlos_agent_v2 import carlos_node_v2
from app.agents.maria_agent_v2 import maria_node_v2
from app.agents.responder_agent import responder_node

# Import utilities
from app.utils.simple_logger import get_logger

logger = get_logger("workflow_supervisor_brain")


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


def create_supervisor_brain_workflow():
    """
    Create workflow with consolidated Supervisor Brain:
    
    1. Receptionist - Loads all GHL data
    2. Supervisor Brain - Analyzes, scores, updates GHL, routes
    3. Agents - Handle conversation
    4. Responder - Sends messages
    """
    # Create workflow
    workflow = StateGraph(ConversationState)
    
    # Add all nodes
    workflow.add_node("receptionist", receptionist_simple_node)
    workflow.add_node("supervisor_brain", supervisor_brain_simple_node)
    workflow.add_node("sofia", sofia_node_v2)
    workflow.add_node("carlos", carlos_node_v2)
    workflow.add_node("maria", maria_node_v2)
    workflow.add_node("responder", responder_node)
    
    # Set entry point - receptionist first!
    workflow.set_entry_point("receptionist")
    
    # Linear flow: Receptionist → Supervisor Brain
    workflow.add_edge("receptionist", "supervisor_brain")
    
    # Conditional routing from supervisor brain
    workflow.add_conditional_edges(
        "supervisor_brain",
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
    ✅ Supervisor Brain workflow created:
    1. Receptionist loads all GHL data first
    2. Supervisor Brain does EVERYTHING:
       - Analyzes and scores lead
       - Updates GHL (score, tags, fields, notes)
       - Routes to appropriate agent
    3. Agents process with complete information
    4. Responder ensures delivery
    
    Flow: Webhook → Receptionist → Supervisor Brain → Agent → Responder
    """)
    
    return app


# Create and export
supervisor_brain_workflow = create_supervisor_brain_workflow()

__all__ = ["supervisor_brain_workflow"]
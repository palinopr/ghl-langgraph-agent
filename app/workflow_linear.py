"""
LINEAR WORKFLOW - No Agent-to-Agent Transfers
Implements true linear flow like n8n:
1. Webhook → Receptionist (loads all data)
2. Supervisor Brain (analyzes, scores, updates GHL, routes)
3. ONE Agent (responds OR escalates back to supervisor)
4. Responder → END

Key difference: Agents can only escalate back to supervisor, not transfer to each other
"""
from typing import Dict, Any, Literal, Union
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
from app.agents.responder_agent_fixed import responder_node_fixed as responder_node

# Import utilities
from app.utils.simple_logger import get_logger

logger = get_logger("workflow_linear")


def route_from_supervisor(state: ConversationState) -> Literal["sofia", "carlos", "maria", "end"]:
    """
    Route based on supervisor decision
    This is the ONLY place where agent routing happens
    """
    # Check end conditions
    if state.get("should_end", False):
        logger.info("Ending workflow: should_end flag is True")
        return "end"
    
    # Check max routing attempts (prevent infinite loops)
    routing_attempts = state.get("routing_attempts", 0)
    if routing_attempts >= 2:
        logger.warning(f"Max routing attempts reached ({routing_attempts}), ending workflow")
        return "end"
    
    # Get routing decision
    next_agent = state.get("next_agent")
    
    if next_agent in ["sofia", "carlos", "maria"]:
        logger.info(f"LINEAR ROUTING: Supervisor → {next_agent} (attempt {routing_attempts + 1}/2)")
        return next_agent
    
    # Default to end if no valid agent
    logger.warning(f"No valid next_agent found: {next_agent}, ending workflow")
    return "end"


def route_from_agent(state: ConversationState) -> Union[Literal["supervisor_brain", "responder"], str]:
    """
    Route from agent - can only go to responder or escalate back to supervisor
    NO direct agent-to-agent transfers allowed!
    """
    # Check if needs rerouting (escalation)
    if state.get("needs_rerouting", False):
        logger.info(f"ESCALATION: {state.get('current_agent')} → Supervisor (reason: {state.get('escalation_reason')})")
        # Clear the rerouting flag for next iteration
        return "supervisor_brain"
    
    # Normal flow: agent → responder
    logger.info(f"Normal flow: {state.get('current_agent')} → Responder")
    return "responder"


def create_linear_workflow():
    """
    Create LINEAR workflow - no agent-to-agent transfers:
    
    1. Receptionist - Loads all GHL data
    2. Supervisor Brain - Analyzes, scores, updates GHL, routes
    3. Agent - Handles conversation (can escalate back to supervisor)
    4. Responder - Sends messages
    
    Key: Agents can ONLY escalate to supervisor, not transfer to each other
    """
    # Create workflow
    workflow = StateGraph(ConversationState)
    
    # Add all nodes
    workflow.add_node("receptionist", receptionist_simple_node)  # Using production version with filtering
    workflow.add_node("supervisor_brain", supervisor_brain_simple_node)
    workflow.add_node("sofia", sofia_node_v2)
    workflow.add_node("carlos", carlos_node_v2)
    workflow.add_node("maria", maria_node_v2)
    workflow.add_node("responder", responder_node)
    
    # Set entry point - receptionist first!
    workflow.set_entry_point("receptionist")
    
    # Linear flow: Receptionist → Supervisor Brain
    workflow.add_edge("receptionist", "supervisor_brain")
    
    # Supervisor routes to ONE agent (or ends)
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
    
    # Each agent can either:
    # 1. Go to responder (normal flow)
    # 2. Escalate back to supervisor (needs rerouting)
    workflow.add_conditional_edges(
        "sofia",
        route_from_agent,
        {
            "responder": "responder",
            "supervisor_brain": "supervisor_brain"  # Escalation only!
        }
    )
    
    workflow.add_conditional_edges(
        "carlos",
        route_from_agent,
        {
            "responder": "responder",
            "supervisor_brain": "supervisor_brain"  # Escalation only!
        }
    )
    
    workflow.add_conditional_edges(
        "maria",
        route_from_agent,
        {
            "responder": "responder",
            "supervisor_brain": "supervisor_brain"  # Escalation only!
        }
    )
    
    # Responder always ends
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
    ✅ LINEAR workflow created - NO agent-to-agent transfers!
    
    Flow patterns:
    1. Normal: Webhook → Receptionist → Supervisor → Agent → Responder → END
    2. Escalation: Agent → Supervisor → Different Agent → Responder → END
    
    Key differences from circular flow:
    - Agents CANNOT transfer to each other
    - Agents can ONLY escalate back to supervisor
    - Supervisor makes ALL routing decisions
    - Maximum 2 routing attempts to prevent loops
    
    This matches the n8n pattern where routing is centralized!
    """)
    
    return app


# Create and export
linear_workflow = create_linear_workflow()

__all__ = ["linear_workflow", "create_linear_workflow"]
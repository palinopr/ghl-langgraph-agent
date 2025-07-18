"""
Enhanced Workflow with Supervisor as the Brain
This workflow matches the n8n pattern where supervisor loads everything first
"""
from typing import Dict, Any, Literal, Union
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.types import Command
from langchain_core.messages import AIMessage, HumanMessage

# Import enhanced supervisor and state
from app.agents.supervisor_enhanced import create_enhanced_supervisor, SupervisorState
from app.state.conversation_state import ConversationState

# Import agent nodes
from app.agents.sofia_agent_v2 import sofia_node_v2
from app.agents.carlos_agent_v2 import carlos_node_v2
from app.agents.maria_agent_v2 import maria_node_v2
from app.agents.responder_agent import responder_node

# Import utilities
from app.utils.simple_logger import get_logger
from app.config import get_settings

logger = get_logger("workflow_enhanced_supervisor")


# Enhanced supervisor node wrapper
async def enhanced_supervisor_node(state: Dict[str, Any]) -> Union[Command, Dict[str, Any]]:
    """
    Enhanced supervisor that loads GHL data first, then analyzes and routes
    """
    try:
        # Create enhanced supervisor
        supervisor = create_enhanced_supervisor()
        
        # The supervisor will:
        # 1. Load full GHL context
        # 2. Analyze what changed
        # 3. Update GHL with changes
        # 4. Route with full context
        result = await supervisor.ainvoke(state)
        
        # Extract routing decision from messages
        messages = result.get("messages", [])
        last_message = messages[-1] if messages else None
        
        # Check if supervisor used a routing tool
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            for tool_call in last_message.tool_calls:
                if hasattr(tool_call, "name") and "route_to_agent" in tool_call.name:
                    # Return the command from the tool
                    return result
        
        # Return state updates
        return {
            "messages": messages,
            "context_loaded": True,
            "ghl_data_loaded": True
        }
        
    except Exception as e:
        logger.error(f"Enhanced supervisor error: {e}", exc_info=True)
        # Fallback to Maria on error
        error_msg = AIMessage(
            content="I need to check your information. One moment please.",
            name="supervisor"
        )
        return {
            "messages": [error_msg],
            "next_agent": "maria",
            "error": str(e)
        }


# Routing function based on supervisor decision
def route_from_enhanced_supervisor(state: SupervisorState) -> Literal["sofia", "carlos", "maria", "end"]:
    """
    Route based on enhanced supervisor decision
    """
    # Check end conditions
    if state.get("should_end", False):
        logger.info("Routing to END due to should_end flag")
        return "end"
    
    # Check interaction limit
    if state.get("interaction_count", 0) >= 3:
        logger.info("Routing to END due to interaction limit")
        return "end"
    
    # Get next agent from state
    next_agent = state.get("next_agent")
    
    # Validate agent name
    if next_agent in ["sofia", "carlos", "maria"]:
        logger.info(f"Routing to agent: {next_agent}")
        return next_agent
    
    # Default to end if no valid agent
    logger.warning(f"Invalid agent name: {next_agent}, ending")
    return "end"


def create_enhanced_workflow():
    """
    Create workflow with enhanced supervisor as the brain
    
    Flow:
    1. START → Enhanced Supervisor (loads GHL, analyzes, updates, routes)
    2. Supervisor → Agent (with full context)
    3. Agent → Responder
    4. Responder → END
    """
    # Create workflow with enhanced state
    workflow = StateGraph(SupervisorState)
    
    # Add nodes
    workflow.add_node("enhanced_supervisor", enhanced_supervisor_node)
    workflow.add_node("sofia", sofia_node_v2)
    workflow.add_node("carlos", carlos_node_v2)
    workflow.add_node("maria", maria_node_v2)
    workflow.add_node("responder", responder_node)
    
    # Set entry point - supervisor is now first
    workflow.set_entry_point("enhanced_supervisor")
    
    # Add edges from supervisor
    workflow.add_conditional_edges(
        "enhanced_supervisor",
        route_from_enhanced_supervisor,
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
    
    # Compile workflow
    app = workflow.compile(
        checkpointer=checkpointer,
        store=store
    )
    
    logger.info("""
    ✅ Enhanced workflow created with:
    - Supervisor as the brain (loads GHL data first)
    - Full context loading before routing
    - Automatic score updates and analysis
    - Context passed to all agents
    - Responder for message delivery
    """)
    
    return app


# Create the enhanced workflow
enhanced_workflow = create_enhanced_workflow()

# Export for langgraph.json
__all__ = ["enhanced_workflow"]
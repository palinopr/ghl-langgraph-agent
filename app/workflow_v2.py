"""
Main LangGraph workflow for GoHighLevel messaging agent - MODERNIZED VERSION
Using latest patterns: Command objects, create_react_agent, supervisor pattern
"""
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.types import Command
from app.state.conversation_state import ConversationState
from app.agents.supervisor import supervisor_node
from app.agents.sofia_agent_v2 import sofia_node_v2, create_sofia_agent

# Import placeholders for other agents (to be implemented)
# For now, we'll use Sofia's implementation as a template
carlos_node_v2 = sofia_node_v2  # TODO: Import from carlos_agent_v2
maria_node_v2 = sofia_node_v2   # TODO: Import from maria_agent_v2
create_carlos_agent = create_sofia_agent  # TODO: Import actual implementation
create_maria_agent = create_sofia_agent   # TODO: Import actual implementation
from app.utils.simple_logger import get_logger

logger = get_logger("workflow_v2")


def create_workflow_v2() -> StateGraph:
    """
    Create the modernized LangGraph workflow with supervisor pattern
    
    Returns:
        Compiled StateGraph workflow
    """
    # Create the graph with ConversationState
    workflow = StateGraph(ConversationState)
    
    # Add the supervisor node (orchestrator)
    workflow.add_node(
        "supervisor", 
        supervisor_node,
        # Specify possible destinations from supervisor
        destinations=["sofia", "carlos", "maria", END]
    )
    
    # Add agent nodes with their modernized implementations
    workflow.add_node("sofia", sofia_node_v2)
    workflow.add_node("carlos", carlos_node_v2)
    workflow.add_node("maria", maria_node_v2)
    
    # Set entry point to supervisor
    workflow.add_edge(START, "supervisor")
    
    # Add edges from agents back to supervisor
    # Agents can return Commands to route elsewhere or end
    workflow.add_edge("sofia", "supervisor")
    workflow.add_edge("carlos", "supervisor")
    workflow.add_edge("maria", "supervisor")
    
    # The supervisor handles all routing logic via Commands
    # No need for conditional edges - Commands handle routing
    
    logger.info("Created modernized workflow with supervisor pattern")
    
    return workflow


def create_workflow_with_memory_v2() -> StateGraph:
    """
    Create workflow with persistent memory and store
    
    Returns:
        Compiled StateGraph with checkpointer and store
    """
    workflow = create_workflow_v2()
    
    # Add memory checkpointer for conversation persistence
    checkpointer = MemorySaver()
    
    # Add store for semantic search and long-term memory
    store = InMemoryStore()
    
    # Compile with checkpointer and store
    app = workflow.compile(
        checkpointer=checkpointer,
        store=store
    )
    
    logger.info("Created workflow with memory persistence and store")
    
    return app


# Alternative: Create individual agent graphs for testing
def create_sofia_graph():
    """Create a standalone Sofia agent graph"""
    from langgraph.prebuilt import create_react_agent
    from app.tools.agent_tools_v2 import appointment_tools_v2
    from app.agents.sofia_agent_v2 import SofiaState, sofia_prompt
    from app.config import get_settings
    
    settings = get_settings()
    
    agent = create_react_agent(
        model=f"openai:{settings.openai_model}",
        tools=appointment_tools_v2,
        state_schema=SofiaState,
        prompt=sofia_prompt,
        checkpointer=MemorySaver(),
        store=InMemoryStore()
    )
    
    return agent


# Helper function to run the workflow
async def run_workflow_v2(
    contact_id: str,
    message: str,
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Run the modernized workflow for a given message
    
    Args:
        contact_id: Contact ID
        message: Incoming message
        context: Additional context (contact info, etc.)
        
    Returns:
        Workflow response
    """
    from langchain_core.messages import HumanMessage
    
    # Create initial state
    initial_state = {
        "messages": [HumanMessage(content=message)],
        "contact_id": contact_id,
        "contact_info": context or {},
        "current_agent": None,
    }
    
    # Get workflow
    app = create_workflow_with_memory_v2()
    
    # Run workflow with thread ID for conversation continuity
    config = {"configurable": {"thread_id": contact_id}}
    
    try:
        # Stream results for real-time processing
        async for event in app.astream(initial_state, config):
            logger.debug(f"Workflow event: {event}")
            
        # Get final state
        final_state = await app.aget_state(config)
        
        logger.info(f"Workflow completed for contact {contact_id}")
        return final_state.values
        
    except Exception as e:
        logger.error(f"Error running workflow: {str(e)}", exc_info=True)
        raise


# Create the compiled workflow for LangGraph Platform
workflow = create_workflow_with_memory_v2()

# Export main components
__all__ = [
    "create_workflow_v2",
    "create_workflow_with_memory_v2",
    "create_sofia_graph",
    "run_workflow_v2",
    "workflow"
]
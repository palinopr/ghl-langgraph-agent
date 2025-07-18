"""
Main LangGraph workflow for GoHighLevel messaging agent
Orchestrates the flow between Sofia, Carlos, and Maria
"""
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver
from .state.conversation_state import ConversationState
from .agents import sofia_node, carlos_node, maria_node, orchestrator_node
from .utils.logger import get_workflow_logger

logger = get_logger("main_workflow")


def should_continue(state: ConversationState) -> Literal["orchestrator", "end"]:
    """
    Determine if the workflow should continue or end
    
    Args:
        state: Current conversation state
        
    Returns:
        "orchestrator" to continue, "end" to stop
    """
    # Check if we should stop
    if state.get("should_continue") is False:
        return "end"
        
    # Check if appointment was booked and confirmed
    if state.get("appointment_status") == "booked" and len(state.get("messages", [])) > 2:
        last_message = state["messages"][-1].content.lower()
        if any(phrase in last_message for phrase in ["thank", "great", "perfect", "see you"]):
            return "end"
    
    # Check if conversation is getting too long
    if len(state.get("messages", [])) > 30:
        logger.warning("Conversation exceeding 30 messages, ending")
        return "end"
        
    # Continue by default
    return "orchestrator"


def route_to_agent(state: ConversationState) -> Literal["sofia", "carlos", "maria"]:
    """
    Route to the appropriate agent based on orchestrator decision
    
    Args:
        state: Current conversation state
        
    Returns:
        Agent name to route to
    """
    next_agent = state.get("next_agent", "maria")
    logger.info(f"Routing to agent: {next_agent}")
    return next_agent


def create_workflow() -> StateGraph:
    """
    Create the main LangGraph workflow
    
    Returns:
        Compiled StateGraph workflow
    """
    # Create the graph
    workflow = StateGraph(ConversationState)
    
    # Add nodes
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("sofia", sofia_node)
    workflow.add_node("carlos", carlos_node)
    workflow.add_node("maria", maria_node)
    
    # Add edges
    # Start with orchestrator
    workflow.set_entry_point("orchestrator")
    
    # From orchestrator, route to appropriate agent
    workflow.add_conditional_edges(
        "orchestrator",
        route_to_agent,
        {
            "sofia": "sofia",
            "carlos": "carlos",
            "maria": "maria"
        }
    )
    
    # From each agent, decide whether to continue or end
    workflow.add_conditional_edges(
        "sofia",
        should_continue,
        {
            "orchestrator": "orchestrator",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "carlos", 
        should_continue,
        {
            "orchestrator": "orchestrator",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "maria",
        should_continue,
        {
            "orchestrator": "orchestrator",
            "end": END
        }
    )
    
    return workflow


def create_workflow_with_memory() -> StateGraph:
    """
    Create workflow with persistent memory
    
    Returns:
        Compiled StateGraph with checkpointer
    """
    workflow = create_workflow()
    
    # Add memory checkpointer
    checkpointer = InMemorySaver()
    
    # Compile with checkpointer
    app = workflow.compile(checkpointer=checkpointer)
    
    logger.info("Created workflow with memory persistence")
    
    return app


# Helper function to run the workflow
async def run_workflow(
    contact_id: str,
    message: str,
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Run the workflow for a given message
    
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
        "agent_responses": []
    }
    
    # Get workflow
    app = create_workflow_with_memory()
    
    # Run workflow
    config = {"configurable": {"thread_id": contact_id}}
    
    try:
        result = await app.ainvoke(initial_state, config)
        logger.info(f"Workflow completed for contact {contact_id}")
        return result
    except Exception as e:
        logger.error(f"Error running workflow: {str(e)}", exc_info=True)
        raise


# Export main components
__all__ = [
    "create_workflow",
    "create_workflow_with_memory",
    "run_workflow"
]
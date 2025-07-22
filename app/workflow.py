"""
Modernized Workflow with Official LangGraph Patterns
Implements all the latest patterns from LangGraph documentation:
1. Official supervisor pattern with task descriptions
2. Command objects for agent handoffs
3. Health check endpoints integration
4. Simplified state management
5. Better error handling and routing
"""
from typing import Dict, Any, Literal, Union
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from langchain_core.messages import AIMessage, HumanMessage

# Import enhanced state
from app.state.minimal_state import MinimalState

# Import modernized nodes
from app.agents.receptionist_memory_aware import receptionist_memory_aware_node
from app.agents.supervisor import supervisor_node
from app.agents.maria_memory_aware import maria_memory_aware_node
from app.agents.carlos_agent_v2_fixed import carlos_node_v2_fixed as carlos_node
from app.agents.sofia_agent_v2_fixed import sofia_node_v2_fixed as sofia_node
from app.agents.responder_streaming import responder_streaming_node as responder_node
from app.intelligence.analyzer import intelligence_node

# Import utilities
from app.utils.simple_logger import get_logger

logger = get_logger("workflow")


def enhance_agent_with_task(agent_func):
    """
    Decorator to enhance agents with task awareness
    """
    async def enhanced_agent(state: Dict[str, Any]) -> Dict[str, Any]:
        # Add task context to state if available
        agent_task = state.get("agent_task")
        if agent_task:
            logger.info(f"Agent received task: {agent_task}")
            # Add task as a system message for context
            task_msg = AIMessage(
                content=f"[Task from supervisor: {agent_task}]",
                name="system"
            )
            if "messages" not in state:
                state["messages"] = []
            state["messages"].append(task_msg)
        
        # Run the original agent
        result = await agent_func(state)
        
        # Clear task after processing
        if "agent_task" in result:
            result["agent_task"] = None
            
        return result
    
    return enhanced_agent


def route_from_supervisor(state: MinimalState) -> Literal["maria", "carlos", "sofia", "responder", "end"]:
    """Route based on supervisor decision"""
    if state.get("should_end", False):
        logger.info("Ending workflow: should_end flag is True")
        return "end"
    
    # Check if supervisor completed
    if not state.get("supervisor_complete"):
        logger.warning("Supervisor not complete, ending workflow")
        return "end"
    
    # Check routing attempts
    routing_attempts = state.get("routing_attempts", 0)
    if routing_attempts >= 3:
        logger.warning("Max routing attempts reached, going to responder")
        return "responder"
    
    next_agent = state.get("next_agent")
    
    if next_agent in ["maria", "carlos", "sofia"]:
        logger.info(f"ROUTING: Supervisor → {next_agent}")
        if state.get("agent_task"):
            logger.info(f"Task: {state['agent_task']}")
        return next_agent
    
    # If no explicit routing, check if we have messages to send
    if state.get("messages"):
        logger.info("No explicit routing, going to responder")
        return "responder"
    
    logger.warning(f"Invalid next_agent: {next_agent}, ending workflow")
    return "end"


def route_from_agent(state: MinimalState) -> Union[Literal["supervisor", "responder"], str]:
    """Route from agent - can escalate back to supervisor or proceed to responder"""
    if state.get("needs_rerouting", False) or state.get("needs_escalation", False):
        reason = state.get("escalation_reason", "unknown")
        logger.info(f"ESCALATION: {state.get('current_agent')} → Supervisor (reason: {reason})")
        
        # Increment routing attempts
        state["routing_attempts"] = state.get("routing_attempts", 0) + 1
        
        # Reset supervisor complete flag for re-routing
        state["supervisor_complete"] = False
        
        return "supervisor"
    
    # Normal flow to responder
    logger.info(f"Normal flow: {state.get('current_agent')} → Responder")
    return "responder"


def create_modernized_workflow():
    """
    Create workflow with official LangGraph patterns
    
    Features:
    1. Official supervisor pattern with handoff tools
    2. Task descriptions in agent handoffs
    3. Command objects for routing
    4. Clean state management
    5. Better error handling
    """
    logger.info("Creating modernized workflow with official patterns")
    
    # Create workflow with standard state
    workflow = StateGraph(MinimalState)
    
    # Enhance agents with task awareness
    maria_enhanced = enhance_agent_with_task(maria_memory_aware_node)
    carlos_enhanced = enhance_agent_with_task(carlos_node)
    sofia_enhanced = enhance_agent_with_task(sofia_node)
    
    # Add all nodes
    workflow.add_node("receptionist", receptionist_memory_aware_node)
    workflow.add_node("intelligence", intelligence_node)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("maria", maria_enhanced)
    workflow.add_node("carlos", carlos_enhanced)
    workflow.add_node("sofia", sofia_enhanced)
    workflow.add_node("responder", responder_node)
    
    # Set entry point
    workflow.set_entry_point("receptionist")
    
    # Define edges
    workflow.add_edge("receptionist", "intelligence")
    workflow.add_edge("intelligence", "supervisor")
    
    # Supervisor routing with official pattern
    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "maria": "maria",
            "carlos": "carlos",
            "sofia": "sofia",
            "responder": "responder",
            "end": END
        }
    )
    
    # Agent routing with escalation support
    for agent in ["maria", "carlos", "sofia"]:
        workflow.add_conditional_edges(
            agent,
            route_from_agent,
            {
                "responder": "responder",
                "supervisor": "supervisor"
            }
        )
    
    # Responder ends
    workflow.add_edge("responder", END)
    
    # Compile with minimal memory
    memory = MemorySaver()
    store = InMemoryStore()
    
    compiled = workflow.compile(
        checkpointer=memory,
        store=store
    )
    
    logger.info("Modernized workflow compiled successfully")
    
    return compiled


# Create the workflow
workflow = create_modernized_workflow()


async def run_workflow(webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the workflow with webhook data
    
    Args:
        webhook_data: Webhook data from GHL
        
    Returns:
        Workflow result
    """
    try:
        # Extract contact ID, message, and thread ID
        contact_id = webhook_data.get("contactId", webhook_data.get("id", "unknown"))
        message_body = webhook_data.get("body", webhook_data.get("message", ""))
        # Use GHL conversationId as thread_id for consistency
        thread_id = (
            webhook_data.get("conversationId") or  # GHL conversation ID
            webhook_data.get("threadId") or        # Fallback to threadId
            f"contact-{contact_id}"                # Last resort: contact-based
        )
        logger.info(f"Using thread_id: {thread_id} for contact: {contact_id}")
        
        # Create initial state
        initial_state = {
            "messages": [HumanMessage(content=message_body)],
            "contact_id": contact_id,
            "thread_id": thread_id,  # Add thread ID for conversation filtering
            "webhook_data": webhook_data,
            "extracted_data": {},
            "lead_score": 0,
            "should_end": False,
            "routing_attempts": 0
        }
        
        
        # Run the workflow
        logger.info(f"Running workflow for contact {contact_id}")
        result = await workflow.ainvoke(
            initial_state,
            config={"configurable": {"thread_id": thread_id}}  # Use consistent thread_id
        )
        
        logger.info(f"Workflow completed for contact {contact_id}")
        return {
            "success": True,
            "contact_id": contact_id,
            "message_sent": result.get("message_sent", False),
            "final_state": result
        }
        
    except Exception as e:
        logger.error(f"Error in workflow: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "contact_id": webhook_data.get("contactId", "unknown")
        }


# Export for langgraph.json and imports
__all__ = ["workflow", "run_workflow"]
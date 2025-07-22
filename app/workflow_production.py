"""
Production workflow without custom checkpointer
For testing with LangGraph Studio/Cloud
"""
from typing import Dict, Any, Literal, Union
from langgraph.graph import StateGraph, END, START
from langchain_core.messages import AIMessage, HumanMessage
import os

# Import enhanced state
from app.state.minimal_state import MinimalState

# Import modernized nodes
from app.agents.receptionist_checkpoint_aware import receptionist_checkpoint_aware_node
from app.agents.supervisor import supervisor_node
from app.agents.maria_memory_aware import maria_memory_aware_node
from app.agents.carlos_agent_v2_fixed import carlos_node_v2_fixed as carlos_node
from app.agents.sofia_agent_v2_fixed import sofia_node_v2_fixed as sofia_node
from app.agents.responder_streaming import responder_streaming_node as responder_node
from app.intelligence.analyzer import intelligence_node

# Import utilities
from app.utils.simple_logger import get_logger

logger = get_logger("workflow_production")


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


# Create workflow for production
logger.info("Creating production workflow for LangGraph")

# Create workflow with standard state
workflow_graph = StateGraph(MinimalState)

# Import enhanced thread mapper
from app.agents.thread_id_mapper_enhanced import thread_id_mapper_enhanced_node as thread_id_mapper_node

# Enhance agents with task awareness
maria_enhanced = enhance_agent_with_task(maria_memory_aware_node)
carlos_enhanced = enhance_agent_with_task(carlos_node)
sofia_enhanced = enhance_agent_with_task(sofia_node)

# Add all nodes - thread mapper FIRST
workflow_graph.add_node("thread_mapper", thread_id_mapper_node)
workflow_graph.add_node("receptionist", receptionist_checkpoint_aware_node)
workflow_graph.add_node("intelligence", intelligence_node)
workflow_graph.add_node("supervisor", supervisor_node)
workflow_graph.add_node("maria", maria_enhanced)
workflow_graph.add_node("carlos", carlos_enhanced)
workflow_graph.add_node("sofia", sofia_enhanced)
workflow_graph.add_node("responder", responder_node)

# Set entry point to thread mapper
workflow_graph.set_entry_point("thread_mapper")

# Define edges
workflow_graph.add_edge("thread_mapper", "receptionist")  # Thread mapper runs first
workflow_graph.add_edge("receptionist", "intelligence")
workflow_graph.add_edge("intelligence", "supervisor")

# Supervisor routing with official pattern
workflow_graph.add_conditional_edges(
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
    workflow_graph.add_conditional_edges(
        agent,
        route_from_agent,
        {
            "responder": "responder",
            "supervisor": "supervisor"
        }
    )

# Responder ends
workflow_graph.add_edge("responder", END)

# Compile WITHOUT checkpointer for Studio/Cloud
workflow = workflow_graph.compile()

logger.info("Production workflow compiled (no custom checkpointer)")

# Export the compiled workflow
__all__ = ["workflow"]
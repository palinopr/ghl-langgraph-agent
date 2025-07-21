"""
Memory-Optimized Workflow
Implements all memory management improvements
"""
from typing import Dict, Any, Literal, Union
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

# Import enhanced state
from app.state.memory_aware_state import MemoryAwareState

# Import memory-aware nodes
from app.agents.receptionist_memory_aware import receptionist_memory_aware_node
from app.agents.supervisor_memory_aware import supervisor_memory_aware_node
from app.agents.maria_memory_aware import maria_memory_aware_node
from app.agents.carlos_agent_v2_fixed import carlos_node_v2_fixed as carlos_node
from app.agents.sofia_agent_v2_fixed import sofia_node_v2_fixed as sofia_node
from app.agents.responder_streaming import responder_streaming_node as responder_node
from app.intelligence.analyzer import intelligence_node

# Import utilities
from app.utils.simple_logger import get_logger
from app.utils.memory_manager import get_memory_manager
from app.utils.context_filter import ContextFilter

logger = get_logger("workflow_memory_optimized")


def create_memory_aware_nodes():
    """
    Create memory-aware versions of Carlos and Sofia
    """
    # We'll enhance Carlos and Sofia inline for now
    # In production, create separate memory-aware versions
    
    async def carlos_memory_aware(state: Dict[str, Any]) -> Dict[str, Any]:
        """Carlos with memory isolation"""
        memory_manager = get_memory_manager()
        
        # Get Carlos's isolated context
        carlos_context = memory_manager.get_agent_context("carlos", state)
        
        # Filter messages for Carlos
        filtered_messages = ContextFilter.filter_messages_for_agent(
            state.get("messages", []),
            "carlos",
            max_messages=8
        )
        
        # Create temporary state with filtered messages
        carlos_state = state.copy()
        carlos_state["messages"] = filtered_messages
        carlos_state["agent_context"] = carlos_context
        
        # Run Carlos with clean context
        result = await carlos_node(carlos_state)
        
        # Restore full message list but keep Carlos's additions
        if len(result.get("messages", [])) > len(filtered_messages):
            # Carlos added new messages
            new_messages = result["messages"][len(filtered_messages):]
            state["messages"].extend(new_messages)
            
            # Add to Carlos's memory
            for msg in new_messages:
                memory_manager.add_agent_message("carlos", msg)
        
        # Copy other updates
        for key in ["needs_rerouting", "escalation_reason"]:
            if key in result:
                state[key] = result[key]
        
        return state
    
    async def sofia_memory_aware(state: Dict[str, Any]) -> Dict[str, Any]:
        """Sofia with memory isolation"""
        memory_manager = get_memory_manager()
        
        # Get Sofia's isolated context
        sofia_context = memory_manager.get_agent_context("sofia", state)
        
        # Filter messages for Sofia
        filtered_messages = ContextFilter.filter_messages_for_agent(
            state.get("messages", []),
            "sofia",
            max_messages=6  # Sofia needs less context
        )
        
        # Create temporary state with filtered messages
        sofia_state = state.copy()
        sofia_state["messages"] = filtered_messages
        sofia_state["agent_context"] = sofia_context
        
        # Run Sofia with clean context
        result = await sofia_node(sofia_state)
        
        # Restore and update
        if len(result.get("messages", [])) > len(filtered_messages):
            new_messages = result["messages"][len(filtered_messages):]
            state["messages"].extend(new_messages)
            
            for msg in new_messages:
                memory_manager.add_agent_message("sofia", msg)
        
        return state
    
    return carlos_memory_aware, sofia_memory_aware


def route_from_supervisor(state: MemoryAwareState) -> Literal["maria", "carlos", "sofia", "end"]:
    """Route based on supervisor decision with memory awareness"""
    if state.get("should_end", False):
        logger.info("Ending workflow: should_end flag is True")
        return "end"
    
    # Check routing attempts
    routing_attempts = state.get("routing_attempts", 0)
    if routing_attempts >= 3:
        logger.warning("Max routing attempts reached, ending workflow")
        return "end"
    
    next_agent = state.get("next_agent")
    
    if next_agent in ["maria", "carlos", "sofia"]:
        logger.info(f"MEMORY-AWARE ROUTING: → {next_agent}")
        
        # Log memory stats
        memory_manager = get_memory_manager()
        if next_agent in memory_manager.agent_memories:
            agent_memory = memory_manager.agent_memories[next_agent]
            logger.info(f"{next_agent} memory: {len(agent_memory.current_context)} messages")
        
        return next_agent
    
    logger.warning(f"Invalid next_agent: {next_agent}, ending workflow")
    return "end"


def route_from_agent(state: MemoryAwareState) -> Union[Literal["supervisor", "responder"], str]:
    """Route from agent with memory handoff consideration"""
    if state.get("needs_rerouting", False) or state.get("needs_escalation", False):
        reason = state.get("escalation_reason", "unknown")
        logger.info(f"ESCALATION: {state.get('current_agent')} → Supervisor (reason: {reason})")
        
        # Prepare for handoff
        memory_manager = get_memory_manager()
        current_agent = state.get("current_agent")
        if current_agent:
            # This will trigger memory handoff in supervisor
            state["pending_handoff"] = True
        
        return "supervisor"
    
    # Normal flow to responder
    logger.info(f"Normal flow: {state.get('current_agent')} → Responder")
    return "responder"


def create_memory_optimized_workflow():
    """
    Create workflow with full memory management
    
    Features:
    1. Memory isolation per agent
    2. Context filtering
    3. Clean handoffs
    4. Historical separation
    5. Sliding window memory
    """
    logger.info("Creating memory-optimized workflow")
    
    # Create workflow with enhanced state
    workflow = StateGraph(MemoryAwareState)
    
    # Get memory-aware node variants
    carlos_memory_aware, sofia_memory_aware = create_memory_aware_nodes()
    
    # Add all nodes
    workflow.add_node("receptionist", receptionist_memory_aware_node)
    workflow.add_node("intelligence", intelligence_node)
    workflow.add_node("supervisor", supervisor_memory_aware_node)
    workflow.add_node("maria", maria_memory_aware_node)
    workflow.add_node("carlos", carlos_memory_aware)
    workflow.add_node("sofia", sofia_memory_aware)
    workflow.add_node("responder", responder_node)
    
    # Set entry point
    workflow.set_entry_point("receptionist")
    
    # Define edges
    workflow.add_edge("receptionist", "intelligence")
    workflow.add_edge("intelligence", "supervisor")
    
    # Supervisor routing with memory awareness
    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "maria": "maria",
            "carlos": "carlos",
            "sofia": "sofia",
            "end": END
        }
    )
    
    # Agent routing with handoff support
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
    
    logger.info("Memory-optimized workflow compiled successfully")
    
    return compiled


# Create the workflow
memory_optimized_workflow = create_memory_optimized_workflow()

# Export
__all__ = ["memory_optimized_workflow", "create_memory_optimized_workflow"]
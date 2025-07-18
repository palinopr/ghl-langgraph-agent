"""
Enhanced LangGraph workflow with streaming, parallel processing, and error recovery
This shows how to integrate all the new features into your existing workflow
"""
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from app.state.conversation_state import ConversationState
from app.intelligence.analyzer import intelligence_node
from app.intelligence.ghl_updater import ghl_update_node
from app.agents.supervisor import supervisor_node

# Import enhanced agents
from app.agents.sofia_agent_v2_enhanced import sofia_node_v2 as sofia_enhanced
from app.agents.carlos_agent_v2_enhanced import carlos_node_v2 as carlos_enhanced
from app.agents.maria_agent_v2 import maria_node_v2

# Import error recovery
from app.utils.error_recovery import error_recovery_middleware, handle_graph_recursion
from app.utils.simple_logger import get_logger

logger = get_logger("workflow_enhanced")


# Wrap nodes with error recovery
@handle_graph_recursion(max_depth=30)
async def protected_supervisor_node(state: ConversationState):
    """Supervisor with recursion protection"""
    return await error_recovery_middleware(supervisor_node, state)


async def protected_sofia_node(state: ConversationState):
    """Sofia with error recovery"""
    return await error_recovery_middleware(sofia_enhanced, state)


async def protected_carlos_node(state: ConversationState):
    """Carlos with error recovery"""
    return await error_recovery_middleware(carlos_enhanced, state)


async def protected_maria_node(state: ConversationState):
    """Maria with error recovery"""
    return await error_recovery_middleware(maria_node_v2, state)


def create_enhanced_workflow() -> StateGraph:
    """
    Create the enhanced workflow with all new features
    """
    # Create the graph
    workflow = StateGraph(ConversationState)
    
    # Add nodes with protection
    workflow.add_node("intelligence", intelligence_node)
    workflow.add_node("ghl_update", ghl_update_node)
    workflow.add_node("supervisor", protected_supervisor_node)
    workflow.add_node("sofia", protected_sofia_node)
    workflow.add_node("carlos", protected_carlos_node)
    workflow.add_node("maria", protected_maria_node)
    
    # Entry point
    workflow.set_entry_point("intelligence")
    
    # Intelligence -> GHL Update -> Supervisor
    workflow.add_edge("intelligence", "ghl_update")
    workflow.add_edge("ghl_update", "supervisor")
    
    # Supervisor edges (handled by Commands from tools)
    # Agents can return to supervisor or end
    workflow.add_edge("sofia", "supervisor")
    workflow.add_edge("carlos", "supervisor")
    workflow.add_edge("maria", "supervisor")
    
    # Conditional edges from supervisor
    def supervisor_route(state: ConversationState) -> Literal["sofia", "carlos", "maria", END]:
        # Check if we should end
        if state.get("should_continue") is False:
            return END
            
        # Check for errors that require ending
        if state.get("error") == "recursion_limit":
            return END
            
        # Route based on next_agent or supervisor decision
        next_agent = state.get("next_agent")
        if next_agent in ["sofia", "carlos", "maria"]:
            return next_agent
            
        # Default to END if no clear direction
        return END
    
    workflow.add_conditional_edges(
        "supervisor",
        supervisor_route,
        {
            "sofia": "sofia",
            "carlos": "carlos", 
            "maria": "maria",
            END: END
        }
    )
    
    return workflow


def create_enhanced_workflow_with_memory() -> StateGraph:
    """
    Create enhanced workflow with memory persistence
    """
    workflow = create_enhanced_workflow()
    
    # Add checkpointing
    memory = MemorySaver()
    
    # Add semantic memory store
    store = InMemoryStore()
    
    # Compile with memory
    return workflow.compile(
        checkpointer=memory,
        store=store
    )


# Streaming wrapper for real-time responses
async def stream_enhanced_workflow(
    contact_id: str,
    message: str,
    context: Dict[str, Any] = None
):
    """
    Stream workflow responses for better UX
    """
    workflow = create_enhanced_workflow_with_memory()
    
    # Create initial state
    initial_state = {
        "messages": [{"role": "user", "content": message}],
        "contact_id": contact_id,
        "contact_info": context or {},
        "stream_response": True  # Enable streaming
    }
    
    # Configuration
    config = {
        "configurable": {
            "thread_id": contact_id,
            "checkpoint_ns": "enhanced"
        }
    }
    
    try:
        # Stream events
        async for event in workflow.astream_events(
            initial_state,
            config,
            version="v2"
        ):
            # Handle different event types
            if event["event"] == "on_chat_model_stream":
                # Stream tokens from agents
                chunk = event.get("data", {}).get("chunk", {})
                if chunk.get("content"):
                    yield {
                        "type": "token",
                        "content": chunk["content"],
                        "agent": event.get("metadata", {}).get("agent_name")
                    }
                    
            elif event["event"] == "on_tool_start":
                # Notify about tool usage
                yield {
                    "type": "tool_start",
                    "tool": event.get("name"),
                    "agent": event.get("metadata", {}).get("agent_name")
                }
                
            elif event["event"] == "on_tool_end":
                # Tool completion
                yield {
                    "type": "tool_end",
                    "tool": event.get("name"),
                    "output": event.get("data", {}).get("output")
                }
                
    except Exception as e:
        logger.error(f"Streaming error: {e}")
        yield {
            "type": "error",
            "message": "Stream interrupted. Falling back to standard response."
        }


# Performance monitoring
async def run_enhanced_workflow_with_metrics(
    contact_id: str,
    message: str,
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Run workflow with performance metrics
    """
    import time
    
    workflow = create_enhanced_workflow_with_memory()
    
    # Track metrics
    start_time = time.time()
    token_count = 0
    tool_calls = 0
    
    initial_state = {
        "messages": [{"role": "user", "content": message}],
        "contact_id": contact_id,
        "contact_info": context or {}
    }
    
    config = {
        "configurable": {"thread_id": contact_id},
        "callbacks": []  # Add callbacks for metrics
    }
    
    try:
        result = await workflow.ainvoke(initial_state, config)
        
        # Calculate metrics
        elapsed_time = time.time() - start_time
        
        # Add metrics to result
        result["_metrics"] = {
            "elapsed_time": elapsed_time,
            "token_count": token_count,
            "tool_calls": tool_calls,
            "agents_used": result.get("agent_history", [])
        }
        
        logger.info(f"Workflow completed in {elapsed_time:.2f}s")
        
        return result
        
    except Exception as e:
        logger.error(f"Workflow error: {e}")
        return {
            "error": str(e),
            "elapsed_time": time.time() - start_time
        }


# Export enhanced components
__all__ = [
    "create_enhanced_workflow",
    "create_enhanced_workflow_with_memory",
    "stream_enhanced_workflow",
    "run_enhanced_workflow_with_metrics"
]
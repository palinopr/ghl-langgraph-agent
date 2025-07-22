"""
Workflow with Async SQLite Checkpoint Implementation
Properly handles AsyncSqliteSaver with context managers
"""
from typing import Dict, Any, Literal, Union
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.store.memory import InMemoryStore
from langchain_core.messages import AIMessage, HumanMessage
import os

# Import enhanced state
from app.state.minimal_state import MinimalState

# Import checkpoint-aware receptionist
from app.agents.receptionist_checkpoint_aware import receptionist_checkpoint_aware_node

# Import other nodes
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
        return await agent_func(state)
    
    return enhanced_agent


def route_from_supervisor(state: Dict[str, Any]) -> str:
    """Route based on supervisor decision"""
    next_agent = state.get("next_agent")
    
    if next_agent == "FINISH" or state.get("should_end", False):
        logger.info("Supervisor routing to END")
        return "end"
    
    if not next_agent:
        logger.warning("No next_agent specified, defaulting to responder")
        return "responder"
    
    logger.info(f"Supervisor routing to: {next_agent}")
    return next_agent


def route_from_agent(state: Dict[str, Any]) -> str:
    """Route from agent based on escalation needs"""
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


async def create_workflow_with_sqlite():
    """
    Create workflow with SQLite persistence using async context manager
    """
    logger.info("Creating workflow with async SQLite persistence")
    
    # Create workflow with standard state
    workflow_graph = StateGraph(MinimalState)
    
    # Enhance agents with task awareness
    maria_enhanced = enhance_agent_with_task(maria_memory_aware_node)
    carlos_enhanced = enhance_agent_with_task(carlos_node)
    sofia_enhanced = enhance_agent_with_task(sofia_node)
    
    # Add all nodes - using checkpoint-aware receptionist
    workflow_graph.add_node("receptionist", receptionist_checkpoint_aware_node)
    workflow_graph.add_node("intelligence", intelligence_node)
    workflow_graph.add_node("supervisor", supervisor_node)
    workflow_graph.add_node("maria", maria_enhanced)
    workflow_graph.add_node("carlos", carlos_enhanced)
    workflow_graph.add_node("sofia", sofia_enhanced)
    workflow_graph.add_node("responder", responder_node)
    
    # Set entry point
    workflow_graph.set_entry_point("receptionist")
    
    # Define edges
    workflow_graph.add_edge("receptionist", "intelligence")
    workflow_graph.add_edge("intelligence", "supervisor")
    
    # Supervisor routing
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
    
    # Compile with SQLite persistence
    checkpoint_db = os.path.join(os.path.dirname(__file__), "checkpoints.db")
    logger.info(f"Using SQLite checkpoint database: {checkpoint_db}")
    
    # Create async SQLite checkpointer and compile within context
    async with AsyncSqliteSaver.from_conn_string(checkpoint_db) as checkpointer:
        store = InMemoryStore()
        
        compiled = workflow_graph.compile(
            checkpointer=checkpointer,
            store=store
        )
        
        logger.info("Workflow compiled with async SQLite persistence")
        
        # Return both workflow and checkpointer for use
        return compiled, checkpointer, checkpoint_db


async def run_workflow_async(webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the workflow with proper async SQLite checkpoint loading
    """
    try:
        # Extract identifiers
        contact_id = webhook_data.get("contactId", webhook_data.get("id", "unknown"))
        message_body = webhook_data.get("body", webhook_data.get("message", ""))
        conversation_id = webhook_data.get("conversationId")
        
        # CRITICAL: Use consistent thread_id based on contact
        thread_id = f"contact-{contact_id}"
        logger.info(f"Thread ID: {thread_id} for contact: {contact_id}")
        
        # Configuration for checkpointer
        config = {"configurable": {"thread_id": thread_id}}
        
        # Create workflow with SQLite checkpointer
        workflow, checkpointer, db_path = await create_workflow_with_sqlite()
        
        # Try to get existing state from checkpoint
        existing_state = None
        try:
            # Get the latest checkpoint
            checkpoint_tuple = await checkpointer.aget(config)
            
            if checkpoint_tuple and checkpoint_tuple.checkpoint:
                existing_state = checkpoint_tuple.checkpoint.get("channel_values", {})
                existing_messages = existing_state.get("messages", [])
                logger.info(f"✅ Loaded {len(existing_messages)} messages from SQLite for thread {thread_id}")
                
                # Debug: Show last message for context
                if existing_messages:
                    logger.info(f"Last message: '{existing_messages[-1].content}'")
                    logger.info("=== CHECKPOINT MESSAGES ===")
                    for i, msg in enumerate(existing_messages[-3:]):
                        logger.info(f"  [{i}] {type(msg).__name__}: {str(msg.content)[:50]}...")
                    logger.info("=== END CHECKPOINT ===")
            else:
                logger.info(f"🆕 No checkpoint in SQLite for thread {thread_id} - new conversation")
        except Exception as e:
            logger.warning(f"Could not load checkpoint: {e}")
        
        # Create initial state
        if existing_state and "messages" in existing_state:
            # Use checkpoint state as base
            initial_state = {
                **existing_state,  # Preserve all checkpoint data
                "webhook_data": webhook_data,
                "thread_id": thread_id,
                # Don't add new message here - receptionist will handle it
            }
            logger.info(f"Using checkpoint state with {len(initial_state.get('messages', []))} existing messages")
        else:
            # Fresh state if no checkpoint
            initial_state = {
                "messages": [],  # Empty - receptionist will add the message
                "contact_id": contact_id,
                "thread_id": thread_id,
                "webhook_data": webhook_data,
                "extracted_data": {},
                "lead_score": 0,
                "should_end": False,
                "routing_attempts": 0
            }
            logger.info("Starting with fresh state (no checkpoint)")
        
        # Run the workflow
        logger.info(f"Running workflow for contact {contact_id}")
        result = await workflow.ainvoke(
            initial_state,
            config=config  # Pass config for checkpoint saving
        )
        
        logger.info(f"Workflow completed for contact {contact_id}")
        logger.info(f"Final state has {len(result.get('messages', []))} messages")
        
        # Extract last sent message if available
        messages = result.get("messages", [])
        last_sent_message = None
        for msg in reversed(messages):
            if hasattr(msg, 'name') and msg.name in ['maria', 'carlos', 'sofia', 'responder']:
                last_sent_message = msg.content
                break
        
        return {
            "success": True,
            "contact_id": contact_id,
            "thread_id": thread_id,
            "message_sent": result.get("message_sent", False),
            "message_count": len(result.get("messages", [])),
            "checkpoint_loaded": existing_state is not None,
            "last_sent_message": last_sent_message,
            "messages": messages,  # Include for testing
            "final_state": result,  # Include full state for debugging
            "db_path": db_path  # Include DB path for verification
        }
        
    except Exception as e:
        logger.error(f"Error in workflow: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "contact_id": webhook_data.get("contactId", "unknown")
        }


# For backwards compatibility
async def run_workflow(webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for backwards compatibility"""
    return await run_workflow_async(webhook_data)


# Export for use
__all__ = ["run_workflow_async", "run_workflow"]
"""
Fixed Workflow with Proper SQLite Checkpoint Implementation
"""
from typing import Dict, Any, Literal, Union, Optional
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.sqlite import SqliteSaver
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

logger = get_logger("workflow_sqlite_fix")

# Global SQLite checkpointer instance
_sqlite_checkpointer = None
_checkpointer_path = None


def get_sqlite_checkpointer():
    """Get or create the global SQLite checkpointer"""
    global _sqlite_checkpointer, _checkpointer_path
    
    if _sqlite_checkpointer is None:
        import sqlite3
        _checkpointer_path = os.path.join(os.path.dirname(__file__), "checkpoints.db")
        # Create connection and checkpointer
        conn = sqlite3.connect(_checkpointer_path, check_same_thread=False)
        _sqlite_checkpointer = SqliteSaver(conn)
        # Setup the database schema
        with conn:
            _sqlite_checkpointer.setup()
        logger.info(f"Created SQLite checkpointer at: {_checkpointer_path}")
    
    return _sqlite_checkpointer


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


def create_sqlite_workflow():
    """
    Create workflow with SQLite persistence
    """
    logger.info("Creating SQLite-persisted workflow")
    
    # Create workflow with standard state
    workflow = StateGraph(MinimalState)
    
    # Enhance agents with task awareness
    maria_enhanced = enhance_agent_with_task(maria_memory_aware_node)
    carlos_enhanced = enhance_agent_with_task(carlos_node)
    sofia_enhanced = enhance_agent_with_task(sofia_node)
    
    # Add all nodes - using checkpoint-aware receptionist
    workflow.add_node("receptionist", receptionist_checkpoint_aware_node)
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
    
    # Supervisor routing
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
    
    # Get SQLite checkpointer
    checkpointer = get_sqlite_checkpointer()
    store = InMemoryStore()
    
    # Compile with SQLite persistence
    compiled = workflow.compile(
        checkpointer=checkpointer,
        store=store
    )
    
    logger.info("SQLite-persisted workflow compiled successfully")
    
    return compiled


# Create the workflow
workflow = create_sqlite_workflow()


async def run_workflow_with_sqlite(webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the workflow with SQLite checkpoint persistence
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
        
        # Get the checkpointer
        checkpointer = get_sqlite_checkpointer()
        
        # Try to get existing state from checkpoint
        existing_state = None
        try:
            # Get the latest checkpoint
            checkpoint_tuple = checkpointer.get_tuple(config)
            
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
            "final_state": result  # Include full state for debugging
        }
        
    except Exception as e:
        logger.error(f"Error in workflow: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "contact_id": webhook_data.get("contactId", "unknown")
        }


# Export for use
__all__ = ["workflow", "run_workflow_with_sqlite", "get_sqlite_checkpointer"]
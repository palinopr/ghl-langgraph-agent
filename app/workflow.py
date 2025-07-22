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
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.memory import InMemoryStore
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


async def create_modernized_workflow():
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
    workflow_graph = StateGraph(MinimalState)
    
    # Import thread mapper
    from app.agents.thread_id_mapper import thread_id_mapper_node
    
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
    
    # Compile with SQLite persistent memory
    checkpoint_db = os.path.join(os.path.dirname(__file__), "checkpoints.db")
    logger.info(f"Using SQLite checkpoint database: {checkpoint_db}")
    
    # Use async context manager for SQLite checkpointer
    async with AsyncSqliteSaver.from_conn_string(checkpoint_db) as memory:
        store = InMemoryStore()
        
        compiled = workflow_graph.compile(
            checkpointer=memory,
            store=store
        )
        
        logger.info("Modernized workflow compiled with SQLite persistence")
        
        return compiled, memory, checkpoint_db


def create_sync_workflow():
    """
    Create a synchronous workflow for module-level compilation.
    This is what LangGraph will import and use.
    """
    logger.info("Creating sync workflow for module export")
    
    # Create workflow with standard state
    workflow_graph = StateGraph(MinimalState)
    
    # Import thread mapper
    from app.agents.thread_id_mapper import thread_id_mapper_node
    
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
    
    # Compile with synchronous SQLite checkpointer for module export
    checkpoint_db = os.path.join(os.path.dirname(__file__), "checkpoints.db")
    
    # Use context manager for sync SQLite
    with SqliteSaver.from_conn_string(checkpoint_db) as checkpointer:
        store = InMemoryStore()
        
        compiled = workflow_graph.compile(
            checkpointer=checkpointer,
            store=store
        )
        
        logger.info(f"Sync workflow compiled with SQLite at {checkpoint_db}")
        
        return compiled


# Global workflow and checkpointer will be created on first use
_workflow = None
_checkpointer = None
_db_path = None


async def run_workflow(webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the workflow with proper checkpoint loading
    
    This ensures conversation history is preserved across messages
    """
    global _workflow, _checkpointer, _db_path
    
    try:
        # Extract identifiers
        contact_id = webhook_data.get("contactId", webhook_data.get("id", "unknown"))
        message_body = webhook_data.get("body", webhook_data.get("message", ""))
        conversation_id = webhook_data.get("conversationId")
        
        # CRITICAL: Use consistent thread_id - prefer conversationId for GHL consistency
        thread_id = (
            webhook_data.get("conversationId") or  # GHL conversation ID (primary)
            webhook_data.get("threadId") or        # Fallback to threadId
            f"contact-{contact_id}"                # Last resort: contact-based
        )
        logger.info(f"Using thread_id: {thread_id} for contact: {contact_id} (conversationId: {conversation_id})")
        
        # Configuration for checkpointer
        config = {"configurable": {"thread_id": thread_id}}
        
        # Create workflow if not exists (runs within SQLite context)
        if _workflow is None:
            _workflow, _checkpointer, _db_path = await create_modernized_workflow()
        
        # SQLite database path
        checkpoint_db = os.path.join(os.path.dirname(__file__), "checkpoints.db")
        
        # Try to get existing state from checkpoint
        existing_state = None
        try:
            # Use async context manager for checkpoint operations
            async with AsyncSqliteSaver.from_conn_string(checkpoint_db) as checkpointer:
                checkpoint_tuple = await checkpointer.aget(config)
                
                if checkpoint_tuple and checkpoint_tuple.checkpoint:
                    existing_state = checkpoint_tuple.checkpoint.get("channel_values", {})
                    existing_messages = existing_state.get("messages", [])
                    logger.info(f"✅ Loaded checkpoint for thread {thread_id}")
                    logger.info(f"   - Messages: {len(existing_messages)}")
                    logger.info(f"   - Extracted data: {existing_state.get('extracted_data', {})}")
                    logger.info(f"   - Lead score: {existing_state.get('lead_score', 0)}")
                    
                    # Debug: Show last few messages for context
                    if existing_messages:
                        logger.info("=== RECENT CONVERSATION HISTORY ===")
                        for i, msg in enumerate(existing_messages[-5:]):  # Show last 5 messages
                            msg_preview = str(msg.content)[:100].replace('\n', ' ')
                            logger.info(f"  [{i}] {type(msg).__name__}: {msg_preview}...")
                        logger.info("=== END HISTORY ===")
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
        
        # Run the workflow within SQLite context
        logger.info(f"Running workflow for contact {contact_id}")
        async with AsyncSqliteSaver.from_conn_string(checkpoint_db) as runtime_checkpointer:
            # Re-compile workflow with runtime checkpointer
            workflow_graph = StateGraph(MinimalState)
            
            # Quick rebuild (same structure as create_modernized_workflow)
            from app.agents.thread_id_mapper import thread_id_mapper_node
            
            maria_enhanced = enhance_agent_with_task(maria_memory_aware_node)
            carlos_enhanced = enhance_agent_with_task(carlos_node)
            sofia_enhanced = enhance_agent_with_task(sofia_node)
            
            workflow_graph.add_node("thread_mapper", thread_id_mapper_node)
            workflow_graph.add_node("receptionist", receptionist_checkpoint_aware_node)
            workflow_graph.add_node("intelligence", intelligence_node)
            workflow_graph.add_node("supervisor", supervisor_node)
            workflow_graph.add_node("maria", maria_enhanced)
            workflow_graph.add_node("carlos", carlos_enhanced)
            workflow_graph.add_node("sofia", sofia_enhanced)
            workflow_graph.add_node("responder", responder_node)
            
            workflow_graph.set_entry_point("thread_mapper")
            workflow_graph.add_edge("thread_mapper", "receptionist")
            workflow_graph.add_edge("receptionist", "intelligence")
            workflow_graph.add_edge("intelligence", "supervisor")
            
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
            
            for agent in ["maria", "carlos", "sofia"]:
                workflow_graph.add_conditional_edges(
                    agent,
                    route_from_agent,
                    {
                        "responder": "responder",
                        "supervisor": "supervisor"
                    }
                )
            
            workflow_graph.add_edge("responder", END)
            
            # Compile with runtime checkpointer
            runtime_workflow = workflow_graph.compile(
                checkpointer=runtime_checkpointer,
                store=InMemoryStore()
            )
            
            # Run the workflow
            result = await runtime_workflow.ainvoke(
                initial_state,
                config=config  # Pass config for checkpoint saving
            )
        
        logger.info(f"Workflow completed for contact {contact_id}")
        logger.info(f"Final state has {len(result.get('messages', []))} messages")
        
        return {
            "success": True,
            "contact_id": contact_id,
            "thread_id": thread_id,
            "message_sent": result.get("message_sent", False),
            "message_count": len(result.get("messages", [])),
            "checkpoint_loaded": existing_state is not None
        }
        
    except Exception as e:
        logger.error(f"Error in workflow: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "contact_id": webhook_data.get("contactId", "unknown")
        }


# Create the compiled workflow at module level for LangGraph
# This is what langgraph.json expects to find
workflow = create_sync_workflow()

# Export for langgraph.json and imports
__all__ = ["workflow", "run_workflow"]
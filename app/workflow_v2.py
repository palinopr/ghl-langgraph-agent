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
from app.intelligence.analyzer import intelligence_node
from app.intelligence.ghl_updater import ghl_update_node
from app.agents.supervisor import supervisor_node

# Import enhanced agents with latest features
from app.agents.sofia_agent_v2_enhanced import sofia_node_v2, create_sofia_agent
from app.agents.carlos_agent_v2_enhanced import carlos_node_v2, create_carlos_agent
from app.agents.maria_agent_v2 import maria_node_v2, create_maria_agent

# Import error recovery for robustness
from app.utils.error_recovery import error_recovery_middleware, handle_graph_recursion
from app.utils.simple_logger import get_logger

logger = get_logger("workflow_v2")


# Wrap nodes with error recovery for robustness
@handle_graph_recursion(max_depth=30)
async def protected_supervisor(state: ConversationState):
    """Supervisor with recursion protection"""
    return await error_recovery_middleware(supervisor_node, state)


async def protected_sofia(state: ConversationState):
    """Sofia with error recovery and streaming support"""
    return await error_recovery_middleware(sofia_node_v2, state)


async def protected_carlos(state: ConversationState):
    """Carlos with error recovery and parallel checks"""
    return await error_recovery_middleware(carlos_node_v2, state)


async def protected_maria(state: ConversationState):
    """Maria with error recovery"""
    return await error_recovery_middleware(maria_node_v2, state)


def create_workflow_v2() -> StateGraph:
    """
    Create the modernized LangGraph workflow with intelligence layer and supervisor pattern
    
    Flow: Message → Intelligence Analysis → GHL Update → Supervisor → Agent → Supervisor
    
    Returns:
        Compiled StateGraph workflow
    """
    # Create the graph with ConversationState
    workflow = StateGraph(ConversationState)
    
    # Add the intelligence analyzer node (pre-processing)
    workflow.add_node("intelligence", intelligence_node)
    
    # Add GHL update node (saves scores and data to GHL)
    workflow.add_node("ghl_update", ghl_update_node)
    
    # Add the supervisor node with protection
    workflow.add_node("supervisor", protected_supervisor)
    
    # Add agent nodes with error recovery
    workflow.add_node("sofia", protected_sofia)
    workflow.add_node("carlos", protected_carlos)
    workflow.add_node("maria", protected_maria)
    
    # Set entry point to intelligence analyzer
    workflow.add_edge(START, "intelligence")
    
    # Intelligence → GHL Update → Supervisor
    workflow.add_edge("intelligence", "ghl_update")
    workflow.add_edge("ghl_update", "supervisor")
    
    # Add edges from agents back to supervisor
    # Agents can return Commands to route elsewhere or end
    workflow.add_edge("sofia", "supervisor")
    workflow.add_edge("carlos", "supervisor")
    workflow.add_edge("maria", "supervisor")
    
    # The supervisor handles all routing logic via Commands
    # Intelligence provides the data, supervisor makes routing decisions
    
    logger.info("Created modernized workflow with intelligence layer and supervisor pattern")
    
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
    contact_id: str = None,
    message: str = None,
    context: Dict[str, Any] = None,
    webhook_data: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Run the modernized workflow for a given message
    
    Args:
        contact_id: Contact ID (optional if webhook_data provided)
        message: Incoming message (optional if webhook_data provided)
        context: Additional context (optional)
        webhook_data: Raw webhook data from GHL (preferred)
        
    Returns:
        Workflow response
    """
    from langchain_core.messages import HumanMessage
    from app.tools.webhook_enricher import process_webhook_with_full_context
    from app.utils.tracing import get_tracing_metadata, is_tracing_enabled
    import uuid
    
    # If webhook data provided, use enricher to get EVERYTHING
    if webhook_data:
        initial_state = await process_webhook_with_full_context(webhook_data)
        logger.info(
            f"Processed webhook with full context: "
            f"Score={initial_state.get('lead_score')}, "
            f"Messages={len(initial_state.get('messages', []))}"
        )
    else:
        # Fallback to old method if no webhook data
        from app.tools.conversation_loader import enrich_workflow_state_with_history
        
        initial_state = {
            "messages": [HumanMessage(content=message)],
            "contact_id": contact_id,
            "contact_info": context or {},
            "current_agent": None,
        }
        
        try:
            initial_state = await enrich_workflow_state_with_history(initial_state, contact_id)
            logger.info(f"Loaded {len(initial_state['messages']) - 1} historical messages from GHL")
        except Exception as e:
            logger.warning(f"Failed to load conversation history: {e}")
            # Continue with just current message if history load fails
    
    # Get workflow
    app = create_workflow_with_memory_v2()
    
    # Generate workflow run ID for tracing
    workflow_run_id = str(uuid.uuid4())
    
    # Run workflow with thread ID for conversation continuity and tracing metadata
    config = {
        "configurable": {
            "thread_id": contact_id or initial_state.get("contact_id", "unknown")
        },
        "metadata": get_tracing_metadata(
            contact_id=contact_id or initial_state.get("contact_id", "unknown"),
            workflow_run_id=workflow_run_id
        ),
        "tags": ["webhook", "production"] if webhook_data else ["direct", "test"]
    }
    
    if is_tracing_enabled():
        logger.info(f"LangSmith tracing enabled for workflow run: {workflow_run_id}")
    
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
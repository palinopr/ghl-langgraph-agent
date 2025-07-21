"""
OPTIMIZED WORKFLOW - AI Supervisor with Context-Aware Agents
Features:
1. AI Supervisor provides rich context to agents
2. Agents don't re-analyze conversations
3. Parallel data loading in receptionist
4. Simplified state management
"""
from typing import Dict, Any, Literal, Union
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
import asyncio

# Import state
from app.state.conversation_state import ConversationState

# Import nodes
from app.agents.receptionist_simple import receptionist_simple_node
from app.agents.supervisor_brain_with_ai import supervisor_brain_ai_node as supervisor_ai_node
from app.agents.sofia_agent_v3 import sofia_node_v3
from app.agents.carlos_agent_v3 import carlos_node_v3
from app.agents.maria_agent_v3 import maria_node_v3
from app.agents.responder_streaming import responder_streaming_node as responder_node
from app.intelligence.analyzer import intelligence_node

# Import utilities
from app.utils.simple_logger import get_logger

logger = get_logger("workflow_optimized")


async def parallel_receptionist_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhanced receptionist with parallel data loading
    """
    contact_id = state.get("contact_id")
    if not contact_id:
        return state
    
    logger.info(f"Loading data in parallel for contact {contact_id}")
    
    try:
        from app.tools.ghl_client import ghl_client
        
        # Load all data in parallel (3x faster!)
        # First get conversations, then messages
        contact_info, conversations, custom_fields = await asyncio.gather(
            ghl_client.get_contact(contact_id),
            ghl_client.get_conversations(contact_id),
            ghl_client.get_contact_custom_fields(contact_id),
            return_exceptions=True
        )
        
        # Get messages from first conversation if exists
        messages = []
        if conversations and not isinstance(conversations, Exception) and len(conversations) > 0:
            first_conv = conversations[0]
            conv_messages = await ghl_client.get_conversation_messages(first_conv['id'])
            if conv_messages:
                messages = conv_messages[:50]  # Limit to 50
        
        # Handle results
        if isinstance(contact_info, Exception):
            logger.error(f"Failed to load contact: {contact_info}")
            contact_info = {}
        
        if isinstance(messages, Exception):
            logger.error(f"Failed to load messages: {messages}")
            messages = []
            
        if isinstance(custom_fields, Exception):
            logger.error(f"Failed to load custom fields: {custom_fields}")
            custom_fields = {}
        
        # Update state with loaded data
        state["contact_info"] = contact_info
        state["conversation_history"] = messages
        state["previous_custom_fields"] = custom_fields
        
        logger.info(f"Parallel load complete: {len(messages)} messages, {len(custom_fields)} fields")
        
        # Call the regular receptionist to process
        return await receptionist_simple_node(state)
        
    except Exception as e:
        logger.error(f"Error in parallel receptionist: {str(e)}", exc_info=True)
        # Fallback to regular receptionist
        return await receptionist_simple_node(state)


def route_from_supervisor(state: ConversationState) -> Literal["sofia", "carlos", "maria", "end"]:
    """
    Route based on AI supervisor decision
    """
    # Check end conditions
    if state.get("should_end", False):
        logger.info("Ending workflow: should_end flag is True")
        return "end"
    
    # Check max routing attempts
    routing_attempts = state.get("routing_attempts", 0)
    if routing_attempts >= 2:
        logger.warning(f"Max routing attempts reached ({routing_attempts}), ending workflow")
        return "end"
    
    # Get routing decision from AI supervisor
    next_agent = state.get("next_agent")
    
    if next_agent in ["sofia", "carlos", "maria"]:
        logger.info(f"AI ROUTING: Supervisor → {next_agent} (attempt {routing_attempts + 1}/2)")
        logger.info(f"Context: {state.get('agent_context', {}).get('customer_intent', 'unknown')}")
        return next_agent
    
    # Default to end if no valid agent
    logger.warning(f"No valid next_agent found: {next_agent}, ending workflow")
    return "end"


def route_from_agent(state: ConversationState) -> Union[Literal["supervisor_ai", "responder"], str]:
    """
    Route from agent - can only go to responder or escalate back to supervisor
    """
    # Check if needs rerouting (escalation)
    if state.get("needs_rerouting", False):
        logger.info(f"ESCALATION: {state.get('current_agent')} → AI Supervisor (reason: {state.get('escalation_reason')})")
        return "supervisor_ai"
    
    # Normal flow: agent → responder
    logger.info(f"Normal flow: {state.get('current_agent')} → Responder")
    return "responder"


def create_optimized_workflow():
    """
    Create OPTIMIZED workflow with:
    
    1. Parallel Receptionist - Loads data 3x faster
    2. Intelligence Node - Deterministic scoring
    3. AI Supervisor - Provides rich context
    4. Context-Aware Agents - No re-analysis
    5. Responder - Sends messages
    """
    # Create workflow
    workflow = StateGraph(ConversationState)
    
    # Add all nodes
    workflow.add_node("receptionist", parallel_receptionist_node)
    workflow.add_node("intelligence", intelligence_node)
    workflow.add_node("supervisor_ai", supervisor_ai_node)
    workflow.add_node("sofia", sofia_node_v3)
    workflow.add_node("carlos", carlos_node_v3)
    workflow.add_node("maria", maria_node_v3)
    workflow.add_node("responder", responder_node)
    
    # Set entry point - receptionist first!
    workflow.set_entry_point("receptionist")
    
    # Define edges
    # Receptionist → Intelligence
    workflow.add_edge("receptionist", "intelligence")
    
    # Intelligence → AI Supervisor
    workflow.add_edge("intelligence", "supervisor_ai")
    
    # AI Supervisor → Agents (conditional)
    workflow.add_conditional_edges(
        "supervisor_ai",
        route_from_supervisor,
        {
            "sofia": "sofia",
            "carlos": "carlos", 
            "maria": "maria",
            "end": END
        }
    )
    
    # Agents → Responder or back to Supervisor (conditional)
    for agent in ["sofia", "carlos", "maria"]:
        workflow.add_conditional_edges(
            agent,
            route_from_agent,
            {
                "responder": "responder",
                "supervisor_ai": "supervisor_ai"
            }
        )
    
    # Responder → END
    workflow.add_edge("responder", END)
    
    # Compile with minimal memory (we reload from GHL anyway)
    memory = MemorySaver()
    store = InMemoryStore()
    
    return workflow.compile(
        checkpointer=memory,
        store=store
    )


# Create the optimized workflow
optimized_workflow = create_optimized_workflow()

# Export
__all__ = ["optimized_workflow", "create_optimized_workflow"]
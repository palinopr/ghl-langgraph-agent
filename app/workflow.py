"""
Production-Ready Workflow with Redis Persistence
Fixed version with proper checkpoint configuration
"""
from typing import Dict, Any, Literal, TypedDict, Annotated, List, Union
from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage
from langchain_openai import ChatOpenAI
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Production State Definition
class ProductionState(TypedDict):
    messages: Annotated[List[BaseMessage], lambda x, y: x + y]
    current_agent: str
    lead_score: int
    contact_id: str
    conversation_id: str
    location_id: str
    next_agent: str
    agent_task: str
    supervisor_complete: bool
    needs_escalation: bool
    escalation_reason: str
    routing_attempts: int
    should_end: bool
    contact_name: str
    email: str
    phone: str
    business_type: str
    goal: str
    urgency_level: str
    budget: str
    thread_id: str
    webhook_data: Dict[str, Any]
    # Receptionist outputs
    last_message: str
    is_first_contact: bool
    receptionist_complete: bool
    # Intelligence outputs  
    last_intent: str
    intelligence_complete: bool
    # Additional fields
    contact_info: Dict[str, Any]
    previous_custom_fields: Dict[str, Any]
    is_new_conversation: bool
    thread_message_count: int
    has_checkpoint: bool
    # Responder outputs
    last_sent_message: str
    message_sent: bool
    final_response: str
    responder_complete: bool
    agent_complete: bool


# Import all agent nodes
from app.agents.thread_id_mapper import thread_id_mapper_enhanced_node as thread_id_mapper_node
from app.agents.receptionist_agent import receptionist_simple_node
from app.intelligence.analyzer import intelligence_node as intelligence_analyzer_node
from app.agents.supervisor import supervisor_node
from app.agents.maria_agent import maria_memory_aware_node as maria_node
from app.agents.carlos_agent import carlos_node_v2_fixed as carlos_node
from app.agents.sofia_agent import sofia_node_v2_fixed as sofia_node
from app.agents.responder_agent import responder_streaming_node


def route_from_supervisor(state: ProductionState) -> Literal["maria", "carlos", "sofia", "responder", "end"]:
    """Route based on supervisor decision"""
    if state.get("should_end", False):
        return "end"
    
    if not state.get("supervisor_complete"):
        return "end"
    
    next_agent = state.get("next_agent")
    
    if next_agent in ["maria", "carlos", "sofia"]:
        return next_agent
    elif next_agent == "responder":
        return "responder"
    else:
        return "end"


def route_from_agent(state: ProductionState) -> Literal["responder", "supervisor"]:
    """Route from agent - either to responder or back to supervisor"""
    if state.get("needs_escalation", False):
        logger.info("Escalating back to supervisor")
        return "supervisor"
    
    return "responder"


# Create the workflow
workflow_graph = StateGraph(ProductionState)

# Add all nodes
workflow_graph.add_node("thread_mapper", thread_mapper_node)
workflow_graph.add_node("receptionist", receptionist_simple_node)  
workflow_graph.add_node("intelligence", intelligence_analyzer_node)
workflow_graph.add_node("supervisor", supervisor_node)
workflow_graph.add_node("maria", maria_node)
workflow_graph.add_node("carlos", carlos_node)
workflow_graph.add_node("sofia", sofia_node)
workflow_graph.add_node("responder", responder_streaming_node)  

# Set entry point
workflow_graph.set_entry_point("thread_mapper")

# Define edges
workflow_graph.add_edge("thread_mapper", "receptionist")
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

# Agent routing
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

# Use simple memory checkpointer - Redis is overkill since GHL stores messages
from langgraph.checkpoint.memory import MemorySaver
checkpointer = MemorySaver()

# Compile workflow
workflow = workflow_graph.compile(checkpointer=checkpointer)

logger.info("Production workflow compiled with memory checkpointer")


async def run_workflow(webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run workflow from webhook data
    
    Args:
        webhook_data: Data from GoHighLevel webhook
        
    Returns:
        Result dictionary with success status and response
    """
    try:
        logger.info(f"Running workflow for contact: {webhook_data.get('contactId')}")
        
        # Extract data from webhook
        contact_id = webhook_data.get("contactId", "")
        conversation_id = webhook_data.get("conversationId", "")
        location_id = webhook_data.get("locationId", "")
        message_body = webhook_data.get("body", "")
        
        # Get contact data
        contact_data = webhook_data.get("contact", {})
        contact_name = f"{contact_data.get('firstName', '')} {contact_data.get('lastName', '')}".strip()
        
        # Create thread ID from conversation ID
        thread_id = f"conv-{conversation_id}" if conversation_id else f"contact-{contact_id}"
        
        # Create initial state - empty messages, receptionist loads from GHL
        initial_state = {
            "messages": [],
            "contact_id": contact_id,
            "conversation_id": conversation_id,
            "location_id": location_id,
            "contact_name": contact_name,
            "email": contact_data.get("email", ""),
            "phone": contact_data.get("phone", ""),
            "thread_id": thread_id,
            "webhook_data": webhook_data,
            "current_agent": "receptionist",
            "lead_score": 0
        }
        
        # Run workflow with thread config
        config = {"configurable": {"thread_id": thread_id}}
        
        # Execute workflow
        result = await workflow.ainvoke(initial_state, config=config)
        
        # Extract response
        last_sent_message = result.get("last_sent_message", "")
        message_sent = result.get("message_sent", False)
        
        return {
            "success": True,
            "contact_id": contact_id,
            "thread_id": thread_id,
            "message_sent": message_sent,
            "response": last_sent_message,
            "agent": result.get("current_agent"),
            "lead_score": result.get("lead_score", 0)
        }
        
    except Exception as e:
        logger.error(f"Workflow error: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "contact_id": webhook_data.get("contactId", "unknown")
        }


# Export everything needed
__all__ = ["workflow", "run_workflow"]
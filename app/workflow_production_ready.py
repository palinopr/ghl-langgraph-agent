"""
Production-Ready Workflow for Deployment
Combines full functionality with clean imports
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
    webhook_data: Dict[str, Any]  # For passing webhook data to receptionist
    # Receptionist outputs
    last_message: str
    is_first_contact: bool
    receptionist_complete: bool
    # Intelligence outputs  
    last_intent: str
    intelligence_complete: bool
    # Additional fields from checkpoint-aware receptionist
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
    # Agent completion flags
    agent_complete: bool


# Import all agent nodes and utilities
from app.agents.thread_id_mapper_enhanced import thread_id_mapper_enhanced_node as thread_mapper_node
from app.agents.receptionist_checkpoint_aware import receptionist_checkpoint_aware_node
from app.intelligence.analyzer import intelligence_node as intelligence_analyzer_node
from app.agents.supervisor import supervisor_node
from app.agents.maria_memory_aware import maria_memory_aware_node as maria_node
from app.agents.carlos_agent_v2_fixed import carlos_node_v2_fixed as carlos_node
from app.agents.sofia_agent_v2_fixed import sofia_node_v2_fixed as sofia_node
from app.agents.responder_streaming import responder_streaming_node


# All agent implementations imported above with full tool access


# Responder node removed - using responder_streaming_node from imports


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


# All nodes imported at top of file

# Create the workflow
workflow_graph = StateGraph(ProductionState)

# Add all nodes
workflow_graph.add_node("thread_mapper", thread_mapper_node)
workflow_graph.add_node("receptionist", receptionist_checkpoint_aware_node)  # Use checkpoint-aware receptionist
workflow_graph.add_node("intelligence", intelligence_analyzer_node)
workflow_graph.add_node("supervisor", supervisor_node)
workflow_graph.add_node("maria", maria_node)
workflow_graph.add_node("carlos", carlos_node)
workflow_graph.add_node("sofia", sofia_node)
workflow_graph.add_node("responder", responder_streaming_node)  # Use the real responder that sends to GHL

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

# Compile with memory checkpointer for conversation persistence
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
workflow = workflow_graph.compile(checkpointer=checkpointer)

logger.info("Production workflow compiled with memory checkpointer for conversation persistence")

# Export
__all__ = ["workflow"]
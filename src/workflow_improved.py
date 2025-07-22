"""
Improved workflow implementation using LangGraph best practices
Demonstrates proper async context management and state reducers
"""
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.store.memory import InMemoryStore
from langchain_core.messages import HumanMessage
import os
from contextlib import asynccontextmanager

# Import improved state
from app.state.improved_state import ImprovedState

# Import nodes
from app.agents.thread_id_mapper_enhanced import thread_id_mapper_enhanced_node
from app.agents.receptionist_checkpoint_aware import receptionist_checkpoint_aware_node
from app.agents.maria_memory_aware import maria_memory_aware_node
from app.agents.carlos_agent_v2_fixed import carlos_node_v2_fixed as carlos_node
from app.agents.sofia_agent_v2_fixed import sofia_node_v2_fixed as sofia_node
from app.agents.responder_streaming import responder_streaming_node as responder_node
from app.intelligence.analyzer import intelligence_node
from app.agents.supervisor import supervisor_node

from app.utils.simple_logger import get_logger

logger = get_logger("workflow_improved")


@asynccontextmanager
async def create_checkpointer():
    """Create checkpointer with proper async context management"""
    checkpoint_db = os.path.join(os.path.dirname(__file__), "checkpoints.db")
    logger.info(f"Creating checkpointer with database: {checkpoint_db}")
    
    async with AsyncSqliteSaver.from_conn_string(checkpoint_db) as checkpointer:
        yield checkpointer


async def create_improved_workflow():
    """
    Create workflow using best practices:
    1. Proper async context management
    2. Improved state with reducers
    3. Clean routing logic
    """
    logger.info("Creating improved workflow")
    
    # Create workflow with improved state
    workflow_graph = StateGraph(ImprovedState)
    
    # Add nodes
    workflow_graph.add_node("thread_mapper", thread_id_mapper_enhanced_node)
    workflow_graph.add_node("receptionist", receptionist_checkpoint_aware_node)
    workflow_graph.add_node("intelligence", intelligence_node)
    workflow_graph.add_node("supervisor", supervisor_node)
    workflow_graph.add_node("maria", maria_node)
    workflow_graph.add_node("carlos", carlos_node)
    workflow_graph.add_node("sofia", sofia_node)
    workflow_graph.add_node("responder", responder_node)
    
    # Set entry point
    workflow_graph.set_entry_point("thread_mapper")
    
    # Define edges
    workflow_graph.add_edge("thread_mapper", "receptionist")
    workflow_graph.add_edge("receptionist", "intelligence")
    workflow_graph.add_edge("intelligence", "supervisor")
    
    # Supervisor routing
    def route_supervisor(state: ImprovedState) -> Literal["maria", "carlos", "sofia", "responder", "end"]:
        """Clean routing logic for supervisor"""
        if state.get("should_end"):
            return "end"
        
        next_agent = state.get("next_agent")
        if next_agent in ["maria", "carlos", "sofia"]:
            logger.info(f"Routing to agent: {next_agent}")
            return next_agent
        
        # Default to responder if we have messages
        if state.get("messages"):
            return "responder"
        
        return "end"
    
    workflow_graph.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "maria": "maria",
            "carlos": "carlos",
            "sofia": "sofia",
            "responder": "responder",
            "end": END
        }
    )
    
    # Agent routing (can escalate back to supervisor)
    def route_agent(state: ImprovedState) -> Literal["supervisor", "responder"]:
        """Route from agent - escalate or respond"""
        if state.get("needs_escalation"):
            logger.info(f"Escalating to supervisor: {state.get('escalation_reason')}")
            return "supervisor"
        return "responder"
    
    for agent in ["maria", "carlos", "sofia"]:
        workflow_graph.add_conditional_edges(
            agent,
            route_agent,
            {
                "responder": "responder",
                "supervisor": "supervisor"
            }
        )
    
    # Responder ends
    workflow_graph.add_edge("responder", END)
    
    # Compile with proper async context
    async with create_checkpointer() as checkpointer:
        store = InMemoryStore()
        compiled = workflow_graph.compile(
            checkpointer=checkpointer,
            store=store
        )
        logger.info("Workflow compiled successfully")
        return compiled


async def run_improved_workflow(webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run workflow with improved state management
    
    Key improvements:
    1. Thread ID is set at API level (not here)
    2. State reducers handle updates automatically
    3. Proper async context management
    """
    try:
        # Extract identifiers
        contact_id = webhook_data.get("contactId", webhook_data.get("id", "unknown"))
        conversation_id = webhook_data.get("conversationId")
        thread_id = webhook_data.get("thread_id")  # Should be set by API handler
        
        # If no thread_id provided, generate one (fallback)
        if not thread_id:
            if conversation_id:
                thread_id = f"conv-{conversation_id}"
            else:
                thread_id = f"contact-{contact_id}"
            logger.warning(f"No thread_id provided, generated: {thread_id}")
        
        # Configuration
        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }
        
        # Initial state - reducers will handle merging
        initial_state = {
            "messages": [],  # Will be populated by receptionist
            "webhook_data": webhook_data,
            "contact_id": contact_id,
            "thread_id": thread_id,
            "conversation_id": conversation_id,
            "lead_score": 0,  # Will be automatically summed
            "extracted_data": {},  # Will be automatically merged
            "score_history": [],  # Will be automatically ordered
            "should_end": False,
            "needs_escalation": False,
            "supervisor_complete": False,
            "message_sent": False,
            "is_new_conversation": True,
            "conversation_stage": "initial",
            "location_id": webhook_data.get("locationId", ""),
            "contact_info": {},
            "workflow_started_at": datetime.utcnow().isoformat(),
            "last_updated_at": datetime.utcnow().isoformat()
        }
        
        # Create and run workflow
        async with create_checkpointer() as checkpointer:
            # Recompile with the checkpointer
            workflow_graph = StateGraph(ImprovedState)
            
            # Add all nodes (same as above)
            workflow_graph.add_node("thread_mapper", thread_id_mapper_enhanced_node)
            workflow_graph.add_node("receptionist", receptionist_checkpoint_aware_node)
            workflow_graph.add_node("intelligence", intelligence_node)
            workflow_graph.add_node("supervisor", supervisor_node)
            workflow_graph.add_node("maria", maria_node)
            workflow_graph.add_node("carlos", carlos_node)
            workflow_graph.add_node("sofia", sofia_node)
            workflow_graph.add_node("responder", responder_node)
            
            # Set edges (same as above)
            workflow_graph.set_entry_point("thread_mapper")
            workflow_graph.add_edge("thread_mapper", "receptionist")
            workflow_graph.add_edge("receptionist", "intelligence")
            workflow_graph.add_edge("intelligence", "supervisor")
            
            # Add conditional edges (using same routing functions)
            workflow_graph.add_conditional_edges(
                "supervisor", route_supervisor,
                {"maria": "maria", "carlos": "carlos", "sofia": "sofia", 
                 "responder": "responder", "end": END}
            )
            
            for agent in ["maria", "carlos", "sofia"]:
                workflow_graph.add_conditional_edges(
                    agent, route_agent,
                    {"responder": "responder", "supervisor": "supervisor"}
                )
            
            workflow_graph.add_edge("responder", END)
            
            # Compile and run
            compiled = workflow_graph.compile(
                checkpointer=checkpointer,
                store=InMemoryStore()
            )
            
            # Run the workflow
            result = await compiled.ainvoke(initial_state, config)
            
            logger.info(f"Workflow completed for thread: {thread_id}")
            logger.info(f"Final lead score: {result.get('lead_score', 0)}")
            logger.info(f"Messages sent: {result.get('message_sent', False)}")
            
            return {
                "success": True,
                "thread_id": thread_id,
                "contact_id": contact_id,
                "lead_score": result.get("lead_score", 0),
                "message_sent": result.get("message_sent", False),
                "extracted_data": result.get("extracted_data", {}),
                "message_count": len(result.get("messages", []))
            }
            
    except Exception as e:
        logger.error(f"Workflow error: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "contact_id": contact_id
        }


# Example agent using improved state:
"""
async def maria_improved_node(state: ImprovedState) -> Dict[str, Any]:
    # OLD WAY:
    # messages = state.get("messages", [])
    # messages.append(AIMessage(content="Hello"))
    # score = state.get("lead_score", 0) + 5
    
    # NEW WAY - Just return what to add/update:
    return {
        "messages": [AIMessage(content="Hello")],  # Automatically appended
        "lead_score": 5,  # Automatically added
        "extracted_data": {"name": "John"},  # Automatically merged
        "last_updated_at": datetime.utcnow().isoformat()  # Simple replacement
    }
"""

# Benefits of this approach:
"""
1. Cleaner agent code - no manual state management
2. Thread-safe operations with reducers
3. Proper async resource management
4. Automatic message deduplication
5. Simplified routing logic
6. Better error handling with context managers
"""
"""
DEPLOYMENT-READY WORKFLOW
This is the final, tested workflow with all fixes integrated:
1. Contact ID annotation fix
2. Loop prevention 
3. Responder agent for GHL message sending
4. Proper error handling
5. All imports verified
"""
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.types import Command
from langchain_core.messages import AIMessage, HumanMessage

# Import state
from app.state.conversation_state import ConversationState

# Import nodes
from app.intelligence.analyzer import intelligence_node
from app.intelligence.ghl_updater import ghl_update_node
from app.agents.supervisor import supervisor_node as original_supervisor_node
from app.agents.sofia_agent_v2 import sofia_node_v2
from app.agents.carlos_agent_v2 import carlos_node_v2
from app.agents.maria_agent_v2 import maria_node_v2
from app.agents.responder_agent import responder_node

# Import utilities
from app.utils.simple_logger import get_logger
from app.config import get_settings

logger = get_logger("workflow_deployment_ready")


# Enhanced supervisor with all safety checks
async def supervisor_with_safety(state: ConversationState) -> Dict[str, Any]:
    """
    Enhanced supervisor that prevents expensive loops and ensures proper routing
    """
    try:
        # Safety check 1: Interaction limit
        interaction_count = state.get("interaction_count", 0)
        if interaction_count >= 3:
            logger.warning(f"Max interactions reached: {interaction_count}")
            return {
                "should_end": True,
                "next_agent": None,
                "interaction_count": interaction_count
            }
        
        # Safety check 2: Response already sent
        if state.get("response_sent", False):
            logger.info("Response already sent, ending conversation")
            return {
                "should_end": True,
                "next_agent": None
            }
        
        # Safety check 3: Explicit end flag
        if state.get("should_end", False):
            logger.info("Should end flag set, ending conversation")
            return {
                "should_end": True,
                "next_agent": None
            }
        
        # Call original supervisor
        try:
            command = await original_supervisor_node(state)
            
            # Process Command response
            result = {
                "interaction_count": interaction_count + 1
            }
            
            if hasattr(command, 'goto'):
                if command.goto in [END, 'end', None]:
                    result["should_end"] = True
                    result["next_agent"] = None
                else:
                    result["next_agent"] = command.goto
                    result["should_end"] = False
                
                # Include any state updates from command
                if hasattr(command, 'update') and command.update:
                    result.update(command.update)
            else:
                # Fallback if not a Command object
                logger.warning("Supervisor didn't return Command, defaulting to maria")
                result["next_agent"] = "maria"
                result["should_end"] = False
            
            return result
            
        except Exception as e:
            logger.error(f"Supervisor error: {e}", exc_info=True)
            # On error, route to Maria as safe default
            return {
                "next_agent": "maria",
                "should_end": False,
                "error": str(e),
                "interaction_count": interaction_count + 1
            }
            
    except Exception as e:
        logger.error(f"Critical supervisor error: {e}", exc_info=True)
        return {
            "should_end": True,
            "error": str(e)
        }


# Routing function from supervisor
def route_from_supervisor(state: ConversationState) -> Literal["sofia", "carlos", "maria", "end"]:
    """
    Route based on supervisor decision with safety checks
    """
    # Check end conditions first
    if state.get("should_end", False):
        logger.info("Routing to END due to should_end flag")
        return "end"
    
    # Check interaction limit
    if state.get("interaction_count", 0) >= 3:
        logger.info("Routing to END due to interaction limit")
        return "end"
    
    # No need to check response_sent anymore - responder handles that
    
    # Get next agent
    next_agent = state.get("next_agent")
    
    # Validate agent name
    if next_agent in ["sofia", "carlos", "maria"]:
        logger.info(f"Routing to agent: {next_agent}")
        return next_agent
    
    # Default to end if no valid agent
    logger.warning(f"Invalid next_agent: {next_agent}, ending")
    return "end"


# Agent wrappers to ensure proper message format
async def sofia_with_message_format(state: ConversationState) -> Dict[str, Any]:
    """Sofia wrapper ensuring messages are in correct format"""
    result = await sofia_node_v2(state)
    
    # Ensure messages are AIMessage objects
    if "messages" in result and isinstance(result["messages"], list):
        formatted_messages = []
        for msg in result["messages"]:
            if isinstance(msg, dict) and "content" in msg:
                # Convert dict to AIMessage
                formatted_messages.append(AIMessage(content=msg["content"]))
            elif isinstance(msg, AIMessage):
                formatted_messages.append(msg)
            elif isinstance(msg, str):
                # Convert string to AIMessage
                formatted_messages.append(AIMessage(content=msg))
        
        result["messages"] = formatted_messages
    
    return result


async def carlos_with_message_format(state: ConversationState) -> Dict[str, Any]:
    """Carlos wrapper ensuring messages are in correct format"""
    result = await carlos_node_v2(state)
    
    # Ensure messages are AIMessage objects
    if "messages" in result and isinstance(result["messages"], list):
        formatted_messages = []
        for msg in result["messages"]:
            if isinstance(msg, dict) and "content" in msg:
                formatted_messages.append(AIMessage(content=msg["content"]))
            elif isinstance(msg, AIMessage):
                formatted_messages.append(msg)
            elif isinstance(msg, str):
                formatted_messages.append(AIMessage(content=msg))
        
        result["messages"] = formatted_messages
    
    return result


async def maria_with_message_format(state: ConversationState) -> Dict[str, Any]:
    """Maria wrapper ensuring messages are in correct format"""
    result = await maria_node_v2(state)
    
    # Ensure messages are AIMessage objects
    if "messages" in result and isinstance(result["messages"], list):
        formatted_messages = []
        for msg in result["messages"]:
            if isinstance(msg, dict) and "content" in msg:
                formatted_messages.append(AIMessage(content=msg["content"]))
            elif isinstance(msg, AIMessage):
                formatted_messages.append(msg)
            elif isinstance(msg, str):
                formatted_messages.append(AIMessage(content=msg))
        
        result["messages"] = formatted_messages
    
    return result


def create_deployment_workflow():
    """
    Create the deployment-ready workflow with all fixes
    """
    logger.info("Creating deployment-ready workflow")
    
    # Create workflow
    workflow = StateGraph(ConversationState)
    
    # Add all nodes
    workflow.add_node("intelligence", intelligence_node)
    workflow.add_node("ghl_update", ghl_update_node)
    workflow.add_node("supervisor", supervisor_with_safety)
    workflow.add_node("sofia", sofia_with_message_format)
    workflow.add_node("carlos", carlos_with_message_format)
    workflow.add_node("maria", maria_with_message_format)
    workflow.add_node("responder", responder_node)
    
    # Set entry point
    workflow.set_entry_point("intelligence")
    
    # Define the flow
    # 1. Intelligence analysis
    workflow.add_edge("intelligence", "ghl_update")
    
    # 2. GHL update to supervisor
    workflow.add_edge("ghl_update", "supervisor")
    
    # 3. Supervisor routes to agents
    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "sofia": "sofia",
            "carlos": "carlos",
            "maria": "maria",
            "end": END
        }
    )
    
    # 4. CRITICAL: All agents go to responder (not back to supervisor!)
    workflow.add_edge("sofia", "responder")
    workflow.add_edge("carlos", "responder")
    workflow.add_edge("maria", "responder")
    
    # 5. Responder always ends
    workflow.add_edge("responder", END)
    
    # Add memory and store
    checkpointer = MemorySaver()
    store = InMemoryStore()
    
    # Compile workflow
    app = workflow.compile(
        checkpointer=checkpointer,
        store=store
    )
    
    logger.info("""
    ✅ Deployment-ready workflow created with:
    - Intelligence layer for Spanish extraction and scoring
    - GHL updater to persist data
    - Supervisor with safety checks (max 3 interactions)
    - Agent message format standardization
    - Responder agent for reliable GHL message sending
    - No expensive routing loops
    - Proper error handling
    """)
    
    return app


# Create and export the workflow
workflow = create_deployment_workflow()

# Export for langgraph.json
__all__ = ["workflow"]
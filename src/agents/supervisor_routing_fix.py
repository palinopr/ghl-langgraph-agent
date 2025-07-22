"""
Fixed Supervisor that ALWAYS routes and NEVER responds directly
Ensures proper handoff to agents based on lead scores
"""
from typing import Dict, Any, List, Optional, Literal
from langchain_core.messages import AnyMessage, BaseMessage, ToolMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command
from app.utils.simple_logger import get_logger
from app.utils.model_factory import create_openai_model
from app.state.minimal_state import MinimalState
from langchain_core.tools import tool
from typing_extensions import Annotated

logger = get_logger("supervisor_routing_fix")


# Handoff tools that return Command objects for proper routing
@tool
def handoff_to_sofia(
    task_description: Annotated[str, "Description of what Sofia should do next"]
) -> str:
    """
    Handoff to Sofia - Appointment Setting Specialist.
    Use when:
    - Lead score is 8-10 (hot leads)
    - Customer is ready to book appointment
    - Has name, email, and $300+ budget confirmed
    """
    logger.info(f"Handoff to Sofia with task: {task_description}")
    return f"HANDOFF:sofia:{task_description}"


@tool
def handoff_to_carlos(
    task_description: Annotated[str, "Description of what Carlos should do next"]
) -> str:
    """
    Handoff to Carlos - Lead Qualification Specialist.
    Use when:
    - Lead score is 5-7 (warm leads)
    - Customer needs qualification
    - Missing budget confirmation or details
    """
    logger.info(f"Handoff to Carlos with task: {task_description}")
    return f"HANDOFF:carlos:{task_description}"


@tool
def handoff_to_maria(
    task_description: Annotated[str, "Description of what Maria should do next"]
) -> str:
    """
    Handoff to Maria - Customer Support Representative.
    Use when:
    - Lead score is 0-4 (cold leads)
    - Customer has general questions
    - Technical issues or complaints
    - Score is 0 or unknown
    """
    logger.info(f"Handoff to Maria with task: {task_description}")
    return f"HANDOFF:maria:{task_description}"


def create_supervisor_that_routes():
    """
    Create a supervisor that ONLY routes, never responds
    """
    model = create_openai_model(temperature=0.0)
    
    tools = [handoff_to_sofia, handoff_to_carlos, handoff_to_maria]
    
    # CRITICAL: Use static prompt that forces tool usage
    supervisor_prompt = """You are a routing supervisor for Main Outlet Media.

YOUR ONLY JOB: Route customers to the appropriate agent using the handoff tools.

CRITICAL RULES:
1. You MUST use a handoff tool - NEVER respond directly to the customer
2. You CANNOT send any message to the customer - only use tools
3. Even for simple greetings like "hola", you MUST handoff to an agent

ROUTING LOGIC:
- Lead Score 0-4 or unknown → handoff_to_maria
- Lead Score 5-7 → handoff_to_carlos  
- Lead Score 8-10 → handoff_to_sofia

Current Lead Score: {lead_score}
Current Category: {lead_category}

IMPORTANT: Look at the lead score and immediately use the appropriate handoff tool.
Do NOT analyze, do NOT greet, do NOT respond - just route!

For score {lead_score}, you should use: {recommended_tool}"""
    
    # Create agent WITH state_schema for proper state handling
    agent = create_react_agent(
        model=model,
        tools=tools,
        state_schema=MinimalState,  # Enable proper state injection
        prompt=supervisor_prompt,
        name="supervisor_routing"
    )
    
    return agent


async def supervisor_routing_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Supervisor node that GUARANTEES routing (never responds directly)
    """
    try:
        # Ensure required fields
        if "messages" not in state:
            state["messages"] = []
        if "thread_id" not in state:
            state["thread_id"] = state.get("contact_id", "unknown")
        if "remaining_steps" not in state:
            state["remaining_steps"] = 10
            
        # Get lead score for routing
        lead_score = state.get("lead_score", 0)
        lead_category = state.get("lead_category", "unknown")
        
        # Determine which tool to recommend
        if lead_score >= 8:
            recommended_tool = "handoff_to_sofia"
            default_agent = "sofia"
        elif lead_score >= 5:
            recommended_tool = "handoff_to_carlos"
            default_agent = "carlos"
        else:
            recommended_tool = "handoff_to_maria"
            default_agent = "maria"
            
        logger.info(f"Supervisor routing for score {lead_score} - should use {recommended_tool}")
        
        # Update state with routing recommendation
        routing_state = {
            **state,
            "lead_score": lead_score,
            "lead_category": lead_category,
            "recommended_tool": recommended_tool
        }
        
        # Create supervisor
        supervisor = create_supervisor_that_routes()
        
        # Run supervisor - it MUST use a handoff tool
        result = await supervisor.ainvoke(routing_state)
        
        # Extract messages from result
        messages = result.get("messages", [])
        
        # Initialize routing update
        routing_update = {
            "supervisor_complete": True,
            "messages": messages
        }
        
        # Look for handoff in messages
        handoff_found = False
        
        # Check all messages for handoff
        for msg in messages:
            # Check for tool calls in AI messages
            if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
                # Supervisor made tool calls - good!
                for tool_call in msg.tool_calls:
                    logger.info(f"Tool call found: {tool_call.get('name', 'unknown')}")
                    handoff_found = True
            
            # Check for HANDOFF pattern in any message content
            if hasattr(msg, 'content') and isinstance(msg.content, str):
                if msg.content.startswith("HANDOFF:"):
                    parts = msg.content.split(":", 2)
                    if len(parts) >= 3:
                        _, agent, task = parts
                        routing_update["next_agent"] = agent
                        routing_update["agent_task"] = task
                        routing_update["routing_reason"] = f"Supervisor routed to {agent}"
                        handoff_found = True
                        logger.info(f"✅ Handoff detected: {agent} - {task}")
                        break
        
        # CRITICAL: If no handoff found, force routing based on score
        if not handoff_found:
            logger.warning(f"⚠️ No handoff detected! Forcing route to {default_agent} for score {lead_score}")
            
            # Check if supervisor responded directly (this should NEVER happen)
            for msg in messages:
                if isinstance(msg, AIMessage) and not msg.tool_calls:
                    logger.error("❌ CRITICAL: Supervisor responded directly instead of using tools!")
                    logger.error(f"   Response: {msg.content[:100]}...")
            
            # Force routing based on lead score
            routing_update["next_agent"] = default_agent
            routing_update["agent_task"] = "Handle customer message"
            routing_update["routing_reason"] = f"Forced routing to {default_agent} (score: {lead_score})"
            routing_update["routing_error"] = "Supervisor didn't use handoff tools"
        
        # Remove any direct responses from supervisor
        filtered_messages = []
        for msg in messages:
            # Keep everything except direct AI responses without tool calls
            if not (isinstance(msg, AIMessage) and not msg.tool_calls):
                filtered_messages.append(msg)
            else:
                logger.warning(f"Removing direct supervisor response: {msg.content[:50]}...")
        
        routing_update["messages"] = filtered_messages
        
        logger.info(f"Final routing: {routing_update.get('next_agent')} - {routing_update.get('routing_reason')}")
        return routing_update
        
    except Exception as e:
        logger.error(f"Error in supervisor routing: {str(e)}", exc_info=True)
        # Always route to Maria on error
        return {
            "next_agent": "maria",
            "agent_task": "Handle customer inquiry",
            "supervisor_complete": True,
            "routing_reason": f"Error routing, defaulting to Maria: {str(e)}",
            "error": str(e),
            "messages": state.get("messages", [])
        }


# Export the fixed supervisor
__all__ = ["supervisor_routing_node", "create_supervisor_that_routes"]
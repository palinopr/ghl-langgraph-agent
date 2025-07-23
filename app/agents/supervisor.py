"""
Fixed Supervisor - ALWAYS routes, NEVER responds directly
Ensures proper handoff to agents based on lead scores
"""
from typing import Dict, Any, List, Optional, Literal, TypedDict, Annotated
from langchain_core.messages import AnyMessage, BaseMessage, ToolMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from app.utils.simple_logger import get_logger
from app.utils.model_factory import create_openai_model

class MinimalState(TypedDict):
    """Minimal state for supervisor agent"""
    messages: Annotated[List[BaseMessage], lambda x, y: x + y]
    lead_score: int
    next_agent: str
    agent_task: str
    supervisor_complete: bool
    needs_escalation: bool
    escalation_reason: str
    should_end: bool

logger = get_logger("supervisor")


# Handoff tools that return routing information
@tool
def handoff_to_sofia(
    task_description: Annotated[str, "Task for Sofia to complete in Spanish"]
) -> str:
    """
    Route to Sofia - Appointment Setting Specialist.
    ONLY use when:
    - Lead score is 8-10 (hot leads)
    - Customer is ready to book appointment
    - Has name, email, and $300+ budget confirmed
    """
    return f"HANDOFF:sofia:{task_description}"


@tool
def handoff_to_carlos(
    task_description: Annotated[str, "Task for Carlos to complete in Spanish"]
) -> str:
    """
    Route to Carlos - Lead Qualification Specialist.
    Use when:
    - Lead score is 5-7 (warm leads)
    - Customer needs qualification
    - Missing budget confirmation or details
    """
    return f"HANDOFF:carlos:{task_description}"


@tool
def handoff_to_maria(
    task_description: Annotated[str, "Task for Maria to complete in Spanish"]
) -> str:
    """
    Route to Maria - Customer Support Representative.
    Use when:
    - Lead score is 0-4 (cold leads) 
    - Score is 0 or unknown
    - Customer has general questions
    - New conversations just starting
    """
    return f"HANDOFF:maria:{task_description}"


def create_supervisor_with_tools():
    """Create supervisor that ONLY routes using tools"""
    model = create_openai_model(temperature=0.0)
    
    tools = [handoff_to_maria, handoff_to_carlos, handoff_to_sofia]
    
    # CRITICAL: Prompt that forces tool usage ONLY
    system_prompt = """You are a routing-only supervisor. You CANNOT talk to customers directly.

YOUR ONLY TASK: Use ONE handoff tool based on the lead score, then STOP.

CRITICAL RULES:
1. Use EXACTLY ONE handoff tool - no more, no less
2. After using the tool, YOU ARE DONE - do not continue
3. NEVER respond to the customer directly
4. NEVER use multiple tools or analyze further
5. ONE TOOL CALL ONLY, THEN STOP

ROUTING BASED ON SCORE:
- Score 0-4 or unknown → Use handoff_to_maria ONCE
- Score 5-7 → Use handoff_to_carlos ONCE
- Score 8-10 → Use handoff_to_sofia ONCE

Current Lead Score: {lead_score}

Use the handoff tool with a Spanish task description, then STOP.
Example: handoff_to_maria("Responder al saludo del cliente")

REMEMBER: ONE TOOL CALL, THEN STOP IMMEDIATELY!"""
    
    def build_prompt(state: MinimalState) -> List[AnyMessage]:
        lead_score = state.get("lead_score", 0)
        messages = state.get("messages", [])
        
        # Format the system prompt with current score
        formatted_system = system_prompt.format(lead_score=lead_score)
        
        return [{"role": "system", "content": formatted_system}] + messages
    
    # Create agent - use state_modifier for production compatibility
    agent = create_react_agent(
        model=model,
        tools=tools,
        state_schema=MinimalState,
        state_modifier=build_prompt
    )
    
    return agent


async def supervisor_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Supervisor node that GUARANTEES routing"""
    try:
        # Ensure required fields
        for field, default in [("messages", []), ("thread_id", state.get("contact_id", "unknown")), ("remaining_steps", 10)]:
            if field not in state:
                state[field] = default
        
        lead_score = state.get("lead_score", 0)
        logger.info(f"Supervisor processing - Lead score: {lead_score}")
        
        # Create and run supervisor
        supervisor = create_supervisor_with_tools()
        result = await supervisor.ainvoke(state)
        
        # Extract routing from result
        routing_update = {
            "supervisor_complete": True,
            "messages": result.get("messages", [])
        }
        
        # Find handoff in messages
        handoff_found = False
        
        for msg in result.get("messages", []):
            # Check if AI message has tool calls
            if isinstance(msg, AIMessage):
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    logger.info(f"✅ Supervisor used {len(msg.tool_calls)} tool(s)")
                    handoff_found = True
                elif msg.content and not msg.tool_calls:
                    # CRITICAL ERROR - supervisor responded directly!
                    logger.error(f"❌ CRITICAL: Supervisor responded directly: {msg.content[:100]}")
                    # Remove this message from output
                    routing_update["messages"] = [m for m in routing_update["messages"] if m != msg]
            
            # Check for handoff pattern
            if hasattr(msg, 'content') and isinstance(msg.content, str) and msg.content.startswith("HANDOFF:"):
                parts = msg.content.split(":", 2)
                if len(parts) >= 3:
                    _, agent, task = parts
                    routing_update.update({
                        "next_agent": agent,
                        "agent_task": task,
                        "routing_reason": f"Routed to {agent} by supervisor"
                    })
                    handoff_found = True
                    logger.info(f"✅ Routing to {agent}: {task}")
        
        # FAILSAFE: Force routing if no handoff detected
        if not handoff_found:
            logger.warning("⚠️ No handoff detected - forcing route based on score")
            
            # Determine agent based on score
            if lead_score >= 8:
                agent = "sofia"
            elif lead_score >= 5:
                agent = "carlos"
            else:
                agent = "maria"
            
            routing_update.update({
                "next_agent": agent,
                "agent_task": "Atender al cliente",
                "routing_reason": f"Forced routing to {agent} (score: {lead_score})"
            })
        
        return routing_update
        
    except Exception as e:
        logger.error(f"Supervisor error: {str(e)}", exc_info=True)
        # Default to maria on any error
        return {
            "next_agent": "maria",
            "agent_task": "Atender al cliente",
            "supervisor_complete": True,
            "routing_reason": f"Error in supervisor: {str(e)}",
            "messages": state.get("messages", [])
        }


# Export
__all__ = ["supervisor_node", "create_supervisor_with_tools"]
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
from app.state.message_manager import MessageManager

class MinimalState(TypedDict):
    """Minimal state for supervisor agent"""
    messages: Annotated[List[BaseMessage], lambda x, y: x + y]
    lead_score: int
    next_agent: str
    agent_task: str
    remaining_steps: int  # Required by create_react_agent
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
    base_model = create_openai_model(temperature=0.0)
    
    tools = [handoff_to_maria, handoff_to_carlos, handoff_to_sofia]
    
    # Force the model to ALWAYS use tools, NEVER respond with text
    model = base_model.bind(tool_choice="required")
    
    # CRITICAL: Prompt that focuses on routing decision only
    system_prompt = """You are a routing engine. Your ONLY function is to select which agent handles this conversation.

Lead Score: {lead_score}

ROUTING DECISION:
- Score 0-4: Use handoff_to_maria
- Score 5-7: Use handoff_to_carlos
- Score 8-10: Use handoff_to_sofia

Select the appropriate handoff tool based on the score above."""
    
    def build_prompt(state: MinimalState) -> List[AnyMessage]:
        lead_score = state.get("lead_score", 0)
        
        # Format the system prompt with current score
        formatted_system = system_prompt.format(lead_score=lead_score)
        
        # Don't pass customer messages - supervisor doesn't need them
        # This prevents the urge to respond to the customer
        return [{"role": "system", "content": formatted_system}]
    
    # Create agent without prompt function for now
    agent = create_react_agent(
        model=model,
        tools=tools,
        state_schema=MinimalState
    )
    
    return agent, build_prompt  # Return both agent and prompt builder


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
        supervisor, build_prompt = create_supervisor_with_tools()
        
        # Build a custom state with only the system prompt
        prompt_messages = build_prompt(state)
        supervisor_state = {
            "messages": prompt_messages,
            "remaining_steps": state.get("remaining_steps", 10)
        }
        
        result = await supervisor.ainvoke(supervisor_state)
        
        # Extract routing from result
        current_messages = state.get("messages", [])
        result_messages = result.get("messages", [])
        
        # Only keep new messages added by supervisor (tool calls)
        new_messages = MessageManager.set_messages(current_messages, result_messages)
        
        routing_update = {
            "supervisor_complete": True,
            "messages": new_messages  # Only new messages to avoid duplication
        }
        
        # Find handoff in messages
        handoff_found = False
        
        # Filter messages to ensure NO direct responses from supervisor
        filtered_messages = []
        for msg in result.get("messages", []):
            # Check if AI message has tool calls
            if isinstance(msg, AIMessage):
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    logger.info(f"✅ Supervisor used {len(msg.tool_calls)} tool(s)")
                    handoff_found = True
                    # Keep the message but remove any content
                    msg.content = ""  # Clear content to ensure no text response
                    filtered_messages.append(msg)
                elif msg.content and not msg.tool_calls:
                    # CRITICAL ERROR - supervisor responded directly!
                    logger.error(f"❌ CRITICAL: Supervisor responded directly: {msg.content[:100]}")
                    # DO NOT include this message at all
                    continue
            else:
                # Keep non-AI messages (like ToolMessage)
                filtered_messages.append(msg)
        
        # Update messages with filtered version
        routing_update["messages"] = MessageManager.set_messages(current_messages, filtered_messages)
        
        # Check for handoff pattern in filtered messages
        for msg in filtered_messages:
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
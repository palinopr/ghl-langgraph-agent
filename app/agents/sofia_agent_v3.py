"""
Sofia - Appointment Specialist V3 (Context-Aware)
Uses context from AI supervisor instead of re-analyzing
"""
from typing import Dict, Any, Optional
from langchain_core.messages import AnyMessage
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState
from app.tools.agent_tools_v2 import (
    check_calendar_availability,
    book_appointment_from_confirmation,
    escalate_to_supervisor
)
from app.utils.simple_logger import get_logger
from app.utils.model_factory import create_openai_model

logger = get_logger("sofia_v3")


class SofiaState(AgentState):
    """Simplified state for Sofia agent"""
    contact_id: str
    agent_context: Optional[Dict[str, Any]]


def sofia_prompt_v3(state: SofiaState) -> list[Dict[str, str]]:
    """
    Simplified prompt that uses supervisor context
    """
    # Get context from AI supervisor
    context = state.get("agent_context", {})
    customer_intent = context.get("customer_intent", "schedule appointment")
    conversation_stage = context.get("conversation_stage", "closing")
    key_points = context.get("key_points", [])
    suggested_approach = context.get("suggested_approach", "offer appointment times")
    do_not = context.get("do_not", [])
    
    # Get basic info
    messages = state.get("messages", [])
    last_user_msg = ""
    for msg in reversed(messages):
        if hasattr(msg, '__class__') and msg.__class__.__name__ == 'HumanMessage':
            last_user_msg = msg.content
            break
    
    system_prompt = f"""You are Sofia, an efficient appointment specialist for Main Outlet Media.
You help qualified leads schedule consultations about our WhatsApp automation services.

SUPERVISOR CONTEXT:
- Customer Intent: {customer_intent}
- Conversation Stage: {conversation_stage}
- Key Points: {', '.join(key_points) if key_points else 'None'}
- Suggested Approach: {suggested_approach}

DO NOT: {', '.join(do_not) if do_not else 'None'}

Current Customer Message: "{last_user_msg}"

YOUR PERSONALITY:
- Efficient and friendly
- Create urgency without being pushy
- Enthusiastic about helping their business
- Use emojis moderately (15-20% of messages)

YOUR GOALS:
1. Show available appointment slots
2. Book the appointment
3. Confirm all details
4. Create excitement about the consultation

AVAILABLE TOOLS:
1. check_calendar_availability - Show available times
2. book_appointment_from_confirmation - Book when customer selects a time
3. escalate_to_supervisor - If customer needs something else

APPOINTMENT CONTEXT:
- 30-minute consultation via Google Meet
- We'll discuss their specific needs and create a custom plan
- No obligation, but we'll show exactly how we can help

Respond efficiently based on the supervisor's guidance."""
    
    return [{"role": "system", "content": system_prompt}] + [
        {"role": msg.__class__.__name__.replace('Message', '').lower(), "content": msg.content}
        for msg in messages[-5:]  # Last 5 messages
    ]


def create_sofia_agent_v3():
    """Create context-aware Sofia agent"""
    model = create_openai_model(temperature=0.7)
    
    tools = [
        check_calendar_availability,
        book_appointment_from_confirmation,
        escalate_to_supervisor
    ]
    
    agent = create_react_agent(
        model=model,
        tools=tools,
        state_schema=SofiaState,
        prompt=sofia_prompt_v3,
        name="sofia_v3"
    )
    
    logger.info("Created Sofia V3 agent (context-aware)")
    return agent


async def sofia_node_v3(state: Dict[str, Any]) -> Dict[str, Any]:
    """Sofia node that uses supervisor context"""
    try:
        # Log that we're using supervisor context
        agent_context = state.get("agent_context", {})
        logger.info(f"Sofia using supervisor context: {agent_context.get('customer_intent', 'unknown')}")
        
        # Create and invoke agent
        agent = create_sofia_agent_v3()
        result = await agent.ainvoke(state)
        
        # Return filtered result
        return {
            "messages": result.get("messages", []),
            "needs_rerouting": result.get("needs_rerouting", False),
            "escalation_reason": result.get("escalation_reason", ""),
            "appointment_booked": result.get("appointment_booked", False)
        }
        
    except Exception as e:
        logger.error(f"Error in Sofia V3: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "messages": []
        }


__all__ = ["sofia_node_v3", "create_sofia_agent_v3", "SofiaState"]
"""
Carlos - Lead Qualification Specialist V3 (Context-Aware)
Uses context from AI supervisor instead of re-analyzing
"""
from typing import Dict, Any, Optional
from langchain_core.messages import AnyMessage
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState
from app.tools.agent_tools_v2 import (
    update_contact_with_state,
    escalate_to_supervisor
)
from app.utils.simple_logger import get_logger
from app.utils.model_factory import create_openai_model

logger = get_logger("carlos_v3")


class CarlosState(AgentState):
    """Simplified state for Carlos agent"""
    contact_id: str
    agent_context: Optional[Dict[str, Any]]


def carlos_prompt_v3(state: CarlosState) -> list[Dict[str, str]]:
    """
    Simplified prompt that uses supervisor context
    """
    # Get context from AI supervisor
    context = state.get("agent_context", {})
    customer_intent = context.get("customer_intent", "needs qualification")
    conversation_stage = context.get("conversation_stage", "qualification")
    key_points = context.get("key_points", [])
    suggested_approach = context.get("suggested_approach", "assess needs and budget")
    do_not = context.get("do_not", [])
    
    # Get basic info
    messages = state.get("messages", [])
    last_user_msg = ""
    for msg in reversed(messages):
        if hasattr(msg, '__class__') and msg.__class__.__name__ == 'HumanMessage':
            last_user_msg = msg.content
            break
    
    system_prompt = f"""You are Carlos, a professional lead qualification specialist for Main Outlet Media.
You help assess if businesses are a good fit for our WhatsApp automation services.

SUPERVISOR CONTEXT:
- Customer Intent: {customer_intent}
- Conversation Stage: {conversation_stage}
- Key Points: {', '.join(key_points) if key_points else 'None'}
- Suggested Approach: {suggested_approach}

DO NOT: {', '.join(do_not) if do_not else 'None'}

Current Customer Message: "{last_user_msg}"

YOUR PERSONALITY:
- Professional yet friendly
- Focus on understanding their business needs
- Provide valuable insights
- Use emojis sparingly (5-10% of messages)

YOUR GOALS:
1. Understand their current challenges
2. Confirm budget ($300+ monthly)
3. Identify their goals
4. Escalate to Sofia when qualified

AVAILABLE TOOLS:
1. qualify_lead_v2 - Update lead qualification status
2. escalate_to_supervisor - When ready for appointment or needs different help

PRICING CONTEXT:
- Plans start at $300/month
- Include automated responses, appointment booking, and analytics
- Custom solutions available for larger businesses

Respond professionally based on the supervisor's guidance."""
    
    return [{"role": "system", "content": system_prompt}] + [
        {"role": msg.__class__.__name__.replace('Message', '').lower(), "content": msg.content}
        for msg in messages[-5:]  # Last 5 messages
    ]


def create_carlos_agent_v3():
    """Create context-aware Carlos agent"""
    model = create_openai_model(temperature=0.6)
    
    tools = [
        update_contact_with_state,
        escalate_to_supervisor
    ]
    
    agent = create_react_agent(
        model=model,
        tools=tools,
        state_schema=CarlosState,
        prompt=carlos_prompt_v3,
        name="carlos_v3"
    )
    
    logger.info("Created Carlos V3 agent (context-aware)")
    return agent


async def carlos_node_v3(state: Dict[str, Any]) -> Dict[str, Any]:
    """Carlos node that uses supervisor context"""
    try:
        # Log that we're using supervisor context
        agent_context = state.get("agent_context", {})
        logger.info(f"Carlos using supervisor context: {agent_context.get('customer_intent', 'unknown')}")
        
        # Create and invoke agent
        agent = create_carlos_agent_v3()
        result = await agent.ainvoke(state)
        
        # Return filtered result
        return {
            "messages": result.get("messages", []),
            "needs_rerouting": result.get("needs_rerouting", False),
            "escalation_reason": result.get("escalation_reason", "")
        }
        
    except Exception as e:
        logger.error(f"Error in Carlos V3: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "messages": []
        }


__all__ = ["carlos_node_v3", "create_carlos_agent_v3", "CarlosState"]
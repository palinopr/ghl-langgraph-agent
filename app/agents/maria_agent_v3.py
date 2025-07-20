"""
Maria - Customer Support Agent V3 (Context-Aware)
Uses context from AI supervisor instead of re-analyzing
"""
from typing import Dict, Any, Optional
from langchain_core.messages import AnyMessage
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState
from app.tools.agent_tools_v2 import (
    get_contact_details_v2,
    escalate_to_supervisor
)
from app.utils.simple_logger import get_logger
from app.utils.model_factory import create_openai_model

logger = get_logger("maria_v3")


class MariaState(AgentState):
    """Simplified state for Maria agent"""
    contact_id: str
    agent_context: Optional[Dict[str, Any]]


def maria_prompt_v3(state: MariaState) -> list[Dict[str, str]]:
    """
    Simplified prompt that uses supervisor context
    """
    # Get context from AI supervisor
    context = state.get("agent_context", {})
    customer_intent = context.get("customer_intent", "general inquiry")
    conversation_stage = context.get("conversation_stage", "initial_contact")
    key_points = context.get("key_points", [])
    suggested_approach = context.get("suggested_approach", "be helpful and friendly")
    do_not = context.get("do_not", [])
    
    # Get basic info
    messages = state.get("messages", [])
    last_user_msg = ""
    for msg in reversed(messages):
        if hasattr(msg, '__class__') and msg.__class__.__name__ == 'HumanMessage':
            last_user_msg = msg.content
            break
    
    system_prompt = f"""You are Maria, a warm and helpful customer support agent for Main Outlet Media.
You help businesses automate their WhatsApp messaging to never miss a customer.

SUPERVISOR CONTEXT:
- Customer Intent: {customer_intent}
- Conversation Stage: {conversation_stage}
- Key Points: {', '.join(key_points) if key_points else 'None'}
- Suggested Approach: {suggested_approach}

DO NOT: {', '.join(do_not) if do_not else 'None'}

Current Customer Message: "{last_user_msg}"

YOUR PERSONALITY:
- Warm, patient, and genuinely helpful
- Speak naturally in Spanish (or English if customer uses English)
- Use emojis sparingly (10-15% of messages)
- Focus on understanding their needs

AVAILABLE TOOLS:
1. get_contact_details_v2 - Get customer information
2. escalate_to_supervisor - When you need to transfer (e.g., ready for appointment, needs pricing)

IMPORTANT: 
- Follow the supervisor's guidance about what to do
- Don't repeat questions mentioned in "DO NOT"
- If customer seems ready for next stage, escalate with clear reason

Respond naturally and helpfully based on the context provided."""
    
    return [{"role": "system", "content": system_prompt}] + [
        {"role": msg.__class__.__name__.replace('Message', '').lower(), "content": msg.content}
        for msg in messages[-5:]  # Last 5 messages
    ]


def create_maria_agent_v3():
    """Create context-aware Maria agent"""
    model = create_openai_model(temperature=0.7)
    
    tools = [
        get_contact_details_v2,
        escalate_to_supervisor
    ]
    
    agent = create_react_agent(
        model=model,
        tools=tools,
        state_schema=MariaState,
        prompt=maria_prompt_v3,
        name="maria_v3"
    )
    
    logger.info("Created Maria V3 agent (context-aware)")
    return agent


async def maria_node_v3(state: Dict[str, Any]) -> Dict[str, Any]:
    """Maria node that uses supervisor context"""
    try:
        # Log that we're using supervisor context
        agent_context = state.get("agent_context", {})
        logger.info(f"Maria using supervisor context: {agent_context.get('customer_intent', 'unknown')}")
        
        # Create and invoke agent
        agent = create_maria_agent_v3()
        result = await agent.ainvoke(state)
        
        # Return filtered result
        return {
            "messages": result.get("messages", []),
            "needs_rerouting": result.get("needs_rerouting", False),
            "escalation_reason": result.get("escalation_reason", "")
        }
        
    except Exception as e:
        logger.error(f"Error in Maria V3: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "messages": []
        }


__all__ = ["maria_node_v3", "create_maria_agent_v3", "MariaState"]
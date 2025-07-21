"""
AI Supervisor - Intelligent routing with rich context for agents
Analyzes conversation and provides complete context so agents don't need to re-analyze
"""
from typing import Dict, Any, Literal, Optional
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command
from app.state.conversation_state import ConversationState
from app.utils.simple_logger import get_logger
from app.utils.model_factory import create_openai_model
from app.tools.agent_tools_v2 import create_handoff_tool_for_supervisor

logger = get_logger("supervisor_ai")


def supervisor_ai_prompt(state: Dict[str, Any]) -> list[Dict[str, str]]:
    """
    Dynamic prompt for AI supervisor that analyzes and provides context
    """
    # Get key information
    lead_score = state.get("lead_score", 0)
    extracted_data = state.get("extracted_data", {})
    messages = state.get("messages", [])
    
    # Get last user message
    last_user_msg = ""
    for msg in reversed(messages):
        if hasattr(msg, '__class__') and msg.__class__.__name__ == 'HumanMessage':
            last_user_msg = msg.content
            break
    
    # Build conversation summary
    conv_summary = []
    for msg in messages[-10:]:  # Last 10 messages
        if hasattr(msg, 'content'):
            role = msg.__class__.__name__.replace('Message', '').lower()
            conv_summary.append(f"{role}: {msg.content[:100]}...")
    
    system_prompt = f"""You are an intelligent routing supervisor for Main Outlet Media.
Your job is to analyze conversations and route to the appropriate agent WITH RICH CONTEXT.

Current Information:
- Lead Score: {lead_score}/10
- Customer Name: {extracted_data.get('name', 'Unknown')}
- Business Type: {extracted_data.get('business_type', 'Not mentioned')}
- Budget: {extracted_data.get('budget', 'Not discussed')}
- Last Message: "{last_user_msg}"

Recent Conversation:
{chr(10).join(conv_summary)}

ROUTING RULES:
1. **Sofia (Score 8-10)**: Ready to book appointments, has budget confirmed
2. **Carlos (Score 5-7)**: Interested but needs qualification
3. **Maria (Score 1-4)**: New leads, general questions, support

YOUR TASK:
1. Analyze the conversation context
2. Determine the customer's current intent and needs
3. Choose the best agent to handle this
4. Provide rich context so the agent knows exactly what to do

When routing, you MUST:
- Use the appropriate handoff tool (handoff_to_maria, handoff_to_carlos, handoff_to_sofia)
- In the context parameter, provide:
  - customer_intent: What the customer wants right now
  - conversation_stage: Where we are in the sales process
  - key_points: Important information to remember
  - suggested_approach: How the agent should respond
  - do_not: Things to avoid (e.g., "don't ask for name again")

Example context:
{{
    "customer_intent": "wants to know pricing for restaurant automation",
    "conversation_stage": "qualification",
    "key_points": ["owns restaurant", "looking for WhatsApp automation"],
    "suggested_approach": "explain pricing tiers and ask about message volume",
    "do_not": ["ask for business type again", "be pushy about appointment"]
}}

Remember: The goal is to prevent agents from re-analyzing. Give them everything they need."""
    
    return [{"role": "system", "content": system_prompt}] + [
        {"role": msg.__class__.__name__.replace('Message', '').lower(), "content": msg.content}
        for msg in messages[-5:]  # Last 5 messages for context
    ]


def create_supervisor_ai():
    """Create AI supervisor with context-aware routing"""
    model = create_openai_model(temperature=0.3)  # Lower temp for consistency
    
    # Create handoff tools with context parameter
    tools = [
        create_handoff_tool_for_supervisor("maria"),
        create_handoff_tool_for_supervisor("carlos"),
        create_handoff_tool_for_supervisor("sofia")
    ]
    
    agent = create_react_agent(
        model=model,
        tools=tools,
        state_schema=ConversationState,
        prompt=supervisor_ai_prompt,
        name="supervisor_ai"
    )
    
    logger.info("Created AI supervisor with context routing")
    return agent


async def supervisor_ai_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    AI Supervisor node that provides rich context to agents
    """
    try:
        # Create and invoke supervisor
        supervisor = create_supervisor_ai()
        result = await supervisor.ainvoke(state)
        
        # The handoff tools will set next_agent and agent_context
        # Extract and return the enriched state
        return {
            "messages": result.get("messages", []),
            "next_agent": result.get("next_agent"),
            "agent_context": result.get("agent_context", {}),
            "routing_attempts": state.get("routing_attempts", 0) + 1
        }
        
    except Exception as e:
        logger.error(f"Error in AI supervisor: {str(e)}", exc_info=True)
        # Fallback to score-based routing
        lead_score = state.get("lead_score", 0)
        if lead_score >= 8:
            next_agent = "sofia"
        elif lead_score >= 5:
            next_agent = "carlos"
        else:
            next_agent = "maria"
            
        return {
            "next_agent": next_agent,
            "agent_context": {
                "error": "Supervisor failed, using score-based routing",
                "fallback": True
            },
            "routing_attempts": state.get("routing_attempts", 0) + 1
        }


__all__ = ["supervisor_ai_node", "create_supervisor_ai"]
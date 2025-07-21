"""
Maria - Customer Support Agent (FIXED VERSION)
Always uses conversation enforcer templates - no freestyle greetings!
"""
from typing import Dict, Any, Optional
from langchain_core.messages import AnyMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState
from app.tools.agent_tools_v2 import (
    get_contact_details_v2,
    escalate_to_supervisor
)
from app.utils.simple_logger import get_logger
from app.utils.model_factory import create_openai_model
from app.utils.conversation_enforcer import ConversationEnforcer, ConversationStage

logger = get_logger("maria_v2_fixed")


class MariaState(AgentState):
    """State for Maria agent"""
    contact_id: str
    contact_name: Optional[str]
    lead_score: int
    extracted_data: Optional[Dict[str, Any]]


def maria_prompt_fixed(state: MariaState) -> list[AnyMessage]:
    """
    FIXED prompt that enforces conversation templates
    """
    # Get basic info from state
    contact_id = state.get("contact_id", "")
    lead_score = state.get("lead_score", 0)
    extracted_data = state.get("extracted_data", {})
    
    # Check if this is wrong agent
    if lead_score >= 5:
        logger.warning(f"Maria received lead with score {lead_score} (should be 1-4)")
    
    # Get messages to analyze conversation stage
    messages = state.get("messages", [])
    
    # Use conversation enforcer to get EXACT response
    enforcer = ConversationEnforcer()
    analysis = enforcer.analyze_conversation(messages)
    
    # Get the allowed response
    allowed_response = analysis.get("allowed_response", "")
    current_stage = analysis.get("current_stage", ConversationStage.GREETING)
    collected_data = analysis.get("collected_data", {})
    
    # If no messages (new conversation), use greeting template
    if not messages or len(messages) == 1:
        # Force greeting stage
        if analysis["language"] == "es":
            allowed_response = "¡Hola! Soy de Main Outlet Media. Ayudamos a negocios como el tuyo a automatizar WhatsApp para nunca perder clientes. ¿Cuál es tu nombre?"
        else:
            allowed_response = "Hi! I'm from Main Outlet Media. We help businesses like yours automate WhatsApp to never miss a customer. What's your name?"
    
    system_prompt = f"""You are Maria, a professional WhatsApp automation consultant for Main Outlet Media.

CRITICAL RULES:
1. You handle ONLY cold leads (score 1-4)
2. If lead score is 5+, IMMEDIATELY escalate with reason="wrong_agent"
3. ALWAYS use the EXACT allowed response provided below
4. NO VARIATIONS from the template allowed

CURRENT STATUS:
- Lead Score: {lead_score}/10
- Stage: {current_stage}
- Collected: Name={collected_data.get('name')}, Business={collected_data.get('business')}, Budget={collected_data.get('budget_confirmed')}

🚨 YOUR EXACT RESPONSE MUST BE:
"{allowed_response}"

⚠️ IMPORTANT:
- If allowed response starts with "ESCALATE:", use escalate_to_supervisor tool
- Otherwise, respond with the EXACT text above, no changes!
- NEVER create your own greeting or questions
- NEVER say "¿En qué puedo ayudarte hoy?" or similar open questions

AVAILABLE TOOLS:
- get_contact_details_v2: Check existing info
- escalate_to_supervisor: Use when:
  - reason="wrong_agent" if score >= 5
  - reason="needs_qualification" after budget confirmed
  - reason="customer_confused" if off-track

Remember: You are NOT a general help desk. You specifically help with WhatsApp automation."""
    
    return [{"role": "system", "content": system_prompt}] + state["messages"]


def create_maria_agent_fixed():
    """Create fixed Maria agent that uses templates"""
    model = create_openai_model(temperature=0.0)
    
    tools = [
        get_contact_details_v2,
        escalate_to_supervisor
    ]
    
    agent = create_react_agent(
        model=model,
        tools=tools,
        state_schema=MariaState,
        prompt=maria_prompt_fixed,
        name="maria_fixed"
    )
    
    logger.info("Created FIXED Maria agent that uses conversation templates")
    return agent


async def maria_node_v2_fixed(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fixed Maria node that enforces templates
    """
    try:
        # Check lead score first
        lead_score = state.get("lead_score", 0)
        if lead_score >= 5:
            logger.info(f"Maria escalating lead with score {lead_score}")
            return {
                "needs_rerouting": True,
                "escalation_reason": "wrong_agent",
                "escalation_details": f"Lead score {lead_score} too high for Maria (handles 1-4)",
                "current_agent": "maria"
            }
        
        # Create and run agent
        agent = create_maria_agent_fixed()
        result = await agent.ainvoke(state)
        
        # Update state
        return {
            "messages": result.get("messages", []),
            "current_agent": "maria"
        }
        
    except Exception as e:
        logger.error(f"Maria error: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "current_agent": "maria"
        }


# Export
__all__ = ["maria_node_v2_fixed", "create_maria_agent_fixed", "MariaState"]
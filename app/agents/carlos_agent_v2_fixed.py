"""
Carlos - Qualification Agent (FIXED VERSION)
Always uses conversation enforcer templates - no freestyle questions!
"""
from typing import Dict, Any, Optional
from langchain_core.messages import AnyMessage
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState
from app.tools.agent_tools_modernized import (
    get_contact_details_with_task,
    update_contact_with_context,
    escalate_to_supervisor,
    save_important_context
)
from app.utils.simple_logger import get_logger
from app.utils.model_factory import create_openai_model

logger = get_logger("carlos_v2_fixed")


class CarlosState(AgentState):
    """State for Carlos agent"""
    contact_id: str
    contact_name: Optional[str]
    lead_score: int
    extracted_data: Optional[Dict[str, Any]]


def carlos_prompt_fixed(state: CarlosState) -> list[AnyMessage]:
    """
    FIXED prompt that enforces conversation templates
    """
    # Get basic info from state
    contact_id = state.get("contact_id", "")
    lead_score = state.get("lead_score", 0)
    extracted_data = state.get("extracted_data", {})
    
    # Get messages to analyze conversation stage
    messages = state.get("messages", [])
    
    # Simplified analysis without enforcer
    analysis = {
        "allowed_response": "",
        "current_stage": "qualification",
        "collected_data": extracted_data
    }
    
    # Get the allowed response
    allowed_response = analysis.get("allowed_response", "")
    current_stage = analysis.get("current_stage")
    collected_data = analysis.get("collected_data", {})
    
    system_prompt = f"""You are Carlos, a lead qualification specialist for Main Outlet Media.

CRITICAL RULES:
1. You handle ONLY warm leads (score 5-7)
2. ALWAYS use the EXACT allowed response provided below
3. NO VARIATIONS from the template allowed
4. Focus on WhatsApp automation benefits

CURRENT STATUS:
- Lead Score: {lead_score}/10
- Stage: {current_stage}
- Collected: Name={collected_data.get('name')}, Business={collected_data.get('business')}, Budget={collected_data.get('budget_confirmed')}

🚨 YOUR EXACT RESPONSE MUST BE:
"{allowed_response}"

⚠️ IMPORTANT:
- If allowed response starts with "ESCALATE:", use escalate_to_supervisor tool
- Otherwise, respond with the EXACT text above, no changes!
- NEVER create your own questions
- NEVER ask "¿Cómo puedo ayudarte?" or similar open questions

AVAILABLE TOOLS:
- get_contact_details_v2: Check existing info
- update_contact_with_state: Save collected data
- escalate_to_supervisor: Use when:
  - reason="needs_appointment" if score >= 8 with email
  - reason="customer_confused" if off-track
  - reason="wrong_agent" if score < 5

Remember: You help businesses understand how WhatsApp automation saves time and captures more leads."""
    
    return [{"role": "system", "content": system_prompt}] + state["messages"]


def create_carlos_agent_fixed():
    """Create fixed Carlos agent that uses templates"""
    model = create_openai_model(temperature=0.3)
    
    tools = [
        get_contact_details_with_task,
        update_contact_with_context,
        escalate_to_supervisor,
        save_important_context
    ]
    
    agent = create_react_agent(
        model=model,
        tools=tools,
        state_schema=CarlosState,
        prompt=carlos_prompt_fixed,
        name="carlos_fixed"
    )
    
    logger.info("Created FIXED Carlos agent that uses conversation templates")
    return agent


async def carlos_node_v2_fixed(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fixed Carlos node that enforces templates
    """
    try:
        # Check lead score
        lead_score = state.get("lead_score", 0)
        extracted_data = state.get("extracted_data", {})
        
        # Route checks
        if lead_score < 5:
            return {
                "needs_rerouting": True,
                "escalation_reason": "wrong_agent",
                "escalation_details": f"Lead score {lead_score} too low for Carlos (handles 5-7)",
                "current_agent": "carlos"
            }
        elif lead_score >= 8 and extracted_data.get("email"):
            return {
                "needs_rerouting": True,
                "escalation_reason": "needs_appointment",
                "escalation_details": "Ready for appointment booking",
                "current_agent": "carlos"
            }
        
        # Create and run agent
        agent = create_carlos_agent_fixed()
        result = await agent.ainvoke(state)
        
        # Update state
        return {
            "messages": result.get("messages", []),
            "current_agent": "carlos"
        }
        
    except Exception as e:
        logger.error(f"Carlos error: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "current_agent": "carlos"
        }


# Export
__all__ = ["carlos_node_v2_fixed", "create_carlos_agent_fixed", "CarlosState"]
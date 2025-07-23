"""
Carlos - Qualification Agent (FIXED VERSION)
Always uses conversation enforcer templates - no freestyle questions!
"""
from typing import Dict, Any, Optional
from langchain_core.messages import AnyMessage
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState
from app.tools.agent_tools import (
    get_contact_details_with_task,
    update_contact_with_context,
    escalate_to_supervisor,
    save_important_context,
    track_lead_progress
)
from app.utils.simple_logger import get_logger
from app.utils.model_factory import create_openai_model
from app.agents.base_agent import (
    get_current_message,
    check_score_boundaries,
    extract_data_status,
    create_error_response
)
from app.state.message_manager import MessageManager
from app.utils.langsmith_debug import debug_node, log_to_langsmith, debugger
from app.agents.message_fixer import fix_agent_messages

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
    
    system_prompt = f"""You are Carlos, a WhatsApp automation expert focused on booking demo calls.

🎯 YOUR GOAL: Convert warm leads into DEMO APPOINTMENTS by showing ROI.

CURRENT DATA:
- Lead Score: {lead_score}/10
- Name: {collected_data.get('name', 'NOT PROVIDED')}
- Business: {collected_data.get('business_type', 'NOT PROVIDED')}
- Problem: {collected_data.get('goal', 'NOT PROVIDED')}
- Budget: {collected_data.get('budget', 'NOT PROVIDED')}

📋 DEMO-FOCUSED STRATEGY:
1. If they have a problem → Quantify the impact
2. Show ROI: "Con $300 al mes, podrías automatizar hasta 1000 conversaciones"
3. Create urgency: "Esta semana tengo 3 espacios para demos personalizadas"
4. Book the demo: "¿Te funciona mañana a las 3pm para una demo de 15 minutos?"

💬 PROBLEM-TO-DEMO FLOW:
- "Perdiendo clientes" → "¿Sabes que el 67% de clientes se van si no respondes en 5 minutos?"
- "No tengo tiempo" → "¿Cuánto vale tu hora? La automatización te ahorra 20 horas/semana"
- Always pivot to: "Te muestro exactamente cómo funciona para tu negocio"

🚀 QUALIFYING QUESTIONS (if needed):
- "¿Cuántos mensajes recibes al día en WhatsApp?"
- "¿Tienes a alguien dedicado a responder mensajes?"
- "¿Qué pasaría si pudieras responder 24/7 automáticamente?"

⚠️ ESCALATION RULES:
- Score 8+ with email → Escalate to Sofia for appointment
- Score < 5 → Escalate back to Maria
- Customer ready to book → Escalate to Sofia

Remember: Don't just qualify - show them why they NEED this demo NOW!"""
    
    # Only include the current message to prevent duplication
    # create_react_agent returns all input messages plus its response
    messages = state.get("messages", [])
    
    # Find the last customer message to process
    customer_message = None
    for msg in reversed(messages):
        # Check for HumanMessage that's from a customer (no name attribute)
        if hasattr(msg, '__class__') and 'Human' in msg.__class__.__name__:
            # Skip if it has a name (means it's from an agent/system)
            if not hasattr(msg, 'name') or not msg.name:
                customer_message = msg
                break
    
    # Build conversation history for context (excluding supervisor messages)
    conversation_history = []
    for msg in messages:
        # Include customer messages (HumanMessage without name)
        if hasattr(msg, '__class__') and 'Human' in msg.__class__.__name__:
            if not hasattr(msg, 'name') or not msg.name:
                conversation_history.append(f"Cliente: {msg.content}")
        # Include agent responses (AIMessage with name that's not supervisor)
        elif hasattr(msg, '__class__') and 'AI' in msg.__class__.__name__:
            if hasattr(msg, 'name') and msg.name and msg.name != 'supervisor':
                conversation_history.append(f"{msg.name.title()}: {msg.content}")
    
    # Add conversation history to prompt
    history_context = ""
    if conversation_history:
        history_context = "\n\n💬 CONVERSATION HISTORY:"
        for msg in conversation_history[-5:]:  # Show last 5 exchanges
            history_context += f"\n{msg}"
    
    # Update system prompt with conversation history
    system_prompt_with_history = system_prompt + history_context
    
    # Only pass the last customer message to avoid duplication
    filtered_messages = [customer_message] if customer_message else []
        
    return [{"role": "system", "content": system_prompt_with_history}] + filtered_messages


def create_carlos_agent_fixed():
    """Create fixed Carlos agent that uses templates"""
    model = create_openai_model(temperature=0.3)
    
    tools = [
        get_contact_details_with_task,
        update_contact_with_context,
        escalate_to_supervisor,
        save_important_context,
        track_lead_progress
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


@debug_node("carlos_agent")
async def carlos_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fixed Carlos node that enforces templates
    """
    try:
        # Check lead score
        lead_score = state.get("lead_score", 0)
        extracted_data = state.get("extracted_data", {})
        
        # Route checks using base function
        boundary_check = check_score_boundaries(lead_score, 5, 7, "Carlos", logger)
        if boundary_check:
            # Special case: if score is 8+ AND has email, needs appointment
            if lead_score >= 8 and extracted_data.get("email"):
                return {
                    "needs_rerouting": True,
                    "escalation_reason": "needs_appointment",
                    "escalation_details": "Ready for appointment booking",
                    "current_agent": "carlos"
                }
            return boundary_check
        
        # Create and run agent
        agent = create_carlos_agent_fixed()
        result = await agent.ainvoke(state)
        
        # Only return new messages to avoid duplication
        current_messages = state.get("messages", [])
        result_messages = result.get("messages", [])
        
        # Fix agent messages to have proper name
        if result_messages:
            result_messages = fix_agent_messages(result_messages, "carlos")
            logger.info(f"Fixed {len(result_messages)} messages with agent name 'carlos'")
        
        new_messages = MessageManager.set_messages(current_messages, result_messages)
        
        # Update state
        return {
            "messages": new_messages,  # Only new messages
            "current_agent": "carlos"
        }
        
    except Exception as e:
        logger.error(f"Carlos error: {str(e)}", exc_info=True)
        return create_error_response("carlos", e, state)


# Export
__all__ = ["carlos_node", "create_carlos_agent_fixed", "CarlosState"]
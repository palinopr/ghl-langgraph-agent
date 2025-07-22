"""
Sofia - Appointment Setting Agent (FIXED VERSION)
Follows conversation rules strictly - no shortcuts!
"""
from typing import Dict, Any, List, Optional
from langchain_core.messages import AnyMessage
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState
from app.tools.agent_tools_modernized import (
    get_contact_details_with_task,
    update_contact_with_context,
    book_appointment_with_instructions,
    escalate_to_supervisor
)
from app.utils.simple_logger import get_logger
from app.utils.model_factory import create_openai_model
from app.agents.base_agent import (
    get_current_message,
    check_score_boundaries,
    extract_data_status,
    create_error_response
)

logger = get_logger("sofia_v2_fixed")


class SofiaState(AgentState):
    """Extended state for Sofia agent"""
    contact_id: str
    contact_name: Optional[str]
    appointment_status: Optional[str]
    appointment_id: Optional[str]
    should_continue: bool = True
    extracted_data: Optional[Dict[str, Any]]
    lead_score: int


def sofia_prompt_fixed(state: SofiaState) -> list[AnyMessage]:
    """
    FIXED prompt for Sofia that follows conversation rules
    """
    # Get basic info from state
    contact_id = state.get("contact_id", "")
    contact_name = state.get("contact_name", "")
    extracted_data = state.get("extracted_data", {})
    lead_score = state.get("lead_score", 0)
    
    # Get what we have collected using base function
    data_status = extract_data_status(extracted_data)
    has_name = data_status["has_name"] or bool(contact_name)
    has_business = data_status["has_business"]
    has_budget = data_status["has_budget"]
    has_email = data_status["has_email"]
    
    # Get current message
    messages = state.get("messages", [])
    current_message = get_current_message(messages)
    
    # Calculate what we need next (ONE THING AT A TIME!)
    next_step = "ASK_NAME"
    if has_name and not has_business:
        next_step = "ASK_BUSINESS"
    elif has_name and has_business and not has_budget:
        next_step = "ASK_BUDGET"
    elif has_name and has_business and has_budget and not has_email:
        next_step = "ASK_EMAIL"
    elif has_name and has_business and has_budget and has_email:
        next_step = "OFFER_APPOINTMENT"
    
    system_prompt = f"""IMPORTANTE: Debes responder SIEMPRE en español. NUNCA en inglés.
    
You are Sofia, appointment specialist for Main Outlet Media.
You ONLY book appointments for QUALIFIED leads (score 8+) who have PROVIDED ALL required information.

CURRENT LEAD STATUS:
- Lead Score: {lead_score}/10
- Has Name: {'✅' if has_name else '❌'} {extracted_data.get('name', '')}
- Has Business: {'✅' if has_business else '❌'} {extracted_data.get('business_type', '')}
- Has Budget: {'✅' if has_budget else '❌'} {extracted_data.get('budget', '')}
- Has Email: {'✅' if has_email else '❌'} {extracted_data.get('email', '')}

🚨 STRICT RULES - NO EXCEPTIONS:
1. You MUST collect ALL information in EXACT order
2. Ask ONE question at a time
3. NEVER skip steps
4. NEVER offer appointments until ALL data is collected

NEXT REQUIRED STEP: {next_step}

Current customer message: "{current_message}"

RESPONSES FOR EACH STEP:

{f'''ASK NAME FIRST:
- "¡Hola! 👋 Soy Sofia de Main Outlet Media. ¿Cuál es tu nombre?"
- "¡Hola! Antes de hablar sobre soluciones de automatización, ¿me podrías decir tu nombre?"''' if next_step == "ASK_NAME" else ''}

{f'''ASK BUSINESS TYPE (only after getting name):
- "Mucho gusto, {extracted_data.get('name', 'there')}. ¿Qué tipo de negocio tienes?"
- "{extracted_data.get('name', 'there')}, cuéntame sobre tu negocio."''' if next_step == "ASK_BUSINESS" else ''}

{f'''ASK BUDGET (only after getting business):
- "{extracted_data.get('name', 'there')}, para tu {extracted_data.get('business_type', 'negocio')}, nuestras soluciones empiezan en $300 al mes. ¿Te funciona ese presupuesto?"
- "Para ayudar a tu {extracted_data.get('business_type', 'negocio')}, la inversión mínima es de $300 al mes. ¿Te parece cómodo?"''' if next_step == "ASK_BUDGET" else ''}

{f'''ASK EMAIL (only after budget confirmed):
- "¡Excelente! Para enviarte el enlace de Google Meet, ¿cuál es tu correo?"
- "¡Perfecto! Necesito tu correo electrónico para enviarte el enlace de la reunión."''' if next_step == "ASK_EMAIL" else ''}

{f'''OFFER APPOINTMENT (only when ALL data collected):
- "¡Excelente! Déjame revisar nuestro calendario para los horarios disponibles..."
- Then use check_calendar_availability tool
- When customer selects time, use book_appointment_from_confirmation''' if next_step == "OFFER_APPOINTMENT" else ''}

AVAILABLE TOOLS:
- get_contact_details_v2: Check what info we already have
- update_contact_with_state: Save collected information
- check_calendar_availability: ONLY when ALL data is collected
- book_appointment_from_confirmation: When customer picks a time
- escalate_to_supervisor: If lead score < 8 or missing data

⚠️ ESCALATION RULES:
- If lead score < 8: escalate with reason="needs_qualification"
- If customer won't provide required info: escalate with reason="customer_confused"
- If you're unsure: escalate with reason="needs_qualification"

Remember: Quality over speed. Follow the process!"""
    
    return [{"role": "system", "content": system_prompt}] + state["messages"]


def create_sofia_agent_fixed():
    """Create fixed Sofia agent that follows rules"""
    model = create_openai_model(temperature=0.3)
    
    tools = [
        get_contact_details_with_task,
        update_contact_with_context,
        book_appointment_with_instructions,
        escalate_to_supervisor
    ]
    
    agent = create_react_agent(
        model=model,
        tools=tools,
        state_schema=SofiaState,
        prompt=sofia_prompt_fixed,
        name="sofia_fixed"
    )
    
    logger.info("Created FIXED Sofia agent that follows conversation rules")
    return agent


async def sofia_node_v2_fixed(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fixed Sofia node that enforces conversation rules
    """
    try:
        # Check if we should even be here
        lead_score = state.get("lead_score", 0)
        # Sofia only handles score 8-10
        boundary_check = check_score_boundaries(lead_score, 8, 10, "Sofia", logger)
        if boundary_check:
            # Override the reason for scores below 8
            if lead_score < 8:
                boundary_check["escalation_reason"] = "needs_qualification"
                boundary_check["escalation_details"] = f"Lead score too low ({lead_score}/10)"
            return boundary_check
        
        # Create and run agent
        agent = create_sofia_agent_fixed()
        result = await agent.ainvoke(state)
        
        # Update state
        return {
            "messages": result.get("messages", []),
            "appointment_status": result.get("appointment_status"),
            "appointment_id": result.get("appointment_id"),
            "current_agent": "sofia"
        }
        
    except Exception as e:
        logger.error(f"Sofia error: {str(e)}", exc_info=True)
        error_response = create_error_response("sofia", e, state)
        # Sofia adds rerouting on errors
        error_response.update({
            "needs_rerouting": True,
            "escalation_reason": "error"
        })
        return error_response


# Export
__all__ = ["sofia_node_v2_fixed", "create_sofia_agent_fixed", "SofiaState"]
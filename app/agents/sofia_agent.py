"""
Sofia - Appointment Setting Agent (FIXED VERSION)
Follows conversation rules strictly - no shortcuts!
"""
from typing import Dict, Any, List, Optional
from langchain_core.messages import AnyMessage
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState
from app.tools.agent_tools import (
    get_contact_details_with_task,
    update_contact_with_context,
    book_appointment_with_instructions,
    escalate_to_router,
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
    
    # Get configurable business context
    from app.config import get_settings
    settings = get_settings()
    
    # Adapt demo pitch based on customer context
    if settings.adapt_to_customer and current_message:
        current_lower = current_message.lower()
        
        # Restaurant/Customer Retention
        if any(word in current_lower for word in ['restaurante', 'restaurant', 'cliente', 'perder']):
            demo_focus = "sistema de retención de clientes"
            demo_pitch = "En 15 minutos te muestro cómo recuperar clientes perdidos automáticamente"
            value_prop = "Imagina enviar ofertas personalizadas a clientes que no han regresado en 30 días"
            urgency_message = "Esta semana implementamos 3 sistemas de retención - quedan 2 espacios"
            
        # Message Overload
        elif any(word in current_lower for word in ['mensaje', 'whatsapp', 'ocupado', 'responder']):
            demo_focus = "automatización de WhatsApp"
            demo_pitch = "En 15 minutos te muestro cómo responder 1000 mensajes automáticamente"
            value_prop = "Respuestas instantáneas 24/7 mientras duermes"
            urgency_message = "Esta semana solo quedan 3 espacios para demos de WhatsApp"
            
        # Retail/Catalog
        elif any(word in current_lower for word in ['tienda', 'producto', 'catálogo', 'venta']):
            demo_focus = "catálogo digital automatizado"
            demo_pitch = "En 15 minutos te muestro cómo vender 24/7 con catálogo en WhatsApp"
            value_prop = "Tus clientes ven productos, precios y compran sin que estés presente"
            urgency_message = "Esta semana lanzamos 3 catálogos digitales - quedan 2 espacios"
            
        # Service/Appointments
        elif any(word in current_lower for word in ['servicio', 'cita', 'agenda', 'consulta']):
            demo_focus = "sistema de agendamiento automático"
            demo_pitch = "En 15 minutos te muestro cómo llenar tu agenda automáticamente"
            value_prop = "Clientes agendan, confirman y reprograman sin tu intervención"
            urgency_message = "Esta semana configuramos 3 sistemas de citas - queda 1 espacio"
            
        else:
            # Generic from settings
            demo_focus = settings.demo_type
            demo_pitch = f"En 15 minutos te muestro exactamente cómo {settings.service_type} transforma tu negocio"
            value_prop = "Automatización personalizada para tu industria específica"
            urgency_message = "Esta semana solo me quedan 3 espacios"
    else:
        # Default values
        demo_focus = settings.demo_type
        demo_pitch = "En 15 minutos te muestro exactamente cómo capturar más clientes 24/7"
        value_prop = "Sistema automatizado que trabaja mientras descansas"
        urgency_message = "Esta semana solo me quedan 3 espacios"
    
    system_prompt = f"""You are Sofia, {demo_focus} closing specialist for {settings.company_name}. 
IMPORTANTE: Responde SIEMPRE en español.

🎯 YOUR GOAL: Close the {demo_focus.upper()} APPOINTMENT - they're already qualified!

CURRENT STATUS:
- Lead Score: {lead_score}/10 (8+ = READY FOR DEMO)
- Name: {extracted_data.get('name', 'NOT PROVIDED')}
- Business: {extracted_data.get('business_type', 'NOT PROVIDED')}
- Problem: {extracted_data.get('goal', 'NOT PROVIDED')}
- Budget: {extracted_data.get('budget', 'NOT PROVIDED')}
- Email: {extracted_data.get('email', 'NOT PROVIDED')}

🎯 SPECIFIC DEMO FOCUS: {demo_focus}
📢 YOUR PITCH: "{demo_pitch}"
💡 VALUE PROP: "{value_prop}"

📋 CONTEXT-SPECIFIC CLOSING STRATEGY:
1. If missing email → "Para enviarte el enlace de la demo de {demo_focus}, ¿cuál es tu correo?"
2. If has all data → BOOK THE DEMO NOW with context-specific pitch
3. Create urgency: "{urgency_message}"
4. Be assumptive: "¿Te va mejor mañana a las 3pm o el jueves a las 11am para ver {demo_focus}?"

🚀 APPOINTMENT BOOKING FLOW:
- STEP 1: Acknowledge their specific problem
- STEP 2: Present YOUR specific solution: "{demo_pitch}"
- STEP 3: Emphasize value: "{value_prop}"
- STEP 4: Use book_appointment_with_instructions tool
- STEP 5: Confirm: "Perfecto {extracted_data.get('name', '')}, te envié los detalles de nuestra demo de {demo_focus}"

💬 CONTEXT-AWARE OBJECTION HANDLING:
- "No tengo tiempo" → "Por eso mismo necesitas {demo_focus}. 15 minutos te ahorrarán horas diarias"
- "Necesito pensarlo" → "¿Qué dudas tienes sobre {demo_focus}? La demo es gratis y personalizada"
- "Es muy caro" → "¿Cuánto pierdes por {extracted_data.get('goal', 'no optimizar')}? El {demo_focus} se paga solo"

⚠️ CRITICAL RULES:
- Score 8+ = Your territory, CLOSE THE {demo_focus.upper()} DEMO
- Score < 8 = Escalate immediately to Carlos
- Always mention the SPECIFIC solution: {demo_focus}
- Book appointments FAST - momentum is key

Remember: They need {demo_focus} - CLOSE THAT SPECIFIC DEMO!"""
    
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


def create_sofia_agent_fixed():
    """Create fixed Sofia agent that follows rules"""
    model = create_openai_model(temperature=0.3)
    
    tools = [
        get_contact_details_with_task,
        update_contact_with_context,
        book_appointment_with_instructions,
        escalate_to_router,
        track_lead_progress
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


@debug_node("sofia_agent")
async def sofia_node(state: Dict[str, Any]) -> Dict[str, Any]:
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
        
        # Only return new messages to avoid duplication
        current_messages = state.get("messages", [])
        result_messages = result.get("messages", [])
        
        # Fix agent messages to have proper name
        if result_messages:
            result_messages = fix_agent_messages(result_messages, "sofia")
            logger.info(f"Fixed {len(result_messages)} messages with agent name 'sofia'")
        
        new_messages = MessageManager.set_messages(current_messages, result_messages)
        
        # Update state
        return {
            "messages": new_messages,  # Only new messages
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
__all__ = ["sofia_node", "create_sofia_agent_fixed", "SofiaState"]
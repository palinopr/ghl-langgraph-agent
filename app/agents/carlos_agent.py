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
    escalate_to_router,
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
from app.utils.conversation_analyzer import analyze_conversation_state

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
    
    # Analyze conversation state
    conversation_analysis = analyze_conversation_state(messages, agent_name="carlos")
    
    # Build context from analysis
    context = f"""
📊 CARLOS CONVERSATION CONTEXT:
🔄 STATUS: {conversation_analysis['status']}
📍 STAGE: {conversation_analysis['stage']}
💬 EXCHANGES: {conversation_analysis['exchange_count']}
❌ OBJECTIONS: {', '.join(conversation_analysis['objections_raised']) if conversation_analysis['objections_raised'] else 'None'}
🎯 DEMO ATTEMPTS: {conversation_analysis['demo_attempts']}

✅ ALREADY DISCUSSED: {', '.join(conversation_analysis['topics_discussed']) if conversation_analysis['topics_discussed'] else 'Nothing yet'}
❓ STILL NEED: {', '.join(conversation_analysis['pending_info']) if conversation_analysis['pending_info'] else 'Ready to close'}"""
    
    # Greeting check
    should_greet = conversation_analysis['exchange_count'] <= 1 and not conversation_analysis['has_greeted']
    
    # Get configurable business context
    from app.config import get_settings
    settings = get_settings()
    
    # Adapt context based on customer's problem
    current_message = get_current_message(messages)
    if settings.adapt_to_customer and current_message:
        current_lower = current_message.lower()
        
        # Restaurant/Customer Retention Context
        if any(word in current_lower for word in ['restaurante', 'restaurant', 'cliente', 'perder', 'retención']):
            service_focus = "sistema de retención de clientes"
            roi_message = "Con $300 al mes, podrías recuperar 50-100 clientes perdidos mensualmente"
            impact_stat = "¿Sabes que el 67% de clientes no regresan si no hay seguimiento post-visita?"
            qualifying_questions = [
                "¿Cuántos clientes nuevos vs. recurrentes tienes?",
                "¿Haces seguimiento después de cada visita?",
                "¿Tienes un programa de lealtad activo?"
            ]
        
        # Message Overload Context
        elif any(word in current_lower for word in ['mensaje', 'ocupado', 'whatsapp', 'chat', 'responder']):
            service_focus = "automatización de WhatsApp"
            roi_message = "Con $300 al mes, automatizas hasta 1000 conversaciones"
            impact_stat = "¿Sabes que el 67% de clientes se van si no respondes en 5 minutos?"
            qualifying_questions = [
                "¿Cuántos mensajes recibes al día en WhatsApp?",
                "¿Tienes a alguien dedicado a responder mensajes?",
                "¿Qué pasaría si pudieras responder 24/7 automáticamente?"
            ]
            
        # Retail/Sales Context
        elif any(word in current_lower for word in ['tienda', 'venta', 'producto', 'catálogo']):
            service_focus = "catálogo digital automatizado"
            roi_message = "Con $300 al mes, aumentas ventas 40% con catálogo 24/7"
            impact_stat = "¿Sabes que el 73% de compras se deciden fuera de horario comercial?"
            qualifying_questions = [
                "¿Cuántos productos manejas?",
                "¿Tus clientes preguntan precios por WhatsApp?",
                "¿Pierdes ventas fuera de horario?"
            ]
            
        # Service/Appointments Context
        elif any(word in current_lower for word in ['servicio', 'cita', 'agenda', 'consulta']):
            service_focus = "sistema de agendamiento automático"
            roi_message = "Con $300 al mes, reduces no-shows 60% y llenas agenda automáticamente"
            impact_stat = "¿Sabes que el 40% de citas se pierden por mala coordinación?"
            qualifying_questions = [
                "¿Cuántas citas manejas semanalmente?",
                "¿Cuántos no-shows tienes?",
                "¿Confirmas citas manualmente?"
            ]
        else:
            # Generic context from settings
            service_focus = settings.service_type
            roi_message = "Con $300 al mes, automatizas procesos y aumentas eficiencia 50%"
            impact_stat = "¿Sabes que la automatización correcta triplica tu capacidad?"
            qualifying_questions = [
                "¿Cuál es tu mayor reto operativo?",
                "¿Qué proceso te quita más tiempo?",
                "¿Has considerado automatizar?"
            ]
    else:
        # Default context
        service_focus = settings.service_type
        roi_message = "Con $300 al mes, automatizas hasta 1000 conversaciones"
        impact_stat = "¿Sabes que el 67% de clientes se van si no respondes en 5 minutos?"
        qualifying_questions = [
            "¿Cuántos mensajes recibes al día?",
            "¿Tienes equipo dedicado a responder?",
            "¿Qué pasaría si respondieras 24/7?"
        ]
    
    system_prompt = f"""You are Carlos, a {service_focus} specialist for {settings.company_name}.

🎯 YOUR GOAL: Convert warm leads into DEMO APPOINTMENTS by showing specific ROI.

{context}

CURRENT DATA:
- Lead Score: {lead_score}/10
- Name: {extracted_data.get('name', 'NOT PROVIDED')}
- Business: {extracted_data.get('business_type', 'NOT PROVIDED')}
- Problem: {extracted_data.get('goal', 'NOT PROVIDED')}
- Budget: {extracted_data.get('budget', 'NOT PROVIDED')}

📋 CONVERSATION RULES:
{f'1. DO NOT GREET - Continue conversation naturally' if not should_greet else '1. START with a warm greeting'}
2. NEVER ask for info already collected: {', '.join(conversation_analysis['topics_discussed'])}
3. ONE question at a time - be conversational
4. Current focus: {conversation_analysis['pending_info'][0] if conversation_analysis['pending_info'] else 'Ready for demo'}

📋 STAGE-BASED STRATEGY - YOU ARE IN: {conversation_analysis['stage'].upper()}

{f'''🔍 DISCOVERY STAGE - Focus on: {conversation_analysis['pending_info'][0] if conversation_analysis['pending_info'] else 'understanding'}
- If missing NAME: "Por cierto, no me compartiste tu nombre. ¿Cómo te llamas?"
- If missing BUSINESS: "Cuéntame más sobre tu {extracted_data.get('business_type', 'negocio')}. ¿Qué tipo de servicios ofreces?"
- If missing PROBLEM: "¿Cuál es el mayor reto que enfrentas con tus clientes actualmente?"
- If missing BUDGET: "¿Qué presupuesto manejas mensualmente para herramientas de marketing?"''' if conversation_analysis['stage'] == 'discovery' else ''}

{f'''📊 QUALIFICATION STAGE - Gather remaining: {', '.join(conversation_analysis['pending_info'])}
- Acknowledge what they shared: "Entiendo que tu {extracted_data.get('business_type', 'negocio')} está {extracted_data.get('goal', 'enfrentando retos')}..."
- Ask for missing info naturally in context
- Show understanding: "{impact_stat}"''' if conversation_analysis['stage'] == 'qualification' else ''}

{f'''💡 VALUE BUILDING STAGE - Show ROI
- ALL info collected! Now show value: "{roi_message}"
- Be specific: "Para tu {extracted_data.get('business_type', 'negocio')}, esto significa..."
- Create urgency: "Esta semana implementamos 3 sistemas - quedan 2 espacios"''' if conversation_analysis['stage'] == 'value_building' else ''}

{f'''🎯 READY FOR DEMO - Close the appointment
- "Perfecto {extracted_data.get('name', '')}, con tu presupuesto de {extracted_data.get('budget', '')} podemos implementar {service_focus}"
- "¿Te funciona mañana a las 3pm o prefieres el jueves a las 11am?"''' if conversation_analysis['stage'] == 'ready_for_demo' else ''}

💬 PROBLEM-TO-DEMO FLOW:
- Customer problem → "{impact_stat}"
- Time concerns → "¿Cuánto vale tu hora? Nuestra solución te ahorra 20+ horas/semana"
- Always pivot to: "Te muestro exactamente cómo {service_focus} funciona para tu {extracted_data.get('business_type', 'negocio')}"

🚀 CONTEXT-SPECIFIC QUALIFYING QUESTIONS:
{chr(10).join(f'- "{q}"' for q in qualifying_questions)}

⚠️ ESCALATION RULES:
- Score 8+ with email → Escalate to Sofia for appointment
- Score < 5 → Escalate back to Maria
- Customer ready to book → Escalate to Sofia

Remember: Be SPECIFIC about {service_focus} benefits - don't be generic!"""
    
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
        escalate_to_router,
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
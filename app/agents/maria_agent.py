"""
Maria - Memory-Aware Customer Support Agent
Uses isolated memory context to prevent confusion
"""
from typing import Dict, Any, List, Union
from langchain_core.messages import AnyMessage, BaseMessage
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command
from app.tools.agent_tools import (
    get_contact_details_with_task,
    escalate_to_router,
    update_contact_with_context,
    save_important_context,
    track_lead_progress
)
from app.utils.simple_logger import get_logger
from app.config import get_settings
from app.utils.model_factory import create_openai_model
from app.agents.base_agent import (
    get_current_message,
    check_score_boundaries,
    extract_data_status,
    create_error_response,
    get_base_contact_info
)
from app.state.message_manager import MessageManager
from app.utils.langsmith_debug import debug_node, log_to_langsmith, debugger
from app.agents.message_fixer import fix_agent_messages
from app.utils.conversation_analyzer import analyze_conversation_state

logger = get_logger("maria")


def maria_memory_prompt(state: Dict[str, Any]) -> List[AnyMessage]:
    """
    Create Maria's prompt with ISOLATED memory context
    No more confusion from other agents or historical messages!
    """
    # Get context directly from state (memory manager removed)
    messages = state.get("messages", [])
    extracted_data = state.get("extracted_data", {})
    handoff_info = state.get("handoff_info")
    current_message = get_current_message(messages)
    
    # Log received extracted data
    if extracted_data:
        logger.info(f"Maria received extracted_data: {extracted_data}")
        if extracted_data.get('business_type'):
            logger.info(f"✅ Maria sees business_type: {extracted_data['business_type']}")
        if extracted_data.get('goal'):
            logger.info(f"✅ Maria sees goal: {extracted_data['goal']}")
    
    # Build Maria's view of the conversation
    context = "\\n📊 MARIA'S CONTEXT:\\n"
    
    # Analyze conversation history to understand where we are
    conversation_analysis = analyze_conversation_state(messages, agent_name="maria")
    
    context += f"\\n🔄 CONVERSATION STATUS: {conversation_analysis['status']}"
    context += f"\\n📍 CONVERSATION STAGE: {conversation_analysis['stage']}"
    context += f"\\n💬 EXCHANGES SO FAR: {conversation_analysis['exchange_count']}"
    
    # Show what we've already discussed
    if conversation_analysis['topics_discussed']:
        context += f"\\n✅ ALREADY DISCUSSED: {', '.join(conversation_analysis['topics_discussed'])}"
    
    # Show what we still need
    if conversation_analysis['pending_info']:
        context += f"\\n❓ STILL NEED: {', '.join(conversation_analysis['pending_info'])}"
    
    # Show handoff if receiving one
    if handoff_info:
        context += f"\\n🔄 HANDOFF: Received from {handoff_info['from_agent']}"
        context += f"\\n   Reason: {handoff_info['reason']}"
        context += "\\n"
    
    # Show what data we have
    context += "\\n📋 CUSTOMER DATA:"
    context += f"\\n- Name: {extracted_data.get('name', 'NOT PROVIDED')}"
    context += f"\\n- Business: {extracted_data.get('business_type', 'NOT PROVIDED')}"
    context += f"\\n- Problem: {extracted_data.get('goal', 'NOT PROVIDED')}"
    context += f"\\n- Budget: {extracted_data.get('budget', 'NOT PROVIDED')}"
    
    # Show current score
    lead_score = state.get("lead_score", 0)
    context += f"\\n\\n🎯 LEAD SCORE: {lead_score}/10"
    if lead_score >= 5:
        context += "\\n⚠️ Score is 5+, prepare to escalate to Carlos!"
    
    # Current message
    if current_message:
        context += f"\\n\\n💬 CUSTOMER JUST SAID: '{current_message}'"
        # Highlight if they just provided new business info
        if "restaurante" in current_message.lower() or "restaurant" in current_message.lower():
            context += "\\n🆕 NEW BUSINESS TYPE MENTIONED!"
    
    # Message count (to track context size)
    context += f"\\n\\n📊 Context size: {len(messages)} messages"
    
    # Get configurable business context
    settings = get_settings()
    
    # Adapt context if customer mentioned specific problem
    if settings.adapt_to_customer and current_message:
        current_lower = current_message.lower()
        
        # Restaurant/Food Service Context
        if any(word in current_lower for word in ['restaurante', 'restaurant', 'comida', 'food', 'cocina', 'mesa', 'comensal']):
            service_context = "soluciones de retención y engagement de clientes"
            problem_focus = "la pérdida de clientes"
            specific_solution = "sistema de seguimiento automatizado que te ayuda a mantener contacto con tus clientes, enviar promociones personalizadas y recordatorios de reservas"
            
        # Busy/Message Overload Context  
        elif any(word in current_lower for word in ['mensaje', 'ocupado', 'busy', 'whatsapp', 'responder', 'chat']):
            service_context = "automatización de WhatsApp"
            problem_focus = "el tiempo perdido respondiendo mensajes repetitivos"
            specific_solution = "sistema de WhatsApp automatizado que responde instantáneamente a consultas frecuentes, toma reservas y envía confirmaciones"
            
        # Retail/Sales Context
        elif any(word in current_lower for word in ['tienda', 'venta', 'producto', 'inventario', 'shop', 'store']):
            service_context = "automatización de ventas y atención al cliente"
            problem_focus = "la gestión manual de consultas de productos"
            specific_solution = "catálogo automatizado en WhatsApp donde los clientes pueden ver productos, precios y hacer pedidos 24/7"
            
        # Service Business Context
        elif any(word in current_lower for word in ['servicio', 'cita', 'appointment', 'consulta', 'agenda']):
            service_context = "gestión automatizada de citas"
            problem_focus = "la coordinación manual de citas"
            specific_solution = "sistema que permite a tus clientes agendar, confirmar y reprogramar citas automáticamente por WhatsApp"
            
        # Generic Business Context
        else:
            service_context = settings.service_description
            problem_focus = settings.target_problem
            specific_solution = "solución personalizada de automatización que se adapta a las necesidades específicas de tu negocio"
    else:
        service_context = settings.service_description
        problem_focus = settings.target_problem
        specific_solution = "sistema de automatización que mejora la comunicación con tus clientes"
    
    system_prompt = f"""You are Maria, a specialist for {settings.company_name}.

{context}

🎯 YOUR GOAL: Book a DEMO CALL by showing how our {service_context} solves their specific problem.

🔧 SPECIFIC SOLUTION FOR THIS CUSTOMER:
{specific_solution}

✅ DATA CHECK - Before asking, check what we already have:
- Name: {extracted_data.get('name', 'NOT PROVIDED')}
- Business: {extracted_data.get('business_type', 'NOT PROVIDED')}  
- Problem: {extracted_data.get('goal', 'NOT PROVIDED')}
- Budget: {extracted_data.get('budget', 'NOT PROVIDED')}

📋 CONVERSATION STRATEGY - STAGE: {conversation_analysis['stage'].upper()}

{f'DO NOT GREET - Already greeted' if conversation_analysis['has_greeted'] else 'START with warm greeting'}

🎯 CURRENT PRIORITY: {conversation_analysis['pending_info'][0].upper() if conversation_analysis['pending_info'] else 'ESCALATE TO CARLOS'}

📋 STEP-BY-STEP APPROACH:
1. NEVER ask for info already collected: {', '.join(conversation_analysis['topics_discussed']) if conversation_analysis['topics_discussed'] else 'nothing yet'}
2. ONE question at a time - be natural and conversational
3. Next info needed: {conversation_analysis['pending_info'][0] if conversation_analysis['pending_info'] else 'All collected!'}

{f'''🔍 DISCOVERY STAGE - Focus: {conversation_analysis['pending_info'][0] if conversation_analysis['pending_info'] else 'understanding'}
- If NAME missing: "Por cierto, ¿cuál es tu nombre?"
- If BUSINESS missing: "¿Qué tipo de negocio tienes?"
- If PROBLEM missing: "¿Cuál es el principal reto que enfrentas con tus clientes?"
- If BUDGET missing: "¿Qué presupuesto manejas para herramientas de marketing?"''' if conversation_analysis['stage'] == 'discovery' else ''}

{f'''📊 INITIAL QUALIFICATION - Acknowledge & Ask Next
- "Entiendo {extracted_data.get('name', '')}, tu {extracted_data.get('business_type', 'negocio')} necesita {extracted_data.get('goal', 'mejorar')}..."
- Ask for missing: {conversation_analysis['pending_info'][0] if conversation_analysis['pending_info'] else 'ready to escalate'}''' if conversation_analysis['stage'] == 'initial_qualification' else ''}

{f'''🚀 READY FOR HANDOFF - You have basics, escalate!
- "Perfecto {extracted_data.get('name', '')}, con lo que me compartes sobre tu {extracted_data.get('business_type', 'negocio')}..."
- "Te voy a conectar con Carlos, nuestro especialista en {service_context}"''' if conversation_analysis['stage'] == 'ready_for_handoff' else ''}

💬 CONTEXT-AWARE RESPONSES (Only AFTER getting basic info):
- If restaurant + losing customers → Acknowledge: "Entiendo, perder clientes es frustrante. ¿Cuántos clientes calculas que pierdes al mes?"
- If busy + messages → Relate: "Sí, responder mensajes consume mucho tiempo. ¿Cuántas horas al día dedicas a WhatsApp?"
- Always tie back to their specific situation

⚡ CRITICAL RULES:
- Lead score 0-4 only (5+ → escalate immediately)
- One strategic question at a time
- ALWAYS reference their specific problem and our specific solution
- Speak conversational Mexican Spanish
- Be ULTRA-SPECIFIC to their context, not generic
- If they provide new info (like business type), UPDATE your understanding

Remember: You have a SPECIFIC solution ({specific_solution}) for their EXACT problem ({problem_focus})!"""
    
    # Only include the current message to prevent duplication
    # create_react_agent returns all input messages plus its response
    # So we only pass the latest message to avoid exponential growth
    
    # BUT we need to show the conversation history in the system prompt
    # so the agent understands the context
    
    # Find the last customer message to process
    customer_message = None
    for msg in reversed(messages):
        # Check for HumanMessage that's from a customer (no name attribute)
        if hasattr(msg, '__class__') and 'Human' in msg.__class__.__name__:
            # Skip if it has a name (means it's from an agent/system)
            if not hasattr(msg, 'name') or not msg.name:
                customer_message = msg
                break
    
    # Build conversation history for context (excluding router messages)
    conversation_history = []
    for msg in messages:
        # Include customer messages (HumanMessage without name)
        if hasattr(msg, '__class__') and 'Human' in msg.__class__.__name__:
            if not hasattr(msg, 'name') or not msg.name:
                conversation_history.append(f"Cliente: {msg.content}")
        # Include agent responses (AIMessage with name that's not router)
        elif hasattr(msg, '__class__') and 'AI' in msg.__class__.__name__:
            if hasattr(msg, 'name') and msg.name and msg.name not in ['supervisor', 'smart_router']:
                conversation_history.append(f"{msg.name.title()}: {msg.content}")
    
    # Add conversation history to context
    history_context = ""
    if conversation_history:
        history_context = "\n\n💬 CONVERSATION HISTORY:"
        for msg in conversation_history[-5:]:  # Show last 5 exchanges
            history_context += f"\n{msg}"
    
    # Update system prompt with full context including conversation history
    system_prompt_with_history = system_prompt + history_context
    
    # Only pass the last customer message to avoid duplication
    filtered_messages = [customer_message] if customer_message else []
        
    return [{"role": "system", "content": system_prompt_with_history}] + filtered_messages


@debug_node("maria_agent")
async def maria_node(state: Dict[str, Any]) -> Union[Command, Dict[str, Any]]:
    """
    Maria agent node with memory isolation
    """
    try:
        logger.info("=== MARIA MEMORY-AWARE STARTING ===")
        
        # Check if Maria should handle this
        lead_score = state.get("lead_score", 0)
        boundary_check = check_score_boundaries(lead_score, 0, 4, "Maria", logger)
        if boundary_check:
            return boundary_check
        
        # Create agent with memory-aware prompt
        model = create_openai_model(temperature=0.0)
        tools = [
            get_contact_details_with_task,
            escalate_to_router,
            update_contact_with_context,
            save_important_context,
            track_lead_progress
        ]
        
        # Get memory-aware messages
        messages = maria_memory_prompt(state)
        
        # Create proper state for the agent
        agent_state = {
            "messages": messages,
            "remaining_steps": 10  # Required by create_react_agent
        }
        
        agent = create_react_agent(
            model=model,
            tools=tools,
            name="maria"
        )
        
        # Track how many messages we sent to the agent
        input_message_count = len(messages)
        
        # Invoke agent with proper state
        result = await agent.ainvoke(agent_state)
        
        # Only return new messages to avoid duplication
        current_messages = state.get("messages", [])
        result_messages = result.get("messages", [])
        
        # Extract only the NEW messages (those added after our input)
        if len(result_messages) > input_message_count:
            # Agent added new messages - take only those
            new_agent_messages = result_messages[input_message_count:]
        else:
            # Fallback - look for the last AI message
            new_agent_messages = []
            for msg in reversed(result_messages):
                if hasattr(msg, '__class__') and 'AI' in msg.__class__.__name__:
                    new_agent_messages = [msg]
                    break
        # Fix agent messages to have proper name
        if new_agent_messages:
            new_agent_messages = fix_agent_messages(new_agent_messages, "maria")
            logger.info(f"Fixed {len(new_agent_messages)} messages with agent name 'maria'")
        
        # Use MessageManager with only the new agent messages
        new_messages = MessageManager.set_messages(current_messages, new_agent_messages)
        
        logger.info("Maria completed successfully with isolated memory")
        
        # Return only new messages
        return {
            "messages": new_messages,
            "current_agent": "maria"
        }
        
    except Exception as e:
        logger.error(f"Error in Maria memory-aware: {str(e)}", exc_info=True)
        return create_error_response("maria", e, state)
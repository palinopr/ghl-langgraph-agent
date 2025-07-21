"""
Smart Responder Utility
Generates appropriate responses based on conversation state
"""
from typing import Dict, Any, Optional
from app.utils.simple_logger import get_logger

logger = get_logger("smart_responder")


def get_smart_response(state: Dict[str, Any], agent_name: str) -> Optional[str]:
    logger.info(f"Smart responder called for {agent_name}")
    """
    Generate an appropriate response based on conversation state
    
    Args:
        state: The workflow state
        agent_name: Name of the agent (maria, carlos, sofia)
        
    Returns:
        Suggested response or None to use default behavior
    """
    extracted_data = state.get("extracted_data", {})
    lead_score = state.get("lead_score", 0)
    
    # Get what we have
    has_name = bool(extracted_data.get("name"))
    has_business = bool(extracted_data.get("business_type") and 
                       extracted_data["business_type"] != "NO_MENCIONADO")
    has_budget = bool(extracted_data.get("budget"))
    
    # Check if we have appointment slots in state
    available_slots = state.get("available_slots") or []
    if agent_name == "sofia":
        logger.info(f"Available slots in state: {len(available_slots)}")
    
    # Get the incoming message from webhook data (the actual new message)
    webhook_data = state.get("webhook_data", {})
    incoming_message = webhook_data.get("message", "").lower() if webhook_data else ""
    
    # Get the incoming message from webhook data (the actual new message)
    webhook_data = state.get("webhook_data", {})
    incoming_message = webhook_data.get("message", "").lower() if webhook_data else ""
    
    # Use incoming message if available, otherwise get from messages
    last_message = incoming_message if incoming_message else ""
    if not last_message:
        messages = state.get("messages", [])
        for msg in reversed(messages):
            # Handle both LangChain messages and dict format
            if hasattr(msg, '__class__') and msg.__class__.__name__ == 'HumanMessage':
                last_message = msg.content.lower()
                break
            elif isinstance(msg, dict) and msg.get('role') == 'user':
                last_message = msg.get('content', '').lower()
                break
    
    # Get the last AI message from history
    messages = state.get("messages", [])
    last_ai_message = ""
    
    logger.info(f"Total messages in state: {len(messages)}")
    
    # Debug: show AI messages with appointment keywords
    ai_messages_with_appointment = []
    for msg in messages:
        content = ""
        if hasattr(msg, '__class__') and msg.__class__.__name__ == 'AIMessage':
            content = msg.content if hasattr(msg, 'content') else ""
        elif isinstance(msg, dict) and msg.get('role') == 'assistant':
            content = msg.get('content', '')
        
        if content and ('agendar' in content.lower() or 'llamada' in content.lower()):
            ai_messages_with_appointment.append(content[:100])
    
    if ai_messages_with_appointment:
        logger.info(f"Found {len(ai_messages_with_appointment)} AI messages with appointment keywords:")
        for i, msg in enumerate(ai_messages_with_appointment[-2:]):  # Last 2
            logger.info(f"  Appointment msg {i}: '{msg}...'")
    
    # Find the last non-internal AI message
    # Look for the most recent AI message that contains appointment keywords if customer said yes
    if last_message in ["sí", "si", "claro", "ok", "perfecto", "dale", "yes"]:
        # Customer is confirming, so look for appointment question
        for i, msg in enumerate(reversed(messages)):
            content = ""
            if hasattr(msg, '__class__') and msg.__class__.__name__ == 'AIMessage':
                content = msg.content if hasattr(msg, 'content') else ""
            elif isinstance(msg, dict) and msg.get('role') == 'assistant':
                content = msg.get('content', '')
            
            if content and ('agendar' in content.lower() or 'llamada' in content.lower()):
                last_ai_message = content.lower()
                logger.info(f"Found appointment question: '{last_ai_message[:50]}...'")
                break
    else:
        # Normal flow - find most recent AI message
        for msg in reversed(messages):
            # Handle both LangChain messages and dict format
            if hasattr(msg, '__class__') and msg.__class__.__name__ == 'AIMessage':
                content = msg.content.lower() if hasattr(msg, 'content') else ""
                # Skip internal system messages
                if (not content.startswith('\nsupervisor analysis') and 
                    not content.startswith('\ndata loaded') and
                    not content.startswith('receptionist summary') and
                    not 'analysis complete' in content and
                    not 'routing to:' in content.lower()):
                    last_ai_message = content
                    logger.info(f"Found AIMessage: '{last_ai_message[:50]}...'")
                    break
                else:
                    logger.info(f"Skipping internal message: '{content[:30]}...'")
            elif isinstance(msg, dict) and msg.get('role') == 'assistant':
                content = msg.get('content', '').lower()
                # Skip internal system messages
                if (not content.startswith('\nsupervisor analysis') and 
                    not content.startswith('\ndata loaded') and
                    not content.startswith('receptionist summary') and
                    not 'analysis complete' in content and
                    not 'routing to:' in content.lower()):
                    last_ai_message = content
                    logger.info(f"Found dict assistant message: '{last_ai_message[:50]}...'")
                    break
    
    # EARLY CHECK: Customer selecting appointment time
    # Check if customer is responding with a time selection - let Sofia handle it
    if agent_name == "sofia":
        # Common time patterns
        time_indicators = ["am", "pm", "10:", "2:", "4:", "primera", "segunda", "tercera", 
                          "mañana a las", "tarde", ":00"]
        
        # Also check if the last AI message offered appointment times
        offered_appointment = False
        if ("horarios disponibles" in last_ai_message or 
            "10:00 am" in last_ai_message or
            "11am" in last_ai_message or 
            "2pm" in last_ai_message or
            "¡excelente! tengo estos horarios" in last_ai_message or
            "cuál prefieres" in last_ai_message or
            "tengo disponibilidad" in last_ai_message):
            offered_appointment = True
            logger.info("Last AI message offered appointment times")
        
        if offered_appointment and any(indicator in last_message.lower() for indicator in time_indicators):
            logger.info(f"Detected appointment time selection: '{last_message}'")
            # Don't intercept - let Sofia use her appointment booking tool
            return None
    
    # Greeting response
    if last_message in ["hola", "hi", "hello", "buenos días", "buenas tardes"]:
        if not has_name:
            return "¡Hola! 👋 Ayudo a las empresas a automatizar WhatsApp para captar más clientes. ¿Cuál es tu nombre?"
        else:
            name = extracted_data.get("name", "")
            if agent_name == "sofia" and has_business and has_budget:
                return f"¡Hola {name}! Veo que tienes un {extracted_data['business_type']} y tu presupuesto está dentro de nuestro rango. ¿Te gustaría agendar una llamada para ver cómo podemos ayudarte?"
            elif agent_name == "carlos" and has_business:
                return f"¡Hola {name}! Me da gusto seguir nuestra conversación. Con tu {extracted_data['business_type']}, ¿cuál es tu mayor reto con los mensajes de WhatsApp?"
            else:
                return f"¡Hola {name}! ¿Qué tipo de negocio tienes?"
    
    # Name response
    if not has_name and last_message and len(last_message.split()) <= 2:
        # Likely a name
        return f"Mucho gusto, {last_message.title()}. ¿Qué tipo de negocio tienes?"
    
    # Business type response
    if has_name and not has_business and ("restaurante" in last_message or "restaurant" in last_message or 
                                          "tienda" in last_message or "negocio" in last_message):
        name = extracted_data.get("name", "")
        return f"Excelente {name}! ¿Cuál es tu mayor desafío con los mensajes de WhatsApp en tu negocio?"
    
    # Budget response  
    if has_business and not has_budget and "$" in last_message:
        if agent_name == "sofia":
            return "Perfecto! Ese presupuesto está dentro de nuestro rango. ¿Te gustaría agendar una llamada de 15 minutos para mostrarte cómo funciona?"
        else:
            return "Excelente! Con ese presupuesto podemos hacer mucho. Déjame pasarte con Sofia para agendar una demostración."
    
    # FIRST CHECK: Appointment confirmation response (higher priority)
    if last_message in ["sí", "si", "claro", "ok", "perfecto", "dale", "yes"]:
        logger.info(f"Detected confirmation: '{last_message}'")
        logger.info(f"Last AI message: '{last_ai_message[:100]}...'")
        logger.info(f"Contains 'agendar': {'agendar' in last_ai_message}")
        logger.info(f"Contains 'llamada': {'llamada' in last_ai_message}")
        
        # Check if we asked about appointment in the last AI message
        if "agendar" in last_ai_message or "llamada" in last_ai_message:
            if agent_name == "sofia":
                logger.info("Returning appointment slots response")
                response = "¡Excelente! Tengo estos horarios disponibles:\n\n📅 Mañana:\n• 10:00 AM\n• 2:00 PM\n• 4:00 PM\n\n¿Cuál prefieres?"
                logger.info("NOTE: Sofia should save available_slots to state when offering times")
                return response
    
    # SECOND CHECK: Hot lead ready for appointment (but not already asked)
    if agent_name == "sofia" and lead_score >= 8 and has_name and has_business and has_budget:
        # Don't ask about appointment if we just got confirmation
        if last_message not in ["sí", "si", "claro", "ok", "perfecto", "dale", "yes"]:
            if "agendar" not in last_ai_message:  # Don't repeat if already asked
                name = extracted_data.get("name", "")
                return f"{name}, con tu {extracted_data['business_type']} y presupuesto de {extracted_data['budget']}, podemos ayudarte a automatizar WhatsApp. ¿Te gustaría agendar una llamada de 15 minutos?"
    
    return None  # Use default agent behavior
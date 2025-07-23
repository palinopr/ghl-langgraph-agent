"""
Shared conversation analysis utilities for all agents
"""
from typing import Dict, Any, List
from langchain_core.messages import BaseMessage
from app.utils.simple_logger import get_logger

logger = get_logger("conversation_analyzer")


def analyze_conversation_state(messages: List[BaseMessage], agent_name: str = None) -> Dict[str, Any]:
    """
    Analyze conversation history to understand:
    - Where we are in the conversation flow
    - What has been discussed
    - What still needs to be covered
    
    Args:
        messages: List of conversation messages
        agent_name: Optional agent name to check for agent-specific greetings
    """
    analysis = {
        "status": "NEW",
        "stage": "initial_contact",
        "exchange_count": 0,
        "has_greeted": False,
        "topics_discussed": [],
        "pending_info": ["name", "business_type", "specific_problem", "email"],
        "customer_messages": [],
        "agent_messages": [],
        "last_customer_message": "",
        "objections_raised": [],
        "demo_attempts": 0,
        "questions_asked": []
    }
    
    # Separate messages by type
    for msg in messages:
        content_lower = str(msg.content).lower()
        
        # Track customer messages
        if hasattr(msg, '__class__') and 'Human' in msg.__class__.__name__:
            if not hasattr(msg, 'name') or not msg.name:  # Real customer message
                analysis["customer_messages"].append(content_lower)
                analysis["exchange_count"] += 1
                analysis["last_customer_message"] = content_lower
                
                # Track questions asked by customer
                if '?' in msg.content:
                    analysis["questions_asked"].append(msg.content)
        
        # Track agent messages (any AI message)
        elif hasattr(msg, '__class__') and 'AI' in msg.__class__.__name__:
            analysis["agent_messages"].append(content_lower)
            
            # Check if we've greeted
            greetings = ['hola', 'buenos días', 'buenas tardes', 'bienvenido', 'mucho gusto', 'encantado']
            if any(greeting in content_lower for greeting in greetings):
                analysis["has_greeted"] = True
            
            # Check for demo booking attempts
            demo_keywords = ['demo', 'demostración', 'mostrar', 'agendar', 'cita', 'reunión']
            if any(keyword in content_lower for keyword in demo_keywords):
                analysis["demo_attempts"] += 1
    
    # Determine conversation status
    if analysis["exchange_count"] == 0:
        analysis["status"] = "NEW - First contact"
    elif analysis["exchange_count"] == 1 and not analysis["has_greeted"]:
        analysis["status"] = "NEW - Need to greet"
    elif analysis["has_greeted"]:
        analysis["status"] = "ONGOING - Skip greeting"
    else:
        analysis["status"] = "ONGOING - Continue conversation"
    
    # Analyze what's been discussed
    all_content = " ".join(analysis["customer_messages"] + analysis["agent_messages"])
    
    # Check for business type mentions
    business_keywords = {
        'restaurante': ['restaurante', 'restaurant', 'comida', 'cocina', 'chef', 'mesa', 'comensal'],
        'tienda': ['tienda', 'store', 'venta', 'producto', 'inventario', 'shop'],
        'clínica': ['clínica', 'clinic', 'dentista', 'doctor', 'médico', 'salud', 'hospital', 'paciente'],
        'servicio': ['servicio', 'service', 'consultoría', 'agencia', 'asesor']
    }
    
    for business_type, keywords in business_keywords.items():
        if any(word in all_content for word in keywords):
            analysis["topics_discussed"].append("business_type")
            if "business_type" in analysis["pending_info"]:
                analysis["pending_info"].remove("business_type")
            break
    
    # Check for problem mentions
    problem_phrases = [
        'perdiendo cliente', 'no vend', 'mensaje', 'cita', 
        'no puedo responder', 'ocupado', 'no tengo tiempo',
        'necesito más', 'problema', 'difícil', 'complicado'
    ]
    if any(phrase in all_content for phrase in problem_phrases):
        analysis["topics_discussed"].append("specific_problem")
        if "specific_problem" in analysis["pending_info"]:
            analysis["pending_info"].remove("specific_problem")
    
    # Check for contact info
    if '@' in all_content or any(phrase in all_content for phrase in ['correo', 'email', 'mail']):
        analysis["topics_discussed"].append("email")
        if "email" in analysis["pending_info"]:
            analysis["pending_info"].remove("email")
    
    # Check for name
    name_phrases = ['me llamo', 'mi nombre', 'soy', 'mucho gusto']
    if any(phrase in all_content for phrase in name_phrases):
        analysis["topics_discussed"].append("name")
        if "name" in analysis["pending_info"]:
            analysis["pending_info"].remove("name")
    
    # Check for budget discussions
    budget_keywords = ['presupuesto', 'precio', 'costo', 'inversión', 'pagar', 'budget']
    if any(keyword in all_content for keyword in budget_keywords):
        analysis["topics_discussed"].append("budget")
    
    # Check for objections
    objection_phrases = [
        'no creo', 'no necesito', 'ya tengo', 'muy caro', 
        'no me interesa', 'no gracias', 'otro momento',
        'tengo que pensarlo', 'consultarlo'
    ]
    for phrase in objection_phrases:
        if phrase in all_content:
            analysis["objections_raised"].append(phrase)
    
    # Determine conversation stage based on agent
    if agent_name == "maria":
        # Maria stages: discovery → qualification → handoff
        if len(analysis["topics_discussed"]) == 0:
            analysis["stage"] = "discovery"
        elif len(analysis["topics_discussed"]) >= 2:
            analysis["stage"] = "ready_for_handoff"
        else:
            analysis["stage"] = "initial_qualification"
    
    elif agent_name == "carlos":
        # Carlos stages: qualification → value_building → demo_push
        if "specific_problem" not in analysis["topics_discussed"]:
            analysis["stage"] = "problem_discovery"
        elif analysis["demo_attempts"] == 0:
            analysis["stage"] = "value_building"
        elif analysis["demo_attempts"] >= 1 and analysis["objections_raised"]:
            analysis["stage"] = "objection_handling"
        else:
            analysis["stage"] = "demo_closing"
    
    elif agent_name == "sofia":
        # Sofia stages: demo_scheduling → confirmation → followup
        if "email" not in analysis["topics_discussed"]:
            analysis["stage"] = "contact_collection"
        elif analysis["demo_attempts"] == 0:
            analysis["stage"] = "demo_scheduling"
        else:
            analysis["stage"] = "confirmation"
    
    else:
        # Generic stages
        if len(analysis["topics_discussed"]) == 0:
            analysis["stage"] = "discovery"
        elif "specific_problem" in analysis["topics_discussed"] and "business_type" in analysis["topics_discussed"]:
            analysis["stage"] = "solution_presentation"
        elif len(analysis["topics_discussed"]) >= 3:
            analysis["stage"] = "closing"
        else:
            analysis["stage"] = "qualification"
    
    # Log analysis for debugging
    logger.info(f"Conversation Analysis for {agent_name or 'agent'}: "
                f"Stage={analysis['stage']}, Exchanges={analysis['exchange_count']}, "
                f"Greeted={analysis['has_greeted']}, Demo attempts={analysis['demo_attempts']}")
    
    return analysis
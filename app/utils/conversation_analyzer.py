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
        "pending_info": ["name", "business_type", "specific_problem", "budget", "email"],
        "customer_messages": [],
        "agent_messages": [],
        "last_customer_message": "",
        "objections_raised": [],
        "demo_attempts": 0,
        "questions_asked": []
    }
    
    # Separate messages by type
    for msg in messages:
        # Handle both dict and BaseMessage objects
        if isinstance(msg, dict):
            content = msg.get('content', '')
            msg_type = msg.get('type', '')
            msg_name = msg.get('name')
        else:
            content = getattr(msg, 'content', '')
            msg_type = msg.__class__.__name__ if hasattr(msg, '__class__') else ''
            msg_name = getattr(msg, 'name', None)
        
        content_lower = str(content).lower()
        
        # Track customer messages
        if 'Human' in msg_type or msg_type == 'human':
            if not msg_name:  # Real customer message
                analysis["customer_messages"].append(content_lower)
                analysis["exchange_count"] += 1
                analysis["last_customer_message"] = content_lower
                
                # Track questions asked by customer
                if '?' in content:
                    analysis["questions_asked"].append(content)
        
        # Track agent messages (any AI message)
        elif 'AI' in msg_type or msg_type == 'ai':
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
    name_found = False
    
    # Direct name phrases
    if any(phrase in all_content for phrase in name_phrases):
        name_found = True
    
    # Check if AI asked for name and human responded with potential name
    if not name_found and len(analysis["agent_messages"]) > 0 and len(analysis["customer_messages"]) > 0:
        # Check if last AI message asked for name
        last_ai = analysis["agent_messages"][-1] if analysis["agent_messages"] else ""
        name_questions = ['tu nombre', 'cómo te llamas', 'cuál es tu nombre', 'your name', 'como te llamas']
        
        if any(question in last_ai for question in name_questions):
            # Check if last customer message could be a name (1-3 words, capitalized)
            last_customer = analysis["last_customer_message"].strip()
            words = last_customer.split()
            
            # Simple heuristic: 1-3 words, starts with capital letter (in original case)
            if 1 <= len(words) <= 3 and len(last_customer) > 1:
                # Get original message to check capitalization
                for msg in reversed(messages):
                    if (isinstance(msg, dict) and msg.get('type') == 'human') or \
                       (hasattr(msg, '__class__') and 'Human' in msg.__class__.__name__):
                        original_content = msg.get('content', '') if isinstance(msg, dict) else getattr(msg, 'content', '')
                        if original_content.strip() and original_content[0].isupper():
                            name_found = True
                            break
                        break
    
    if name_found:
        analysis["topics_discussed"].append("name")
        if "name" in analysis["pending_info"]:
            analysis["pending_info"].remove("name")
    
    # Check for budget discussions
    budget_keywords = ['presupuesto', 'precio', 'costo', 'inversión', 'pagar', 'budget', '$', 'dollar', 'peso']
    if any(keyword in all_content for keyword in budget_keywords):
        analysis["topics_discussed"].append("budget")
        if "budget" in analysis["pending_info"]:
            analysis["pending_info"].remove("budget")
    
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
        # Maria needs at least name, business_type, and specific_problem before handoff
        required_for_handoff = ["name", "business_type", "specific_problem"]
        collected = [info for info in required_for_handoff if info in analysis["topics_discussed"]]
        
        if len(collected) == 0:
            analysis["stage"] = "discovery"
        elif len(collected) < 3:
            analysis["stage"] = "initial_qualification"
        else:
            analysis["stage"] = "ready_for_handoff"
    
    elif agent_name == "carlos":
        # Carlos stages: qualification → value_building → demo_push
        # Carlos needs ALL info before moving to demo
        required_info = ["name", "business_type", "specific_problem", "budget"]
        collected_info = [info for info in required_info if info in analysis["topics_discussed"]]
        
        if len(collected_info) < 2:
            analysis["stage"] = "discovery"
        elif len(collected_info) < 4:
            analysis["stage"] = "qualification"
        elif len(collected_info) == 4 and analysis["demo_attempts"] == 0:
            analysis["stage"] = "value_building"
        elif analysis["objections_raised"]:
            analysis["stage"] = "objection_handling"
        elif analysis["demo_attempts"] >= 1:
            analysis["stage"] = "demo_closing"
        else:
            analysis["stage"] = "ready_for_demo"
    
    elif agent_name == "sofia":
        # Sofia stages: should only work when we have all info
        required_info = ["name", "business_type", "specific_problem", "budget"]
        collected_info = [info for info in required_info if info in analysis["topics_discussed"]]
        
        if len(collected_info) < 4:
            analysis["stage"] = "too_early_need_qualification"
        elif "email" not in analysis["topics_discussed"]:
            analysis["stage"] = "email_collection"
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
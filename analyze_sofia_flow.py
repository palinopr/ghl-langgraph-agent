#!/usr/bin/env python3
"""
Analyze Sofia's behavior when customer selects appointment time
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock the langsmith module
class MockClient:
    pass

sys.modules['langsmith'] = type(sys)('langsmith')
sys.modules['langsmith'].Client = MockClient

from app.utils.conversation_enforcer import ConversationEnforcer
from app.utils.smart_responder import get_smart_response
from langchain_core.messages import HumanMessage, AIMessage

def analyze_appointment_selection():
    """Analyze what happens when customer selects appointment time"""
    
    print("🔍 ANALYZING APPOINTMENT SELECTION FLOW")
    print("="*60)
    
    # Create test state with conversation history
    state = {
        "messages": [
            AIMessage(content="¡Hola! 👋 Ayudo a las empresas a automatizar WhatsApp para captar más clientes. ¿Cuál es tu nombre?"),
            HumanMessage(content="Jaime"),
            AIMessage(content="Mucho gusto, Jaime. ¿Qué tipo de negocio tienes?"),
            HumanMessage(content="Restaurante"),
            AIMessage(content="Ya veo, restaurante. ¿Cuál es tu mayor desafío con los mensajes de WhatsApp?"),
            HumanMessage(content="No respondo rápido"),
            AIMessage(content="Definitivamente puedo ayudarte con eso. Mis soluciones empiezan en $300/mes. ¿Te funciona ese presupuesto?"),
            HumanMessage(content="Sí"),
            AIMessage(content="¡Perfecto! Para coordinar nuestra videollamada, ¿cuál es tu correo electrónico?"),
            HumanMessage(content="jaime@restaurant.com"),
            AIMessage(content="¡Excelente! Tengo estos horarios disponibles:\\n\\n📅 Mañana:\\n• 10:00 AM\\n• 2:00 PM\\n• 4:00 PM\\n\\n¿Cuál prefieres?"),
        ],
        "webhook_data": {
            "message": "10:00 AM"
        },
        "extracted_data": {
            "name": "Jaime",
            "business_type": "restaurante",
            "budget": "300+",
            "email": "jaime@restaurant.com"
        },
        "lead_score": 8,
        "available_slots": [
            {"startTime": "10:00 AM"},
            {"startTime": "2:00 PM"},
            {"startTime": "4:00 PM"}
        ]
    }
    
    # Add the customer's time selection
    state["messages"].append(HumanMessage(content="10:00 AM"))
    
    print("📊 CONVERSATION STATE:")
    print(f"  - Name: {state['extracted_data']['name']}")
    print(f"  - Business: {state['extracted_data']['business_type']}")
    print(f"  - Budget: {state['extracted_data']['budget']}")
    print(f"  - Email: {state['extracted_data']['email']}")
    print(f"  - Lead Score: {state['lead_score']}")
    print(f"  - Available Slots: {len(state['available_slots'])}")
    print(f"  - Customer Selection: '10:00 AM'")
    print()
    
    # Test conversation enforcer
    print("1️⃣ CONVERSATION ENFORCER ANALYSIS:")
    enforcer = ConversationEnforcer()
    analysis = enforcer.analyze_conversation(state["messages"])
    print(f"  - Current Stage: {analysis['current_stage'].value}")
    print(f"  - Next Action: {analysis['next_action']}")
    print(f"  - Allowed Response: '{analysis['allowed_response']}'")
    print()
    
    # Test smart responder
    print("2️⃣ SMART RESPONDER ANALYSIS:")
    smart_response = get_smart_response(state, "sofia")
    print(f"  - Smart Response: {smart_response}")
    print()
    
    # Determine what Sofia should do
    print("3️⃣ EXPECTED BEHAVIOR:")
    if analysis['allowed_response'] == "USE_APPOINTMENT_TOOL":
        print("  ✅ Conversation enforcer says: USE APPOINTMENT TOOL")
    else:
        print("  ❌ Conversation enforcer says: Use template response")
        
    if smart_response is None:
        print("  ✅ Smart responder says: Let Sofia use her tools")
    else:
        print("  ❌ Smart responder says: Use this response")
    
    print()
    print("4️⃣ FINAL DECISION:")
    if analysis['allowed_response'] == "USE_APPOINTMENT_TOOL" or smart_response is None:
        print("  ✅ Sofia should use book_appointment_from_confirmation tool")
        print("  Expected: Appointment booked confirmation message")
    else:
        print("  ❌ Sofia will use enforced response or smart response")
        print("  Problem: Appointment won't be booked")

if __name__ == "__main__":
    analyze_appointment_selection()
#!/usr/bin/env python3
"""
Debug Sofia's state when receiving appointment time selection
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

# Test data
from langchain_core.messages import HumanMessage, AIMessage

messages = [
    HumanMessage(content="Hola"),
    AIMessage(content="¡Hola! Soy Sofia de Main Outlet Media. Ayudo a negocios a automatizar WhatsApp. ¿Cuál es tu nombre?"),
    HumanMessage(content="Diego"),
    AIMessage(content="Mucho gusto, Diego. ¿Qué tipo de negocio tienes?"),
    HumanMessage(content="Restaurante"),
    AIMessage(content="Excelente Diego! ¿Qué es lo que más tiempo te quita en tu restaurante?"),
    HumanMessage(content="Necesito automatizar las reservas"),
    AIMessage(content="Diego, mis servicios empiezan en $300/mes. ¿Te funciona ese presupuesto?"),
    HumanMessage(content="Sí, perfecto"),
    AIMessage(content="¡Genial Diego! Para mostrarte cómo funciona, necesito tu email para enviarte el enlace."),
    HumanMessage(content="diego@restaurant.com"),
    AIMessage(content="¡Excelente! Tengo estos horarios disponibles:\n\n📅 Martes:\n• 10:00 AM\n• 2:00 PM\n\n📅 Miércoles:\n• 11:00 AM\n• 4:00 PM\n\n¿Cuál prefieres?"),
    HumanMessage(content="El martes a las 2pm está perfecto")
]

# Check conversation analysis
from app.utils.conversation_enforcer import get_conversation_analysis

analysis = get_conversation_analysis(messages)

print("="*60)
print("CONVERSATION ANALYSIS")
print("="*60)
print(f"Current Stage: {analysis['current_stage'].value}")
print(f"Next Action: {analysis['next_action']}")
print(f"Allowed Response: {analysis['allowed_response']}")
print(f"\nCollected Data:")
for key, value in analysis['collected_data'].items():
    print(f"  - {key}: {value}")

# Check what Sofia's prompt would be
from app.agents.sofia_agent_v2 import sofia_prompt, SofiaState

state = SofiaState(
    messages=messages,
    contact_id="Emp7UWc546yDMiWVEzKF",
    contact_name="Diego",
    extracted_data={
        "name": "Diego",
        "business_type": "restaurante",
        "email": "diego@restaurant.com",
        "budget": "300+/month"
    }
)

prompt_messages = sofia_prompt(state)

# Find system message
for msg in prompt_messages:
    if isinstance(msg, dict) and msg.get("role") == "system":
        system_prompt = msg.get("content", "")
        
        # Check key parts
        print("\n" + "="*60)
        print("SOFIA PROMPT ANALYSIS")
        print("="*60)
        
        # Check if time selection is detected
        if "SELECTING AN APPOINTMENT TIME!" in system_prompt:
            print("✅ Detected: Customer is SELECTING AN APPOINTMENT TIME!")
        else:
            print("❌ NOT detected as time selection")
            
        # Check instruction
        if "USE book_appointment_simple TOOL IMMEDIATELY" in system_prompt:
            print("✅ Instruction: USE book_appointment_simple TOOL IMMEDIATELY")
            
            # Extract the full instruction
            start = system_prompt.find("USE book_appointment_simple")
            end = system_prompt.find('"', start + 50) if start > -1 else -1
            if start > -1 and end > start:
                instruction = system_prompt[start:end]
                print(f"\n📝 Full instruction:\n{instruction}")
        else:
            print("❌ No book_appointment_simple instruction found")
            
        # Check conversation stage info
        if "Current Stage:" in system_prompt:
            start = system_prompt.find("Current Stage:")
            end = system_prompt.find("\n", start)
            if start > -1 and end > start:
                stage_line = system_prompt[start:end]
                print(f"\n📊 {stage_line}")
                
        break

print("\n" + "="*60)
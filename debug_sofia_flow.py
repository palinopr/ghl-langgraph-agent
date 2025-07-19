#!/usr/bin/env python3
"""
Debug Sofia's flow to see what's happening
"""
from app.utils.conversation_enforcer import get_conversation_analysis
from langchain_core.messages import HumanMessage, AIMessage

# Mock conversation
messages = [
    AIMessage(content="Hi! 👋 I help businesses automate WhatsApp to capture more clients. What's your name?"),
    HumanMessage(content="Diego"),
    AIMessage(content="Diego, con tu restaurante y presupuesto de 500, podemos ayudarte a automatizar WhatsApp. ¿Te gustaría agendar una llamada de 15 minutos?"),
    HumanMessage(content="Sí, perfecto. ¿Qué horarios tienen disponibles?")
]

# Analyze
analysis = get_conversation_analysis(messages)

print("Conversation Analysis:")
print(f"Current Stage: {analysis['current_stage'].value}")
print(f"Next Action: {analysis['next_action']}")
print(f"Allowed Response: {analysis['allowed_response']}")
print(f"Collected Data: {analysis['collected_data']}")

# Check specific conditions
last_msg = messages[-1].content.lower()
print(f"\nLast message: '{last_msg}'")
print(f"Contains 'horarios': {'horarios' in last_msg}")
print(f"Contains 'disponibles': {'disponibles' in last_msg}")

# Test what Sofia should do
if "horarios" in last_msg or "disponibles" in last_msg:
    print("\n✅ Customer is asking for appointment times!")
    print("Sofia should use: check_calendar_availability tool")
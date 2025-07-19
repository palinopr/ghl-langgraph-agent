#!/usr/bin/env python3
"""
Debug smart responder logic
"""
from app.utils.smart_responder import get_smart_response

# Create test state similar to what we'd see after "Sí" response
test_state = {
    "webhook_data": {
        "message": "Sí"
    },
    "messages": [
        # Previous messages
        type('HumanMessage', (), {'content': 'Hola', '__class__': type('cls', (), {'__name__': 'HumanMessage'})})(),
        type('AIMessage', (), {'content': '¡Hola Jaime! Veo que tienes un restaurante y tu presupuesto está dentro de nuestro rango. ¿Te gustaría agendar una llamada para ver cómo podemos ayudarte?', '__class__': type('cls', (), {'__name__': 'AIMessage'})})(),
        type('HumanMessage', (), {'content': 'Sí', '__class__': type('cls', (), {'__name__': 'HumanMessage'})})(),
    ],
    "extracted_data": {
        "name": "Jaime",
        "business_type": "restaurante",
        "budget": "300+/month"
    },
    "lead_score": 23
}

# Test the smart responder
response = get_smart_response(test_state, "sofia")
print(f"Smart Response: {response}")

# Debug the conditions
webhook_msg = test_state["webhook_data"]["message"].lower()
print(f"\nWebhook message: '{webhook_msg}'")

# Check AI message
for msg in reversed(test_state["messages"]):
    if hasattr(msg, '__class__') and msg.__class__.__name__ == 'AIMessage':
        ai_content = msg.content.lower()
        print(f"Last AI message: '{ai_content[:100]}...'")
        print(f"Contains 'agendar': {'agendar' in ai_content}")
        break

print(f"\nShould trigger appointment slots: {webhook_msg in ['sí', 'si'] and 'agendar' in ai_content}")
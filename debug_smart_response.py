#!/usr/bin/env python3
"""
Debug why smart response isn't working
"""
from app.utils.smart_responder import get_smart_response

# Create state similar to what Sofia receives
test_state = {
    # From webhook
    "webhook_data": {
        "message": "Sí"
    },
    # From receptionist/supervisor
    "extracted_data": {
        "name": "Jaime",
        "business_type": "restaurante",
        "budget": "300+/month"
    },
    "lead_score": 27,
    "contact_id": "z49hFQn0DxOX5sInJg60",
    # Messages with proper LangChain format
    "messages": [
        # Previous messages loaded by receptionist
        {"role": "user", "content": "Hola"},
        {"role": "assistant", "content": "¡Hola! 👋 Ayudo a las empresas a automatizar WhatsApp para captar más clientes. ¿Cuál es tu nombre?"},
        {"role": "user", "content": "Jaime"},
        {"role": "assistant", "content": "Mucho gusto, Jaime. ¿Qué tipo de negocio tienes?"},
        {"role": "user", "content": "tengo un restaurante"},
        {"role": "assistant", "content": "Excelente Jaime! ¿Cuál es tu mayor desafío con los mensajes de WhatsApp en tu negocio?"},
        {"role": "user", "content": "pues como responder rapido"},
        {"role": "assistant", "content": "Entiendo perfectamente, Jaime. Responder rápido a todos los mensajes puede ser agotador.\n\n¿Aproximadamente cuánto estarías dispuesto a invertir mensualmente en una solución que responda automáticamente y nunca pierda un cliente? 💰"},
        {"role": "user", "content": "como unos $300"},
        {"role": "assistant", "content": "¡Hola Jaime! Veo que tienes un restaurante y tu presupuesto está dentro de nuestro rango. ¿Te gustaría agendar una llamada para ver cómo podemos ayudarte?"},
        {"role": "user", "content": "Sí"}
    ]
}

# Test the smart responder
print("Testing smart responder with state similar to Sofia's...")
print(f"\nState summary:")
print(f"- Name: {test_state['extracted_data']['name']}")
print(f"- Business: {test_state['extracted_data']['business_type']}")
print(f"- Budget: {test_state['extracted_data']['budget']}")
print(f"- Lead Score: {test_state['lead_score']}")
print(f"- Last message: {test_state['webhook_data']['message']}")

response = get_smart_response(test_state, "sofia")
print(f"\nSmart Response: {response}")

# Debug the message format issue
print("\nChecking message formats:")
for i, msg in enumerate(test_state['messages']):
    print(f"Message {i}: type={type(msg)}, content='{msg.get('content', '')[:50]}...'")
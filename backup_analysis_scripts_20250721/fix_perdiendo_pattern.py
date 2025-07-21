#!/usr/bin/env python3
"""
Fix to handle "perdiendo restaurantes" and similar patterns
"""

def enhanced_business_extraction(message):
    """
    Enhanced extraction that handles:
    1. Plural forms (restaurantes)
    2. Negative contexts (perdiendo, cerrando)
    3. Partial matches
    """
    
    # Base business words (singular)
    business_base_words = {
        "restaurante": ["restaurante", "restaurantes", "restaurant", "restaurants"],
        "tienda": ["tienda", "tiendas"],
        "salon": ["salon", "salón", "salones"],
        "barberia": ["barbería", "barberia", "barberías", "barberias"],
        "clinica": ["clinica", "clínica", "clinicas", "clínicas"],
        "consultorio": ["consultorio", "consultorios"],
        "agencia": ["agencia", "agencias"],
        "hotel": ["hotel", "hoteles"],
        "gym": ["gym", "gimnasio", "gyms", "gimnasios"],
        "spa": ["spa", "spas"],
        "cafe": ["café", "cafe", "cafés", "cafes"],
        "pizzeria": ["pizzería", "pizzeria", "pizzerías", "pizzerias"],
        "panaderia": ["panadería", "panaderia", "panaderías", "panaderias"],
        "farmacia": ["farmacia", "farmacias"],
        "negocio": ["negocio", "negocios"]
    }
    
    # Urgency indicators
    urgency_words = [
        "perdiendo", "perder", "pierdo", "cerrando", "cerrar",
        "problema", "ayuda", "urgente", "necesito", "fallando",
        "no puedo", "difícil", "complicado", "cayendo"
    ]
    
    message_lower = message.lower().strip()
    found_business = None
    found_urgency = False
    
    # Check all variations
    for base, variations in business_base_words.items():
        for variant in variations:
            if variant in message_lower:
                found_business = base
                break
        if found_business:
            break
    
    # Check urgency
    for urgency in urgency_words:
        if urgency in message_lower:
            found_urgency = True
            break
    
    return {
        "business_type": found_business,
        "has_urgency": found_urgency,
        "urgency_boost": 2 if found_urgency else 0
    }


# Test cases that should pass
test_cases = [
    ("Estoy perdiendo restaurantes", {"business_type": "restaurante", "has_urgency": True}),
    ("Tengo u. Restaurante", {"business_type": "restaurante", "has_urgency": False}),
    ("Mi restaurante está cerrando", {"business_type": "restaurante", "has_urgency": True}),
    ("Necesito ayuda con mis tiendas", {"business_type": "tienda", "has_urgency": True}),
    ("perdiendo muchas reservas", {"business_type": None, "has_urgency": True}),
    ("Tengo 3 restaurantes", {"business_type": "restaurante", "has_urgency": False}),
]

print("Testing enhanced extraction:")
for test_input, expected in test_cases:
    result = enhanced_business_extraction(test_input)
    status = "✅" if result["business_type"] == expected["business_type"] and result["has_urgency"] == expected["has_urgency"] else "❌"
    print(f"{status} '{test_input}' → business: {result['business_type']}, urgent: {result['has_urgency']}")


# The actual fix for supervisor_brain_simple.py would be:
"""
# In extract_and_update_lead() function, replace the business extraction with:

# Enhanced business extraction with plural and urgency handling
extraction_result = enhanced_business_extraction(current_message)
if extraction_result["business_type"]:
    extracted["business_type"] = extraction_result["business_type"]
    
# Add urgency boost to scoring
if extraction_result["has_urgency"]:
    urgency_boost = extraction_result["urgency_boost"]
    # Add to final score
"""
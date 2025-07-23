"""
Shared constants used across the application
"""

# GHL Custom Field IDs (from n8n workflow)
FIELD_MAPPINGS = {
    "score": "wAPjuqxtfgKLCJqahjo1",
    "intent": "Q1n5kaciimUU6JN5PBD6", 
    "business_type": "HtoheVc48qvAfvRUKhfG",
    "urgency_level": "dXasgCZFgqd62psjw7nd",
    "goal": "r7jFiJBYHiEllsGn7jZC",
    "budget": "4Qe8P25JRLW0IcZc5iOs",
    "name": "TjB0I5iNfVwx3zyxZ9sW",
    "preferred_day": "D1aD9KUDNm5Lp4Kz8yAD",
    "preferred_time": "M70lUtadchW4f2pJGDJ5"
}

# Lead category thresholds
COLD_LEAD_THRESHOLD = 4
WARM_LEAD_THRESHOLD = 7

# Lead intents
LEAD_INTENTS = {
    "LISTO_COMPRAR": "Ready to buy",
    "BUSCANDO_INFO": "Looking for information",
    "COMPARANDO_OPCIONES": "Comparing options",
    "SOLO_PREGUNTANDO": "Just asking",
    "NO_INTERESADO": "Not interested"
}

# Agent names
AGENT_NAMES = {
    "maria": "Maria",
    "carlos": "Carlos",
    "sofia": "Sofia"
}
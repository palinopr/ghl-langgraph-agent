#!/usr/bin/env python3
"""
Debug Maria's state to understand why she repeats questions
"""
import asyncio
import json
from datetime import datetime
from langchain_core.messages import HumanMessage
from app.state.conversation_state import ConversationState
from app.intelligence.analyzer import IntelligenceAnalyzer
from app.utils.simple_logger import get_logger

logger = get_logger("debug_maria")

async def debug_maria_state():
    """Debug what state Maria receives"""
    
    # Create analyzer
    analyzer = IntelligenceAnalyzer()
    
    # Test case 1: Simple "Restaurante" message
    print("\n=== TEST 1: 'Restaurante' ===")
    state1 = {
        "messages": [HumanMessage(content="Restaurante")],
        "contact_id": "test123",
        "webhook_data": {"message": "Restaurante"},
        "extracted_data": {},
        "lead_score": 0
    }
    
    # Run intelligence analysis
    enriched_state1 = await analyzer.analyze(state1)
    print(f"After Intelligence Analysis:")
    print(f"- extracted_data: {json.dumps(enriched_state1['extracted_data'], indent=2)}")
    print(f"- lead_score: {enriched_state1['lead_score']}")
    print(f"- suggested_agent: {enriched_state1['suggested_agent']}")
    
    # Test case 2: Full conversation
    print("\n\n=== TEST 2: Full conversation ===")
    state2 = {
        "messages": [
            HumanMessage(content="Hola"),
            HumanMessage(content="Me llamo Juan"),  
            HumanMessage(content="Tengo un restaurante"),
            HumanMessage(content="Necesito más clientes")
        ],
        "contact_id": "test456",
        "webhook_data": {"message": "Necesito más clientes"},
        "extracted_data": {},
        "lead_score": 0
    }
    
    # Run intelligence analysis
    enriched_state2 = await analyzer.analyze(state2)
    print(f"After Intelligence Analysis:")
    print(f"- extracted_data: {json.dumps(enriched_state2['extracted_data'], indent=2)}")
    print(f"- lead_score: {enriched_state2['lead_score']}")
    print(f"- suggested_agent: {enriched_state2['suggested_agent']}")
    
    # Test case 3: What Maria sees
    print("\n\n=== TEST 3: Maria's view of state ===")
    from app.agents.maria_agent_v2 import maria_prompt
    
    # Create state as Maria would receive it
    maria_state = {
        **enriched_state1,
        "messages": enriched_state1["messages"],
        "current_step": "employment_inquiry"  # Typical Maria step
    }
    
    # Get Maria's prompt to see what she sees
    prompt_messages = maria_prompt(maria_state)
    system_prompt = prompt_messages[0]["content"]
    
    # Extract the context section
    context_start = system_prompt.find("📊 CONVERSATION STATE:")
    if context_start != -1:
        context_end = system_prompt.find("\n\n", context_start + 200)
        if context_end == -1:
            context_end = len(system_prompt)
        context_section = system_prompt[context_start:context_end]
        print("Maria's Context View:")
        print(context_section)
    
    # Check what Maria thinks she has
    print("\n\nChecking Maria's data access:")
    print(f"- state.get('extracted_data'): {maria_state.get('extracted_data')}")
    print(f"- Conversation analysis from Maria's view:")
    
    # Import conversation analyzer
    from app.utils.conversation_enforcer import get_conversation_analysis
    analysis = get_conversation_analysis(maria_state.get("messages", []))
    print(f"  - collected_data: {analysis['collected_data']}")
    print(f"  - current_stage: {analysis['current_stage']}")
    print(f"  - expecting_answer_for: {analysis['expecting_answer_for']}")

if __name__ == "__main__":
    asyncio.run(debug_maria_state())
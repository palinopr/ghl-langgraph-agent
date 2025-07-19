#!/usr/bin/env python3
"""
Analyze conversation flow to identify repeated questions issue
"""

# Based on the trace data, let's analyze the conversation flow

print("="*80)
print("CONVERSATION FLOW ANALYSIS")
print("="*80)

# From the traces, we have:
trace1 = {
    "id": "1f064974-3f93-6d5e-a756-1dd912bc6798",
    "time": "2025-07-19 11:55:29",
    "user_message": "No puedo contestar todos los mensajes",
    "agent_response": "Entiendo, Jaime. Manejar tantos mensajes puede ser realmente abrumador, especialmente en un restaurante. ¿Cuál dirías que es tu mayor desafío con la gestión de mensajes de clientes?",
    "lead_score": 5,
    "conversation_history": []
}

trace2 = {
    "id": "1f064982-efbc-6aba-9b85-f3b5227b2c2b", 
    "time": "2025-07-19 12:02:03",
    "user_message": "No estar todo el tiempo pendiente",
    "agent_response": "Entiendo, Jaime. Eso puede ser realmente agotador. Dime, ¿cuál es el mayor desafío que enfrentas con tu restaurante actualmente?",
    "lead_score": 6,
    "conversation_history": []
}

print("\nKEY OBSERVATIONS:")
print("-" * 40)

print("\n1. REPEATED QUESTION PATTERN:")
print("   - Both responses ask about the 'mayor desafío' (biggest challenge)")
print("   - First: '¿Cuál dirías que es tu mayor desafío con la gestión de mensajes de clientes?'")
print("   - Second: '¿cuál es el mayor desafío que enfrentas con tu restaurante actualmente?'")

print("\n2. CONVERSATION HISTORY:")
print("   - Both traces show empty conversation_history: []")
print("   - This suggests the agent is NOT seeing previous interactions")

print("\n3. USER RESPONSES:")
print("   - First: 'No puedo contestar todos los mensajes' (I can't answer all messages)")
print("   - Second: 'No estar todo el tiempo pendiente' (Not being available all the time)")
print("   - The second response IS actually answering the challenge question from the first interaction!")

print("\n4. LEAD SCORE PROGRESSION:")
print("   - First interaction: score 5")
print("   - Second interaction: score 6")
print("   - Score increased, but agent still asks the same type of question")

print("\n" + "="*80)
print("ROOT CAUSE ANALYSIS:")
print("="*80)

print("\nThe issue is that the agent is repeating the challenge question because:")
print("\n1. CONVERSATION HISTORY NOT PERSISTED:")
print("   - The conversation_history array is empty in both traces")
print("   - The agent has no context of previous interactions")
print("   - Each message is treated as a new conversation")

print("\n2. THE USER DID ANSWER THE QUESTION:")
print("   - 'No estar todo el tiempo pendiente' IS the answer to the previous challenge question")
print("   - But the agent doesn't recognize this as a continuation")

print("\n3. MISSING CONVERSATION STATE:")
print("   - No tracking of 'challenge_question_asked' flag")
print("   - No tracking of 'challenge_question_answered' flag")
print("   - No mechanism to prevent re-asking questions")

print("\n" + "="*80)
print("RECOMMENDED FIXES:")
print("="*80)

print("\n1. LOAD CONVERSATION HISTORY:")
print("   - Ensure previous messages are loaded from GHL/Supabase")
print("   - Pass full conversation context to the agent")

print("\n2. ADD CONVERSATION STATE TRACKING:")
print("   - Track which questions have been asked")
print("   - Track which questions have been answered")
print("   - Prevent duplicate questions")

print("\n3. IMPROVE CONVERSATION ANALYZER:")
print("   - Add logic to detect when a user is answering a previous question")
print("   - Update the conversation enforcer to track challenge questions")

print("\n4. FIX THE WEBHOOK PROCESSOR:")
print("   - Ensure it loads and includes conversation history")
print("   - Make sure state is properly maintained between messages")

print("\n" + "="*80)
print("CODE LOCATIONS TO CHECK:")
print("="*80)

print("\n1. app/api/webhook.py or webhook_concurrent.py")
print("   - Check how conversation history is loaded")
print("   - Verify it's being passed to the agent")

print("\n2. app/tools/webhook_processor.py")
print("   - Check get_conversation_history() implementation")
print("   - Ensure it's fetching previous messages")

print("\n3. app/utils/conversation_enforcer.py")
print("   - Add tracking for challenge questions")
print("   - Implement state management for questions asked/answered")

print("\n4. app/agents/carlos_agent_v2*.py")
print("   - Update prompt to check conversation history")
print("   - Add logic to avoid repeating questions")
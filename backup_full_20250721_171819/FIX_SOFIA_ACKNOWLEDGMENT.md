# Fix 4: Sofia Acknowledging Problems Before Email

## Problem
When a customer says "tengo un restaurante y estoy perdiendo reservas", Sofia responds with:
"¡Hola! Para poder enviarte el enlace de Google Meet, ¿cuál es tu correo electrónico?"

She's not acknowledging the customer's problem because she sees a high score (9/10) and jumps to email collection.

## Root Cause
1. Intelligence layer gives high score based on polluted data
2. Sofia sees score 8+ and thinks customer is "ready to buy"
3. Her prompt prioritizes email collection over acknowledgment

## Solution

### 1. Add Problem Acknowledgment Rule

```python
# app/agents/sofia_agent_v2.py

# In the prompt, add a new rule:
CRITICAL ACKNOWLEDGMENT RULE:
If customer mentions a specific problem or pain point in their CURRENT message:
1. ALWAYS acknowledge it first before asking for data
2. Show empathy and understanding
3. Connect their problem to your solution
4. THEN continue with data collection

Examples:
Customer: "estoy perdiendo reservas"
GOOD: "Entiendo tu frustración con las reservas perdidas. Puedo ayudarte a automatizar ese proceso. ¿Cómo te llamas?"
BAD: "¿Cuál es tu correo?"

Customer: "tengo problemas con clientes que no llegan"
GOOD: "Los no-shows son frustrantes. Te puedo ayudar con recordatorios automáticos. ¿Cuál es tu nombre?"
BAD: "Para enviarte el link, necesito tu email"
```

### 2. Add Current Message Analysis

Before jumping to email collection, check if current message contains a problem:

```python
# Check if current message mentions a problem
problem_keywords = [
    "perdiendo", "problema", "dificultad", "no puedo", 
    "necesito", "ayuda", "frustra", "cuesta", "difícil",
    "no llegan", "cancelan", "olvidan"
]

mentions_problem = any(keyword in current_message.lower() for keyword in problem_keywords)

if mentions_problem and not analysis.get('problem_acknowledged'):
    # Force acknowledgment first
    context += "\n\n🚨 CUSTOMER JUST MENTIONED A PROBLEM - ACKNOWLEDGE IT FIRST!"
```

### 3. Update Prompt Priority

Change the prompt to prioritize acknowledgment:

```python
# Current priority seems to be:
# 1. Check score
# 2. If high score → ask email
# 3. Send to appointment

# New priority should be:
# 1. Check if current message has problem
# 2. If yes → acknowledge problem first
# 3. Then continue normal flow
```

## Implementation

The key is to make Sofia analyze the CURRENT message, not just rely on the score. Even with a high score, she should:
1. Read what the customer just said
2. If they mention a problem → acknowledge it
3. Show she understands their pain
4. THEN continue with data collection

This makes the conversation feel natural instead of robotic.
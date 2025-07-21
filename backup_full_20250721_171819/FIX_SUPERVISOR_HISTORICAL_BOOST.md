# Fix: Supervisor Historical Context Boost Issue

## Problem
The supervisor is boosting scores too aggressively based on historical context:
- Customer says "hola" → Score correctly calculated as 2/10
- Supervisor finds "restaurante" and "perdiendo" in history → Boosts to 6/10
- This happens even though current message has no business context

## Root Cause
In `app/agents/supervisor_brain_with_ai.py` lines 286-289:
```python
if historical_business and historical_problem:
    # This is a returning customer with a business problem - minimum score 6
    previous_score = max(previous_score, 6)
```

## Solution

### Option 1: Remove Historical Boost (Simplest)
Just comment out or remove the boost logic. Let current message drive the score.

### Option 2: Smarter Historical Context (Better)
Only boost if current message relates to business:

```python
# Check if current message relates to business context
current_msg_lower = current_message.lower()
is_business_related = any(indicator in current_msg_lower for indicator in [
    "negocio", "restaurante", "ayuda", "necesito", "problema", 
    "reserva", "cliente", "perdiendo", "automatizar", "sistema"
])

# Only boost if current conversation is business-related
if historical_business and historical_problem and is_business_related:
    # Boost by 2 points, not directly to 6
    previous_score = min(previous_score + 2, 6)
    logger.info("Business context detected - modest boost applied")
```

### Option 3: Time-Based Decay (Most Sophisticated)
Only consider recent history:

```python
# Only check recent messages (last 24 hours)
recent_business = False
recent_problem = False
now = datetime.now()

for msg in messages:
    # Check message timestamp
    msg_time = msg.additional_kwargs.get('timestamp')
    if msg_time and (now - msg_time).days < 1:
        # Process only recent messages
        ...
```

## Recommended Fix
Use Option 2 - it maintains the intent of recognizing returning customers while preventing simple greetings from triggering high scores.

## Expected Behavior After Fix
- "hola" from returning customer → Score 2 (maybe 3 if recognized)
- "hola, necesito ayuda con mi restaurante" → Score 4-6 (business context)
- "estoy perdiendo clientes" → Score 6+ (clear problem statement)
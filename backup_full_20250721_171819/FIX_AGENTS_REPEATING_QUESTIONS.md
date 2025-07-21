# Fixed: AI Agents Repeating Questions

## Problem
The AI agents (Maria, Carlos, Sofia) were asking for information that was already extracted by the intelligence layer:
- Customer says "Jaime" → Intelligence extracts name → Agent still asks "What's your name?"
- Customer mentions "restaurante" → Intelligence extracts business → Agent asks again

## Root Cause
Agents were ONLY checking `collected_data` from the conversation analysis instead of FIRST checking `state["extracted_data"]` from the intelligence layer.

## Solution Applied
Modified all three agents to prioritize data from the intelligence layer:

```python
# BEFORE (wrong):
customer_name = collected_data['name']
business_type = collected_data['business']

# AFTER (correct):
extracted_data = state.get("extracted_data", {})
customer_name = extracted_data.get('name') or collected_data['name']
business_type = extracted_data.get('business_type') or collected_data['business']
```

## Files Modified
1. `app/agents/maria_agent_v2.py`
   - Lines 52-53: Fixed data extraction priority
   - Lines 72-82: Updated data display logic

2. `app/agents/carlos_agent_v2.py`
   - Lines 52-65: Fixed data extraction priority
   - Added checks for extracted_data fields

3. `app/agents/sofia_agent_v2.py`
   - Lines 60-63: Fixed data extraction priority
   - Lines 71-75: Updated boolean checks

## Expected Behavior After Fix
```
Customer: "Jaime"
Intelligence: Extracts name = "Jaime"
Maria: "Hola Jaime! ¿Qué tipo de negocio tienes?" ✓

Customer: "tengo un restaurante"
Intelligence: Extracts business = "restaurante"
Carlos: "Entiendo, para tu restaurante..." ✓
```

## Testing
Test with messages that contain extractable information:
```bash
# Test 1: Name extraction
Message: "Mi nombre es Carlos"
Expected: Agent should NOT ask for name again

# Test 2: Business extraction
Message: "tengo una peluquería"
Expected: Agent should acknowledge business type

# Test 3: Combined extraction
Message: "Hola, soy María y tengo un restaurante"
Expected: Agent should skip name and business questions
```

## Impact
- Agents will now see data extracted by the intelligence layer
- Conversations will flow more naturally
- No more repeating questions for information already provided
- Better user experience with context-aware responses
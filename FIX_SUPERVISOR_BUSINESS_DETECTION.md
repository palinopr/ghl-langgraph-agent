# Fix for Supervisor Business Type Detection Issue

## Problem Identified

The supervisor_brain is incorrectly analyzing the last message in the messages array. When it runs, the last message is the receptionist's system message ("DATA LOADED SUCCESSFULLY...") instead of the user's actual message ("Restaurante").

## Current Incorrect Logic

```python
# Line 40 in supervisor_brain.py
current_message = state.get("messages", [])[-1].content if state.get("messages") else ""
```

This gets the LAST message, which after receptionist runs is:
```
"DATA LOADED SUCCESSFULLY:
- Contact: Jaime Ortiz
- Email: none
..."
```

## Root Cause

The message flow is:
1. User: "Restaurante" 
2. Receptionist adds: "DATA LOADED SUCCESSFULLY..."
3. Supervisor analyzes the receptionist's message instead of user's message

## Solution

The supervisor needs to find the last HUMAN message, not just the last message:

```python
# Get the last human message (user's actual input)
messages = state.get("messages", [])
current_message = ""
for msg in reversed(messages):
    if hasattr(msg, 'type') and msg.type == 'human':
        current_message = msg.content
        break
```

## Alternative Solutions

1. **Option A**: Have receptionist not add messages to the state
2. **Option B**: Pass the user's message explicitly in state
3. **Option C**: Filter messages by type when analyzing

## Impact

This fix will ensure:
- Supervisor correctly detects "Restaurante" as business type
- Lead score is calculated correctly 
- Maria won't ask for business type again
- Proper routing based on actual user input

## Testing

Test cases needed:
- User says just "Restaurante"
- User says "Tengo un restaurante"
- User says other business types
- Multiple messages in conversation
# Supervisor Message Extraction Fix

## Problem
When the workflow is invoked through the LangGraph API (not directly via webhook), the supervisor was analyzing the wrong message. It was looking at the receptionist's summary message ("DATA LOADED SUCCESSFULLY...") instead of the user's actual message ("Restaurante").

## Root Cause
1. LangGraph API calls don't include `webhook_data` field
2. Receptionist adds its summary message at the END of the messages array
3. Supervisor's fallback logic was looking for the LAST human message
4. Since messages include history, the "last" human message could be from history

## Solution
Updated the supervisor to:
1. First try webhook_data (when available)
2. Look for the FIRST human message WITHOUT 'ghl_history' source
3. This correctly identifies the new user message vs historical messages

## Code Changes
File: `app/agents/supervisor_brain_simple.py` (lines 40-59)

### Before:
```python
# Look for human messages starting from the end
for msg in reversed(messages):
    if hasattr(msg, '__class__') and msg.__class__.__name__ == 'HumanMessage':
        current_message = msg.content
        break
```

### After:
```python
# Look for the first human message without ghl_history source
for msg in messages:
    if hasattr(msg, '__class__') and msg.__class__.__name__ == 'HumanMessage':
        # Check if it's NOT from history
        additional_kwargs = getattr(msg, 'additional_kwargs', {})
        if additional_kwargs.get('source') != 'ghl_history':
            current_message = msg.content
            logger.info(f"Found user message: {current_message}")
            break
```

## Impact
- Supervisor now correctly identifies "Restaurante" as the user's message
- Business type extraction will work properly
- Maria won't repeat questions about business type
- Works for both webhook and LangGraph API invocations

## Testing
Test with both:
1. Direct webhook calls (includes webhook_data)
2. LangGraph API calls (no webhook_data, relies on message ordering)
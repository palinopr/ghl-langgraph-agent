# Fix 3: Remove Debug Messages from Customer View

## Problem
Debug messages like "Lead scored 9/10, routing to sofia" are appearing in customer conversations.

## Possible Sources
Based on the trace analysis, these messages appear to be coming from:
1. Logging messages that somehow get included in the conversation
2. System messages added by agents
3. Debug output from tools being included in state

## Solution

### 1. Ensure Responder Filters System Messages

The responder already filters out messages from receptionist and supervisor:

```python
# app/agents/responder_agent.py
# Skip system messages from receptionist and supervisor
msg_name = getattr(msg, 'name', '')
if msg_name in ['receptionist', 'supervisor', 'supervisor_brain']:
    continue
```

### 2. Add Additional Filtering

We should also filter out any messages that look like debug/system messages:

```python
# app/agents/responder_agent.py

# Enhanced filtering
for msg in reversed(all_messages[-10:]):
    if isinstance(msg, AIMessage) and msg.content:
        # Skip system messages
        msg_name = getattr(msg, 'name', '')
        if msg_name in ['receptionist', 'supervisor', 'supervisor_brain', 'intelligence']:
            continue
        
        # Skip debug-like messages
        content_lower = msg.content.lower()
        if any(pattern in content_lower for pattern in [
            'lead scored',
            'routing to',
            'data loaded',
            'analysis complete',
            'ghl updated',
            'debug:',
            'error:',
            'loading'
        ]):
            logger.info(f"Filtering out debug message: {msg.content[:50]}...")
            continue
            
        # Check for duplicates
        if not is_duplicate_message(contact_id, msg.content):
            messages_to_send.append(msg)
            break  # Only send ONE message
```

### 3. Ensure No Debug Messages in Agent Responses

Check that agents are not including debug info in their responses:

```python
# In each agent, ensure responses are clean
response = "¡Hola! Soy de Main Outlet Media..."  # Good
# NOT: "Lead scored 3/10. ¡Hola! Soy de Main Outlet Media..."  # Bad
```

### 4. Check State Updates

Ensure state updates don't add debug messages to the messages array:

```python
# Good - updating metadata
return {
    "lead_score": score,
    "routing_reason": reason
}

# Bad - adding to messages
return {
    "messages": [AIMessage(content=f"Lead scored {score}/10")]
}
```

## Implementation

The main fix is to enhance the responder's filtering to catch any debug-like messages that shouldn't be sent to customers.
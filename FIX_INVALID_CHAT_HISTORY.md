# Fix for Invalid Chat History Error

## Problem
Agents were failing with error:
```
Found AIMessages with tool_calls that do not have a corresponding ToolMessage
```

This occurred when:
1. Supervisor calls a tool (e.g., `handoff_to_maria`) 
2. The AIMessage with tool_calls and the ToolMessage result are added to state
3. Agent receives incomplete conversation context
4. `create_react_agent` validates chat history and fails

## Root Cause
The agents were receiving supervisor's internal messages which contain tool calls. When we only pass the last message, `create_react_agent` sees an incomplete conversation with tool_calls but no context.

## Solution
Modified all agent prompt functions to:
1. Filter messages to only include customer messages
2. Skip any messages with a `name` attribute (supervisor/agent messages)
3. Only pass the last customer HumanMessage to the agent

## Code Changes
Updated prompt functions in:
- `app/agents/maria_agent.py`
- `app/agents/carlos_agent.py`  
- `app/agents/sofia_agent.py`

```python
# Find the last customer message (HumanMessage without a name attribute)
# Skip supervisor messages, tool messages, and agent messages
customer_message = None
for msg in reversed(messages):
    # Check for HumanMessage that's from a customer (no name attribute)
    if hasattr(msg, '__class__') and 'Human' in msg.__class__.__name__:
        # Skip if it has a name (means it's from an agent/system)
        if not hasattr(msg, 'name') or not msg.name:
            customer_message = msg
            break

# Include the customer message if found
filtered_messages = [customer_message] if customer_message else []
```

## Benefits
1. Agents only see clean customer conversation
2. No more validation errors from incomplete tool_calls
3. Agents focus on customer needs, not internal routing
4. Simpler message handling logic
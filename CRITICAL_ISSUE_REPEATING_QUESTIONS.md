# CRITICAL ISSUE: AI Agents Repeating Questions

## The Problem
The AI agents (Maria, Carlos, Sofia) are asking for information that was already provided:
- Customer says "Jaime" → AI asks "What's your name?"
- Customer mentions business → AI asks about business again
- The conversation doesn't progress forward

## Root Causes

### 1. State Not Being Passed to Agent Prompts
The agents might not be seeing the extracted data in their prompts.

### 2. Agent Prompts Not Using Extracted Data
Even if state is passed, the prompts might not be using it.

### 3. Agents Not Checking Previous Extraction
Agents are asking questions without checking what's already known.

## Investigation Needed

### Check Agent State Access
```python
# In maria_agent_v2.py, carlos_agent_v2.py, sofia_agent_v2.py
# The agent should see:
state["extracted_data"] = {
    "name": "Jaime",
    "business_type": "restaurante",
    ...
}
```

### Check Agent Prompts
The prompts should include:
```python
# What we already know about the customer
known_info = state.get("extracted_data", {})
if known_info.get("name"):
    prompt += f"\nCustomer's name: {known_info['name']}"
if known_info.get("business_type"):
    prompt += f"\nBusiness type: {known_info['business_type']}"
```

## Quick Diagnosis

The issue is likely in how agents build their prompts. They need to:
1. Check extracted_data FIRST
2. Only ask for MISSING information
3. Move the conversation FORWARD

## Example of the Problem

```
Customer: "Jaime"
Intelligence: Extracts name = "Jaime" ✓
Supervisor: Routes to Maria ✓
Maria: "¿Cuál es tu nombre?" ❌ (Should say "Hola Jaime!")
```

## Files to Check

1. `app/agents/maria_agent_v2.py` - Check maria_prompt function
2. `app/agents/carlos_agent_v2.py` - Check carlos_prompt function
3. `app/agents/sofia_agent_v2.py` - Check sofia_prompt function
4. The prompts should use state["extracted_data"] to avoid re-asking
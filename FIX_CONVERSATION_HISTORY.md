# Fix 1: Conversation History Loading

## Problem
The system is loading ALL conversations ever for a contact, causing:
- Old messages appearing in new conversations
- Intelligence layer extracting from wrong messages
- Scores based on polluted data

## Root Cause
In `app/tools/conversation_loader.py`:
- `get_conversation_history()` loads ALL conversations
- No filtering by conversation/thread ID
- Returns mixed messages from different sessions

## Solution

### 1. Update GHL Client to Filter by Thread

```python
# app/tools/ghl_client.py

async def get_conversation_messages_for_thread(
    self, 
    contact_id: str,
    thread_id: str = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Get messages for current conversation thread only
    
    Args:
        contact_id: Contact ID
        thread_id: Optional thread/conversation ID to filter by
        limit: Maximum messages to return
        
    Returns:
        List of messages from current thread only
    """
    # If no thread_id, get the most recent conversation
    if not thread_id:
        conversations = await self.get_conversations(contact_id)
        if not conversations:
            return []
        # Get most recent conversation ID
        thread_id = conversations[0].get('id')
    
    # Get messages for specific conversation
    messages = await self.get_conversation_messages(thread_id)
    
    # Return limited messages
    return messages[-limit:] if messages else []
```

### 2. Update Conversation Loader

```python
# app/tools/conversation_loader.py

async def load_conversation_history(
    self, 
    contact_id: str,
    thread_id: str = None,
    limit: int = 20
) -> List[BaseMessage]:
    """
    Load conversation history for CURRENT thread only
    """
    messages = []
    
    try:
        # Get messages for current thread only
        ghl_history = await self.ghl_client.get_conversation_messages_for_thread(
            contact_id,
            thread_id,
            limit
        )
        
        if ghl_history:
            logger.info(f"Loaded {len(ghl_history)} messages from current thread")
            messages = self._convert_ghl_to_langchain(ghl_history)
    except Exception as e:
        logger.warning(f"Failed to load thread history: {e}")
    
    return messages
```

### 3. Update Webhook to Include Thread ID

```python
# app/api/webhook.py

# Extract thread_id from webhook data
thread_id = webhook_data.get("conversationId") or webhook_data.get("threadId")

# Pass to workflow
initial_state = {
    "messages": [HumanMessage(content=message)],
    "contact_id": contact_id,
    "thread_id": thread_id,  # Add this
    # ... rest of state
}
```

### 4. Update Receptionist to Use Thread ID

```python
# app/agents/receptionist_agent.py

@tool
async def get_conversation_history(
    state: Annotated[ConversationState, InjectedState]
) -> str:
    """
    Load conversation history from CURRENT thread only
    """
    contact_id = state.get("contact_id")
    thread_id = state.get("thread_id")  # Get thread ID from state
    
    if not contact_id:
        return "Error: No contact_id found in state"
        
    try:
        ghl_client = GHLClient()
        
        # Get messages for current thread only
        messages = await ghl_client.get_conversation_messages_for_thread(
            contact_id,
            thread_id,
            limit=10  # Only last 10 messages
        )
        
        if not messages:
            return "No messages in current conversation"
            
        # Format recent messages
        history = f"CURRENT CONVERSATION ({len(messages)} messages):\\n"
        
        for msg in messages:
            sender = "Customer" if msg.get('direction') == 'inbound' else 'AI'
            timestamp = msg.get('dateAdded', '')
            body = msg.get('body', '')[:100]
            history += f"\\n[{timestamp}] {sender}: {body}..."
            
        # Store in state
        state["conversation_history"] = messages
        
        return history
        
    except Exception as e:
        logger.error(f"Error loading history: {e}")
        return f"Error loading history: {str(e)}"
```

## Testing

### Before Fix
```
Customer: "hola"
System loads: ALL conversations ever
- "el viernes" (from last week)
- "tengo un restaurante" (from months ago)
- "mi presupuesto es $500" (old conversation)
Intelligence extracts: business="negocio hola", budget="10"
Score: 9/10 (wrong!)
```

### After Fix
```
Customer: "hola"
System loads: Current thread only (empty for new conversation)
Intelligence extracts: Nothing (correct)
Score: 1-2 (correct!)
```

## Implementation Order
1. Add `get_conversation_messages_for_thread()` to GHL client
2. Update conversation loader to use thread filtering
3. Update webhook to extract and pass thread_id
4. Update receptionist tool to use thread_id
5. Test with new conversation
# Fix: LangGraph Cloud Thread ID Persistence

## Problem
LangGraph Cloud is using its own UUID thread_ids (e.g., `cd60c1f6-0050-4ee7-b0b3-40c68cb41dc1`) instead of our consistent pattern (`contact-{contact_id}`), causing complete memory loss between messages.

## Root Cause
When deployed to LangGraph Cloud:
1. The platform invokes the compiled `workflow` object directly
2. It bypasses our `run_workflow()` function that sets the proper thread_id
3. It uses its own thread_id from the API request headers

## Solution
We need to implement a thread_id mapper at the workflow compilation level that transforms LangGraph Cloud's thread_ids into our consistent pattern based on the input data.

## Implementation

### Option 1: Custom Thread ID Transformer (Recommended)
Add a thread_id transformer to the workflow compilation:

```python
# app/workflow.py

def get_thread_id_from_input(input_data: dict) -> str:
    """
    Extract consistent thread_id from input data.
    This runs BEFORE checkpoint loading.
    """
    # Handle both direct webhook data and LangGraph Cloud format
    if isinstance(input_data, dict):
        # Try to get contact_id from various possible locations
        contact_id = (
            input_data.get("contact_id") or
            input_data.get("contactId") or
            input_data.get("webhook_data", {}).get("contactId") or
            input_data.get("messages", [{}])[0].get("contact_id", None) if input_data.get("messages") else None
        )
        
        # Try to get conversationId
        conversation_id = (
            input_data.get("conversationId") or
            input_data.get("webhook_data", {}).get("conversationId") or
            input_data.get("conversation_id")
        )
        
        # Generate consistent thread_id
        if conversation_id:
            return f"conv-{conversation_id}"
        elif contact_id:
            return f"contact-{contact_id}"
    
    # Fallback to LangGraph's thread_id if we can't extract contact info
    return None

# Update workflow compilation
def create_sync_workflow():
    """Create a synchronous workflow for module-level compilation."""
    logger.info("Creating sync workflow for module export")
    
    # ... existing graph setup ...
    
    # Compile with thread_id transformer
    checkpoint_db = os.path.join(os.path.dirname(__file__), "checkpoints.db")
    
    with SqliteSaver.from_conn_string(checkpoint_db) as checkpointer:
        store = InMemoryStore()
        
        # Create a custom checkpointer that transforms thread_ids
        class ThreadMappingCheckpointer:
            def __init__(self, base_checkpointer):
                self.base = base_checkpointer
                
            def get(self, config):
                # Transform thread_id based on input
                if "input" in config.get("configurable", {}):
                    custom_thread_id = get_thread_id_from_input(config["configurable"]["input"])
                    if custom_thread_id:
                        config["configurable"]["thread_id"] = custom_thread_id
                return self.base.get(config)
                
            def put(self, config, checkpoint, metadata):
                # Transform thread_id based on checkpoint data
                if checkpoint and "channel_values" in checkpoint:
                    custom_thread_id = get_thread_id_from_input(checkpoint["channel_values"])
                    if custom_thread_id:
                        config["configurable"]["thread_id"] = custom_thread_id
                return self.base.put(config, checkpoint, metadata)
                
            # Delegate other methods
            def __getattr__(self, name):
                return getattr(self.base, name)
        
        # Wrap the checkpointer
        mapped_checkpointer = ThreadMappingCheckpointer(checkpointer)
        
        compiled = workflow_graph.compile(
            checkpointer=mapped_checkpointer,
            store=store
        )
```

### Option 2: Input Preprocessor (Simpler)
Add preprocessing to ensure thread_id is in the initial state:

```python
# In receptionist node or first node
def receptionist_checkpoint_aware_node(state: MinimalState) -> Dict[str, Any]:
    """First node that sets proper thread_id in state"""
    
    # Extract contact_id from state
    contact_id = state.get("contact_id") or state.get("webhook_data", {}).get("contactId")
    conversation_id = state.get("conversationId") or state.get("webhook_data", {}).get("conversationId")
    
    # Set consistent thread_id in state
    thread_id = (
        f"conv-{conversation_id}" if conversation_id else
        f"contact-{contact_id}" if contact_id else
        state.get("thread_id")  # Fallback to existing
    )
    
    # CRITICAL: Update the checkpoint configuration
    if hasattr(state, "__config__") and thread_id:
        state.__config__["configurable"]["thread_id"] = thread_id
        logger.info(f"Updated thread_id to: {thread_id}")
```

### Option 3: LangGraph Cloud API Headers
Configure the API request to include the proper thread_id:

When calling the LangGraph Cloud API, ensure the thread_id is set in headers:
```javascript
// In your client code
const threadId = conversationId ? `conv-${conversationId}` : `contact-${contactId}`;

const response = await axios.post(
  'https://your-app.langgraph.app/threads/{threadId}/messages',
  {
    messages: [{role: 'user', content: messageText}],
    contact_id: contactId,
    // ... other data
  },
  {
    headers: {
      'x-thread-id': threadId  // Ensure consistent thread_id
    }
  }
);
```

## Verification

After implementing, verify with:
```python
# Check logs for:
"Updated thread_id to: contact-hZoKFVUv6ZiwI9FyVmrI"

# Check database for consistent threads:
sqlite3 app/checkpoints.db "SELECT DISTINCT thread_id FROM checkpoints WHERE thread_id LIKE 'contact-%' OR thread_id LIKE 'conv-%';"
```

## Critical Notes
1. The thread_id MUST be set before checkpoint loading occurs
2. LangGraph Cloud's thread_id in the trace metadata is NOT the one used for checkpointing
3. The checkpointer uses the thread_id from the config passed to it, which we can control
# Immediate Thread ID Fix for LangGraph Cloud

## Problem Summary
- LangGraph Cloud generates new UUID thread_ids for each webhook
- Thread mapper updates state but not checkpoint configuration
- Result: No conversation memory between messages

## Immediate Solution: Update Thread Mapper to Override Checkpoint Config

Since we can't control the initial thread_id from LangGraph Cloud, we need to make the thread_mapper more aggressive:

### 1. Enhanced Thread Mapper

Update `app/agents/thread_id_mapper.py`:

```python
async def thread_id_mapper_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Enhanced mapper that overrides checkpoint configuration"""
    logger.info("=== ENHANCED THREAD ID MAPPER ===")
    
    # Get identifiers
    contact_id = (
        state.get("contact_id") or
        state.get("contactId") or
        state.get("webhook_data", {}).get("contactId")
    )
    
    conversation_id = (
        state.get("conversationId") or
        state.get("conversation_id") or
        state.get("webhook_data", {}).get("conversationId")
    )
    
    # Generate consistent thread_id
    if conversation_id:
        new_thread_id = f"conv-{conversation_id}"
    elif contact_id:
        new_thread_id = f"contact-{contact_id}"
    else:
        logger.error("No identifiers found!")
        return state
    
    logger.info(f"Mapping thread_id to: {new_thread_id}")
    
    # CRITICAL: Override the configurable thread_id
    if "__config__" in state:
        if "configurable" not in state["__config__"]:
            state["__config__"]["configurable"] = {}
        state["__config__"]["configurable"]["thread_id"] = new_thread_id
        logger.info(f"✅ Overrode config thread_id to: {new_thread_id}")
    
    # Update state
    state["thread_id"] = new_thread_id
    state["mapped_thread_id"] = new_thread_id
    
    return state
```

### 2. Verify Checkpoint Loading in Receptionist

The receptionist should use the mapped thread_id from state:

```python
# In receptionist_checkpoint_aware_node
thread_id = state.get("mapped_thread_id") or state.get("thread_id")
config = {"configurable": {"thread_id": thread_id}}
```

### 3. Test the Fix

1. Deploy the updated thread_mapper
2. Send multiple messages from same contact
3. Check logs for "Overrode config thread_id"
4. Verify conversation continuity

## Alternative: Custom Checkpointer

If the above doesn't work, implement a custom checkpointer that maps all UUIDs:

```python
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

class ContactMappedCheckpointer(AsyncSqliteSaver):
    """Checkpointer that maps UUID thread_ids to contact patterns"""
    
    def _extract_contact_id(self, state: dict) -> Optional[str]:
        """Extract contact ID from state"""
        return (
            state.get("contact_id") or
            state.get("contactId") or
            state.get("webhook_data", {}).get("contactId")
        )
    
    def _map_thread_id(self, thread_id: str, state: dict) -> str:
        """Map UUID to contact pattern"""
        # If it looks like a UUID, map it
        if len(thread_id) == 36 and thread_id.count("-") == 4:
            contact_id = self._extract_contact_id(state)
            if contact_id:
                return f"contact-{contact_id}"
        return thread_id
    
    async def aget(self, config: RunnableConfig) -> Optional[Checkpoint]:
        """Get checkpoint with mapped thread_id"""
        # Extract state from somewhere (this is the tricky part)
        state = config.get("state", {})
        
        # Map the thread_id
        original_thread_id = config["configurable"]["thread_id"]
        mapped_thread_id = self._map_thread_id(original_thread_id, state)
        
        # Create new config with mapped ID
        mapped_config = {
            **config,
            "configurable": {
                **config["configurable"],
                "thread_id": mapped_thread_id
            }
        }
        
        return await super().aget(mapped_config)
```

## Quick Deploy Steps

1. Update thread_id_mapper.py with config override
2. Test locally with sequential messages
3. Deploy to LangGraph Cloud
4. Monitor logs for successful mapping

This should finally fix the conversation memory issue!
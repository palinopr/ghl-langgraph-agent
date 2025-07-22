# LangGraph Cloud Thread Persistence - Real Solution

## The Real Problem

1. **LangGraph Cloud bypasses run_workflow**: It uses the compiled `workflow` object directly
2. **Thread IDs are set at infrastructure level**: Before any node runs
3. **Thread mapper updates state but not checkpoints**: Checkpoints use the infrastructure thread_id

## Evidence

From the traces:
- Message 1: thread_id `3798d672-14ac-4195-bfb6-329fd9c1cfe0` 
- Message 2: thread_id `887dbb15-d4ed-4c1d-ae13-c03e550fcf68`
- Both correctly mapped to `contact-daRK4gKoyQJ0tb6pB18u` in state
- But checkpoints still use the UUIDs!

## Why Current Approach Fails

```
LangGraph Cloud → Sets UUID thread_id → Invokes workflow → thread_mapper runs → Updates state
                                                             ↓
                                                    But checkpoints already configured with UUID!
```

## The Real Solution

### Option 1: Pass thread_id in the invocation request

Instead of letting LangGraph Cloud generate UUIDs, we need to pass our thread_id in the webhook request:

```python
# In webhook handler or client code
response = await client.invoke(
    graph_name="agent",
    input=webhook_data,
    config={
        "configurable": {
            "thread_id": f"contact-{contact_id}"  # Set it here!
        }
    }
)
```

### Option 2: Use a custom checkpointer wrapper

Create a checkpointer that maps UUIDs to our pattern:

```python
class MappedCheckpointer(AsyncSqliteSaver):
    def _map_thread_id(self, thread_id: str, state: dict) -> str:
        """Map UUID to our pattern"""
        if "-" in thread_id and len(thread_id) == 36:  # Likely UUID
            contact_id = state.get("contact_id")
            if contact_id:
                return f"contact-{contact_id}"
        return thread_id
    
    async def aget(self, config: dict) -> Optional[Checkpoint]:
        # Map thread_id before getting
        if "thread_id" in config.get("configurable", {}):
            state = config.get("state", {})
            mapped_id = self._map_thread_id(
                config["configurable"]["thread_id"], 
                state
            )
            config["configurable"]["thread_id"] = mapped_id
        return await super().aget(config)
```

### Option 3: Intercept at the API layer

Since the webhook is calling the workflow through an API, we need to check where the thread_id can be set in the request.

## Immediate Action Required

1. Check if webhook can pass thread_id in the request
2. Verify LangGraph Cloud API documentation for thread_id configuration
3. Test with explicit thread_id in invocation

## Code to Test

```python
# In the webhook handler
async def invoke_langgraph_with_thread_id(webhook_data):
    contact_id = webhook_data.get("contactId")
    thread_id = f"contact-{contact_id}"
    
    # If using HTTP API
    response = await http_client.post(
        "https://your-langgraph-url/invoke",
        json={
            "input": webhook_data,
            "config": {
                "configurable": {
                    "thread_id": thread_id  # Force our thread_id
                }
            }
        }
    )
    
    return response
```

This is the only way to ensure consistent thread_ids across messages!
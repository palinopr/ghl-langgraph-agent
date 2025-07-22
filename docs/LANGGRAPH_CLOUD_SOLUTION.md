# LangGraph Cloud Thread Persistence Solution

## Current Situation

Your LangGraph Cloud deployment on LangSmith is receiving webhooks from GoHighLevel, but:
- LangGraph Cloud assigns random UUID thread_ids at the infrastructure level
- The enhanced thread_mapper in your workflow updates the state but cannot override checkpoint configuration
- Each message gets a new thread_id, causing complete conversation memory loss

## The Real Problem

When GoHighLevel sends a webhook to:
```
https://ghl-langgraph-agent-95f8713b0bd6545391589bd2f0ca67eb.us.langgraph.app/runs
```

LangGraph Cloud:
1. Creates a new UUID thread_id (e.g., `391f02c8-3bfc-4197-8344-a021eb04bb46`)
2. Ignores any thread_id passed in the config
3. Your thread_mapper updates the state to use `conv-{conversationId}` but the checkpoint still uses the UUID

## Solution Options

### Option 1: Use LangGraph Client Library (Recommended)

Instead of direct webhook integration, use the LangGraph client to maintain thread continuity:

```python
from langgraph_sdk import get_client

client = get_client(
    url="https://ghl-langgraph-agent-95f8713b0bd6545391589bd2f0ca67eb.us.langgraph.app",
    api_key="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"
)

# For each message, use the same thread
thread = await client.threads.create()  # Create once per conversation
result = await client.runs.create(
    thread_id=thread["thread_id"],
    assistant_id="agent",
    input=webhook_data
)
```

### Option 2: Webhook Proxy Service

Deploy a simple proxy that:
1. Receives webhooks from GoHighLevel
2. Maps conversationId to LangGraph thread_ids
3. Uses the LangGraph SDK to invoke with correct thread_id

### Option 3: Update GoHighLevel Integration

Configure GoHighLevel to:
1. Store the LangGraph thread_id after first message
2. Pass it in subsequent webhooks
3. Use stored thread_id for conversation continuity

## Immediate Fix

The quickest solution is to deploy a webhook proxy (Option 2) that properly manages threads:

```python
# Webhook proxy that maintains thread mapping
thread_map = {}  # In production, use Redis or database

@app.post("/webhook/message")
async def handle_webhook(webhook_data: dict):
    conversation_id = webhook_data.get("conversationId")
    
    # Get or create thread
    if conversation_id not in thread_map:
        thread = await client.threads.create()
        thread_map[conversation_id] = thread["thread_id"]
    
    # Use existing thread
    thread_id = thread_map[conversation_id]
    
    # Invoke with proper thread
    result = await client.runs.create(
        thread_id=thread_id,
        assistant_id="agent",
        input={"webhook_data": webhook_data}
    )
    
    return {"status": "success", "thread_id": thread_id}
```

## Why Current Approach Doesn't Work

1. **Direct API calls to /runs endpoint**: Always create new threads
2. **Config thread_id ignored**: LangGraph Cloud doesn't use thread_id from config
3. **Thread mapper limitations**: Can update state but not checkpoint configuration

## Next Steps

1. Deploy the webhook proxy service
2. Update GoHighLevel to point to proxy instead of direct LangGraph URL
3. Proxy maintains conversation→thread mapping
4. All messages in a conversation use the same LangGraph thread

This is the only reliable way to maintain conversation continuity with LangGraph Cloud.
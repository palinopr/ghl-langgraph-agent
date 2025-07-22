# LangGraph Cloud Webhook Handler - Thread Persistence Fix

## Overview

This webhook handler solves the conversation memory issue in LangGraph Cloud deployments by ensuring consistent thread IDs across all messages from the same contact or conversation.

## Problem Solved

- **Before**: LangGraph Cloud assigns random UUID thread_ids, causing conversation memory loss
- **After**: Webhook handler enforces consistent thread_ids (`conv-{id}` or `contact-{id}`)

## Quick Start

### 1. Configuration

The `.env.webhook` file contains your LangChain Smith credentials:
```bash
LANGGRAPH_API_KEY=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
LANGGRAPH_API_URL=https://api.smith.langchain.com
LANGGRAPH_DEPLOYMENT_URL=https://ghl-langgraph-agent-95f8713b0bd6545391589bd2f0ca67eb.us.langgraph.app
```

### 2. Local Testing

```bash
# Test the webhook handler locally
./deploy_production.sh test
```

### 3. Deploy to Production

```bash
# Deploy to Railway
./deploy_production.sh deploy railway

# Or build Docker image
./deploy_production.sh deploy docker
```

### 4. Verify Deployment

```bash
# Replace with your actual deployment URL
./deploy_production.sh verify https://your-handler.railway.app
```

### 5. Update GoHighLevel

```bash
# Get instructions for updating GHL webhook
./deploy_production.sh update-ghl https://your-handler.railway.app
```

## How It Works

1. **Receives webhook** from GoHighLevel at `/webhook/message`
2. **Generates thread_id**:
   - Primary: `conv-{conversationId}` if available
   - Fallback: `contact-{contactId}`
3. **Invokes LangGraph Cloud** with proper configuration:
   ```python
   config = {"configurable": {"thread_id": thread_id}}
   ```
4. **Returns quickly** to GoHighLevel (async processing)

## Endpoints

- `POST /webhook/message` - Main webhook handler
- `GET /health` - Health check
- `GET /` - Service info
- `POST /invoke/{thread_id}` - Direct testing endpoint

## Testing Thread Persistence

1. Send initial message:
   ```bash
   curl -X POST http://localhost:8000/webhook/message \
     -H "Content-Type: application/json" \
     -d '{
       "contactId": "test-123",
       "conversationId": "conv-456",
       "body": "Hola, mi nombre es María",
       "type": "Contact"
     }'
   ```

2. Send follow-up to test memory:
   ```bash
   curl -X POST http://localhost:8000/webhook/message \
     -H "Content-Type: application/json" \
     -d '{
       "contactId": "test-123",
       "conversationId": "conv-456",
       "body": "¿Cuál es mi nombre?",
       "type": "Contact"
     }'
   ```

3. Agent should respond with "María" - proving thread persistence works!

## Monitoring

Check for:
- ✅ Consistent thread IDs in database
- ✅ No UUID-based threads
- ✅ Conversation context maintained
- ✅ Lead scores accumulating properly

## Troubleshooting

1. **Client initialization fails**
   - Verify LANGGRAPH_API_KEY is set correctly
   - Check network connectivity to LangChain Smith

2. **Thread persistence not working**
   - Verify webhook handler is receiving correct data
   - Check logs for thread_id generation
   - Ensure config is passed correctly to LangGraph

3. **Slow responses**
   - Handler uses async processing
   - Check LangGraph Cloud response times
   - Monitor server resources

## Architecture

```
GoHighLevel → Webhook Handler → LangGraph Cloud
     ↓              ↓                  ↓
  Webhook      Thread ID          Persistent
  Message      Generation         Conversation
```

This handler acts as a critical middleware layer ensuring proper thread management for conversation persistence.
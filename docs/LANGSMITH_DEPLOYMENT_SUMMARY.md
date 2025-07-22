# LangSmith/LangGraph Cloud Deployment Summary

## Your Deployment Details

- **LangGraph Cloud URL**: `https://ghl-langgraph-agent-95f8713b0bd6545391589bd2f0ca67eb.us.langgraph.app`
- **Assistant ID**: `fe096781-5601-53d2-b2f6-0d3403f7e9ca`
- **Graph ID**: `agent`
- **LangSmith Project**: `ghl-langgraph-agent`
- **Host**: LangSmith Cloud (saas)

## Critical Thread Persistence Fix

### The Problem
From your traces, each webhook gets a new UUID thread_id:
- Message 1: `3798d672-14ac-4195-bfb6-329fd9c1cfe0`
- Message 2: `887dbb15-d4ed-4c1d-ae13-c03e550fcf68`

This causes complete conversation memory loss between messages.

### The Solution
Deploy the webhook handler that intercepts GoHighLevel webhooks and properly configures thread_id before invoking LangGraph Cloud.

## Quick Deployment Steps

### 1. Set Your API Key
```bash
# Get your API key from LangSmith dashboard
export LANGGRAPH_API_KEY="lsv2_pt_xxxxx"
```

### 2. Test Locally First
```bash
cd langgraph-ghl-agent
./quick_deploy.sh local

# In another terminal, test it:
curl -X POST http://localhost:8000/webhook/message \
  -H "Content-Type: application/json" \
  -d '{"contactId": "test123", "body": "Hola"}'
```

### 3. Deploy to Production

#### Option A: Railway (Recommended)
```bash
./quick_deploy.sh railway
# Note the deployment URL (e.g., https://your-webhook.up.railway.app)
```

#### Option B: Docker
```bash
docker build -f Dockerfile.webhook -t webhook-handler .
docker run -p 8000:8000 \
  -e LANGGRAPH_API_KEY=$LANGGRAPH_API_KEY \
  -e LANGGRAPH_API_URL=https://ghl-langgraph-agent-95f8713b0bd6545391589bd2f0ca67eb.us.langgraph.app \
  webhook-handler
```

### 4. Update GoHighLevel Webhook

In GoHighLevel:
1. Go to Settings → Integrations → Webhooks
2. Update the message webhook URL:
   - From: `https://ghl-langgraph-agent-95f8713b0bd6545391589bd2f0ca67eb.us.langgraph.app/webhook/message`
   - To: `https://your-webhook-handler.up.railway.app/webhook/message`

### 5. Verify Success
```bash
./quick_deploy.sh verify
```

Look for:
- ✅ Thread patterns: `conv-xxx` or `contact-xxx`
- ❌ No UUID patterns
- ✅ Agents remember conversation context

## How It Works

```
Before (Broken):
GHL → LangGraph Cloud → UUID thread_id → No memory

After (Fixed):
GHL → Webhook Handler → Set thread_id → LangGraph Cloud → Persistent memory
```

The webhook handler:
1. Receives webhook from GHL
2. Generates consistent thread_id: `conv-{conversationId}` or `contact-{contactId}`
3. Invokes LangGraph Cloud with proper config:
   ```python
   config = {"configurable": {"thread_id": thread_id}}
   ```
4. Returns quick 200 to GHL

## Monitoring

Check LangSmith dashboard for:
- Traces showing consistent thread_ids
- Conversation continuity across messages
- No more repetitive questions from agents

## Troubleshooting

If issues persist:
1. Check webhook handler logs: `railway logs`
2. Verify API key is correct
3. Check LangSmith traces for thread_id patterns
4. Ensure webhook URL is updated in GHL

## Success Metrics

You'll know it's working when:
- Database shows `contact-*` patterns (not UUIDs)
- Maria remembers names between messages
- Lead scores accumulate properly
- No more "What's your name?" after introduction

This webhook handler is the critical piece that ensures LangGraph Cloud uses your thread_id pattern instead of random UUIDs!
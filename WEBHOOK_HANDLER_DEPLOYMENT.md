# Webhook Handler Deployment Guide

## Quick Start

### 1. Set Your API Key
```bash
# Get your API key from https://smith.langchain.com/settings
export LANGGRAPH_API_KEY="lsv2_pt_xxxxx"
```

### 2. Deploy the Handler
```bash
cd langgraph-ghl-agent
./deploy_webhook_handler.sh
```

Choose option 1 for Railway deployment (recommended).

### 3. Update GoHighLevel

In GoHighLevel settings:
1. Go to **Settings → Integrations → Webhooks**
2. Find your message webhook
3. Update the URL:
   - **From**: `https://ghl-langgraph-agent-95f8713b0bd6545391589bd2f0ca67eb.us.langgraph.app/webhook/message`
   - **To**: `https://your-webhook-handler.up.railway.app/webhook/message`

## What This Fixes

### The Problem
Your LangGraph Cloud deployment assigns random UUID thread_ids to each message:
- Message 1: `3798d672-14ac-4195-bfb6-329fd9c1cfe0` 
- Message 2: `887dbb15-d4ed-4c1d-ae13-c03e550fcf68`

This causes complete memory loss between messages.

### The Solution
The webhook handler intercepts webhooks and sets consistent thread_ids:
- Uses `conv-{conversationId}` when available
- Falls back to `contact-{contactId}`
- Ensures LangGraph Cloud uses these IDs for checkpoints

## Architecture

```
Before (Broken):
GHL → LangGraph Cloud → Random UUID → No Memory

After (Fixed):
GHL → Webhook Handler → Set thread_id → LangGraph Cloud → Persistent Memory
```

## Verification

After deployment, send test messages and check LangSmith traces:

✅ **Success indicators:**
- Thread IDs show `conv-xxx` or `contact-xxx` patterns
- Agents remember names and context between messages
- Lead scores accumulate properly
- No repetitive questions

❌ **If still seeing UUIDs:**
- Check webhook URL is updated in GHL
- Verify API key is correct
- Check Railway logs: `railway logs`

## Manual Testing

Test your deployment:
```bash
curl -X POST https://your-handler.up.railway.app/webhook/message \
  -H "Content-Type: application/json" \
  -d '{
    "contactId": "test123",
    "conversationId": "conv456",
    "body": "Hello, this is a test"
  }'
```

Expected response:
```json
{
  "status": "accepted",
  "thread_id": "conv-conv456",
  "message": "Webhook received and processing"
}
```

## Monitoring

### Railway Logs
```bash
railway logs -f
```

### Health Check
```bash
curl https://your-handler.up.railway.app/health
```

### LangSmith Traces
1. Go to https://smith.langchain.com
2. Select your project: `ghl-langgraph-agent`
3. Look for traces with consistent thread_ids

## Troubleshooting

### Handler not receiving webhooks
- Verify GHL webhook URL is updated
- Check Railway deployment status
- Test with curl command above

### Still seeing UUID thread_ids
- Check handler logs for errors
- Verify LANGGRAPH_API_KEY is set
- Ensure handler is invoking with correct config

### 5xx errors from handler
- Check API key permissions
- Verify LangGraph Cloud URL is correct
- Look at detailed error in Railway logs

## Next Steps

Once deployed and verified:
1. Monitor first few conversations
2. Confirm agents maintain context
3. Check lead scoring accumulation
4. Remove any debug logging if needed

This webhook handler is the critical piece that fixes conversation persistence!
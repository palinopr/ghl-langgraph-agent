# Deploy Webhook Handler - Simple Guide

## What This Fixes
Your agents lose memory between messages because LangGraph Cloud assigns random thread IDs. This webhook handler fixes that by intercepting GoHighLevel webhooks and setting consistent thread IDs.

## Quick Deploy to Railway

### 1. Install Railway CLI (if needed)
```bash
curl -fsSL https://railway.app/install.sh | sh
```

### 2. Deploy the Webhook Handler
```bash
cd langgraph-ghl-agent

# Login to Railway
railway login

# Create new project
railway init -n ghl-webhook-handler

# Set your API key
railway variables set LANGGRAPH_API_KEY="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"

# Create Railway configuration
cat > railway.json << 'EOF'
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile.webhook"
  },
  "deploy": {
    "numReplicas": 1,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
EOF

# Create simple Dockerfile
cat > Dockerfile.webhook << 'EOF'
FROM python:3.11-slim
WORKDIR /app
RUN pip install fastapi uvicorn httpx
COPY app/api/webhook_standalone.py app/api/
ENV LANGGRAPH_API_URL=https://ghl-langgraph-agent-95f8713b0bd6545391589bd2f0ca67eb.us.langgraph.app
ENV PORT=8000
CMD ["uvicorn", "app.api.webhook_standalone:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# Deploy to Railway
railway up

# Get your deployment URL
railway domain
```

### 3. Update GoHighLevel

After deployment, update your webhook URL in GoHighLevel:

1. Go to **Settings → Integrations → Webhooks**
2. Update the message webhook URL to: `https://YOUR-RAILWAY-URL/webhook/message`

## Test Your Deployment

Send a test message through GoHighLevel and check LangSmith traces:
- ✅ Thread IDs should show: `conv-{conversationId}` or `contact-{contactId}`
- ✅ Agents should remember conversation context
- ❌ No more random UUID thread IDs

## Monitor Logs
```bash
railway logs -f
```

That's it! Your agents will now remember conversations properly.
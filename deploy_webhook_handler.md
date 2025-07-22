# LangGraph Cloud Webhook Handler Deployment

## Environment Variables Required
```bash
LANGGRAPH_API_URL=https://ghl-langgraph-agent-95f8713b0bd6545391589bd2f0ca67eb.us.langgraph.app
LANGGRAPH_API_KEY=your-api-key-here
LANGGRAPH_ASSISTANT_ID=agent
```

## Deployment Options

### Option A: Deploy as Separate Service (Recommended)
1. Deploy webhook handler to Railway/Heroku/Cloud Run
2. Update GoHighLevel webhook URL to point to:
   `https://your-handler-url/webhook/message`
3. Handler forwards to LangGraph Cloud with proper thread_id

### Option B: Replace Existing Webhook
1. Backup current webhook_simple.py
2. Update app.py to use webhook_langgraph_cloud
3. Redeploy entire application

## Verification Steps
1. Send test message: "Hola, soy Juan"
2. Send follow-up: "¿Cuál es mi nombre?"
3. Agent should remember "Juan" from first message

## Railway Deployment Example

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Initialize project
railway init

# Create Dockerfile for webhook handler
cat > Dockerfile.webhook << EOF
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/api/webhook_langgraph_cloud.py app/api/
CMD ["uvicorn", "app.api.webhook_langgraph_cloud:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# Deploy
railway up
```

## Docker Compose Local Testing

```yaml
# docker-compose.webhook.yml
version: '3.8'
services:
  webhook-handler:
    build:
      context: .
      dockerfile: Dockerfile.webhook
    ports:
      - "8000:8000"
    environment:
      - LANGGRAPH_API_URL=${LANGGRAPH_API_URL}
      - LANGGRAPH_API_KEY=${LANGGRAPH_API_KEY}
      - LANGGRAPH_ASSISTANT_ID=${LANGGRAPH_ASSISTANT_ID}
    restart: unless-stopped
```

## Production Checklist

- [ ] Set all environment variables
- [ ] Configure logging to cloud service
- [ ] Set up health monitoring
- [ ] Configure auto-restart on failure
- [ ] Test webhook endpoint with curl
- [ ] Update GoHighLevel webhook URL
- [ ] Verify thread persistence works
- [ ] Monitor first 100 messages
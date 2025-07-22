# Deploy LangGraph SDK Webhook Proxy

This proxy properly manages thread continuity for your LangGraph Cloud deployment on LangSmith.

## Why This Works

- Uses the official LangGraph SDK to create and manage threads
- Maintains conversation→thread mappings
- Ensures all messages in a conversation use the same LangGraph thread
- Agents will remember conversation context

## Quick Deploy

### 1. Install Dependencies

```bash
pip install langgraph-sdk fastapi uvicorn httpx redis
```

### 2. Create Deployment Files

```bash
# Create requirements
cat > requirements_proxy.txt << EOF
fastapi==0.104.1
uvicorn==0.24.0
httpx==0.25.2
langgraph-sdk==0.1.35
redis==5.0.1
EOF

# Create Dockerfile
cat > Dockerfile.proxy << EOF
FROM python:3.11-slim
WORKDIR /app
COPY requirements_proxy.txt .
RUN pip install --no-cache-dir -r requirements_proxy.txt
COPY app/api/webhook_proxy_sdk.py app/api/
ENV LANGGRAPH_API_URL=https://ghl-langgraph-agent-95f8713b0bd6545391589bd2f0ca67eb.us.langgraph.app
ENV ASSISTANT_ID=agent
ENV PORT=8000
CMD ["uvicorn", "app.api.webhook_proxy_sdk:app", "--host", "0.0.0.0", "--port", "8000"]
EOF
```

### 3. Deploy to Railway

```bash
# Set environment variables
export LANGGRAPH_API_KEY="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"

# Deploy
railway init -n langgraph-proxy
railway variables --set LANGGRAPH_API_KEY=$LANGGRAPH_API_KEY
railway up
railway domain
```

### 4. Update GoHighLevel

Change webhook URL in GoHighLevel to:
```
https://YOUR-PROXY-URL/webhook/message
```

## How It Works

1. **GoHighLevel sends webhook** → Proxy receives it
2. **Proxy checks if conversation has a thread**:
   - If yes: Uses existing LangGraph thread
   - If no: Creates new thread via SDK
3. **Proxy invokes LangGraph** with correct thread_id
4. **LangGraph maintains conversation state** across messages

## Verify It's Working

After deployment, check:

1. **Proxy Health**:
   ```bash
   curl https://YOUR-PROXY-URL/health
   ```

2. **Thread Info**:
   ```bash
   curl https://YOUR-PROXY-URL/threads/CONVERSATION_ID
   ```

3. **LangSmith Traces**:
   - Should show consistent thread_ids per conversation
   - Agents remember context between messages

## Production Considerations

For production, add Redis:

```bash
railway plugin add redis
railway variables --set REDIS_URL=$REDIS_URL
railway up
```

This ensures thread mappings persist across deployments.

## Troubleshooting

- **Check logs**: `railway logs -f`
- **Reset thread**: `DELETE /threads/{conversation_id}`
- **Verify API key**: Check health endpoint

This proxy is the missing piece that ensures proper conversation continuity!
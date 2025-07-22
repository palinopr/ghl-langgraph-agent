# Final Deployment Commands

## Deploy the Webhook Handler to Railway

Run these commands in order:

```bash
# 1. Navigate to project directory
cd /Users/jaimeortiz/open-agent-platform/langgraph-ghl-agent

# 2. Login to Railway (opens browser)
railway login

# 3. Create new Railway project
railway init -n ghl-webhook-handler

# 4. Set environment variables
railway variables set LANGGRAPH_API_KEY="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"
railway variables set PORT=8000

# 5. Deploy to Railway
railway up

# 6. Generate public URL for your service
railway domain
```

## After Deployment

1. Copy the URL from `railway domain` command (e.g., `ghl-webhook-handler.up.railway.app`)

2. Update GoHighLevel webhook:
   - Go to GoHighLevel → Settings → Integrations → Webhooks
   - Update message webhook URL to: `https://YOUR-RAILWAY-URL/webhook/message`

3. Test by sending a message in GoHighLevel

4. Monitor logs:
   ```bash
   railway logs -f
   ```

## What Success Looks Like

In the Railway logs, you should see:
```
Using conversation-based thread_id: conv-{conversationId}
✅ LangGraph invocation successful for thread: conv-{conversationId}
```

In LangSmith traces:
- Thread IDs show pattern `conv-xxx` or `contact-xxx`
- No more UUID thread IDs
- Agents remember conversation context

## Troubleshooting

If deployment fails:
```bash
# Check deployment status
railway status

# View detailed logs
railway logs --tail 100

# Redeploy if needed
railway up --detach
```

## Current Status
- ✅ Webhook handler created and tested locally
- ✅ Railway configuration ready
- ⏳ Ready to deploy - just run the commands above
- ⏳ Then update GoHighLevel webhook URL
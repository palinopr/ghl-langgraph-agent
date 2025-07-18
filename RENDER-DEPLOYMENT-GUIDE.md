# Render Deployment Guide for LangGraph Agent

## Prerequisites
- [x] Render account created
- [x] GitHub repository connected
- [x] Render CLI installed
- [ ] Render CLI authenticated

## Step 1: Authenticate with Render

Run in your terminal:
```bash
render login
```

This will open your browser. Click "Authorize" to generate a CLI token.

## Step 2: Deploy Services

Once authenticated, run:
```bash
cd /Users/jaimeortiz/open-agent-platform/langgraph-ghl-agent
render up
```

This will create:
1. **Web Service** (`ghl-langgraph-agent`) - For webhook endpoints
2. **Background Worker** (`ghl-message-processor`) - For queue processing

## Step 3: Configure Environment Variables

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click on `ghl-langgraph-agent` service
3. Go to "Environment" tab
4. Add these variables:

```env
OPENAI_API_KEY=sk-...
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
GHL_API_TOKEN=your-ghl-token
GHL_LOCATION_ID=your-location-id
GHL_CALENDAR_ID=your-calendar-id
GHL_ASSIGNED_USER_ID=your-user-id
WEBHOOK_SECRET=generate-random-secret
```

5. Click "Save Changes" - services will auto-redeploy

## Step 4: Update GoHighLevel Webhook

1. Your webhook URL will be:
   ```
   https://ghl-langgraph-agent.onrender.com/webhook/message
   ```

2. In GoHighLevel:
   - Go to Settings → Integrations → Webhooks
   - Update the webhook URL
   - Add header: `X-Webhook-Signature: your-webhook-secret`

## Step 5: Verify Deployment

1. Check service logs in Render dashboard
2. Test the health endpoint:
   ```bash
   curl https://ghl-langgraph-agent.onrender.com/health
   ```

3. Send a test message through GoHighLevel

## Monitoring

### View Logs
```bash
render logs ghl-langgraph-agent --tail
render logs ghl-message-processor --tail
```

### Check Status
```bash
render status
```

### Restart Services
```bash
render restart ghl-langgraph-agent
render restart ghl-message-processor
```

## Troubleshooting

### Service Won't Start
- Check logs for missing environment variables
- Verify Python version (should be 3.11)
- Check for import errors

### Messages Not Processing
- Verify webhook URL in GoHighLevel
- Check webhook secret matches
- Look at worker logs for errors

### Database Connection Issues
- Verify Supabase credentials
- Check network connectivity
- Ensure tables exist in Supabase

## Costs

With Render's Individual plan ($7/month):
- ✅ Custom domains
- ✅ Persistent disks
- ✅ Background workers
- ✅ Auto-deploy from Git
- ✅ Free SSL certificates

## Next Steps

1. Set up monitoring alerts
2. Configure custom domain (optional)
3. Set up database backups
4. Monitor usage and scale as needed
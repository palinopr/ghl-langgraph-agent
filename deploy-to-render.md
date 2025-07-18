# Deploy to Render - Step by Step

Since you're authenticated with Render, here's how to deploy your LangGraph agent:

## Option 1: Deploy via Dashboard (Recommended)

1. **Go to Render Dashboard**
   - Visit: https://dashboard.render.com/
   - Click "New +" → "Web Service"

2. **Connect Your Repository**
   - Choose "Build and deploy from a Git repository"
   - Connect your GitHub account if not already connected
   - Select your repository: `open-agent-platform`
   - Set root directory to: `langgraph-ghl-agent`

3. **Configure Web Service**
   - **Name**: `ghl-langgraph-agent`
   - **Region**: Choose closest to you
   - **Branch**: `main`
   - **Root Directory**: `langgraph-ghl-agent`
   - **Runtime**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`

4. **Set Environment Variables**
   Click "Advanced" and add:
   ```
   OPENAI_API_KEY=your-key
   SUPABASE_URL=your-url
   SUPABASE_ANON_KEY=your-key
   GHL_API_TOKEN=your-token
   GHL_LOCATION_ID=your-id
   GHL_CALENDAR_ID=your-id
   GHL_ASSIGNED_USER_ID=your-id
   WEBHOOK_SECRET=generate-random-secret
   PYTHONUNBUFFERED=1
   ```

5. **Create Background Worker**
   - After web service is created, go back to dashboard
   - Click "New +" → "Background Worker"
   - Same repository and settings
   - **Start Command**: `python worker.py`
   - Use same environment variables

## Option 2: Use Blueprint (Automated)

1. **Create render.yaml in your repo** (already done ✓)

2. **Go to**: https://dashboard.render.com/select-repo?type=blueprint

3. **Select your repository**

4. **Render will auto-detect render.yaml and create both services**

5. **Add environment variables in dashboard after creation**

## Your Webhook URL

Once deployed, your webhook URL will be:
```
https://ghl-langgraph-agent.onrender.com/webhook/message
```

## Verify Deployment

Check if services are running:
```bash
# View web service logs
render logs services/ghl-langgraph-agent --tail -o text

# Check service status
render services list -o text
```

## Next Steps

1. Update GoHighLevel webhook URL
2. Test with a message
3. Monitor logs for any issues
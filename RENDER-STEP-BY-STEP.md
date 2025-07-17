# Step-by-Step Render Deployment Guide

## Step 1: Go to Render Dashboard
1. Open your browser
2. Go to: https://dashboard.render.com/
3. You should see your dashboard

## Step 2: Create New Web Service
1. Look for the **"New +"** button (usually purple, in the top right)
2. Click **"New +"**
3. Select **"Web Service"**

![New Service Button Location]
- If you don't see "New +", look for:
  - A purple/blue button
  - "Create" button
  - "New Service" link

## Step 3: Connect Repository
You'll see two options:
- **"Build and deploy from a Git repository"** ← Click this one
- "Deploy an existing image from a registry"

### If GitHub is NOT connected:
1. Click **"Connect GitHub"**
2. Authorize Render to access your repos
3. Select the `open-agent-platform` repository

### If GitHub IS connected:
1. Click **"Connect a repository"**
2. Search for `open-agent-platform`
3. Click **"Connect"** next to it

## Step 4: Configure the Service

You'll see a form with these fields:

**Name**: `ghl-langgraph-agent`

**Region**: Choose closest to you (e.g., Oregon USA)

**Branch**: `main`

**Root Directory**: `langgraph-ghl-agent`
- ⚠️ IMPORTANT: Click the pencil icon next to "Root Directory"
- Type: `langgraph-ghl-agent`
- This tells Render where your app is

**Environment**: Python 3

**Build Command**: 
```
pip install -r requirements.txt
```

**Start Command**:
```
python main.py
```

## Step 5: Choose Instance Type
- Select **"Starter"** ($7/month)
- Or use **"Free"** tier to test first

## Step 6: Add Environment Variables
1. Scroll down to **"Advanced"** section
2. Click **"Add Environment Variable"**
3. Add each of these (click "Add" after each one):

| Key | Value |
|-----|-------|
| PYTHONUNBUFFERED | 1 |
| OPENAI_API_KEY | sk-... (your OpenAI key) |
| SUPABASE_URL | https://xxx.supabase.co |
| SUPABASE_ANON_KEY | eyJ... (your Supabase key) |
| GHL_API_TOKEN | (your GoHighLevel token) |
| GHL_LOCATION_ID | (your location ID) |
| GHL_CALENDAR_ID | (your calendar ID) |
| GHL_ASSIGNED_USER_ID | (your user ID) |
| WEBHOOK_SECRET | (generate a random string) |

## Step 7: Create Web Service
Click the big **"Create Web Service"** button at the bottom

## Step 8: Wait for Deployment
- Render will now build and deploy your service
- This takes 5-10 minutes
- You'll see logs showing the progress

## Step 9: Create Background Worker
After the web service is created:

1. Go back to dashboard: https://dashboard.render.com/
2. Click **"New +"** again
3. Select **"Background Worker"**
4. Same repository (`open-agent-platform`)
5. Same settings except:
   - **Name**: `ghl-message-processor`
   - **Start Command**: `python worker.py`
6. Use the same environment variables
7. Click **"Create Background Worker"**

## Step 10: Get Your Webhook URL
Once deployed, your webhook URL will be:
```
https://ghl-langgraph-agent.onrender.com/webhook/message
```

## Troubleshooting

### Can't find "New +" button?
- Look in the top navigation bar
- Or try: https://dashboard.render.com/new/web

### Repository not showing?
1. Go to: https://dashboard.render.com/account/github
2. Click "Configure" next to GitHub
3. Add `open-agent-platform` to accessible repos

### Build failing?
- Check the logs for missing dependencies
- Make sure root directory is set correctly
- Verify Python version is 3.11

## Alternative: Blueprint Deploy

If the manual steps aren't working:
1. Go to: https://dashboard.render.com/blueprints
2. Click "New Blueprint Instance"
3. Select your repo
4. Render will use the `render.yaml` file automatically
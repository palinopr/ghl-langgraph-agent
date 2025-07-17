#!/bin/bash

# Render API deployment script
API_KEY="rnd_7Hi05GVxCFpucKpdQ3z3x4XZbe2D"
API_URL="https://api.render.com/v1"

echo "🚀 Deploying LangGraph Agent to Render via API"
echo "============================================="

# Function to make API calls
render_api() {
    curl -s -H "Authorization: Bearer $API_KEY" \
         -H "Content-Type: application/json" \
         "$@"
}

# First, let's get your user info and owner ID
echo "Getting account information..."
OWNER_INFO=$(render_api "$API_URL/owners")
OWNER_ID=$(echo $OWNER_INFO | jq -r '.[] | select(.owner.type == "user") | .owner.id' | head -1)

if [ -z "$OWNER_ID" ]; then
    echo "❌ Could not get owner ID. Response:"
    echo $OWNER_INFO | jq .
    exit 1
fi

echo "✅ Found owner ID: $OWNER_ID"

# Create the web service
echo ""
echo "Creating web service..."

WEB_SERVICE_PAYLOAD=$(cat <<EOF
{
  "type": "web_service",
  "name": "ghl-langgraph-agent",
  "ownerId": "$OWNER_ID",
  "repo": "https://github.com/YOUR_GITHUB_USERNAME/open-agent-platform",
  "branch": "main",
  "rootDir": "langgraph-ghl-agent",
  "runtime": "python",
  "buildCommand": "pip install -r requirements.txt",
  "startCommand": "python main.py",
  "envVars": [
    {"key": "PYTHONUNBUFFERED", "value": "1"},
    {"key": "PORT", "value": "8000"}
  ],
  "plan": "starter"
}
EOF
)

WEB_RESPONSE=$(render_api -X POST "$API_URL/services" -d "$WEB_SERVICE_PAYLOAD")
WEB_SERVICE_ID=$(echo $WEB_RESPONSE | jq -r '.service.id')

if [ -z "$WEB_SERVICE_ID" ] || [ "$WEB_SERVICE_ID" = "null" ]; then
    echo "❌ Failed to create web service. Response:"
    echo $WEB_RESPONSE | jq .
else
    echo "✅ Created web service with ID: $WEB_SERVICE_ID"
fi

# Create the background worker
echo ""
echo "Creating background worker..."

WORKER_PAYLOAD=$(cat <<EOF
{
  "type": "background_worker",
  "name": "ghl-message-processor",
  "ownerId": "$OWNER_ID",
  "repo": "https://github.com/YOUR_GITHUB_USERNAME/open-agent-platform",
  "branch": "main",
  "rootDir": "langgraph-ghl-agent",
  "runtime": "python",
  "buildCommand": "pip install -r requirements.txt",
  "startCommand": "python worker.py",
  "envVars": [
    {"key": "PYTHONUNBUFFERED", "value": "1"}
  ],
  "plan": "starter"
}
EOF
)

WORKER_RESPONSE=$(render_api -X POST "$API_URL/services" -d "$WORKER_PAYLOAD")
WORKER_ID=$(echo $WORKER_RESPONSE | jq -r '.service.id')

if [ -z "$WORKER_ID" ] || [ "$WORKER_ID" = "null" ]; then
    echo "❌ Failed to create worker. Response:"
    echo $WORKER_RESPONSE | jq .
else
    echo "✅ Created background worker with ID: $WORKER_ID"
fi

echo ""
echo "================================================"
echo "IMPORTANT: Replace YOUR_GITHUB_USERNAME in this script with your actual GitHub username!"
echo ""
echo "Next steps:"
echo "1. Edit this script and replace YOUR_GITHUB_USERNAME"
echo "2. Run the script again"
echo "3. Go to https://dashboard.render.com to add environment variables"
echo "4. Your webhook URL will be: https://ghl-langgraph-agent.onrender.com/webhook/message"
echo "================================================"
#!/bin/bash
# Render deployment script

echo "🚀 Deploying LangGraph Agent to Render"
echo "======================================"

# Check if render CLI is installed
if ! command -v render &> /dev/null; then
    echo "❌ Render CLI not found. Installing..."
    
    # Install render CLI based on OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        brew tap render-oss/render
        brew install render
    else
        # Linux
        curl -fsSL https://render.com/install.sh | sh
    fi
fi

echo "✅ Render CLI installed"
echo ""
echo "📝 Please follow these steps:"
echo "1. Run: render login"
echo "2. This will open your browser to authenticate"
echo "3. Once authenticated, run this script again"
echo ""
echo "After login, this script will:"
echo "- Create services from render.yaml"
echo "- Set up environment variables"
echo "- Deploy the application"

# Check if already logged in
if render whoami &> /dev/null; then
    echo "✅ Already logged in to Render"
    echo ""
    echo "📦 Creating services..."
    
    # Deploy using render.yaml
    render up
    
    echo ""
    echo "🎉 Deployment initiated!"
    echo ""
    echo "Next steps:"
    echo "1. Go to https://dashboard.render.com"
    echo "2. Find your services:"
    echo "   - ghl-langgraph-agent (web service)"
    echo "   - ghl-message-processor (background worker)"
    echo "3. Add environment variables in the dashboard:"
    echo "   - OPENAI_API_KEY"
    echo "   - SUPABASE_URL"
    echo "   - SUPABASE_ANON_KEY"
    echo "   - GHL_API_TOKEN"
    echo "   - GHL_LOCATION_ID"
    echo "   - GHL_CALENDAR_ID"
    echo "   - GHL_ASSIGNED_USER_ID"
    echo "   - WEBHOOK_SECRET"
    echo ""
    echo "4. Your webhook URL will be:"
    echo "   https://ghl-langgraph-agent.onrender.com/webhook/message"
else
    echo "⚠️  Please run: render login"
fi
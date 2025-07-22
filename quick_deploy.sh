#!/bin/bash
# Quick deployment script for LangGraph Cloud Webhook Handler

echo "🚀 LangGraph Cloud Webhook Handler - Quick Deploy"
echo "================================================"

# Check for required environment variables
if [ -z "$LANGGRAPH_API_KEY" ]; then
    echo "❌ Error: LANGGRAPH_API_KEY not set"
    echo "Please run: export LANGGRAPH_API_KEY='your-api-key'"
    exit 1
fi

# Set default values if not provided
export LANGGRAPH_API_URL="${LANGGRAPH_API_URL:-https://ghl-langgraph-agent-95f8713b0bd6545391589bd2f0ca67eb.us.langgraph.app}"
export LANGGRAPH_ASSISTANT_ID="${LANGGRAPH_ASSISTANT_ID:-agent}"

echo "📋 Configuration:"
echo "  API URL: $LANGGRAPH_API_URL"
echo "  Assistant ID: $LANGGRAPH_ASSISTANT_ID"
echo "  API Key: ***${LANGGRAPH_API_KEY: -4}"
echo ""

# Change to project directory
cd langgraph-ghl-agent

# Option 1: Run locally for testing
if [ "$1" == "local" ]; then
    echo "🏠 Running locally on port 8000..."
    uvicorn app.api.webhook_langgraph_cloud:app --host 0.0.0.0 --port 8000 --reload
    
# Option 2: Deploy to Railway
elif [ "$1" == "railway" ]; then
    echo "🚂 Deploying to Railway..."
    
    # Create minimal Dockerfile
    cat > Dockerfile.webhook << EOF
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/api/webhook_langgraph_cloud.py app/api/
CMD ["uvicorn", "app.api.webhook_langgraph_cloud:app", "--host", "0.0.0.0", "--port", "8000"]
EOF
    
    # Deploy with Railway
    railway up
    
# Option 3: Run verification
elif [ "$1" == "verify" ]; then
    echo "🧪 Running verification script..."
    python verify_thread_persistence.py
    
# Default: Show usage
else
    echo "Usage: ./quick_deploy.sh [command]"
    echo ""
    echo "Commands:"
    echo "  local    - Run webhook handler locally"
    echo "  railway  - Deploy to Railway"
    echo "  verify   - Run verification tests"
    echo ""
    echo "Example:"
    echo "  ./quick_deploy.sh local"
fi
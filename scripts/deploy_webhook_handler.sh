#!/bin/bash
# Deploy webhook handler for LangGraph Cloud thread persistence fix

echo "🚀 Deploying Webhook Handler for Thread Persistence Fix"
echo "===================================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "langgraph.json" ]; then
    echo -e "${RED}❌ Error: Not in langgraph-ghl-agent directory${NC}"
    echo "Please run from the langgraph-ghl-agent directory"
    exit 1
fi

# Check for required environment variable
if [ -z "$LANGGRAPH_API_KEY" ]; then
    echo -e "${RED}❌ Error: LANGGRAPH_API_KEY not set${NC}"
    echo "Please run: export LANGGRAPH_API_KEY='your-api-key'"
    echo "Get your API key from: https://smith.langchain.com/settings"
    exit 1
fi

echo -e "${GREEN}✓ Configuration verified${NC}"
echo "  API Key: ***${LANGGRAPH_API_KEY: -4}"
echo ""

# Step 1: Create minimal webhook service
echo -e "${YELLOW}📦 Creating webhook service files...${NC}"

# Use the standalone webhook handler
WEBHOOK_FILE="app/api/webhook_standalone.py"
echo "Using standalone webhook handler..."

# Create the webhook handler if it doesn't exist
if [ ! -f "$WEBHOOK_FILE" ]; then
    echo -e "${RED}❌ Error: $WEBHOOK_FILE not found${NC}"
    echo "Creating webhook handler..."
    cat > $WEBHOOK_FILE << 'EOF'
"""
Webhook handler that properly sets thread_id for LangGraph Cloud
This ensures conversation persistence by controlling thread_id at the API level
"""
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, Any
import httpx
import os
from datetime import datetime

app = FastAPI(
    title="GHL Webhook Handler for LangGraph Cloud",
    description="Ensures proper thread_id for conversation persistence",
    version="1.0.0"
)

# Configuration
LANGGRAPH_API_URL = os.getenv(
    "LANGGRAPH_API_URL", 
    "https://ghl-langgraph-agent-95f8713b0bd6545391589bd2f0ca67eb.us.langgraph.app"
)
LANGGRAPH_API_KEY = os.getenv("LANGGRAPH_API_KEY")


@app.post("/webhook/message")
async def handle_ghl_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receive webhook from GoHighLevel and invoke LangGraph with proper thread_id
    """
    try:
        webhook_data = await request.json()
        print(f"[{datetime.now()}] Received webhook: {webhook_data}")
        
        # Extract identifiers
        contact_id = webhook_data.get("contactId", webhook_data.get("id"))
        conversation_id = webhook_data.get("conversationId")
        
        if not contact_id:
            return JSONResponse(
                status_code=400,
                content={"error": "Missing contact ID"}
            )
        
        # CRITICAL: Generate consistent thread_id
        if conversation_id:
            thread_id = f"conv-{conversation_id}"
        else:
            thread_id = f"contact-{contact_id}"
        
        print(f"[{datetime.now()}] Using thread_id: {thread_id}")
        
        # Add task to process in background
        background_tasks.add_task(
            invoke_langgraph_cloud,
            webhook_data=webhook_data,
            thread_id=thread_id,
            contact_id=contact_id,
            conversation_id=conversation_id
        )
        
        # Return immediate response to GHL
        return JSONResponse(
            status_code=200,
            content={
                "status": "accepted",
                "thread_id": thread_id,
                "message": "Webhook received and processing"
            }
        )
        
    except Exception as e:
        print(f"[{datetime.now()}] Webhook error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


async def invoke_langgraph_cloud(
    webhook_data: Dict[str, Any],
    thread_id: str,
    contact_id: str,
    conversation_id: str | None
):
    """
    Invoke LangGraph Cloud with proper configuration
    """
    try:
        # Prepare the input for LangGraph
        graph_input = {
            "webhook_data": webhook_data,
            "contact_id": contact_id,
            "thread_id": thread_id,
            "conversation_id": conversation_id,
        }
        
        # CRITICAL: Set thread_id in the configuration
        config = {
            "configurable": {
                "thread_id": thread_id,
            }
        }
        
        # Prepare the invocation request
        invocation_payload = {
            "input": graph_input,
            "config": config,
            "stream_mode": "values"
        }
        
        print(f"[{datetime.now()}] Invoking LangGraph with thread_id: {thread_id}")
        
        # Make the API call to LangGraph Cloud
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"Content-Type": "application/json"}
            if LANGGRAPH_API_KEY:
                headers["x-api-key"] = LANGGRAPH_API_KEY
            
            response = await client.post(
                f"{LANGGRAPH_API_URL}/runs/invoke",
                json=invocation_payload,
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"[{datetime.now()}] ✅ LangGraph invocation successful for thread: {thread_id}")
            else:
                print(f"[{datetime.now()}] ❌ LangGraph invocation failed: {response.status_code}")
                print(f"Response: {response.text}")
                
    except Exception as e:
        print(f"[{datetime.now()}] Error invoking LangGraph: {e}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "webhook-cloud-fix",
        "langgraph_url": LANGGRAPH_API_URL,
        "api_key_configured": bool(LANGGRAPH_API_KEY),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/")
async def root():
    """Root endpoint with instructions"""
    return {
        "service": "GHL Webhook Handler for LangGraph Cloud",
        "purpose": "Ensures proper thread_id for conversation persistence",
        "endpoints": {
            "/webhook/message": "POST - Receive GHL webhooks",
            "/health": "GET - Health check"
        }
    }
EOF
fi

# Create requirements for webhook service
echo -e "${YELLOW}📝 Creating minimal requirements...${NC}"
cat > requirements_webhook.txt << EOF
fastapi==0.104.1
uvicorn==0.24.0
httpx==0.25.2
python-dotenv==1.0.0
EOF

# Create Dockerfile for webhook
echo -e "${YELLOW}🐳 Creating Dockerfile...${NC}"
cat > Dockerfile.webhook << EOF
FROM python:3.11-slim

WORKDIR /app

# Install minimal requirements
COPY requirements_webhook.txt .
RUN pip install --no-cache-dir -r requirements_webhook.txt

# Copy only the webhook handler
COPY app/api/webhook_standalone.py app/api/

# Set environment variables
ENV LANGGRAPH_API_URL=https://ghl-langgraph-agent-95f8713b0bd6545391589bd2f0ca67eb.us.langgraph.app
ENV PORT=8000

# Run the webhook handler
CMD ["uvicorn", "app.api.webhook_standalone:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# Step 2: Test locally
echo ""
echo -e "${YELLOW}🧪 Testing webhook handler locally...${NC}"
echo "Starting local server..."

# Start server in background
LANGGRAPH_API_KEY=$LANGGRAPH_API_KEY uvicorn app.api.webhook_standalone:app --host 0.0.0.0 --port 8000 > webhook.log 2>&1 &
SERVER_PID=$!

# Wait for server to start
sleep 3

# Test health endpoint
echo "Testing health endpoint..."
if curl -s http://localhost:8000/health | grep -q "healthy"; then
    echo -e "${GREEN}✓ Health check passed${NC}"
else
    echo -e "${RED}❌ Health check failed${NC}"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

# Test webhook endpoint
echo "Testing webhook endpoint..."
TEST_RESPONSE=$(curl -s -X POST http://localhost:8000/webhook/message \
  -H "Content-Type: application/json" \
  -d '{"contactId": "test123", "body": "Test message", "conversationId": "conv456"}')

if echo "$TEST_RESPONSE" | grep -q "conv-conv456"; then
    echo -e "${GREEN}✓ Webhook test passed - thread_id generated correctly${NC}"
else
    echo -e "${RED}❌ Webhook test failed${NC}"
    echo "Response: $TEST_RESPONSE"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

# Stop test server
kill $SERVER_PID 2>/dev/null
echo -e "${GREEN}✓ Local tests passed${NC}"
echo ""

# Step 3: Deploy options
echo -e "${YELLOW}📍 Choose deployment option:${NC}"
echo "1) Deploy to Railway (recommended)"
echo "2) Deploy with Docker locally"
echo "3) Get deployment instructions only"
echo ""
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo -e "${YELLOW}🚂 Deploying to Railway...${NC}"
        
        # Check if railway CLI is installed
        if ! command -v railway &> /dev/null; then
            echo -e "${RED}Railway CLI not found. Installing...${NC}"
            curl -fsSL https://railway.app/install.sh | sh
        fi
        
        # Create railway.json
        cat > railway.json << EOF
{
  "\$schema": "https://railway.app/railway.schema.json",
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
        
        # Login to Railway
        echo "Please login to Railway..."
        railway login
        
        # Create new project
        echo "Creating Railway project..."
        railway init -n ghl-webhook-handler
        
        # Set environment variables
        railway variables set LANGGRAPH_API_KEY=$LANGGRAPH_API_KEY
        railway variables set PORT=8000
        
        # Deploy
        echo "Deploying to Railway..."
        railway up
        
        # Get deployment URL
        DEPLOY_URL=$(railway domain)
        echo ""
        echo -e "${GREEN}✅ Deployment complete!${NC}"
        echo -e "${GREEN}Webhook URL: https://$DEPLOY_URL/webhook/message${NC}"
        echo ""
        echo -e "${YELLOW}📋 Next steps:${NC}"
        echo "1. Update GoHighLevel webhook URL to: https://$DEPLOY_URL/webhook/message"
        echo "2. Send a test message to verify thread persistence"
        echo "3. Check Railway logs: railway logs"
        ;;
        
    2)
        echo -e "${YELLOW}🐳 Building Docker image...${NC}"
        docker build -f Dockerfile.webhook -t ghl-webhook-handler .
        
        echo -e "${YELLOW}🏃 Running Docker container...${NC}"
        docker run -d \
            --name ghl-webhook-handler \
            -p 8000:8000 \
            -e LANGGRAPH_API_KEY=$LANGGRAPH_API_KEY \
            ghl-webhook-handler
        
        echo ""
        echo -e "${GREEN}✅ Docker container running!${NC}"
        echo -e "${GREEN}Webhook URL: http://localhost:8000/webhook/message${NC}"
        echo ""
        echo -e "${YELLOW}📋 For production deployment:${NC}"
        echo "1. Deploy this container to your cloud provider"
        echo "2. Set up HTTPS/SSL"
        echo "3. Update GoHighLevel webhook URL"
        echo ""
        echo "View logs: docker logs -f ghl-webhook-handler"
        ;;
        
    3)
        echo ""
        echo -e "${YELLOW}📋 Manual Deployment Instructions:${NC}"
        echo ""
        echo "1. Deploy the webhook handler to your preferred platform:"
        echo "   - The handler is in: app/api/webhook_cloud_fix.py"
        echo "   - Requirements: requirements_webhook.txt"
        echo "   - Dockerfile: Dockerfile.webhook"
        echo ""
        echo "2. Set environment variables:"
        echo "   LANGGRAPH_API_KEY=$LANGGRAPH_API_KEY"
        echo "   LANGGRAPH_API_URL=https://ghl-langgraph-agent-95f8713b0bd6545391589bd2f0ca67eb.us.langgraph.app"
        echo ""
        echo "3. Update GoHighLevel webhook:"
        echo "   From: https://ghl-langgraph-agent-95f8713b0bd6545391589bd2f0ca67eb.us.langgraph.app/webhook/message"
        echo "   To: https://your-deployment-url/webhook/message"
        echo ""
        echo "4. Test with a message to verify thread_id persistence"
        ;;
esac

echo ""
echo -e "${GREEN}🎯 Summary:${NC}"
echo "The webhook handler intercepts GHL webhooks and ensures proper thread_id"
echo "configuration before invoking LangGraph Cloud. This fixes the conversation"
echo "memory loss issue by using consistent thread IDs like 'conv-123' instead"
echo "of random UUIDs."
echo ""
echo -e "${YELLOW}🔍 Verification:${NC}"
echo "After deployment, check LangSmith traces to confirm:"
echo "- Thread IDs follow pattern: conv-{conversationId} or contact-{contactId}"
echo "- Messages maintain conversation context"
echo "- Agents remember previous interactions"
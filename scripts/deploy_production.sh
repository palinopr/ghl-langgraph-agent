#!/bin/bash
# Production deployment script for LangGraph Cloud Webhook Handler
# Using LangChain Smith API

echo "🚀 LangGraph Cloud Webhook Handler - Production Deploy"
echo "======================================================"

# Load environment variables from .env.webhook
if [ -f ".env.webhook" ]; then
    export $(cat .env.webhook | grep -v '^#' | xargs)
    echo "✅ Loaded environment from .env.webhook"
else
    echo "❌ Error: .env.webhook file not found"
    exit 1
fi

# Verify required variables
if [ -z "$LANGGRAPH_API_KEY" ]; then
    echo "❌ Error: LANGGRAPH_API_KEY not set in .env.webhook"
    exit 1
fi

echo ""
echo "📋 Configuration:"
echo "  API URL: $LANGGRAPH_API_URL"
echo "  Deployment URL: $LANGGRAPH_DEPLOYMENT_URL"
echo "  Assistant ID: $LANGGRAPH_ASSISTANT_ID"
echo "  API Key: lsv2_pt_***${LANGGRAPH_API_KEY: -10}"
echo ""

# Option 1: Test locally first
if [ "$1" == "test" ]; then
    echo "🧪 Testing webhook handler locally..."
    echo ""
    
    # Start the server in background
    uvicorn app.api.webhook_langgraph_cloud:app --host 0.0.0.0 --port 8000 &
    SERVER_PID=$!
    
    # Wait for server to start
    sleep 5
    
    # Test health endpoint
    echo "Testing health endpoint..."
    curl -s http://localhost:8000/health | python -m json.tool
    
    # Test webhook with sample data
    echo -e "\n\nTesting webhook endpoint..."
    curl -X POST http://localhost:8000/webhook/message \
        -H "Content-Type: application/json" \
        -d '{
            "contactId": "test-contact-123",
            "conversationId": "test-conv-456",
            "body": "Test message for thread persistence",
            "type": "Contact",
            "locationId": "test-location"
        }' | python -m json.tool
    
    # Kill the server
    kill $SERVER_PID
    
    echo -e "\n✅ Local test complete"

# Option 2: Deploy to production
elif [ "$1" == "deploy" ]; then
    echo "🌐 Deploying to production..."
    
    # Create optimized Dockerfile
    cat > Dockerfile.production << EOF
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app/api/webhook_langgraph_cloud.py app/api/
COPY .env.webhook .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "app.api.webhook_langgraph_cloud:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

    echo "✅ Dockerfile created"
    
    # Deploy based on platform
    if [ "$2" == "railway" ]; then
        echo "Deploying to Railway..."
        railway up
    elif [ "$2" == "docker" ]; then
        echo "Building Docker image..."
        docker build -f Dockerfile.production -t langgraph-webhook-handler .
        echo "Run with: docker run -p 8000:8000 --env-file .env.webhook langgraph-webhook-handler"
    else
        echo "Please specify deployment platform: railway or docker"
        echo "Example: ./deploy_production.sh deploy railway"
    fi

# Option 3: Verify production deployment
elif [ "$1" == "verify" ]; then
    if [ -z "$2" ]; then
        echo "Please provide the production URL"
        echo "Example: ./deploy_production.sh verify https://your-handler.railway.app"
        exit 1
    fi
    
    PROD_URL=$2
    echo "🔍 Verifying production deployment at: $PROD_URL"
    
    # Test health
    echo -e "\nHealth check:"
    curl -s $PROD_URL/health | python -m json.tool
    
    # Test webhook
    echo -e "\n\nWebhook test:"
    curl -X POST $PROD_URL/webhook/message \
        -H "Content-Type: application/json" \
        -d '{
            "contactId": "verify-contact-789",
            "conversationId": "verify-conv-012",
            "body": "Production verification test",
            "type": "Contact",
            "locationId": "prod-location"
        }' | python -m json.tool
    
    echo -e "\n✅ Production verification complete"

# Option 4: Update GoHighLevel
elif [ "$1" == "update-ghl" ]; then
    if [ -z "$2" ]; then
        echo "Please provide the production webhook URL"
        echo "Example: ./deploy_production.sh update-ghl https://your-handler.railway.app"
        exit 1
    fi
    
    WEBHOOK_URL=$2
    echo "📝 GoHighLevel Webhook Update Instructions"
    echo "=========================================="
    echo ""
    echo "1. Log into GoHighLevel"
    echo "2. Navigate to: Settings → Integrations → Webhooks"
    echo "3. Update webhook URL to:"
    echo "   $WEBHOOK_URL/webhook/message"
    echo ""
    echo "4. Test with a message containing:"
    echo "   'Hola, soy Carlos y tengo un restaurante'"
    echo ""
    echo "5. Follow up with:"
    echo "   '¿Cuál es mi nombre?'"
    echo ""
    echo "The agent should remember 'Carlos' from the first message!"

else
    echo "Usage: ./deploy_production.sh [command] [options]"
    echo ""
    echo "Commands:"
    echo "  test              - Test webhook handler locally"
    echo "  deploy railway    - Deploy to Railway"
    echo "  deploy docker     - Build Docker image"
    echo "  verify [url]      - Verify production deployment"
    echo "  update-ghl [url]  - Instructions to update GoHighLevel"
    echo ""
    echo "Examples:"
    echo "  ./deploy_production.sh test"
    echo "  ./deploy_production.sh deploy railway"
    echo "  ./deploy_production.sh verify https://my-handler.railway.app"
fi
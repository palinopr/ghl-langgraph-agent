#!/bin/bash

# Deploy to LangGraph Cloud Script
# This script handles the complete deployment process

set -e  # Exit on error

echo "🚀 Starting LangGraph Cloud Deployment..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Step 1: Check prerequisites
echo -e "${YELLOW}📋 Checking prerequisites...${NC}"

if ! command_exists langgraph; then
    echo -e "${RED}❌ LangGraph CLI not found. Installing...${NC}"
    pip install -U langgraph-cli
fi

if [ -z "$LANGSMITH_API_KEY" ]; then
    echo -e "${RED}❌ LANGSMITH_API_KEY not set. Please set it first:${NC}"
    echo "export LANGSMITH_API_KEY='your-api-key'"
    exit 1
fi

# Step 2: Clean up old files
echo -e "${YELLOW}🧹 Cleaning up old deployment files...${NC}"
rm -rf .langgraph_api
rm -f langgraph-deploy.json

# Step 3: Stage production files
echo -e "${YELLOW}📦 Staging production files...${NC}"
git add langgraph.json
git add app/workflow_production_ready.py
git add api/webhook_production.py
git add requirements_production.txt
git add DEPLOYMENT_INSTRUCTIONS.md

# Step 4: Create deployment configuration
echo -e "${YELLOW}⚙️  Creating deployment configuration...${NC}"
cat > langgraph-deploy.json << EOF
{
  "name": "ghl-langgraph-agent",
  "version": "3.1.1",
  "description": "GoHighLevel Multi-Agent System",
  "graphs": {
    "agent": "./app/workflow_production_ready.py:workflow"
  },
  "dependencies": ["."],
  "env": ".env",
  "python_version": "3.13",
  "environment_variables": {
    "LANGCHAIN_PROJECT": "ghl-langgraph-agent",
    "LANGCHAIN_TRACING_V2": "true"
  }
}
EOF

# Step 5: Validate workflow
echo -e "${YELLOW}✅ Validating workflow...${NC}"
python -c "
try:
    from app.workflow_production_ready import workflow
    print('✅ Workflow imports successfully')
except Exception as e:
    print(f'❌ Workflow validation failed: {e}')
    exit(1)
"

# Step 6: Deploy to LangGraph Cloud
echo -e "${GREEN}🚀 Deploying to LangGraph Cloud...${NC}"
echo "This will:"
echo "1. Build your graph"
echo "2. Upload to LangGraph Cloud"
echo "3. Start your deployment"
echo ""
echo "Press Enter to continue or Ctrl+C to cancel..."
read

# Deploy with production configuration
langgraph deploy \
  --langsmith-api-key "$LANGSMITH_API_KEY" \
  --name "ghl-langgraph-agent-prod" \
  --description "Production GoHighLevel Multi-Agent System"

# Step 7: Get deployment info
echo -e "${GREEN}📊 Deployment Information:${NC}"
echo "Your deployment should now be available at:"
echo "https://smith.langchain.com/studio"
echo ""
echo "Webhook URL will be:"
echo "https://your-deployment-id.graphs.langchain.com/webhook"
echo ""
echo -e "${YELLOW}📝 Next Steps:${NC}"
echo "1. Go to https://smith.langchain.com/studio"
echo "2. Find your deployment"
echo "3. Copy the deployment URL"
echo "4. Update your GoHighLevel webhook URL"
echo "5. Test with a message!"

# Step 8: Create production environment file template
echo -e "${YELLOW}📄 Creating production .env template...${NC}"
cat > .env.production << EOF
# LangGraph Cloud Production Environment
LANGSMITH_API_KEY=${LANGSMITH_API_KEY}
LANGCHAIN_PROJECT=ghl-langgraph-agent
LANGCHAIN_TRACING_V2=true

# OpenAI
OPENAI_API_KEY=your-openai-key

# GoHighLevel
GHL_API_TOKEN=your-ghl-token
GHL_LOCATION_ID=your-location-id

# Supabase (if using)
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key
EOF

echo -e "${GREEN}✅ Deployment script completed!${NC}"
echo ""
echo "To monitor your deployment:"
echo "1. Go to https://smith.langchain.com"
echo "2. Click on your project"
echo "3. View traces in real-time"
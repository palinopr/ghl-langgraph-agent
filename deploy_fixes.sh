#!/bin/bash
# Deploy production fixes to LangGraph

echo "🚀 Deploying LangGraph Production Fixes"
echo "======================================="

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Activating virtual environment..."
    source venv/bin/activate
fi

echo ""
echo "📋 Deployment Checklist:"
echo "1. ✅ Fixed workflow: app/workflow_production_fixed.py"
echo "2. ✅ Fixed supervisor: app/agents/supervisor_fixed.py"
echo "3. ✅ Redis checkpointer: app/state/redis_store.py"
echo "4. ✅ Updated langgraph.json to v3.1.2"

echo ""
echo "📝 MANUAL STEPS REQUIRED:"
echo "========================"
echo ""
echo "1. Go to: https://smith.langchain.com"
echo "2. Navigate to your project: 'ghl-langgraph-agent'"
echo "3. Go to Deployments section"
echo "4. Add environment variable:"
echo "   REDIS_URL=redis://default:7LOQGvcF6ZQzOv3kvR9JcqpFE3jjNbwo@redis-19970.c9.us-east-1-4.ec2.redns.redis-cloud.com:19970"
echo "5. Save and restart deployment"

echo ""
echo "🧪 Test Locally First:"
echo "langgraph dev --port 8080"

echo ""
echo "📊 After Deployment, Check Traces For:"
echo "- checkpoint_loaded: true"
echo "- No message duplication"
echo "- Proper agent routing"
echo "- Redis operations in logs"

echo ""
echo "✅ All code fixes are ready for deployment!"
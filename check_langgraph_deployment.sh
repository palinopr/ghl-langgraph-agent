#!/bin/bash

# Check LangGraph deployment status using curl
API_KEY="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"
BASE_URL="https://api.smith.langchain.com"

echo "Checking LangGraph Platform deployment..."
echo "========================================"

# Check if deployment exists (this will give us info about the deployment)
curl -s -X GET \
  "${BASE_URL}/deployments" \
  -H "x-api-key: ${API_KEY}" \
  -H "Content-Type: application/json" | python3 -m json.tool

echo -e "\n\nTo check deployment in the UI:"
echo "1. Go to https://smith.langchain.com"
echo "2. Click 'LangGraph Platform' in the left menu"
echo "3. Look for 'ghl-langgraph-agent' deployment"
echo "4. Check build logs and status"
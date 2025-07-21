#!/usr/bin/env python3
"""
LangGraph Deployment Information
Deployment ID: b91140bf-d8b2-4d1f-b36a-53f18f2db65d
"""

import os

# Read API key from .env file
api_key = None
try:
    with open('.env', 'r') as f:
        for line in f:
            if line.startswith('LANGCHAIN_API_KEY='):
                api_key = line.split('=', 1)[1].strip()
                break
except:
    pass

if not api_key:
    api_key = "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"

deployment_id = "b91140bf-d8b2-4d1f-b36a-53f18f2db65d"

print(f"""
🚀 LangGraph Deployment Access Guide
===================================

Deployment ID: {deployment_id}
API Key: {api_key[:20]}...

📋 Access Methods:
-----------------

1️⃣ View in LangSmith UI:
   https://smith.langchain.com/deployments/{deployment_id}

2️⃣ Get Deployment Info (curl):
   curl -X GET \\
     "https://api.smith.langchain.com/deployments/{deployment_id}" \\
     -H "x-api-key: {api_key}" \\
     -H "Content-Type: application/json"

3️⃣ List Recent Runs:
   curl -X GET \\
     "https://api.smith.langchain.com/runs?project_name=ghl-langgraph-agent&limit=10" \\
     -H "x-api-key: {api_key}" \\
     -H "Content-Type: application/json"

4️⃣ Invoke the Deployment:
   The deployment endpoint depends on your LangGraph Cloud URL.
   Common patterns:
   
   - https://[deployment-id].us.langgraph.app/runs/stream
   - https://api.langchain.com/v1/deployments/{deployment_id}/invoke
   - https://[your-org].langgraph.cloud/deployments/{deployment_id}/invoke

5️⃣ Test Invocation:
   curl -X POST \\
     "https://{deployment_id}.us.langgraph.app/runs/stream" \\
     -H "x-api-key: {api_key}" \\
     -H "Content-Type: application/json" \\
     -d '{{
       "assistant_id": "agent",
       "input": {{
         "messages": [{{"role": "user", "content": "Hola, necesito automatizar mi negocio"}}],
         "contact_id": "test_123",
         "webhook_data": {{
           "locationId": "sHFG9Rw6BdGh6d6bfMqG",
           "type": "WhatsAppMessage"
         }}
       }},
       "stream_mode": "updates"
     }}'

6️⃣ Python SDK Access:
   from langsmith import Client
   
   client = Client(api_key="{api_key[:20]}...")
   
   # Get deployment info
   deployment = client.get_deployment("{deployment_id}")
   
   # List runs
   runs = list(client.list_runs(
       project_name="ghl-langgraph-agent",
       limit=10
   ))

📊 Project Details:
------------------
- Project: ghl-langgraph-agent  
- Type: LangGraph Cloud Deployment
- Region: US (based on deployment ID)
- Status: Check LangSmith UI

🔍 Debugging Tips:
-----------------
1. Check deployment status in LangSmith UI first
2. Look for the deployment URL in your LangSmith dashboard
3. Verify API key has proper permissions
4. Check project name matches ("ghl-langgraph-agent")

""")

# Try to get more info
print("\n🔧 Quick Checks:")
print("-" * 50)
print(f"✓ Deployment ID: {deployment_id}")
print(f"✓ API Key Found: {'Yes' if api_key else 'No'}")
print(f"✓ API Key Format: {'Valid (lsv2_pt_...)' if api_key.startswith('lsv2_pt_') else 'Invalid'}")
print(f"✓ Project: ghl-langgraph-agent")
print(f"✓ Agent ID: agent")

print("\n📝 Next Steps:")
print("-" * 50)
print("1. Open https://smith.langchain.com in your browser")
print("2. Navigate to Deployments section")
print(f"3. Search for deployment: {deployment_id}")
print("4. Copy the deployment URL from the dashboard")
print("5. Use the URL with the curl commands above")
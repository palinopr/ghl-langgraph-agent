#!/usr/bin/env python3
"""
Access LangGraph deployment using LangSmith API
Deployment ID: b91140bf-d8b2-4d1f-b36a-53f18f2db65d
"""

import os
import json
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

def main():
    deployment_id = "b91140bf-d8b2-4d1f-b36a-53f18f2db65d"
    api_key = os.getenv("LANGCHAIN_API_KEY")
    
    if not api_key:
        print("ERROR: LANGCHAIN_API_KEY not found in .env")
        return
    
    print(f"LangGraph Deployment Access")
    print(f"=========================")
    print(f"Deployment ID: {deployment_id}")
    print(f"API Key: {api_key[:20]}...")
    
    # The deployment ID appears to be a LangGraph Cloud deployment
    # This can be accessed through the LangSmith API
    
    print("\n📋 How to Access This Deployment:")
    print("-" * 50)
    
    print("\n1. Using LangSmith SDK:")
    print(f"""
from langsmith import Client

client = Client(api_key="{api_key[:20]}...")

# Get traces for this deployment
runs = list(client.list_runs(
    filter='eq(deployment_id, "{deployment_id}")',
    limit=10
))

for run in runs:
    print(f"Run ID: {{run.id}}")
    print(f"Status: {{run.status}}")
    print(f"Created: {{run.created_at}}")
""")
    
    print("\n2. Using HTTP API:")
    print(f"""
curl -X GET \\
  "https://api.smith.langchain.com/runs?filter=eq(deployment_id,\\"{deployment_id}\\")&limit=10" \\
  -H "x-api-key: {api_key[:20]}..." \\
  -H "Content-Type: application/json"
""")
    
    print("\n3. To Invoke the Deployment:")
    print(f"""
curl -X POST \\
  "https://YOUR-DEPLOYMENT-URL.us.langgraph.app/runs/stream" \\
  -H "x-api-key: {api_key[:20]}..." \\
  -H "Content-Type: application/json" \\
  -d '{{
    "assistant_id": "agent",
    "input": {{
      "messages": [{{"role": "user", "content": "Hola"}}],
      "contact_id": "test123"
    }}
  }}'
""")
    
    print("\n4. View in LangSmith UI:")
    print(f"https://smith.langchain.com/deployments/{deployment_id}")
    
    print("\n📊 Deployment Details:")
    print("-" * 50)
    print("Project: ghl-langgraph-agent")
    print("Type: LangGraph Cloud Deployment")
    print("Status: Check LangSmith UI for current status")
    
    # Try to access using langsmith if available
    try:
        import langsmith
        client = langsmith.Client(api_key=api_key)
        
        print("\n🔍 Checking Recent Runs...")
        print("-" * 50)
        
        # Try to get runs
        runs = list(client.list_runs(
            project_name="ghl-langgraph-agent",
            limit=5,
            execution_order=1
        ))
        
        if runs:
            print(f"Found {len(runs)} recent runs:")
            for run in runs:
                print(f"\n- Run ID: {run.id}")
                print(f"  Status: {run.status}")
                print(f"  Start: {run.start_time}")
                if run.inputs and 'messages' in run.inputs:
                    msgs = run.inputs['messages']
                    if msgs and len(msgs) > 0:
                        last_msg = msgs[-1]
                        if isinstance(last_msg, dict) and 'content' in last_msg:
                            print(f"  Message: {last_msg['content'][:50]}...")
        else:
            print("No recent runs found")
            
    except ImportError:
        print("\n⚠️  LangSmith SDK not installed. Install with: pip install langsmith")
    except Exception as e:
        print(f"\n⚠️  Error accessing LangSmith: {e}")

if __name__ == "__main__":
    main()
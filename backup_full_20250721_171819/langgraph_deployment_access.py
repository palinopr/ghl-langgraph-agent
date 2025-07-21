#!/usr/bin/env python3
"""
Access LangGraph Cloud Deployment
Deployment ID: b91140bf-d8b2-4d1f-b36a-53f18f2db65d
"""

import os
import httpx
import asyncio
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import json
from datetime import datetime

# Load environment variables
load_dotenv()

class LangGraphCloudClient:
    """Client for LangGraph Cloud deployments"""
    
    def __init__(self, deployment_id: str):
        self.deployment_id = deployment_id
        self.api_key = os.getenv("LANGCHAIN_API_KEY")
        
        if not self.api_key:
            raise ValueError("LANGCHAIN_API_KEY not found in environment variables")
        
        # LangGraph Cloud endpoints
        self.base_url = "https://api.langchain.com"
        
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
    
    async def get_deployment_status(self) -> Dict[str, Any]:
        """Check deployment status"""
        async with httpx.AsyncClient() as client:
            try:
                # Try different possible endpoints
                endpoints = [
                    f"/v1/deployments/{self.deployment_id}",
                    f"/langgraph/deployments/{self.deployment_id}",
                    f"/deployments/{self.deployment_id}"
                ]
                
                for endpoint in endpoints:
                    try:
                        response = await client.get(
                            f"{self.base_url}{endpoint}",
                            headers=self.headers
                        )
                        if response.status_code == 200:
                            return response.json()
                    except:
                        continue
                
                return {"error": "Could not find deployment endpoint"}
                
            except Exception as e:
                return {"error": str(e)}
    
    async def invoke_agent(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke the agent deployment"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                # Standard LangGraph Cloud invocation endpoint
                response = await client.post(
                    f"{self.base_url}/v1/runs",
                    headers=self.headers,
                    json={
                        "deployment_id": self.deployment_id,
                        "input": input_data,
                        "config": {
                            "metadata": {
                                "source": "api",
                                "timestamp": datetime.now().isoformat()
                            }
                        }
                    }
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {
                        "error": f"HTTP {response.status_code}",
                        "detail": response.text
                    }
                    
            except Exception as e:
                return {"error": str(e)}
    
    async def get_traces(self, limit: int = 10) -> Dict[str, Any]:
        """Get recent traces/runs for this deployment"""
        async with httpx.AsyncClient() as client:
            try:
                # LangSmith traces endpoint
                response = await client.get(
                    "https://api.smith.langchain.com/runs",
                    headers={
                        "x-api-key": self.api_key,
                        "Content-Type": "application/json"
                    },
                    params={
                        "filter": f'eq(deployment_id, "{self.deployment_id}")',
                        "limit": limit,
                        "order": "desc"
                    }
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"HTTP {response.status_code}"}
                    
            except Exception as e:
                return {"error": str(e)}

async def test_deployment_access():
    """Test accessing the deployment"""
    deployment_id = "b91140bf-d8b2-4d1f-b36a-53f18f2db65d"
    
    print(f"Testing access to LangGraph deployment: {deployment_id}")
    print("=" * 60)
    
    client = LangGraphCloudClient(deployment_id)
    
    # 1. Check deployment status
    print("\n1. Checking deployment status...")
    status = await client.get_deployment_status()
    print(json.dumps(status, indent=2))
    
    # 2. Test invocation
    print("\n2. Testing agent invocation...")
    test_message = {
        "messages": [
            {"role": "user", "content": "Hola, necesito automatizar mi negocio"}
        ],
        "contact_id": "test_" + datetime.now().strftime("%Y%m%d_%H%M%S"),
        "webhook_data": {
            "type": "WhatsAppMessage",
            "locationId": "test_location"
        }
    }
    
    result = await client.invoke_agent(test_message)
    print(json.dumps(result, indent=2))
    
    # 3. Get recent traces
    print("\n3. Getting recent traces...")
    traces = await client.get_traces(limit=5)
    print(json.dumps(traces, indent=2))

# Using curl commands as alternative
def show_curl_examples():
    """Show curl commands for direct API access"""
    deployment_id = "b91140bf-d8b2-4d1f-b36a-53f18f2db65d"
    api_key = os.getenv("LANGCHAIN_API_KEY", "your-api-key")
    
    print("\n" + "=" * 60)
    print("CURL EXAMPLES FOR DIRECT API ACCESS")
    print("=" * 60)
    
    print("\n1. Get deployment info:")
    print(f"""
curl -X GET \\
  "https://api.langchain.com/v1/deployments/{deployment_id}" \\
  -H "X-API-Key: {api_key}" \\
  -H "Content-Type: application/json"
""")
    
    print("\n2. Invoke the deployment:")
    print(f"""
curl -X POST \\
  "https://api.langchain.com/v1/runs" \\
  -H "X-API-Key: {api_key}" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "deployment_id": "{deployment_id}",
    "input": {{
      "messages": [{{"role": "user", "content": "Hola"}}],
      "contact_id": "test123"
    }}
  }}'
""")
    
    print("\n3. Get traces from LangSmith:")
    print(f"""
curl -X GET \\
  "https://api.smith.langchain.com/runs?filter=eq(deployment_id,\\"{deployment_id}\\")&limit=10" \\
  -H "x-api-key: {api_key}" \\
  -H "Content-Type: application/json"
""")

if __name__ == "__main__":
    print("LangGraph Cloud Deployment Access")
    print("=================================\n")
    
    # Check for API key
    if not os.getenv("LANGCHAIN_API_KEY"):
        print("ERROR: LANGCHAIN_API_KEY not found")
        print("\nPlease set it in your .env file:")
        print("LANGCHAIN_API_KEY=lsv2_pt_...")
        exit(1)
    
    # Run async test
    asyncio.run(test_deployment_access())
    
    # Show curl examples
    show_curl_examples()
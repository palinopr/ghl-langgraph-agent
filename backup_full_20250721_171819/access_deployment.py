#!/usr/bin/env python3
"""
Access LangGraph deployment via LangSmith API
Deployment ID: b91140bf-d8b2-4d1f-b36a-53f18f2db65d
"""

import os
import httpx
import asyncio
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

class LangGraphDeploymentClient:
    """Client for accessing LangGraph deployments via API"""
    
    def __init__(self, deployment_id: str):
        self.deployment_id = deployment_id
        self.api_key = os.getenv("LANGCHAIN_API_KEY")
        
        if not self.api_key:
            raise ValueError("LANGCHAIN_API_KEY not found in environment variables")
        
        # LangGraph Cloud API endpoint
        self.base_url = "https://api.langchain.com/v1"
        
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
    
    async def get_deployment_info(self) -> Dict[str, Any]:
        """Get deployment information"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/deployments/{self.deployment_id}",
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                print(f"Error getting deployment info: {e}")
                return {}
    
    async def invoke_deployment(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke the deployment with input data"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                # LangGraph Cloud uses /runs endpoint for invocations
                response = await client.post(
                    f"{self.base_url}/deployments/{self.deployment_id}/runs",
                    headers=self.headers,
                    json={
                        "input": input_data,
                        "config": {}
                    }
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                print(f"Error invoking deployment: {e}")
                if hasattr(e, 'response') and e.response:
                    print(f"Response: {e.response.text}")
                return {}
    
    async def stream_deployment(self, input_data: Dict[str, Any]):
        """Stream responses from the deployment"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                # Stream endpoint
                async with client.stream(
                    "POST",
                    f"{self.base_url}/deployments/{self.deployment_id}/stream",
                    headers=self.headers,
                    json={
                        "input": input_data,
                        "config": {}
                    }
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            yield json.loads(line)
            except httpx.HTTPError as e:
                print(f"Error streaming deployment: {e}")
                if hasattr(e, 'response') and e.response:
                    print(f"Response: {e.response.text}")
    
    async def get_runs(self, limit: int = 10) -> Dict[str, Any]:
        """Get recent runs for this deployment"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/deployments/{self.deployment_id}/runs",
                    headers=self.headers,
                    params={"limit": limit}
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                print(f"Error getting runs: {e}")
                return {}

async def test_deployment():
    """Test the deployment access"""
    deployment_id = "b91140bf-d8b2-4d1f-b36a-53f18f2db65d"
    client = LangGraphDeploymentClient(deployment_id)
    
    print(f"Accessing deployment: {deployment_id}")
    print("=" * 50)
    
    # Get deployment info
    print("\n1. Getting deployment info...")
    info = await client.get_deployment_info()
    if info:
        print(json.dumps(info, indent=2))
    
    # Test invocation
    print("\n2. Testing deployment invocation...")
    test_input = {
        "messages": [
            {"role": "user", "content": "Hola, necesito ayuda"}
        ],
        "contact_id": "test_contact_123"
    }
    
    result = await client.invoke_deployment(test_input)
    if result:
        print(json.dumps(result, indent=2))
    
    # Get recent runs
    print("\n3. Getting recent runs...")
    runs = await client.get_runs(limit=5)
    if runs:
        print(json.dumps(runs, indent=2))
    
    # Test streaming
    print("\n4. Testing streaming...")
    async for event in client.stream_deployment(test_input):
        print(f"Stream event: {event}")

# Alternative: Using LangSmith SDK
def access_via_langsmith_sdk():
    """Access deployment using LangSmith SDK"""
    try:
        import langsmith
        
        # Initialize client
        client = langsmith.Client(
            api_key=os.getenv("LANGCHAIN_API_KEY"),
            api_url="https://api.smith.langchain.com"
        )
        
        # Get deployment runs
        deployment_id = "b91140bf-d8b2-4d1f-b36a-53f18f2db65d"
        
        # List runs for deployment
        runs = client.list_runs(
            project_name=deployment_id,
            limit=10
        )
        
        for run in runs:
            print(f"Run ID: {run.id}")
            print(f"Status: {run.status}")
            print(f"Created: {run.created_at}")
            print("-" * 30)
            
    except Exception as e:
        print(f"Error with LangSmith SDK: {e}")

if __name__ == "__main__":
    print("LangGraph Deployment Access Tool")
    print("================================\n")
    
    # Check for API key
    if not os.getenv("LANGCHAIN_API_KEY"):
        print("ERROR: LANGCHAIN_API_KEY not found in environment variables")
        print("Please set it in your .env file or export it:")
        print("export LANGCHAIN_API_KEY='your-api-key'")
        exit(1)
    
    # Run async test
    asyncio.run(test_deployment())
    
    print("\n\nTrying LangSmith SDK approach...")
    access_via_langsmith_sdk()
"""
Check the current LangGraph Cloud deployment on LangSmith
"""
import httpx
import asyncio
import os
from datetime import datetime

LANGGRAPH_API_URL = "https://ghl-langgraph-agent-95f8713b0bd6545391589bd2f0ca67eb.us.langgraph.app"
LANGGRAPH_API_KEY = os.getenv("LANGGRAPH_API_KEY", "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")


async def test_deployment():
    """Test the current deployment to see how it handles thread IDs"""
    
    headers = {
        "Content-Type": "application/json",
        "x-api-key": LANGGRAPH_API_KEY
    }
    
    # Test webhook data similar to what GHL sends
    test_webhook = {
        "contactId": "test-contact-123",
        "conversationId": "test-conv-456",
        "body": "Hola, necesito ayuda",
        "locationId": "test-location",
        "id": "msg-789"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print(f"Testing LangGraph Cloud deployment...")
        print(f"URL: {LANGGRAPH_API_URL}")
        print(f"API Key: ***{LANGGRAPH_API_KEY[-4:]}")
        print("-" * 50)
        
        # Test 1: Send with our desired thread_id in config
        print("\n1. Testing with explicit thread_id in config...")
        desired_thread_id = f"conv-{test_webhook['conversationId']}"
        
        response = await client.post(
            f"{LANGGRAPH_API_URL}/runs",
            json={
                "assistant_id": "agent",
                "input": {
                    "webhook_data": test_webhook,
                    "contact_id": test_webhook["contactId"],
                    "thread_id": desired_thread_id,  # Pass in input
                    "conversation_id": test_webhook["conversationId"]
                },
                "config": {
                    "configurable": {
                        "thread_id": desired_thread_id  # Pass in config
                    }
                }
            },
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            actual_thread_id = result.get("thread_id")
            print(f"✅ Request successful")
            print(f"Desired thread_id: {desired_thread_id}")
            print(f"Actual thread_id: {actual_thread_id}")
            print(f"Run ID: {result.get('run_id')}")
            
            if actual_thread_id == desired_thread_id:
                print("✅ Thread ID preserved correctly!")
            else:
                print("❌ Thread ID was overridden by LangGraph Cloud")
                
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"Response: {response.text}")
        
        # Test 2: Check if the thread mapper is working
        print("\n2. Checking thread mapper effectiveness...")
        print("The thread_mapper should convert thread_id to our pattern")
        print("If it's working, we should see 'conv-' or 'contact-' patterns in traces")
        
        # Test 3: Direct webhook endpoint (if exists)
        print("\n3. Testing direct webhook endpoint...")
        response = await client.post(
            f"{LANGGRAPH_API_URL}/webhook/message",
            json=test_webhook,
            headers=headers
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 404:
            print("❌ No webhook endpoint - workflow runs through /runs API")
            print("This means GHL must be calling /runs directly")
        else:
            print(f"Response: {response.text[:200]}")


async def check_recent_runs():
    """Check recent runs to see thread_id patterns"""
    
    headers = {
        "Content-Type": "application/json", 
        "x-api-key": LANGGRAPH_API_KEY
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("\n" + "="*50)
        print("Checking recent runs for thread_id patterns...")
        
        # Try to get recent runs (this endpoint might not exist)
        response = await client.get(
            f"{LANGGRAPH_API_URL}/runs",
            headers=headers,
            params={"limit": 5}
        )
        
        if response.status_code == 200:
            runs = response.json()
            print(f"Found {len(runs)} recent runs")
            for run in runs:
                print(f"- Thread ID: {run.get('thread_id')} | Status: {run.get('status')}")
        else:
            print(f"Could not fetch runs: {response.status_code}")


if __name__ == "__main__":
    print("Analyzing LangGraph Cloud deployment on LangSmith...")
    print("="*50)
    
    asyncio.run(test_deployment())
    asyncio.run(check_recent_runs())
    
    print("\n" + "="*50)
    print("CONCLUSION:")
    print("The thread_mapper is already deployed as part of your workflow")
    print("It should be converting thread_ids to the 'conv-' or 'contact-' pattern")
    print("Check LangSmith traces to verify if it's working correctly")
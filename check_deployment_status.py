#!/usr/bin/env python3
"""
Check deployment status and get the URL
"""
import os
import requests
from datetime import datetime

# LangSmith API configuration
API_KEY = "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"
LANGSMITH_API_URL = "https://api.smith.langchain.com"

def check_deployment():
    """Check deployment status via LangSmith API"""
    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json"
    }
    
    print("🔍 Checking deployment status...")
    print("=" * 60)
    
    # Try to get deployment info
    # Note: The exact endpoint might vary, this is a common pattern
    endpoints_to_try = [
        "/deployments",
        "/projects/ghl-langgraph-agent/deployments",
        "/assistants",
        "/runs"
    ]
    
    for endpoint in endpoints_to_try:
        try:
            url = f"{LANGSMITH_API_URL}{endpoint}"
            print(f"\nTrying: {url}")
            
            response = requests.get(url, headers=headers, params={"limit": 5})
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Success! Response type: {type(data)}")
                
                # Handle different response formats
                if isinstance(data, list):
                    print(f"Found {len(data)} items")
                    for item in data[:3]:  # Show first 3
                        if isinstance(item, dict):
                            print(f"  - {item.get('name', 'unnamed')}: {item.get('status', 'unknown')}")
                            if 'url' in item:
                                print(f"    URL: {item['url']}")
                elif isinstance(data, dict):
                    if 'items' in data:
                        print(f"Found {len(data['items'])} items")
                    else:
                        print(f"Keys: {list(data.keys())[:5]}")
            else:
                print(f"❌ Status {response.status_code}")
                if response.status_code == 404:
                    continue
                else:
                    print(f"Error: {response.text[:200]}")
                    
        except Exception as e:
            print(f"❌ Exception: {e}")
    
    print("\n" + "=" * 60)
    print("DEPLOYMENT INSTRUCTIONS:")
    print("=" * 60)
    print("\n1. Go to https://smith.langchain.com")
    print("2. Navigate to your project: ghl-langgraph-agent")
    print("3. Click on 'Deployments' tab")
    print("4. Look for your deployment URL")
    print("\nThe URL format is typically:")
    print("https://YOUR-DEPLOYMENT-ID.us.langgraph.app/runs/stream")
    print("\n5. Once you have the URL, update test scripts with it")
    
    # Show timing info
    print("\n" + "=" * 60)
    print("TIMING INFORMATION:")
    print("=" * 60)
    deployment_time = datetime(2025, 7, 21, 17, 20, 0)
    current_time = datetime.now()
    elapsed = current_time - deployment_time.replace(tzinfo=None)
    
    print(f"Deployment pushed: {deployment_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S')} local")
    print(f"Time elapsed: {elapsed}")
    
    if elapsed.total_seconds() < 900:  # 15 minutes
        print("\n⏳ Deployment may still be building (typically takes 15 minutes)")
    else:
        print("\n✅ Deployment should be live by now")

if __name__ == "__main__":
    check_deployment()
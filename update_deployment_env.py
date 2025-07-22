#!/usr/bin/env python3
"""
Update LangGraph Platform deployment with Redis URL
"""
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Your LangSmith API key
LANGSMITH_API_KEY = "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"
REDIS_URL = os.getenv("REDIS_URL")

# LangGraph Platform API endpoint
# Note: You'll need to get your deployment ID from LangSmith
CONTROL_PLANE_HOST = "https://api.smith.langchain.com"

def get_headers():
    """Return headers for API requests"""
    return {
        "X-Api-Key": LANGSMITH_API_KEY,
        "Content-Type": "application/json"
    }

def list_deployments():
    """List all deployments to find yours"""
    response = requests.get(
        url=f"{CONTROL_PLANE_HOST}/v2/deployments",
        headers=get_headers()
    )
    
    if response.status_code == 200:
        deployments = response.json()
        print("📋 Your deployments:")
        for dep in deployments:
            print(f"  - {dep['name']} (ID: {dep['id']})")
        return deployments
    else:
        print(f"❌ Failed to list deployments: {response.status_code}")
        print(response.text)
        return []

def update_deployment_env(deployment_id, env_vars):
    """Update deployment environment variables"""
    
    headers = get_headers()
    
    # Prepare secrets/environment variables
    secrets = []
    for key, value in env_vars.items():
        secrets.append({
            "name": key,
            "value": value
        })
    
    # Update deployment
    response = requests.patch(
        url=f"{CONTROL_PLANE_HOST}/v2/deployments/{deployment_id}",
        headers=headers,
        json={
            "secrets": secrets
        }
    )
    
    if response.status_code == 200:
        print(f"✅ Successfully updated deployment with Redis URL!")
        return True
    else:
        print(f"❌ Failed to update deployment: {response.status_code}")
        print(response.text)
        return False

def main():
    print("🚀 LangGraph Platform Deployment Updater")
    print("=" * 50)
    
    if not REDIS_URL:
        print("❌ REDIS_URL not found in environment!")
        return
    
    print(f"Redis URL: {REDIS_URL[:50]}...")
    print()
    
    # First, list deployments
    deployments = list_deployments()
    
    if not deployments:
        print("\n❌ No deployments found or API access issue")
        print("Please check:")
        print("1. Your API key is correct")
        print("2. You have deployments in LangSmith")
        return
    
    # If you know your deployment ID, you can set it here
    # Otherwise, manually pick from the list above
    deployment_id = input("\nEnter your deployment ID: ").strip()
    
    if deployment_id:
        print(f"\n📝 Updating deployment {deployment_id}...")
        
        # Environment variables to add/update
        env_vars = {
            "REDIS_URL": REDIS_URL,
            # Keep existing env vars
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            "GHL_API_TOKEN": os.getenv("GHL_API_TOKEN"),
            "GHL_LOCATION_ID": os.getenv("GHL_LOCATION_ID"),
            "GHL_CALENDAR_ID": os.getenv("GHL_CALENDAR_ID"),
            "GHL_ASSIGNED_USER_ID": os.getenv("GHL_ASSIGNED_USER_ID"),
            "SUPABASE_URL": os.getenv("SUPABASE_URL"),
            "SUPABASE_KEY": os.getenv("SUPABASE_KEY"),
            "LANGCHAIN_TRACING_V2": "true",
            "LANGCHAIN_API_KEY": LANGSMITH_API_KEY,
            "LANGCHAIN_PROJECT": "ghl-langgraph-agent"
        }
        
        if update_deployment_env(deployment_id, env_vars):
            print("\n✅ Deployment updated successfully!")
            print("\n🎯 Next steps:")
            print("1. Wait for deployment to restart")
            print("2. Send test messages")
            print("3. Check LangSmith traces - you should see:")
            print("   - checkpoint_loaded: true")
            print("   - Messages accumulating (not duplicating)")
        else:
            print("\n❌ Failed to update deployment")

if __name__ == "__main__":
    main()
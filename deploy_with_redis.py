#!/usr/bin/env python3
"""
Deploy LangGraph with Redis persistence enabled
"""
import os
import subprocess
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("🚀 LangGraph Deployment with Redis Persistence")
print("=" * 60)

# Check Redis URL
redis_url = os.getenv("REDIS_URL")
if not redis_url:
    print("❌ REDIS_URL not found in .env file!")
    exit(1)

print(f"✅ Redis URL configured: {redis_url[:50]}...")

# Environment variables for deployment
env_vars = {
    "REDIS_URL": redis_url,
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    "GHL_API_TOKEN": os.getenv("GHL_API_TOKEN"),
    "GHL_LOCATION_ID": os.getenv("GHL_LOCATION_ID"),
    "GHL_CALENDAR_ID": os.getenv("GHL_CALENDAR_ID"),
    "GHL_ASSIGNED_USER_ID": os.getenv("GHL_ASSIGNED_USER_ID"),
    "SUPABASE_URL": os.getenv("SUPABASE_URL"),
    "SUPABASE_KEY": os.getenv("SUPABASE_KEY"),
    "LANGCHAIN_TRACING_V2": "true",
    "LANGCHAIN_API_KEY": os.getenv("LANGCHAIN_API_KEY"),
    "LANGCHAIN_PROJECT": os.getenv("LANGCHAIN_PROJECT", "ghl-langgraph-agent")
}

print("\n📋 Deployment Configuration:")
for key, value in env_vars.items():
    if value:
        display_value = value[:20] + "..." if len(value) > 20 else value
        if "KEY" in key or "TOKEN" in key:
            display_value = "***" + value[-4:]
        print(f"  {key}: {display_value}")

print("\n🛠️  Since LangSmith API deployment endpoints are not available,")
print("   you need to update your deployment manually:")
print("\n📝 Manual Steps:")
print("1. Go to https://smith.langchain.com")
print("2. Navigate to your project: 'ghl-langgraph-agent'")
print("3. Go to Deployments section")
print("4. Click on your deployment")
print("5. Update Environment Variables:")
print("   - Add REDIS_URL with the value from .env")
print("6. Save and restart the deployment")

print("\n🧪 Test Your Deployment:")
print("1. Send a test message to your webhook")
print("2. Check LangSmith traces")
print("3. Look for 'checkpoint_loaded: true' in the trace")
print("4. Verify messages accumulate (not duplicate)")

print("\n💡 Alternative: Local Testing")
print("Run: langgraph dev --port 8080")
print("This will use your local .env with Redis automatically")

# Ask if user wants to run local dev server
response = input("\n🤔 Would you like to start the local dev server now? (y/n): ")
if response.lower() == 'y':
    print("\n🏃 Starting LangGraph dev server...")
    try:
        subprocess.run(["langgraph", "dev", "--port", "8080"], 
                      env={**os.environ, **env_vars})
    except KeyboardInterrupt:
        print("\n✋ Dev server stopped")
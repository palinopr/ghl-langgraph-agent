#!/usr/bin/env python3
"""
Start LangGraph local dev server with Redis persistence
"""
import os
import subprocess
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("🚀 Starting LangGraph Local Server with Redis")
print("=" * 60)

# Check Redis URL
redis_url = os.getenv("REDIS_URL")
if redis_url:
    print(f"✅ Redis persistence enabled: {redis_url[:50]}...")
else:
    print("⚠️  No Redis URL found - using SQLite checkpoint")

print("\n📡 Server will start at: http://localhost:8080")
print("📊 Traces will be sent to LangSmith")
print("\n🛑 Press Ctrl+C to stop the server\n")

# Start the dev server
try:
    subprocess.run(["source", "venv/bin/activate", "&&", "langgraph", "dev", "--port", "8080"], 
                  shell=True, 
                  executable="/bin/bash")
except KeyboardInterrupt:
    print("\n✋ Server stopped")
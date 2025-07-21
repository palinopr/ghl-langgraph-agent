#!/usr/bin/env python3
"""
Fetch traces for project using the API key from environment
"""
import os
import json
import subprocess
from datetime import datetime, timezone, timedelta

# Get API key from environment
api_key = os.getenv("LANGSMITH_API_KEY", "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")
project_id = "a807d9fb-2c58-4d09-a4b2-4037e0668fcc"

# Calculate time range
end_time = datetime.now(timezone.utc)
start_time = end_time - timedelta(hours=6)

# Build curl command
curl_cmd = [
    "curl", "-s",
    "-H", f"x-api-key: {api_key}",
    "-H", "Content-Type: application/json",
    f"https://api.smith.langchain.com/api/v1/runs?session_id={project_id}&limit=10"
]

print(f"🔍 Fetching traces for project: {project_id}")
print(f"Time range: Last 6 hours")
print("=" * 80)

try:
    # Execute curl
    result = subprocess.run(curl_cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        try:
            data = json.loads(result.stdout)
            
            if "runs" in data:
                runs = data["runs"]
                print(f"\n✅ Found {len(runs)} traces")
                
                for i, run in enumerate(runs[:10]):
                    print(f"\n📊 Trace {i+1}:")
                    print(f"ID: {run.get('id')}")
                    print(f"Name: {run.get('name')}")
                    print(f"Status: {run.get('status')}")
                    print(f"Start: {run.get('start_time')}")
                    
                    # Check inputs
                    inputs = run.get('inputs', {})
                    if inputs and 'messages' in inputs:
                        messages = inputs['messages']
                        if messages and len(messages) > 0:
                            last_msg = messages[-1]
                            if isinstance(last_msg, dict) and 'content' in last_msg:
                                print(f"Message: {last_msg['content'][:100]}...")
                    
                    # Check for errors
                    if run.get('error'):
                        print(f"❌ ERROR: {run['error']}")
                    
                    print("-" * 40)
            else:
                # Try different endpoint
                print("Trying alternative endpoint...")
                
                # Try with session_id as query param
                alt_cmd = [
                    "curl", "-s",
                    "-H", f"x-api-key: {api_key}",
                    f"https://api.smith.langchain.com/api/v1/sessions/{project_id}/runs?limit=10"
                ]
                
                alt_result = subprocess.run(alt_cmd, capture_output=True, text=True)
                if alt_result.returncode == 0:
                    print(f"Response: {alt_result.stdout[:500]}...")
                else:
                    print(f"Error: {alt_result.stderr}")
                    
        except json.JSONDecodeError:
            print(f"Raw response: {result.stdout[:500]}...")
    else:
        print(f"Curl error: {result.stderr}")
        
except Exception as e:
    print(f"Error: {str(e)}")

# Also try to get project info
print("\n🔍 Checking project info...")
project_cmd = [
    "curl", "-s",
    "-H", f"x-api-key: {api_key}",
    f"https://api.smith.langchain.com/api/v1/sessions/{project_id}"
]

project_result = subprocess.run(project_cmd, capture_output=True, text=True)
if project_result.returncode == 0:
    try:
        project_data = json.loads(project_result.stdout)
        print(f"Project Name: {project_data.get('name', 'Unknown')}")
        print(f"Project ID: {project_data.get('id', project_id)}")
    except:
        print(f"Project response: {project_result.stdout[:200]}...")
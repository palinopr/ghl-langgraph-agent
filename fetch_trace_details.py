#!/usr/bin/env python3
"""
Fetch and analyze trace details from LangSmith
"""
import os
import sys
import json
import httpx
from datetime import datetime

# Load environment variables
env_file = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

async def fetch_trace(trace_id: str):
    """Fetch trace details from LangSmith"""
    
    api_key = os.getenv('LANGCHAIN_API_KEY') or os.getenv('LANGSMITH_API_KEY')
    if not api_key:
        print("❌ No LangSmith API key found")
        return None
    
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    # LangSmith API endpoint
    url = f"https://api.smith.langchain.com/runs/{trace_id}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Error fetching trace: {response.status_code}")
                print(f"Response: {response.text}")
                return None
        except Exception as e:
            print(f"❌ Failed to fetch trace: {str(e)}")
            return None

async def analyze_trace_data(trace_id: str):
    """Analyze the trace to understand what happened"""
    
    print(f"\n🔍 FETCHING TRACE: {trace_id}")
    print("="*60)
    
    trace_data = await fetch_trace(trace_id)
    if not trace_data:
        return
    
    # Basic info
    print(f"\n📊 TRACE OVERVIEW:")
    print(f"  - Name: {trace_data.get('name', 'N/A')}")
    print(f"  - Status: {trace_data.get('status', 'N/A')}")
    print(f"  - Start: {trace_data.get('start_time', 'N/A')}")
    print(f"  - End: {trace_data.get('end_time', 'N/A')}")
    
    # Input
    inputs = trace_data.get('inputs', {})
    print(f"\n📥 INPUTS:")
    if isinstance(inputs, dict):
        for key, value in inputs.items():
            if key == 'messages' and isinstance(value, list):
                print(f"  - {key}:")
                for msg in value:
                    if isinstance(msg, dict):
                        print(f"    • {msg.get('type', 'unknown')}: {msg.get('content', '')[:100]}...")
            else:
                print(f"  - {key}: {str(value)[:100]}...")
    
    # Output
    outputs = trace_data.get('outputs', {})
    print(f"\n📤 OUTPUTS:")
    if outputs:
        print(json.dumps(outputs, indent=2)[:500] + "...")
    
    # Error
    error = trace_data.get('error')
    if error:
        print(f"\n❌ ERROR:")
        print(f"{error}")
    
    # Events/Steps
    events = trace_data.get('events', [])
    if events:
        print(f"\n📍 EXECUTION STEPS:")
        for i, event in enumerate(events[:10]):  # First 10 events
            print(f"{i+1}. {event.get('name', 'Unknown')} - {event.get('event', 'N/A')}")
    
    # Child runs (sub-traces)
    child_runs = trace_data.get('child_runs', [])
    if child_runs:
        print(f"\n🔗 CHILD RUNS ({len(child_runs)} total):")
        for i, child in enumerate(child_runs[:5]):  # First 5
            print(f"{i+1}. {child.get('name', 'Unknown')} - {child.get('status', 'N/A')}")
            if child.get('error'):
                print(f"   ❌ Error: {child['error']}")
    
    # Extract key information
    print(f"\n🎯 KEY FINDINGS:")
    
    # Check for specific issues
    trace_str = json.dumps(trace_data)
    
    if "10:00 AM" in trace_str and "$10" in trace_str:
        print("  ⚠️  Budget extraction issue: '10:00 AM' might be extracted as '$10'")
    
    if "book_appointment_from_confirmation" in trace_str:
        print("  ✅ Appointment booking tool was called")
    else:
        print("  ❌ Appointment booking tool was NOT called")
    
    if "available_slots" in trace_str:
        print("  ✅ Available slots were loaded")
    else:
        print("  ⚠️  No available slots found in trace")
    
    # Save full trace for detailed analysis
    with open(f"trace_{trace_id}.json", "w") as f:
        json.dump(trace_data, f, indent=2)
    print(f"\n💾 Full trace saved to: trace_{trace_id}.json")

if __name__ == "__main__":
    import asyncio
    
    trace_id = "1f064cd1-554a-6fd6-b196-9d317c823332"
    
    print("🧪 LANGSMITH TRACE ANALYZER")
    asyncio.run(analyze_trace_data(trace_id))
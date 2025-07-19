#!/usr/bin/env python3
"""
Fetch trace from LangSmith using curl
"""
import os
import json
import subprocess

# Load environment variables
env_file = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

def fetch_trace(trace_id: str):
    """Fetch trace using curl"""
    
    api_key = os.getenv('LANGCHAIN_API_KEY') or os.getenv('LANGSMITH_API_KEY')
    if not api_key:
        print("❌ No LangSmith API key found")
        return None
    
    print(f"\n🔍 FETCHING TRACE: {trace_id}")
    print("="*60)
    
    # Build curl command
    curl_cmd = [
        'curl', '-s',
        f'https://api.smith.langchain.com/runs/{trace_id}',
        '-H', f'x-api-key: {api_key}',
        '-H', 'Content-Type: application/json'
    ]
    
    try:
        result = subprocess.run(curl_cmd, capture_output=True, text=True)
        if result.stdout:
            return json.loads(result.stdout)
        else:
            print(f"❌ Error: {result.stderr}")
            return None
    except Exception as e:
        print(f"❌ Failed to fetch: {str(e)}")
        return None

def analyze_trace_data(trace_id: str):
    """Analyze the trace"""
    
    trace_data = fetch_trace(trace_id)
    if not trace_data:
        return
    
    # Save raw data first
    with open(f"trace_{trace_id}_raw.json", "w") as f:
        json.dump(trace_data, f, indent=2)
    print(f"💾 Raw trace saved to: trace_{trace_id}_raw.json")
    
    # Basic info
    print(f"\n📊 TRACE OVERVIEW:")
    print(f"  - Name: {trace_data.get('name', 'N/A')}")
    print(f"  - Status: {trace_data.get('status', 'N/A')}")
    print(f"  - Error: {'Yes' if trace_data.get('error') else 'No'}")
    
    # Input
    inputs = trace_data.get('inputs', {})
    print(f"\n📥 INPUTS:")
    print(json.dumps(inputs, indent=2)[:500])
    
    # Look for specific patterns
    trace_str = json.dumps(trace_data)
    
    print(f"\n🎯 KEY CHECKS:")
    
    # Check which node we're in
    if "receptionist" in trace_data.get('name', '').lower():
        print("  📍 This is the RECEPTIONIST node")
        # Check if conversation history loaded
        if "conversation_history" in trace_str:
            print("  ✅ Conversation history loaded")
        else:
            print("  ⚠️  No conversation history found")
    
    elif "supervisor" in trace_data.get('name', '').lower():
        print("  📍 This is the SUPERVISOR node")
        # Check score
        if "lead_score" in trace_str:
            import re
            scores = re.findall(r'"lead_score":\s*(\d+)', trace_str)
            if scores:
                print(f"  📊 Lead scores found: {scores}")
    
    elif "sofia" in trace_data.get('name', '').lower():
        print("  📍 This is SOFIA agent")
        # Check for appointment tool
        if "book_appointment_from_confirmation" in trace_str:
            print("  ✅ Appointment tool called")
        else:
            print("  ❌ Appointment tool NOT called")
    
    # Check for common issues
    if "10:00 AM" in trace_str:
        print(f"\n⚠️  Found '10:00 AM' in trace")
        if '"budget": "10' in trace_str or '"budget":"10' in trace_str:
            print("  ❌ BUDGET BUG: '10:00 AM' extracted as budget!")
    
    # Error details
    if trace_data.get('error'):
        print(f"\n❌ ERROR DETAILS:")
        print(trace_data['error'])
    
    # Outputs
    outputs = trace_data.get('outputs', {})
    if outputs:
        print(f"\n📤 OUTPUT:")
        print(json.dumps(outputs, indent=2)[:300])

if __name__ == "__main__":
    trace_id = "1f064cd1-554a-6fd6-b196-9d317c823332"
    
    print("🧪 LANGSMITH TRACE ANALYZER")
    analyze_trace_data(trace_id)
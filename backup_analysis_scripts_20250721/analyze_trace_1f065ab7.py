#!/usr/bin/env python3
"""
Analyze trace 1f065ab7-af0c-6b8f-b629-457ad5e5145c
"""
import os
import sys
import json
from datetime import datetime
import requests

def format_timestamp(ts):
    """Format timestamp for readability"""
    if isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            return dt.strftime('%H:%M:%S.%f')[:-3]
        except:
            return ts
    return str(ts)

def analyze_trace():
    """Analyze the specific trace"""
    trace_id = "1f065ab7-af0c-6b8f-b629-457ad5e5145c"
    
    print(f"🔍 Analyzing Trace: {trace_id}")
    print("=" * 80)
    
    # Check if we have the API key
    api_key = os.getenv('LANGSMITH_API_KEY')
    if not api_key:
        print("❌ LANGSMITH_API_KEY not found in environment")
        print("\nTrying to fetch from LangSmith web UI...")
        print(f"\nPlease visit: https://smith.langchain.com/o/4c95e8d5-51d9-5c98-9f15-da9d8fd05782/projects/p/8f9e7a4f-5aad-4919-bd03-88f695c7c8cf/r/{trace_id}")
        print("\nLook for:")
        print("1. Input messages and contact info")
        print("2. Which agent handled the request")
        print("3. Any errors or unexpected behavior")
        print("4. The final response sent")
        return
    
    # Try to fetch from API
    headers = {
        'x-api-key': api_key,
        'Content-Type': 'application/json'
    }
    
    url = f"https://api.smith.langchain.com/runs/{trace_id}"
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            
            # Basic info
            print(f"Name: {data.get('name', 'N/A')}")
            print(f"Status: {data.get('status', 'N/A')}")
            print(f"Start: {format_timestamp(data.get('start_time'))}")
            print(f"End: {format_timestamp(data.get('end_time'))}")
            
            # Input
            print("\n📥 INPUT:")
            inputs = data.get('inputs', {})
            print(json.dumps(inputs, indent=2))
            
            # Output
            print("\n📤 OUTPUT:")
            outputs = data.get('outputs', {})
            print(json.dumps(outputs, indent=2))
            
            # Errors
            if data.get('error'):
                print("\n❌ ERROR:")
                print(data['error'])
            
            # Save for reference
            with open(f'trace_{trace_id[:8]}.json', 'w') as f:
                json.dump(data, f, indent=2)
            print(f"\n💾 Full trace saved to: trace_{trace_id[:8]}.json")
            
        else:
            print(f"❌ Failed to fetch trace: {response.status_code}")
            print(f"Response: {response.text}")
    
    except Exception as e:
        print(f"❌ Error fetching trace: {str(e)}")
        print("\nPlease check the trace manually in LangSmith UI")
    
    # Provide context about what to look for
    print("\n📋 Key Things to Check:")
    print("1. Is this a webhook message or direct API call?")
    print("2. What's the contact ID and message content?")
    print("3. Which agent (Maria/Carlos/Sofia) handled it?")
    print("4. Was the lead score calculated correctly?")
    print("5. Were appointment tools invoked if needed?")
    print("6. What was the final response?")
    print("7. Any errors or unexpected routing?")

if __name__ == "__main__":
    analyze_trace()
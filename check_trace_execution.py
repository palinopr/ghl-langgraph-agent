#!/usr/bin/env python3
"""
Check LangSmith traces to verify GHL message sending
"""
import os
import urllib.request
import urllib.parse
import json
from datetime import datetime

# LangSmith API configuration
LANGSMITH_API_KEY = "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"
LANGSMITH_API_URL = "https://api.smith.langchain.com"

# Trace IDs to check
TRACE_IDS = [
    "1f067450-f248-6c65-ad62-5b003dd1b02a",
    "1f067452-0dda-61cc-bd5a-b380392345a3"
]

def get_trace_details(trace_id: str):
    """Get detailed information about a trace"""
    url = f"{LANGSMITH_API_URL}/runs/{trace_id}"
    
    req = urllib.request.Request(url, headers={
        "x-api-key": LANGSMITH_API_KEY,
        "Content-Type": "application/json"
    })
    
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Error fetching trace {trace_id}: {e.code}")
        return None

def get_child_runs(parent_id: str):
    """Get all child runs of a parent run"""
    params = urllib.parse.urlencode({
        "parent_run_id": parent_id,
        "limit": 100
    })
    url = f"{LANGSMITH_API_URL}/runs?{params}"
    
    req = urllib.request.Request(url, headers={
        "x-api-key": LANGSMITH_API_KEY,
        "Content-Type": "application/json"
    })
    
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Error fetching child runs: {e.code}")
        return None

def analyze_responder_execution(trace_id: str):
    """Analyze if responder is executing and sending messages"""
    print(f"\n{'='*60}")
    print(f"Analyzing trace: {trace_id}")
    print(f"{'='*60}")
    
    # Get main trace
    trace = get_trace_details(trace_id)
    if not trace:
        return
    
    print(f"Trace Name: {trace.get('name')}")
    print(f"Status: {trace.get('status')}")
    print(f"Start Time: {trace.get('start_time')}")
    
    # Get all child runs
    children = get_child_runs(trace_id)
    if not children:
        print("No child runs found")
        return
    
    runs = children.get('runs', [])
    print(f"\nTotal child runs: {len(runs)}")
    
    # Look for responder node
    responder_found = False
    ghl_calls_found = False
    
    for run in runs:
        run_name = run.get('name', '')
        run_type = run.get('run_type', '')
        
        # Check for responder node
        if 'responder' in run_name.lower():
            responder_found = True
            print(f"\n🎯 RESPONDER NODE FOUND:")
            print(f"  - Name: {run_name}")
            print(f"  - Type: {run_type}")
            print(f"  - Status: {run.get('status')}")
            
            # Check outputs
            outputs = run.get('outputs', {})
            if outputs:
                print(f"  - Outputs:")
                for key, value in outputs.items():
                    if isinstance(value, str) and len(value) > 100:
                        print(f"    - {key}: {value[:100]}...")
                    else:
                        print(f"    - {key}: {value}")
            
            # Check for errors
            error = run.get('error')
            if error:
                print(f"  - ❌ ERROR: {error}")
            
            # Get child runs of responder to see if GHL calls were made
            responder_children = get_child_runs(run['id'])
            if responder_children and responder_children.get('runs'):
                print(f"  - Child runs: {len(responder_children['runs'])}")
                for child in responder_children['runs']:
                    child_name = child.get('name', '')
                    if 'ghl' in child_name.lower() or 'send' in child_name.lower():
                        ghl_calls_found = True
                        print(f"    - GHL Call: {child_name}")
        
        # Also check for any GHL-related calls
        if 'ghl' in run_name.lower() or 'send_message' in run_name.lower():
            print(f"\n📤 GHL API CALL FOUND:")
            print(f"  - Name: {run_name}")
            print(f"  - Status: {run.get('status')}")
            ghl_calls_found = True
    
    # Summary
    print(f"\n{'='*30} SUMMARY {'='*30}")
    print(f"✅ Responder node found: {responder_found}")
    print(f"{'✅' if ghl_calls_found else '❌'} GHL API calls found: {ghl_calls_found}")
    
    if responder_found and not ghl_calls_found:
        print("\n⚠️  WARNING: Responder executed but no GHL API calls detected!")
        print("This suggests the responder is not actually sending messages to GHL.")

def main():
    """Main function"""
    print("Checking LangSmith traces for GHL message sending...")
    print(f"API Key: {LANGSMITH_API_KEY[:20]}...")
    
    for trace_id in TRACE_IDS:
        analyze_responder_execution(trace_id)
    
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)

if __name__ == "__main__":
    main()
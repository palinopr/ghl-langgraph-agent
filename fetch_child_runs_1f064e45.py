#!/usr/bin/env python3
"""
Fetch child runs to understand the exact flow
"""

import urllib.request
import json
import os
from datetime import datetime
from pathlib import Path

# Manually load API key from .env.langsmith
env_path = Path(__file__).parent / '.env.langsmith'
api_key = None

with open(env_path, 'r') as f:
    for line in f:
        if line.startswith('LANGSMITH_API_KEY='):
            api_key = line.strip().split('=', 1)[1]
            break

if not api_key:
    print('ERROR: LANGSMITH_API_KEY not found in .env.langsmith')
    exit(1)

# Load parent trace to get child IDs
with open('trace_1f064e45_raw.json', 'r') as f:
    parent_trace = json.load(f)

child_ids = parent_trace.get('child_run_ids', [])
print(f"Found {len(child_ids)} child runs to analyze\n")

# Fetch and analyze key child runs
analysis_results = []

for i, child_id in enumerate(child_ids[:10]):  # Analyze first 10 child runs
    print(f"Fetching child run {i+1}/{min(10, len(child_ids))}: {child_id}")
    
    url = f'https://api.smith.langchain.com/runs/{child_id}'
    req = urllib.request.Request(url)
    req.add_header('x-api-key', api_key)
    req.add_header('Content-Type', 'application/json')
    
    try:
        with urllib.request.urlopen(req) as response:
            child_data = json.loads(response.read().decode())
            
            # Extract key info
            name = child_data.get('name', 'N/A')
            run_type = child_data.get('run_type', 'N/A')
            status = child_data.get('status', 'N/A')
            
            # Save child data
            filename = f'child_run_{i+1}_{child_id[:8]}.json'
            with open(filename, 'w') as f:
                json.dump(child_data, f, indent=2)
            
            print(f"  - Name: {name}")
            print(f"  - Type: {run_type}")
            print(f"  - Status: {status}")
            
            # Look for conversation data
            if 'outputs' in child_data:
                if isinstance(child_data['outputs'], dict):
                    if 'messages' in child_data['outputs']:
                        print(f"  - Found messages in outputs")
                    if 'content' in child_data['outputs']:
                        content = str(child_data['outputs']['content'])[:100]
                        print(f"  - Output content: {content}...")
                elif isinstance(child_data['outputs'], str):
                    print(f"  - Output: {child_data['outputs'][:100]}...")
            
            # Look for inputs
            if 'inputs' in child_data:
                if 'messages' in child_data['inputs']:
                    msg_count = len(child_data['inputs']['messages'])
                    print(f"  - Input messages: {msg_count}")
                    
                    # Show last message
                    if msg_count > 0:
                        last_msg = child_data['inputs']['messages'][-1]
                        print(f"  - Last message: {last_msg.get('content', 'N/A')[:100]}...")
            
            print()
            
            # Store analysis
            analysis_results.append({
                'id': child_id,
                'name': name,
                'type': run_type,
                'data': child_data
            })
            
    except Exception as e:
        print(f"  - Error fetching: {str(e)}\n")

# Analyze the workflow
print("\n=== WORKFLOW ANALYSIS ===\n")

# Look for specific agent runs
for result in analysis_results:
    name = result['name']
    if 'maria' in name.lower():
        print(f"\nMARIA AGENT RUN: {result['id'][:8]}")
        data = result['data']
        
        # Check inputs
        if 'inputs' in data:
            print("  Inputs:")
            print(f"    {json.dumps(data['inputs'], indent=4)[:500]}...")
        
        # Check outputs
        if 'outputs' in data:
            print("  Outputs:")
            print(f"    {json.dumps(data['outputs'], indent=4)[:500]}...")
    
    elif 'supervisor' in name.lower():
        print(f"\nSUPERVISOR RUN: {result['id'][:8]}")
        data = result['data']
        
        # Check what supervisor sees
        if 'inputs' in data:
            if 'messages' in data['inputs']:
                print(f"  Messages seen by supervisor: {len(data['inputs']['messages'])}")
                # Show last few messages
                for msg in data['inputs']['messages'][-3:]:
                    print(f"    - {msg.get('type', 'N/A')}: {msg.get('content', 'N/A')[:50]}...")

print("\n=== SUMMARY ===")
print(f"✓ Fetched {len(analysis_results)} child runs")
print(f"✓ Saved individual child run data to child_run_*.json files")
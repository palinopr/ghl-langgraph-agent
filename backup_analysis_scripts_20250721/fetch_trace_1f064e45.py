#!/usr/bin/env python3
"""
Fetch and analyze LangSmith trace to check if Maria is still repeating questions
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

# Fetch the trace
trace_id = '1f064e45-bb3d-6835-9e97-a6140d66431f'
url = f'https://api.smith.langchain.com/runs/{trace_id}'

# Create request with headers
req = urllib.request.Request(url)
req.add_header('x-api-key', api_key)
req.add_header('Content-Type', 'application/json')

print(f'Fetching trace {trace_id}...')

try:
    with urllib.request.urlopen(req) as response:
        trace_data = json.loads(response.read().decode())
        
        # Save the raw trace data
        with open('trace_1f064e45_raw.json', 'w') as f:
            json.dump(trace_data, f, indent=2)
        
        print(f'✓ Trace fetched successfully')
        print(f'✓ Raw data saved to trace_1f064e45_raw.json')
        print(f'\nTrace Overview:')
        print(f'- Name: {trace_data.get("name", "N/A")}')
        print(f'- Status: {trace_data.get("status", "N/A")}')
        print(f'- Start Time: {trace_data.get("start_time", "N/A")}')
        print(f'- End Time: {trace_data.get("end_time", "N/A")}')
        print(f'- Total Tokens: {trace_data.get("total_tokens", "N/A")}')
        
        # Extract and analyze messages
        print('\n\nAnalyzing conversation flow...')
        
        # Look for inputs/outputs
        if 'inputs' in trace_data:
            print('\n--- INPUTS ---')
            print(json.dumps(trace_data['inputs'], indent=2)[:1000] + '...' if len(json.dumps(trace_data['inputs'])) > 1000 else json.dumps(trace_data['inputs'], indent=2))
            
        if 'outputs' in trace_data:
            print('\n--- OUTPUTS ---')
            print(json.dumps(trace_data['outputs'], indent=2)[:1000] + '...' if len(json.dumps(trace_data['outputs'])) > 1000 else json.dumps(trace_data['outputs'], indent=2))
        
        # Try to find child runs to analyze the conversation flow
        if 'child_run_ids' in trace_data and trace_data['child_run_ids']:
            print(f'\n\nFound {len(trace_data["child_run_ids"])} child runs')
            print('Child run IDs:', trace_data['child_run_ids'][:5], '...' if len(trace_data['child_run_ids']) > 5 else '')
        
except urllib.error.HTTPError as e:
    print(f'ERROR: HTTP {e.code} - {e.reason}')
    print(f'Response: {e.read().decode()}')
except Exception as e:
    print(f'ERROR: {str(e)}')
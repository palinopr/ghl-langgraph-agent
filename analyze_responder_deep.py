#!/usr/bin/env python3
"""Deep dive into responder node execution to check GHL message sending."""

import os
import json
from langsmith import Client

# Set up the client
os.environ['LANGCHAIN_API_KEY'] = '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'
client = Client()

# Trace IDs to analyze
trace_ids = [
    '1f067450-f248-6c65-ad62-5b003dd1b02a',
    '1f067452-0dda-61cc-bd5a-b380392345a3'
]

def get_all_runs_recursive(client, session_id, parent_id=None, depth=0):
    """Recursively get all runs in a trace."""
    runs = []
    
    if parent_id:
        filter_str = f'eq(parent_run_id, "{parent_id}")'
    else:
        filter_str = f'eq(session_id, "{session_id}")'
    
    current_runs = list(client.list_runs(
        project_id=session_id,
        filter=filter_str
    ))
    
    for run in current_runs:
        run_info = {
            'id': run.id,
            'name': run.name,
            'status': run.status,
            'error': run.error,
            'inputs': run.inputs,
            'outputs': run.outputs,
            'depth': depth,
            'extra': run.extra,
            'events': getattr(run, 'events', [])
        }
        runs.append(run_info)
        
        # Get children
        child_runs = get_all_runs_recursive(client, session_id, run.id, depth + 1)
        runs.extend(child_runs)
    
    return runs

def analyze_trace_deep(trace_id):
    """Deep analysis of a trace."""
    print(f'\n{"="*80}')
    print(f'DEEP ANALYSIS OF TRACE: {trace_id}')
    print('='*80)
    
    try:
        # Get the main run
        main_run = client.read_run(trace_id)
        session_id = main_run.session_id
        
        # Get all runs recursively
        all_runs = get_all_runs_recursive(client, session_id, trace_id)
        
        print(f'\nTotal Runs (including nested): {len(all_runs)}')
        
        # Look for responder and GHL-related runs
        responder_runs = []
        ghl_runs = []
        tool_runs = []
        
        for run in all_runs:
            name_lower = run['name'].lower()
            
            # Responder runs
            if 'responder' in name_lower:
                responder_runs.append(run)
            
            # GHL-related runs
            if any(keyword in name_lower for keyword in ['ghl', 'send_message', 'send', 'message']):
                ghl_runs.append(run)
            
            # Tool runs
            if 'tool' in name_lower or run['name'] in ['send_message', 'create_contact', 'get_contact']:
                tool_runs.append(run)
        
        # Print responder runs
        print(f'\n[RESPONDER RUNS]: {len(responder_runs)}')
        for run in responder_runs:
            indent = '  ' * run['depth']
            print(f'{indent}Name: {run["name"]}')
            print(f'{indent}Status: {run["status"]}')
            if run['outputs']:
                print(f'{indent}Outputs:')
                output_str = json.dumps(run['outputs'], indent=2)
                for line in output_str.split('\n')[:10]:  # First 10 lines
                    print(f'{indent}  {line}')
        
        # Print GHL runs
        print(f'\n[GHL/MESSAGE RUNS]: {len(ghl_runs)}')
        for run in ghl_runs:
            indent = '  ' * run['depth']
            print(f'{indent}Name: {run["name"]}')
            print(f'{indent}Status: {run["status"]}')
            if run['error']:
                print(f'{indent}Error: {run["error"]}')
            if run['outputs']:
                print(f'{indent}Outputs: {json.dumps(run["outputs"], indent=2)[:200]}...')
        
        # Print tool runs
        print(f'\n[TOOL RUNS]: {len(tool_runs)}')
        for run in tool_runs:
            indent = '  ' * run['depth']
            print(f'{indent}Name: {run["name"]}')
            print(f'{indent}Status: {run["status"]}')
            if run['error']:
                print(f'{indent}Error: {run["error"]}')
            if run['outputs']:
                print(f'{indent}Outputs: {json.dumps(run["outputs"], indent=2)[:200]}...')
        
        # Check for any runs that might be sending messages
        print('\n[CHECKING FOR MESSAGE SENDING INDICATORS]')
        message_indicators = ['message_sent', 'last_sent_message', 'response', 'reply']
        
        for run in all_runs:
            if run['outputs'] and isinstance(run['outputs'], dict):
                for key in run['outputs']:
                    if any(indicator in key.lower() for indicator in message_indicators):
                        print(f'\nFound in {run["name"]}:')
                        print(f'  Key: {key}')
                        print(f'  Value: {run["outputs"][key]}')
        
        # Print full hierarchy
        print('\n[FULL RUN HIERARCHY]')
        for run in all_runs:
            indent = '  ' * run['depth']
            print(f'{indent}{run["name"]} ({run["status"]})')
            if run['error']:
                print(f'{indent}  ERROR: {run["error"]}')
                
    except Exception as e:
        print(f'Error analyzing trace {trace_id}: {e}')
        import traceback
        traceback.print_exc()

# Run analysis
if __name__ == "__main__":
    for trace_id in trace_ids:
        analyze_trace_deep(trace_id)
#!/usr/bin/env python3
"""Trace GHL message sending in detail"""

import os
import json
from langsmith import Client
from datetime import datetime

# Set up the client
os.environ['LANGCHAIN_API_KEY'] = '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'
client = Client()

# Trace IDs to analyze
trace_ids = [
    '1f067450-f248-6c65-ad62-5b003dd1b02a',
    '1f067452-0dda-61cc-bd5a-b380392345a3'
]

def get_all_runs_in_trace(client, trace_id):
    """Get all runs in a trace recursively"""
    all_runs = []
    
    def get_runs_recursive(parent_id=None, depth=0):
        if parent_id:
            runs = list(client.list_runs(
                project_name="default",
                filter=f'eq(parent_run_id, "{parent_id}")'
            ))
        else:
            runs = [client.read_run(trace_id)]
        
        for run in runs:
            all_runs.append({
                'id': run.id,
                'name': run.name,
                'status': run.status,
                'error': run.error,
                'inputs': run.inputs,
                'outputs': run.outputs,
                'depth': depth,
                'start_time': run.start_time,
                'end_time': run.end_time,
                'run_type': run.run_type,
                'parent_run_id': run.parent_run_id,
                'events': getattr(run, 'events', [])
            })
            # Recursively get children
            get_runs_recursive(run.id, depth + 1)
    
    get_runs_recursive()
    return all_runs

def analyze_trace_for_ghl(trace_id):
    """Analyze trace for GHL message sending"""
    print(f"\n{'='*80}")
    print(f"TRACE: {trace_id}")
    print('='*80)
    
    try:
        # Get all runs
        all_runs = get_all_runs_in_trace(client, trace_id)
        
        print(f"Total runs: {len(all_runs)}")
        
        # Find responder node
        responder_runs = [r for r in all_runs if 'responder' in r['name'].lower()]
        
        if responder_runs:
            print(f"\n[RESPONDER NODE ANALYSIS]")
            for r in responder_runs:
                print(f"Name: {r['name']}")
                print(f"Status: {r['status']}")
                print(f"Start: {r['start_time']}")
                print(f"End: {r['end_time']}")
                
                if r['outputs']:
                    print("Outputs:")
                    print(json.dumps(r['outputs'], indent=2))
                
                # Check if there are any child runs
                responder_children = [run for run in all_runs if run['parent_run_id'] == r['id']]
                print(f"\nChild runs of responder: {len(responder_children)}")
                
                for child in responder_children:
                    print(f"  - {child['name']} ({child['run_type']}) - Status: {child['status']}")
                    if child['error']:
                        print(f"    ERROR: {child['error']}")
        
        # Look for any API calls or tool invocations
        print("\n[TOOL/API CALLS]")
        tool_runs = [r for r in all_runs if r['run_type'] in ['tool', 'chain']]
        
        for tool in tool_runs:
            print(f"\nTool: {tool['name']}")
            print(f"Type: {tool['run_type']}")
            print(f"Status: {tool['status']}")
            if tool['error']:
                print(f"Error: {tool['error']}")
            
            # Check inputs/outputs for GHL-related content
            if tool['inputs']:
                input_str = str(tool['inputs'])
                if any(keyword in input_str.lower() for keyword in ['ghl', 'message', 'send', 'contact']):
                    print(f"GHL-related inputs: {tool['inputs']}")
            
            if tool['outputs']:
                output_str = str(tool['outputs'])
                if any(keyword in output_str.lower() for keyword in ['ghl', 'message', 'send', 'contact']):
                    print(f"GHL-related outputs: {tool['outputs']}")
        
        # Check for any async function calls
        print("\n[ASYNC EXECUTION CHECK]")
        async_keywords = ['await', 'async', 'asyncio', 'coroutine']
        
        for run in all_runs:
            if run['error']:
                error_str = str(run['error']).lower()
                if any(kw in error_str for kw in async_keywords):
                    print(f"\nAsync error in {run['name']}:")
                    print(f"  {run['error']}")
        
        # Look for actual message sending evidence
        print("\n[MESSAGE SENDING EVIDENCE]")
        message_evidence = []
        
        for run in all_runs:
            # Check outputs for message_sent flags
            if run['outputs'] and isinstance(run['outputs'], dict):
                if run['outputs'].get('message_sent'):
                    message_evidence.append({
                        'node': run['name'],
                        'message_sent': run['outputs'].get('message_sent'),
                        'last_sent_message': run['outputs'].get('last_sent_message', '')[0:100] + '...'
                    })
        
        for evidence in message_evidence:
            print(f"\n✅ {evidence['node']} reported message_sent={evidence['message_sent']}")
            print(f"   Message: {evidence['last_sent_message']}")
        
        # Check the actual execution flow
        print("\n[EXECUTION FLOW]")
        for i, run in enumerate(all_runs):
            indent = '  ' * run['depth']
            duration = None
            if run['start_time'] and run['end_time']:
                duration = (run['end_time'] - run['start_time']).total_seconds()
            
            duration_str = f"{duration:.2f}s" if duration else "N/A"
            print(f"{indent}{i+1}. {run['name']} ({run['run_type']}) - {run['status']} [{duration_str}]")
        
    except Exception as e:
        print(f"Error analyzing trace: {e}")
        import traceback
        traceback.print_exc()

# Run analysis
if __name__ == "__main__":
    for trace_id in trace_ids:
        analyze_trace_for_ghl(trace_id)
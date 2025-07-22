#!/usr/bin/env python3
"""Analyze LangSmith traces for responder node execution."""

import os
import json
from datetime import datetime
from langsmith import Client

# Set up the client
os.environ['LANGCHAIN_API_KEY'] = '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'
client = Client()

# Trace IDs to analyze
trace_ids = [
    '1f067450-f248-6c65-ad62-5b003dd1b02a',
    '1f067452-0dda-61cc-bd5a-b380392345a3'
]

def analyze_trace(trace_id):
    """Analyze a single trace for responder node execution."""
    print(f'\n{"="*80}')
    print(f'ANALYZING TRACE: {trace_id}')
    print('='*80)
    
    try:
        # Get the run tree
        run = client.read_run(trace_id)
        
        print(f'\nRun Name: {run.name}')
        print(f'Status: {run.status}')
        print(f'Error: {run.error}')
        print(f'Total Tokens: {run.total_tokens}')
        print(f'Total Cost: {run.total_cost}')
        
        # Get all child runs
        child_runs = list(client.list_runs(
            project_id=run.session_id, 
            filter=f'eq(parent_run_id, "{trace_id}")'
        ))
        
        print(f'\nTotal Child Runs: {len(child_runs)}')
        
        # Look for responder_streaming_node
        responder_found = False
        ghl_send_found = False
        import_errors = []
        async_errors = []
        
        # Analyze each child run
        for child in child_runs:
            # Check for responder node
            if 'responder' in child.name.lower():
                responder_found = True
                print(f'\n[RESPONDER NODE FOUND]')
                print(f'  Name: {child.name}')
                print(f'  Status: {child.status}')
                print(f'  Error: {child.error}')
                print(f'  Start Time: {child.start_time}')
                print(f'  End Time: {child.end_time}')
                
                if child.outputs:
                    print(f'  Outputs: {json.dumps(child.outputs, indent=2)[:500]}...')
                
                if child.inputs:
                    print(f'  Inputs: {json.dumps(child.inputs, indent=2)[:500]}...')
                
                # Check for deeper runs within responder
                responder_children = list(client.list_runs(
                    project_id=run.session_id,
                    filter=f'eq(parent_run_id, "{child.id}")'
                ))
                
                print(f'  Child Runs: {len(responder_children)}')
                for rc in responder_children:
                    print(f'    - {rc.name} (Status: {rc.status})')
                    if rc.error:
                        print(f'      ERROR: {rc.error}')
            
            # Check for GHL send message
            if 'send_message' in child.name.lower() or 'ghl' in child.name.lower():
                ghl_send_found = True
                print(f'\n[GHL SEND MESSAGE FOUND]')
                print(f'  Name: {child.name}')
                print(f'  Status: {child.status}')
                print(f'  Error: {child.error}')
                if child.outputs:
                    print(f'  Outputs: {json.dumps(child.outputs, indent=2)[:500]}...')
            
            # Check for import errors
            if child.error and 'import' in str(child.error).lower():
                import_errors.append({
                    'node': child.name,
                    'error': child.error
                })
            
            # Check for async errors
            if child.error and ('async' in str(child.error).lower() or 'await' in str(child.error).lower()):
                async_errors.append({
                    'node': child.name,
                    'error': child.error
                })
        
        # Summary
        print('\n[SUMMARY]')
        print(f'Responder Node Found: {responder_found}')
        print(f'GHL Send Message Found: {ghl_send_found}')
        print(f'Import Errors: {len(import_errors)}')
        print(f'Async Errors: {len(async_errors)}')
        
        if import_errors:
            print('\n[IMPORT ERRORS]')
            for err in import_errors:
                print(f'  Node: {err["node"]}')
                print(f'  Error: {err["error"]}')
        
        if async_errors:
            print('\n[ASYNC ERRORS]')
            for err in async_errors:
                print(f'  Node: {err["node"]}')
                print(f'  Error: {err["error"]}')
        
        # List all node names for visibility
        print('\n[ALL NODES IN TRACE]')
        for i, child in enumerate(child_runs):
            print(f'{i+1}. {child.name} - Status: {child.status}')
            if child.error:
                print(f'   ERROR: {child.error}')
        
        # Check for specific node patterns
        print('\n[NODE PATTERN ANALYSIS]')
        node_types = {}
        for child in child_runs:
            node_type = child.name.split('_')[0] if '_' in child.name else child.name
            node_types[node_type] = node_types.get(node_type, 0) + 1
        
        for node_type, count in sorted(node_types.items()):
            print(f'  {node_type}: {count} runs')
                
    except Exception as e:
        print(f'Error analyzing trace {trace_id}: {e}')
        import traceback
        traceback.print_exc()

# Run analysis
if __name__ == "__main__":
    for trace_id in trace_ids:
        analyze_trace(trace_id)
    
    print('\n' + '='*80)
    print('ANALYSIS COMPLETE')
    print('='*80)
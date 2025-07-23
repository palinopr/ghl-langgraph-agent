#!/usr/bin/env python3
"""Analyze LangSmith trace 1f067eb0-decd-6fa0-bd20-0b503c8fd356"""

import os
import sys
from datetime import datetime
from langsmith import Client
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

def analyze_trace(trace_id):
    """Analyze a specific trace from LangSmith"""
    client = Client()
    
    print(f"\n{'='*80}")
    print(f"Analyzing Trace: {trace_id}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")
    
    try:
        # Get the main run
        run = client.read_run(trace_id)
        
        print(f"Run Name: {run.name}")
        print(f"Run Type: {run.run_type}")
        print(f"Status: {run.status}")
        print(f"Start Time: {run.start_time}")
        print(f"End Time: {run.end_time}")
        print(f"Total Tokens: {run.total_tokens if hasattr(run, 'total_tokens') else 'N/A'}")
        
        # Print inputs
        print(f"\n{'='*40} INPUTS {'='*40}")
        print(json.dumps(run.inputs, indent=2) if run.inputs else "No inputs")
        
        # Print outputs
        print(f"\n{'='*40} OUTPUTS {'='*40}")
        print(json.dumps(run.outputs, indent=2) if run.outputs else "No outputs")
        
        # Print error if any
        if run.error:
            print(f"\n{'='*40} ERROR {'='*40}")
            print(run.error)
        
        # Get child runs
        print(f"\n{'='*40} CHILD RUNS {'='*40}")
        
        # Get project ID from session_id or use a default project
        project_id = None
        if hasattr(run, 'session_id') and run.session_id:
            project_id = str(run.session_id)
        
        # Try to get child runs
        try:
            if project_id:
                child_runs = list(client.list_runs(
                    project_id=project_id,
                    filter=f'eq(parent_run_id, "{trace_id}")',
                    is_root=False
                ))
            else:
                # Alternative approach - get all runs and filter
                child_runs = []
                for r in client.list_runs(is_root=False):
                    if hasattr(r, 'parent_run_id') and str(r.parent_run_id) == trace_id:
                        child_runs.append(r)
                    if len(child_runs) > 20:  # Limit to prevent too many
                        break
        except Exception as e:
            print(f"Error getting child runs: {e}")
            child_runs = []
        
        for i, child in enumerate(child_runs):
            print(f"\n--- Child Run {i+1} ---")
            print(f"Name: {child.name}")
            print(f"Type: {child.run_type}")
            print(f"Status: {child.status}")
            
            # Special handling for receptionist
            if "receptionist" in child.name.lower():
                print("\n[RECEPTIONIST DETAILS]")
                print(f"Inputs: {json.dumps(child.inputs, indent=2) if child.inputs else 'None'}")
                print(f"Outputs: {json.dumps(child.outputs, indent=2) if child.outputs else 'None'}")
                
                # Look for message processing details
                if child.outputs:
                    if isinstance(child.outputs, dict):
                        messages = child.outputs.get('messages', [])
                        new_messages = child.outputs.get('new_messages', 0)
                        print(f"\nMessages in state: {len(messages) if isinstance(messages, list) else 'N/A'}")
                        print(f"New messages reported: {new_messages}")
            
            # Check for state updates
            if child.outputs and isinstance(child.outputs, dict):
                if 'messages' in child.outputs:
                    messages = child.outputs.get('messages', [])
                    if isinstance(messages, list):
                        print(f"\nMessage count: {len(messages)}")
                        # Show last few messages
                        for msg in messages[-3:]:
                            if isinstance(msg, dict):
                                print(f"  - {msg.get('type', 'unknown')}: {msg.get('content', '')[:100]}...")
        
        # Look for state transitions
        print(f"\n{'='*40} STATE TRANSITIONS {'='*40}")
        state_runs = [r for r in child_runs if 'state' in r.name.lower() or 'checkpoint' in r.name.lower()]
        for state_run in state_runs:
            print(f"\nState Update: {state_run.name}")
            if state_run.outputs:
                print(json.dumps(state_run.outputs, indent=2)[:500] + "...")
        
        # Check for routing decisions
        print(f"\n{'='*40} ROUTING DECISIONS {'='*40}")
        routing_runs = [r for r in child_runs if 'route' in r.name.lower() or 'supervisor' in r.name.lower()]
        for route_run in routing_runs:
            print(f"\nRouting: {route_run.name}")
            if route_run.outputs:
                print(json.dumps(route_run.outputs, indent=2))
        
    except Exception as e:
        print(f"Error analyzing trace: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    trace_id = "1f067eb0-decd-6fa0-bd20-0b503c8fd356"
    if len(sys.argv) > 1:
        trace_id = sys.argv[1]
    
    analyze_trace(trace_id)
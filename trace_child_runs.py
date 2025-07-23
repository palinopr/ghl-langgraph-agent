#!/usr/bin/env python3
"""Analyze child runs to find where message duplication occurs."""

import os
import json
from datetime import datetime
from langsmith import Client

# Initialize LangSmith client
client = Client(
    api_key="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"
)

def analyze_child_runs(trace_id):
    """Analyze child runs to identify where duplication happens."""
    print(f"\n{'='*80}")
    print(f"CHILD RUN ANALYSIS FOR TRACE: {trace_id}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")
    
    try:
        # Get main run
        main_run = client.read_run(trace_id)
        
        # Get all runs from the project
        project_runs = list(client.list_runs(
            project_id=main_run.session_id,
            limit=200
        ))
        
        # Filter for our trace
        child_runs = [r for r in project_runs if str(r.trace_id) == trace_id and r.id != trace_id]
        
        # Sort by start time
        child_runs.sort(key=lambda x: x.start_time)
        
        print(f"Found {len(child_runs)} child runs\n")
        
        # Track message evolution
        message_tracking = []
        
        for i, run in enumerate(child_runs, 1):
            print(f"\n{'='*60}")
            print(f"RUN {i}: {run.name}")
            print(f"{'='*60}")
            print(f"ID: {run.id}")
            print(f"Type: {run.run_type}")
            print(f"Status: {run.status}")
            print(f"Start: {run.start_time.strftime('%H:%M:%S.%f')[:-3]}")
            
            # Check inputs
            if run.inputs:
                if 'messages' in run.inputs:
                    input_messages = run.inputs['messages']
                    print(f"\nINPUT Messages: {len(input_messages)}")
                    
                    # Show unique message contents
                    unique_contents = {}
                    for msg in input_messages:
                        if isinstance(msg, dict):
                            content = msg.get('content', '')
                            if content:
                                if content not in unique_contents:
                                    unique_contents[content] = 0
                                unique_contents[content] += 1
                        elif isinstance(msg, str):
                            if msg not in unique_contents:
                                unique_contents[msg] = 0
                            unique_contents[msg] += 1
                    
                    for content, count in unique_contents.items():
                        if count > 1:
                            print(f"  - '{content[:50]}...' (x{count}) ⚠️")
                        else:
                            print(f"  - '{content[:50]}...'")
                
                # Show other relevant inputs
                for key, value in run.inputs.items():
                    if key != 'messages' and key in ['contact_id', 'thread_id', 'next_agent']:
                        print(f"  {key}: {value}")
            
            # Check outputs
            if run.outputs:
                if 'messages' in run.outputs:
                    output_messages = run.outputs['messages']
                    print(f"\nOUTPUT Messages: {len(output_messages)}")
                    
                    # Show unique message contents
                    unique_contents = {}
                    for msg in output_messages:
                        if isinstance(msg, dict):
                            content = msg.get('content', '')
                            if content:
                                if content not in unique_contents:
                                    unique_contents[content] = 0
                                unique_contents[content] += 1
                        elif isinstance(msg, str):
                            if msg not in unique_contents:
                                unique_contents[msg] = 0
                            unique_contents[msg] += 1
                    
                    for content, count in unique_contents.items():
                        if count > 1:
                            print(f"  - '{content[:50]}...' (x{count}) ⚠️")
                        else:
                            print(f"  - '{content[:50]}...'")
                    
                    # Track message count changes
                    if run.inputs and 'messages' in run.inputs:
                        input_count = len(run.inputs['messages'])
                        output_count = len(output_messages)
                        if output_count > input_count:
                            print(f"\n⚠️  MESSAGE COUNT INCREASED: {input_count} → {output_count} (+{output_count - input_count})")
                
                # Check for specific outputs
                if 'next_agent' in run.outputs:
                    print(f"\nNext Agent: {run.outputs['next_agent']}")
                
                if 'agent_task' in run.outputs:
                    print(f"Agent Task: {run.outputs['agent_task']}")
            
            # Check for errors
            if run.error:
                print(f"\n❌ ERROR: {run.error}")
        
        # Summary of duplication sources
        print(f"\n{'='*80}")
        print("DUPLICATION ANALYSIS SUMMARY:")
        print(f"{'='*80}\n")
        
        # Find runs that increased message count
        duplication_runs = []
        for run in child_runs:
            if run.inputs and run.outputs:
                if 'messages' in run.inputs and 'messages' in run.outputs:
                    input_count = len(run.inputs['messages'])
                    output_count = len(run.outputs['messages'])
                    if output_count > input_count:
                        duplication_runs.append({
                            'name': run.name,
                            'increase': output_count - input_count,
                            'input': input_count,
                            'output': output_count
                        })
        
        if duplication_runs:
            print("RUNS THAT INCREASED MESSAGE COUNT:")
            for dup in duplication_runs:
                print(f"  - {dup['name']}: {dup['input']} → {dup['output']} (+{dup['increase']})")
        
        # Check for specific patterns
        print("\nKEY OBSERVATIONS:")
        
        # Check if fetch_conversation is being called multiple times
        fetch_runs = [r for r in child_runs if 'fetch' in r.name.lower() or 'load' in r.name.lower()]
        if len(fetch_runs) > 1:
            print(f"  ⚠️  Multiple fetch/load operations: {len(fetch_runs)}")
        
        # Check for multiple responder calls
        responder_runs = [r for r in child_runs if 'responder' in r.name.lower()]
        if len(responder_runs) > 1:
            print(f"  ⚠️  Multiple responder calls: {len(responder_runs)}")
        
        # Check routing
        route_runs = [r for r in child_runs if 'route' in r.name.lower()]
        print(f"  - Routing operations: {len(route_runs)}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    trace_id = "1f0676c2-3fcd-6754-a8ab-e2e3f352e0c1"
    analyze_child_runs(trace_id)
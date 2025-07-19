#!/usr/bin/env python3
"""
Simple trace analyzer for the specific trace ID
"""
import os
import json
from langsmith import Client

# The trace ID to analyze
TRACE_ID = "1f0649dd-8dac-6802-9b24-a91f9943836c"

# Set API key
os.environ["LANGSMITH_API_KEY"] = "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"

def analyze_trace():
    """Analyze the trace to find GHL API calls and conversation history loading"""
    
    try:
        client = Client()
        
        print(f"\n{'='*80}")
        print(f"ANALYZING TRACE: {TRACE_ID}")
        print(f"{'='*80}")
        
        # Get the main run
        run = client.read_run(TRACE_ID)
        
        print(f"\nMain Run Details:")
        print(f"- Name: {run.name}")
        print(f"- Type: {run.run_type}")
        print(f"- Status: {run.status}")
        print(f"- Start: {run.start_time}")
        
        # Show inputs
        print(f"\n{'='*60}")
        print("INPUTS:")
        print(f"{'='*60}")
        if run.inputs:
            print(json.dumps(run.inputs, indent=2, default=str))
        
        # Get child runs - try without project name first
        try:
            # First get the project from the run
            project_id = run.session_id
            print(f"Project ID from run: {project_id}")
            
            child_runs = list(client.list_runs(
                project_id=project_id,
                filter=f'eq(parent_run_id, "{TRACE_ID}")',
                limit=200
            ))
        except:
            # Fallback to just parent filter
            child_runs = list(client.list_runs(
                filter=f'eq(parent_run_id, "{TRACE_ID}")',
                limit=200
            ))
        
        # Sort by start time
        child_runs.sort(key=lambda x: x.start_time)
        
        print(f"\n{'='*60}")
        print("LOOKING FOR GHL API CALLS AND CONVERSATION HISTORY:")
        print(f"{'='*60}")
        
        # Track GHL calls and conversation history
        ghl_calls = []
        conversation_loads = []
        receptionist_activity = []
        
        for child in child_runs:
            # Look for receptionist node
            if "receptionist" in child.name.lower():
                receptionist_activity.append({
                    "name": child.name,
                    "type": child.run_type,
                    "start": child.start_time,
                    "status": child.status,
                    "inputs": child.inputs,
                    "outputs": child.outputs
                })
            
            # Look for conversation history loading
            if any(term in child.name.lower() for term in ["conversation", "history", "load"]):
                conversation_loads.append({
                    "name": child.name,
                    "type": child.run_type,
                    "start": child.start_time,
                    "status": child.status,
                    "inputs": child.inputs,
                    "outputs": child.outputs
                })
            
            # Look for GHL API calls
            if any(term in child.name.lower() for term in ["ghl", "api", "request", "fetch"]) or \
               (child.run_type == "tool" and "ghl" in str(child.inputs).lower()):
                ghl_calls.append({
                    "name": child.name,
                    "type": child.run_type,
                    "start": child.start_time,
                    "status": child.status,
                    "inputs": child.inputs,
                    "outputs": child.outputs
                })
        
        # Print receptionist activity
        print(f"\n{'='*60}")
        print(f"RECEPTIONIST ACTIVITY ({len(receptionist_activity)} found):")
        print(f"{'='*60}")
        for activity in receptionist_activity:
            print(f"\n{activity['name']} ({activity['type']})")
            print(f"Start: {activity['start']}")
            print(f"Status: {activity['status']}")
            if activity['inputs']:
                print(f"Inputs: {json.dumps(activity['inputs'], indent=2, default=str)[:500]}...")
            if activity['outputs']:
                print(f"Outputs: {json.dumps(activity['outputs'], indent=2, default=str)[:500]}...")
        
        # Print conversation history loads
        print(f"\n{'='*60}")
        print(f"CONVERSATION HISTORY LOADS ({len(conversation_loads)} found):")
        print(f"{'='*60}")
        for load in conversation_loads:
            print(f"\n{load['name']} ({load['type']})")
            print(f"Start: {load['start']}")
            print(f"Status: {load['status']}")
            if load['inputs']:
                print(f"Inputs: {json.dumps(load['inputs'], indent=2, default=str)[:500]}...")
            if load['outputs']:
                print(f"Outputs: {json.dumps(load['outputs'], indent=2, default=str)[:500]}...")
        
        # Print GHL API calls
        print(f"\n{'='*60}")
        print(f"GHL API CALLS ({len(ghl_calls)} found):")
        print(f"{'='*60}")
        for call in ghl_calls:
            print(f"\n{call['name']} ({call['type']})")
            print(f"Start: {call['start']}")
            print(f"Status: {call['status']}")
            if call['inputs']:
                print(f"Inputs: {json.dumps(call['inputs'], indent=2, default=str)[:500]}...")
            if call['outputs']:
                print(f"Outputs: {json.dumps(call['outputs'], indent=2, default=str)[:500]}...")
        
        # Look for all tool calls
        print(f"\n{'='*60}")
        print("ALL TOOL CALLS:")
        print(f"{'='*60}")
        tool_calls = [c for c in child_runs if c.run_type == "tool"]
        for tool in tool_calls[:20]:  # Show first 20
            print(f"\n{tool.name}")
            if tool.inputs:
                print(f"Inputs: {str(tool.inputs)[:200]}...")
            if tool.outputs:
                print(f"Outputs: {str(tool.outputs)[:200]}...")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_trace()
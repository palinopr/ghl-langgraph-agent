#!/usr/bin/env python3
"""
Raw Traces Simplified - Just the data
"""

import os
import json
from langsmith import Client

# Your API key
api_key = "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"

# Initialize client
client = Client(
    api_key=api_key,
    api_url="https://api.smith.langchain.com"
)

# Your specific trace IDs
TRACE_IDS = [
    "1f0669c6-a989-67ec-a016-8f63b91f79c2",
    "1f0669c7-6120-6563-b484-e5ca2a2740d1",
    "1f0669c8-709c-6207-9a9f-ac54af55789c",
    "1f0669c9-c860-6dac-9fd9-2f962b941a71"
]

def dump_trace(run_id: str, index: int):
    """Dump complete raw trace data"""
    print(f"\n{'='*80}")
    print(f"TRACE {index}: {run_id}")
    print(f"{'='*80}")
    
    try:
        # Get the run
        run = client.read_run(run_id)
        
        # Convert to dict for complete dump
        run_dict = {
            "id": str(run.id),
            "name": run.name,
            "status": run.status,
            "type": run.run_type,
            "start_time": str(run.start_time),
            "end_time": str(run.end_time),
            "parent_run_id": str(run.parent_run_id) if run.parent_run_id else None,
            "error": run.error,
            "inputs": run.inputs,
            "outputs": run.outputs,
            "metadata": run.metadata,
            "extra": run.extra,
            "tags": run.tags,
            "total_tokens": run.total_tokens,
            "prompt_tokens": run.prompt_tokens,
            "completion_tokens": run.completion_tokens,
            "total_cost": run.total_cost,
            "prompt_cost": run.prompt_cost,
            "completion_cost": run.completion_cost,
            "events": run.events,
            "session_id": str(run.session_id),
            "revision_id": run.revision_id
        }
        
        # Pretty print the entire run
        print(json.dumps(run_dict, indent=2))
        
        # Get ALL child runs
        print(f"\n{'='*40}")
        print("CHILD RUNS:")
        print(f"{'='*40}")
        
        child_runs = list(client.list_runs(
            project_name="ghl-langgraph-agent",
            filter=f'eq(parent_run_id, "{run_id}")',
            limit=100
        ))
        
        for i, child in enumerate(child_runs, 1):
            child_dict = {
                "index": i,
                "id": str(child.id),
                "name": child.name,
                "type": child.run_type,
                "status": child.status,
                "start_time": str(child.start_time),
                "end_time": str(child.end_time),
                "error": child.error,
                "inputs": child.inputs,
                "outputs": child.outputs,
                "metadata": child.metadata if hasattr(child, 'metadata') else None,
                "total_tokens": child.total_tokens if hasattr(child, 'total_tokens') else None
            }
            
            print(f"\nCHILD {i}:")
            print(json.dumps(child_dict, indent=2))
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """Show raw data for all traces"""
    print("RAW TRACE DATA DUMP")
    print(f"Analyzing {len(TRACE_IDS)} traces")
    
    for i, trace_id in enumerate(TRACE_IDS, 1):
        dump_trace(trace_id, i)
    
    print(f"\n{'='*80}")
    print("COMPLETE")

if __name__ == "__main__":
    main()
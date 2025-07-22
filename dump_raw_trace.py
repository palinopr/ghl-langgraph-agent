#!/usr/bin/env python3
"""
Dump Complete Raw Trace Data
Just the raw data, no analysis
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

# Trace to dump
TRACE_ID = "1f066a2d-302a-6ee9-88b8-db984174a418"

def dump_raw(run_id: str):
    """Dump everything raw"""
    print(f"\n{'='*80}")
    print(f"RAW TRACE DUMP: {run_id}")
    print(f"{'='*80}\n")
    
    try:
        # Get the run
        run = client.read_run(run_id)
        
        # Print every attribute
        print("=== RUN ATTRIBUTES ===")
        for attr in dir(run):
            if not attr.startswith('_'):
                try:
                    value = getattr(run, attr)
                    if not callable(value):
                        print(f"\n{attr}:")
                        print(value)
                        print("-" * 40)
                except Exception as e:
                    print(f"\n{attr}: ERROR - {str(e)}")
        
        print("\n\n=== CHILD RUNS ===")
        # Get ALL child runs
        child_runs = list(client.list_runs(
            project_name="ghl-langgraph-agent",
            filter=f'eq(parent_run_id, "{run_id}")',
            limit=100
        ))
        
        print(f"TOTAL CHILD RUNS: {len(child_runs)}\n")
        
        for i, child in enumerate(child_runs, 1):
            print(f"\n{'='*60}")
            print(f"CHILD {i}: {child.name}")
            print(f"{'='*60}")
            
            # Dump all child attributes
            for attr in dir(child):
                if not attr.startswith('_'):
                    try:
                        value = getattr(child, attr)
                        if not callable(value):
                            print(f"\n{attr}:")
                            print(value)
                    except:
                        pass
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    dump_raw(TRACE_ID)
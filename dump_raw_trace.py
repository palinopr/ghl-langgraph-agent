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
TRACE_ID = "1f067063-cb0e-6fcb-afd5-c1ccbd774d31"

def dump_raw(run_id: str):
    """Dump everything raw"""
    output_file = f"trace_dump_{run_id[:8]}.txt"
    
    with open(output_file, 'w') as f:
        f.write(f"\n{'='*80}\n")
        f.write(f"RAW TRACE DUMP: {run_id}\n")
        f.write(f"{'='*80}\n\n")
        
        try:
            # Get the run
            run = client.read_run(run_id)
            
            # Print every attribute
            f.write("=== RUN ATTRIBUTES ===\n")
            for attr in dir(run):
                if not attr.startswith('_'):
                    try:
                        value = getattr(run, attr)
                        if not callable(value):
                            f.write(f"\n{attr}:\n")
                            f.write(str(value))
                            f.write("\n" + "-" * 40 + "\n")
                    except Exception as e:
                        f.write(f"\n{attr}: ERROR - {str(e)}\n")
            
            f.write("\n\n=== CHILD RUNS ===\n")
            # Get ALL child runs
            child_runs = list(client.list_runs(
                project_name="ghl-langgraph-agent",
                filter=f'eq(parent_run_id, "{run_id}")',
                limit=100
            ))
            
            f.write(f"TOTAL CHILD RUNS: {len(child_runs)}\n\n")
            
            for i, child in enumerate(child_runs, 1):
                f.write(f"\n{'='*60}\n")
                f.write(f"CHILD {i}: {child.name}\n")
                f.write(f"{'='*60}\n")
                
                # Dump all child attributes
                for attr in dir(child):
                    if not attr.startswith('_'):
                        try:
                            value = getattr(child, attr)
                            if not callable(value):
                                f.write(f"\n{attr}:\n")
                                f.write(str(value))
                                f.write("\n")
                        except:
                            pass
            
            print(f"✅ Raw trace dumped to {output_file}")
            
        except Exception as e:
            f.write(f"ERROR: {str(e)}\n")
            import traceback
            f.write(traceback.format_exc())
            print(f"❌ Error dumping trace: {str(e)}")

if __name__ == "__main__":
    dump_raw(TRACE_ID)
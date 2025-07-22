#!/usr/bin/env python3
"""
Dump Complete Raw Trace Data for Three Specific Traces
Just the raw data, no analysis
"""

import os
import json
from langsmith import Client
from datetime import datetime

# Your API key
api_key = "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"

# Initialize client
client = Client(
    api_key=api_key,
    api_url="https://api.smith.langchain.com"
)

# Traces to dump
TRACE_IDS = [
    "1f066b63-5c88-6e9b-9cd1-285e5309cd5d",
    "1f066b64-acfe-6cc3-86e8-f9e9959eb119",
    "1f066b66-360c-64b2-9bce-eef3d5acb32d"
]

def dump_raw(run_id: str, output_file):
    """Dump everything raw"""
    output_file.write(f"\n{'='*80}\n")
    output_file.write(f"RAW TRACE DUMP: {run_id}\n")
    output_file.write(f"{'='*80}\n\n")
    
    try:
        # Get the run
        run = client.read_run(run_id)
        
        # Print every attribute
        output_file.write("=== RUN ATTRIBUTES ===\n")
        for attr in dir(run):
            if not attr.startswith('_'):
                try:
                    value = getattr(run, attr)
                    if not callable(value):
                        output_file.write(f"\n{attr}:\n")
                        output_file.write(str(value))
                        output_file.write("\n" + "-" * 40 + "\n")
                except Exception as e:
                    output_file.write(f"\n{attr}: ERROR - {str(e)}\n")
        
        output_file.write("\n\n=== CHILD RUNS ===\n")
        # Get ALL child runs
        child_runs = list(client.list_runs(
            project_name="ghl-langgraph-agent",
            filter=f'eq(parent_run_id, "{run_id}")',
            limit=100
        ))
        
        output_file.write(f"TOTAL CHILD RUNS: {len(child_runs)}\n\n")
        
        for i, child in enumerate(child_runs, 1):
            output_file.write(f"\n{'='*60}\n")
            output_file.write(f"CHILD {i}: {child.name}\n")
            output_file.write(f"{'='*60}\n")
            
            # Dump all child attributes
            for attr in dir(child):
                if not attr.startswith('_'):
                    try:
                        value = getattr(child, attr)
                        if not callable(value):
                            output_file.write(f"\n{attr}:\n")
                            output_file.write(str(value))
                            output_file.write("\n")
                    except:
                        pass
        
    except Exception as e:
        output_file.write(f"ERROR: {str(e)}\n")
        import traceback
        output_file.write(traceback.format_exc())

if __name__ == "__main__":
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"raw_debug_traces_{timestamp}.txt"
    
    with open(output_filename, 'w') as f:
        f.write(f"Raw Trace Debug Dump - Generated at {datetime.now()}\n")
        f.write(f"Total traces to dump: {len(TRACE_IDS)}\n")
        f.write("="*100 + "\n\n")
        
        for trace_id in TRACE_IDS:
            print(f"Dumping trace: {trace_id}")
            dump_raw(trace_id, f)
            f.write("\n\n" + "="*100 + "\n\n")
    
    print(f"\nDump complete! Saved to: {output_filename}")
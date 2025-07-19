#!/usr/bin/env python3
"""
Debug the receptionist in the trace to see what's happening
"""
import os
from langsmith import Client
import json

# Initialize client
client = Client()

def analyze_receptionist_in_trace(trace_id):
    """Analyze what the receptionist node is doing"""
    
    try:
        print(f"\n{'='*80}")
        print(f"ANALYZING RECEPTIONIST IN TRACE: {trace_id}")
        print(f"{'='*80}")
        
        # Get all runs
        child_runs = list(client.list_runs(
            project_name="ghl-langgraph-agent",
            filter=f'eq(parent_run_id, "{trace_id}")',
            limit=200
        ))
        
        # Sort by time
        child_runs.sort(key=lambda x: x.start_time)
        
        # Find receptionist node
        receptionist_run = None
        for run in child_runs:
            if "receptionist" in run.name.lower():
                receptionist_run = run
                break
        
        if not receptionist_run:
            print("❌ No receptionist run found!")
            return
            
        print(f"\n✓ Found receptionist run: {receptionist_run.name}")
        print(f"  Status: {receptionist_run.status}")
        print(f"  Start: {receptionist_run.start_time}")
        
        # Check inputs
        print(f"\n📥 RECEPTIONIST INPUTS:")
        if receptionist_run.inputs:
            print(json.dumps(receptionist_run.inputs, indent=2, default=str)[:1000])
        
        # Check outputs
        print(f"\n📤 RECEPTIONIST OUTPUTS:")
        if receptionist_run.outputs:
            outputs_str = json.dumps(receptionist_run.outputs, indent=2, default=str)
            
            # Check for key fields
            if "conversation_history" in outputs_str:
                print("✓ Has conversation_history field")
            else:
                print("❌ NO conversation_history field")
                
            if "formatted_history_count" in outputs_str:
                print("✓ Has formatted_history_count field")
            else:
                print("❌ NO formatted_history_count field")
                
            if "messages" in outputs_str:
                # Count messages
                messages = receptionist_run.outputs.get("messages", [])
                print(f"✓ Has {len(messages)} messages")
                
                # Check for historical messages
                historical_count = 0
                for msg in messages:
                    if isinstance(msg, dict):
                        kwargs = msg.get("additional_kwargs", {})
                        if kwargs.get("source") == "ghl_history":
                            historical_count += 1
                
                print(f"  - Historical messages: {historical_count}")
                print(f"  - New messages: {len(messages) - historical_count}")
            
            # Show first 2000 chars of output
            print(f"\nFull output preview:")
            print(outputs_str[:2000])
            
        # Check for errors
        if receptionist_run.error:
            print(f"\n❌ RECEPTIONIST ERROR: {receptionist_run.error}")
            
        # Look for child runs (logging, API calls, etc)
        print(f"\n🔍 RECEPTIONIST CHILD RUNS:")
        receptionist_children = list(client.list_runs(
            project_name="ghl-langgraph-agent",
            filter=f'eq(parent_run_id, "{receptionist_run.id}")',
            limit=50
        ))
        
        for child in receptionist_children:
            print(f"  - {child.name} ({child.run_type})")
            if "ghl" in child.name.lower() or "conversation" in child.name.lower():
                print(f"    → Relevant GHL call!")
                if child.outputs:
                    print(f"    → Output: {str(child.outputs)[:200]}")
                    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


# Analyze the trace
analyze_receptionist_in_trace("1f0649dd-8dac-6802-9b24-a91f9943836c")
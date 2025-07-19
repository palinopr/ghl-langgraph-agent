#!/usr/bin/env python3
"""
Analyze specific LangSmith trace for GHL conversation history loading
"""
import sys
import os
import json
from datetime import datetime

try:
    from langsmith import Client
except ImportError:
    print("Error: langsmith package not installed")
    sys.exit(1)

def analyze_ghl_conversation_trace(trace_id):
    """Analyze trace specifically for GHL conversation history issues"""
    
    api_key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
    if not api_key:
        print("Error: API key not set")
        return
    
    try:
        client = Client()
        
        print(f"\n{'='*80}")
        print(f"ANALYZING GHL CONVERSATION HISTORY TRACE: {trace_id}")
        print(f"{'='*80}")
        
        run = client.read_run(trace_id)
        
        print(f"\nMain Run Details:")
        print(f"- Name: {run.name}")
        print(f"- Type: {run.run_type}")
        print(f"- Status: {run.status}")
        print(f"- Start: {run.start_time}")
        
        # Show webhook inputs
        print(f"\n{'='*60}")
        print("WEBHOOK INPUTS:")
        print(f"{'='*60}")
        if run.inputs:
            print(json.dumps(run.inputs, indent=2, default=str))
        
        # Get child runs
        project_name = "ghl-langgraph-agent"
        
        child_runs = list(client.list_runs(
            project_name=project_name,
            filter=f'eq(parent_run_id, "{trace_id}")',
            limit=200
        ))
        
        # Sort by start time
        child_runs.sort(key=lambda x: x.start_time)
        
        # Track GHL-related calls
        ghl_calls = []
        conversation_history_calls = []
        
        print(f"\n{'='*60}")
        print("SEARCHING FOR GHL CONVERSATION HISTORY CALLS:")
        print(f"{'='*60}")
        
        for i, child in enumerate(child_runs):
            # Look for get_conversation_history function calls
            if "get_conversation_history" in child.name.lower() or \
               "conversation" in child.name.lower() and "history" in child.name.lower():
                conversation_history_calls.append(child)
                print(f"\n✓ FOUND: {child.name}")
                print(f"  Type: {child.run_type}")
                print(f"  Time: {child.start_time}")
                if child.inputs:
                    print(f"  Inputs: {json.dumps(child.inputs, indent=2, default=str)}")
                if child.outputs:
                    print(f"  Outputs: {json.dumps(child.outputs, indent=2, default=str)[:1000]}")
                if child.error:
                    print(f"  ERROR: {child.error}")
            
            # Look for GHL API calls
            if "ghl" in child.name.lower() or "goHighLevel" in str(child.inputs).lower():
                ghl_calls.append(child)
                print(f"\n→ GHL API Call: {child.name}")
                if child.inputs:
                    # Check for API endpoints
                    inputs_str = str(child.inputs)
                    if "conversations" in inputs_str or "messages" in inputs_str:
                        print(f"  API Endpoint mentioned: {inputs_str[:500]}")
                if child.outputs:
                    print(f"  Response: {str(child.outputs)[:500]}")
            
            # Look for HTTP requests
            if child.run_type == "tool" and ("http" in child.name.lower() or "request" in child.name.lower()):
                print(f"\n→ HTTP Request: {child.name}")
                if child.inputs:
                    print(f"  Inputs: {json.dumps(child.inputs, indent=2, default=str)[:500]}")
                if child.outputs:
                    print(f"  Response: {str(child.outputs)[:500]}")
        
        # Look for state updates with conversation history
        print(f"\n{'='*60}")
        print("CHECKING STATE UPDATES:")
        print(f"{'='*60}")
        
        for child in child_runs:
            if "state" in child.name.lower() or "update" in child.name.lower():
                # Check if conversation history is in the state
                if child.outputs and "conversation_history" in str(child.outputs):
                    print(f"\n✓ State with conversation_history: {child.name}")
                    print(f"  Content: {str(child.outputs)[:1000]}")
        
        # Summary
        print(f"\n{'='*60}")
        print("SUMMARY:")
        print(f"{'='*60}")
        print(f"Total child runs: {len(child_runs)}")
        print(f"GHL-related calls: {len(ghl_calls)}")
        print(f"Conversation history calls: {len(conversation_history_calls)}")
        
        if not conversation_history_calls:
            print("\n⚠️  NO get_conversation_history CALLS FOUND!")
            print("This suggests the function might not be called at all.")
        
        # Check the supervisor/receptionist flow
        print(f"\n{'='*60}")
        print("AGENT FLOW:")
        print(f"{'='*60}")
        
        for child in child_runs[:20]:  # First 20 runs
            if any(agent in child.name.lower() for agent in ["supervisor", "receptionist", "maria", "carlos", "sofia"]):
                print(f"\n{child.name}")
                if child.outputs and "messages" in str(child.outputs):
                    output_str = str(child.outputs)
                    if "conversation_history" in output_str:
                        print("  → Has conversation_history in output")
                    else:
                        print("  → NO conversation_history in output")
                        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

# Analyze the specific trace
analyze_ghl_conversation_trace("1f0649dd-8dac-6802-9b24-a91f9943836c")
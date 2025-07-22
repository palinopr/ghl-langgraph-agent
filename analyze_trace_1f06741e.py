#!/usr/bin/env python3
"""
Analyze LangSmith Trace 1f06741e-ccb0-601a-b8f1-27a2983f26b7
Specifically looking for responder node execution and GHL API calls
"""

import os
from datetime import datetime
from langsmith import Client
import json

# Initialize client
api_key = os.getenv("LANGSMITH_API_KEY", "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")
client = Client(
    api_key=api_key,
    api_url="https://api.smith.langchain.com"
)

# The specific trace ID to analyze
TRACE_ID = "1f06741e-ccb0-601a-b8f1-27a2983f26b7"

def print_run_details(run, indent=0):
    """Print detailed information about a run"""
    prefix = "  " * indent
    
    print(f"{prefix}━━━ {run.name} [{run.run_type}] ━━━")
    print(f"{prefix}ID: {run.id}")
    print(f"{prefix}Status: {run.status}")
    print(f"{prefix}Start: {run.start_time}")
    print(f"{prefix}End: {run.end_time}")
    
    if run.error:
        print(f"{prefix}❌ ERROR: {run.error}")
    
    # Check for responder node
    if "responder" in run.name.lower():
        print(f"{prefix}✓ RESPONDER NODE FOUND!")
        if run.inputs:
            print(f"{prefix}Inputs: {json.dumps(run.inputs, indent=2)[:500]}...")
        if run.outputs:
            print(f"{prefix}Outputs: {json.dumps(run.outputs, indent=2)[:500]}...")
    
    # Check for GHL API calls
    if run.run_type == "tool" and ("ghl" in run.name.lower() or "send" in run.name.lower() or "message" in run.name.lower()):
        print(f"{prefix}✓ GHL API CALL DETECTED!")
        if run.inputs:
            print(f"{prefix}API Inputs: {json.dumps(run.inputs, indent=2)[:500]}...")
        if run.outputs:
            print(f"{prefix}API Response: {json.dumps(run.outputs, indent=2)[:500]}...")
    
    # Check for final response
    if run.outputs and isinstance(run.outputs, dict):
        if "messages" in run.outputs:
            messages = run.outputs.get("messages", [])
            for msg in messages:
                if isinstance(msg, dict) and msg.get("type") == "ai":
                    print(f"{prefix}🤖 AI Response: {msg.get('content', 'No content')[:200]}...")
        
        # Check for response field
        if "response" in run.outputs:
            print(f"{prefix}📝 Final Response: {run.outputs['response'][:200]}...")

def analyze_trace_tree(run_id, indent=0):
    """Recursively analyze the trace tree"""
    try:
        # Get child runs
        child_runs = list(client.list_runs(
            project_name="ghl-langgraph-agent",
            filter=f'eq(parent_run_id, "{run_id}")',
            limit=100
        ))
        
        for child in child_runs:
            print_run_details(child, indent)
            # Recurse into children
            analyze_trace_tree(child.id, indent + 1)
            
    except Exception as e:
        print(f"{'  ' * indent}Error getting children: {e}")

def main():
    """Main analysis function"""
    print(f"🔍 Analyzing LangSmith Trace: {TRACE_ID}")
    print("=" * 80)
    
    try:
        # Get the main run
        run = client.read_run(TRACE_ID)
        
        print("\n=== MAIN RUN DETAILS ===")
        print(f"Name: {run.name}")
        print(f"Type: {run.run_type}")
        print(f"Status: {run.status}")
        print(f"Start Time: {run.start_time}")
        print(f"End Time: {run.end_time}")
        print(f"Error: {run.error}")
        
        # Show inputs
        print("\n=== INPUTS ===")
        if run.inputs:
            print(json.dumps(run.inputs, indent=2)[:1000])
            if len(json.dumps(run.inputs)) > 1000:
                print("... (truncated)")
        
        # Show outputs
        print("\n=== OUTPUTS ===")
        if run.outputs:
            print(json.dumps(run.outputs, indent=2)[:1000])
            if len(json.dumps(run.outputs)) > 1000:
                print("... (truncated)")
        
        # Analyze the execution tree
        print("\n=== EXECUTION FLOW ===")
        print_run_details(run, 0)
        analyze_trace_tree(TRACE_ID, 1)
        
        # Summary
        print("\n=== ANALYSIS SUMMARY ===")
        
        # Count nodes
        all_runs = [run]
        
        def collect_all_runs(run_id):
            child_runs = list(client.list_runs(
                project_name="ghl-langgraph-agent",
                filter=f'eq(parent_run_id, "{run_id}")',
                limit=100
            ))
            all_runs.extend(child_runs)
            for child in child_runs:
                collect_all_runs(child.id)
        
        collect_all_runs(TRACE_ID)
        
        # Analyze what we found
        responder_found = False
        ghl_calls = []
        errors = []
        final_responses = []
        
        for r in all_runs:
            if "responder" in r.name.lower():
                responder_found = True
            
            if r.run_type == "tool" and ("ghl" in r.name.lower() or "send" in r.name.lower()):
                ghl_calls.append(r)
            
            if r.error:
                errors.append((r.name, r.error))
            
            if r.outputs and isinstance(r.outputs, dict):
                if "response" in r.outputs:
                    final_responses.append(r.outputs["response"])
                if "messages" in r.outputs:
                    for msg in r.outputs.get("messages", []):
                        if isinstance(msg, dict) and msg.get("type") == "ai":
                            final_responses.append(msg.get("content", ""))
        
        print(f"\n1. Message Processing: {'✓ SUCCESS' if run.status == 'success' else '❌ FAILED'}")
        print(f"2. Responder Node Called: {'✓ YES' if responder_found else '❌ NO'}")
        print(f"3. GHL API Calls: {len(ghl_calls)} found")
        for call in ghl_calls:
            print(f"   - {call.name}: {call.status}")
        print(f"4. Errors: {len(errors)} found")
        for name, error in errors:
            print(f"   - {name}: {error[:100]}...")
        print(f"5. Final Responses: {len(final_responses)} found")
        for i, resp in enumerate(final_responses[:3]):
            print(f"   - Response {i+1}: {resp[:100]}...")
        
    except Exception as e:
        print(f"❌ Error analyzing trace: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
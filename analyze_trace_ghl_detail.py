#!/usr/bin/env python3
"""
Deep dive into GHL API calls and message sending
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

def analyze_all_runs(trace_id):
    """Get all runs in the trace tree"""
    all_runs = []
    
    def collect_runs(run_id):
        try:
            # Get child runs
            child_runs = list(client.list_runs(
                project_name="ghl-langgraph-agent",
                filter=f'eq(parent_run_id, "{run_id}")',
                limit=200
            ))
            all_runs.extend(child_runs)
            
            # Recurse for each child
            for child in child_runs:
                collect_runs(child.id)
        except Exception as e:
            print(f"Error collecting runs: {e}")
    
    # Get the main run
    try:
        main_run = client.read_run(trace_id)
        all_runs.append(main_run)
        collect_runs(trace_id)
    except Exception as e:
        print(f"Error reading main run: {e}")
    
    return all_runs

def main():
    print(f"🔍 Deep Analysis of GHL API Calls in Trace: {TRACE_ID}")
    print("=" * 80)
    
    # Get all runs
    all_runs = analyze_all_runs(TRACE_ID)
    print(f"\nTotal runs found: {len(all_runs)}")
    
    # Look for any API-related activity
    print("\n=== SEARCHING FOR GHL/API ACTIVITY ===")
    
    api_keywords = ["ghl", "send", "message", "api", "http", "request", "post", "webhook", "conversation", "create"]
    
    for run in all_runs:
        # Check run name for API-related keywords
        name_lower = run.name.lower() if run.name else ""
        if any(keyword in name_lower for keyword in api_keywords):
            print(f"\n📌 Potential API Activity: {run.name}")
            print(f"   Type: {run.run_type}")
            print(f"   Status: {run.status}")
            print(f"   ID: {run.id}")
            
            if run.inputs:
                print(f"   Inputs: {json.dumps(run.inputs, indent=4)[:500]}...")
            if run.outputs:
                print(f"   Outputs: {json.dumps(run.outputs, indent=4)[:500]}...")
            if run.error:
                print(f"   ❌ Error: {run.error}")
    
    # Check for tools specifically
    print("\n=== ALL TOOL CALLS ===")
    tool_runs = [r for r in all_runs if r.run_type == "tool"]
    
    if tool_runs:
        for tool in tool_runs:
            print(f"\n🔧 Tool: {tool.name}")
            print(f"   Status: {tool.status}")
            print(f"   Duration: {(tool.end_time - tool.start_time).total_seconds() if tool.end_time and tool.start_time else 'N/A'}s")
            if tool.inputs:
                print(f"   Inputs: {json.dumps(tool.inputs, indent=4)[:300]}...")
            if tool.outputs:
                print(f"   Outputs: {json.dumps(tool.outputs, indent=4)[:300]}...")
    else:
        print("No tool calls found!")
    
    # Check the responder node specifically
    print("\n=== RESPONDER NODE ANALYSIS ===")
    responder_runs = [r for r in all_runs if "responder" in (r.name or "").lower()]
    
    for responder in responder_runs:
        print(f"\n✅ Responder: {responder.name}")
        print(f"   Status: {responder.status}")
        
        if responder.outputs:
            print(f"   Outputs: {json.dumps(responder.outputs, indent=4)}")
            
            # Check if responder tried to send message
            if "ghl_response" in responder.outputs:
                print("   ⚠️  Found ghl_response in outputs!")
            if "error" in responder.outputs:
                print("   ❌ Found error in outputs!")
    
    # Look for any HTTP/API related content in outputs
    print("\n=== CHECKING FOR API RESPONSES IN OUTPUTS ===")
    for run in all_runs:
        if run.outputs and isinstance(run.outputs, dict):
            output_str = json.dumps(run.outputs).lower()
            if any(keyword in output_str for keyword in ["status_code", "response", "error", "api", "http", "ghl"]):
                print(f"\n🔍 {run.name} contains API-related output:")
                print(f"   {json.dumps(run.outputs, indent=4)[:500]}...")
    
    # Final summary
    print("\n=== SUMMARY ===")
    print(f"1. Total runs analyzed: {len(all_runs)}")
    print(f"2. Tool calls found: {len(tool_runs)}")
    print(f"3. Responder nodes found: {len(responder_runs)}")
    
    # Check if message was sent to GHL
    ghl_sent = False
    for run in all_runs:
        if run.outputs and isinstance(run.outputs, dict):
            if "ghl_response" in run.outputs or "status_code" in str(run.outputs):
                ghl_sent = True
                break
    
    print(f"4. Message sent to GHL: {'✓ YES' if ghl_sent else '❌ NO'}")
    
    # Get final response
    final_response = None
    for run in responder_runs:
        if run.outputs and isinstance(run.outputs, dict):
            final_response = run.outputs.get("final_response", None)
            if final_response:
                break
    
    if final_response:
        print(f"\n5. Final Response Generated:")
        print(f"   {final_response}")
    else:
        print("\n5. No final response found in responder outputs")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Analyze why responder is not sending to GHL
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

def get_all_runs(trace_id):
    """Get all runs in trace hierarchy"""
    all_runs = []
    
    def collect_runs(run_id, depth=0):
        try:
            if depth == 0:
                # Get the main run
                run = client.read_run(run_id)
                all_runs.append(run)
            
            # Get child runs
            child_runs = list(client.list_runs(
                project_name="ghl-langgraph-agent",
                filter=f'eq(parent_run_id, "{run_id}")',
                limit=200
            ))
            
            for child in child_runs:
                all_runs.append(child)
                collect_runs(child.id, depth + 1)
                
        except Exception as e:
            print(f"Error collecting runs at depth {depth}: {e}")
    
    collect_runs(trace_id)
    return all_runs

def main():
    print(f"🔍 Analyzing Responder Issue in Trace: {TRACE_ID}")
    print("=" * 80)
    
    # Get all runs
    all_runs = get_all_runs(TRACE_ID)
    print(f"Total runs found: {len(all_runs)}")
    
    # Find responder node
    responder_runs = [r for r in all_runs if "responder" in (r.name or "").lower()]
    
    if not responder_runs:
        print("\n❌ NO RESPONDER NODE FOUND!")
        return
    
    for responder in responder_runs:
        print(f"\n=== RESPONDER NODE ANALYSIS ===")
        print(f"Name: {responder.name}")
        print(f"Type: {responder.run_type}")
        print(f"Status: {responder.status}")
        print(f"ID: {responder.id}")
        print(f"Start: {responder.start_time}")
        print(f"End: {responder.end_time}")
        
        # Check inputs
        print("\n📥 RESPONDER INPUTS:")
        if responder.inputs:
            print(json.dumps(responder.inputs, indent=2))
        else:
            print("No inputs!")
        
        # Check outputs
        print("\n📤 RESPONDER OUTPUTS:")
        if responder.outputs:
            print(json.dumps(responder.outputs, indent=2))
        else:
            print("No outputs!")
        
        # Check for errors
        if responder.error:
            print(f"\n❌ ERROR: {responder.error}")
        
        # Look for child runs (should include GHL API calls)
        print("\n🔄 RESPONDER CHILD RUNS:")
        responder_children = [r for r in all_runs if r.parent_run_id == responder.id]
        
        if responder_children:
            for child in responder_children:
                print(f"\n  └─ {child.name} [{child.run_type}]")
                print(f"     Status: {child.status}")
                if child.error:
                    print(f"     ❌ Error: {child.error}")
                if child.inputs:
                    print(f"     Inputs: {json.dumps(child.inputs, indent=6)[:200]}...")
                if child.outputs:
                    print(f"     Outputs: {json.dumps(child.outputs, indent=6)[:200]}...")
        else:
            print("  ❌ No child runs (NO GHL API CALLS!)")
    
    # Check state at responder
    print("\n=== STATE AT RESPONDER ===")
    for responder in responder_runs:
        if responder.inputs:
            state = responder.inputs
            print(f"contact_id: {state.get('contact_id')}")
            print(f"webhook_data type: {state.get('webhook_data', {}).get('type')}")
            print(f"message_sent: {state.get('message_sent')}")
            print(f"last_sent_message: {state.get('last_sent_message', 'None')[:50]}...")
            print(f"Number of messages: {len(state.get('messages', []))}")
            
            # Check last few messages
            messages = state.get('messages', [])
            if messages:
                print("\nLast 3 messages:")
                for i, msg in enumerate(messages[-3:]):
                    msg_type = msg.get('type') if isinstance(msg, dict) else type(msg).__name__
                    content = msg.get('content', '') if isinstance(msg, dict) else getattr(msg, 'content', '')
                    print(f"  [{i}] {msg_type}: {content[:60]}...")
    
    # Summary
    print("\n=== DIAGNOSIS ===")
    
    # Check if responder ran
    if responder_runs:
        print("✅ Responder node executed")
        
        # Check if it has outputs
        has_outputs = any(r.outputs for r in responder_runs)
        if has_outputs:
            print("✅ Responder produced outputs")
        else:
            print("❌ Responder produced no outputs")
        
        # Check for GHL calls
        ghl_calls = [r for r in all_runs if r.parent_run_id in [resp.id for resp in responder_runs]]
        if ghl_calls:
            print(f"✅ Found {len(ghl_calls)} child runs from responder")
        else:
            print("❌ No GHL API calls made by responder")
        
        # Check for final_response
        for resp in responder_runs:
            if resp.outputs and resp.outputs.get('final_response'):
                print(f"✅ Final response generated: '{resp.outputs['final_response'][:50]}...'")
            else:
                print("⚠️  No final_response in outputs")
    else:
        print("❌ Responder node never executed!")

if __name__ == "__main__":
    main()
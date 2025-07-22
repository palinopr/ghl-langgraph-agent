#!/usr/bin/env python3
"""
Analyze LangSmith traces using the SDK to check GHL message sending
"""
import os
from langsmith import Client
from datetime import datetime

# Set API key
os.environ["LANGSMITH_API_KEY"] = "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"

# Initialize client
client = Client()

# Trace IDs to analyze
TRACE_IDS = [
    "1f067450-f248-6c65-ad62-5b003dd1b02a",
    "1f067452-0dda-61cc-bd5a-b380392345a3",
    "1f067457-2c04-6467-a9a8-13cdc906c098"  # Most recent trace
]

def analyze_trace(trace_id: str):
    """Analyze a single trace"""
    print(f"\n{'='*70}")
    print(f"ANALYZING TRACE: {trace_id}")
    print(f"{'='*70}")
    
    try:
        # Get the main run
        run = client.read_run(trace_id)
        
        print(f"\nMain Run:")
        print(f"  Name: {run.name}")
        print(f"  Status: {run.status}")
        print(f"  Start: {run.start_time}")
        print(f"  End: {run.end_time}")
        
        # Get child runs
        child_runs = list(client.list_runs(parent_run_id=trace_id))
        print(f"\nTotal child runs: {len(child_runs)}")
        
        # Look for responder node
        responder_found = False
        ghl_calls = []
        
        for child in child_runs:
            # Print all child run names for debugging
            print(f"\n  [{child.run_type}] {child.name}")
            
            # Check for responder
            if "responder" in child.name.lower():
                responder_found = True
                print(f"\n    🎯 RESPONDER NODE FOUND!")
                print(f"    - ID: {child.id}")
                print(f"    - Status: {child.status}")
                
                # Check outputs
                if child.outputs:
                    print(f"    - Outputs:")
                    for key, value in child.outputs.items():
                        if key == "last_sent_message" and value:
                            print(f"      - {key}: {str(value)[:100]}...")
                        else:
                            print(f"      - {key}: {value}")
                
                # Check for errors
                if child.error:
                    print(f"    - ❌ ERROR: {child.error}")
                
                # Get grandchild runs (responder's children)
                grandchildren = list(client.list_runs(parent_run_id=child.id))
                if grandchildren:
                    print(f"    - Child runs of responder: {len(grandchildren)}")
                    for gc in grandchildren:
                        print(f"      - {gc.name}")
                        if "ghl" in gc.name.lower() or "send" in gc.name.lower():
                            ghl_calls.append(gc)
            
            # Also check for GHL calls at any level
            if "ghl" in child.name.lower() or "send_message" in child.name.lower():
                ghl_calls.append(child)
                print(f"\n    📤 GHL API CALL: {child.name}")
        
        # Print summary
        print(f"\n{'='*30} SUMMARY {'='*30}")
        print(f"✅ Responder found: {responder_found}")
        print(f"{'✅' if ghl_calls else '❌'} GHL API calls: {len(ghl_calls)}")
        
        if responder_found and not ghl_calls:
            print("\n⚠️  WARNING: Responder executed but no GHL API calls detected!")
            print("This confirms the responder is not sending messages to GHL.")
        
        # Look for specific nodes
        print(f"\n📋 Workflow Execution Order:")
        sorted_runs = sorted(child_runs, key=lambda x: x.start_time)
        for i, run in enumerate(sorted_runs[:10]):  # Show first 10
            print(f"  {i+1}. {run.name} ({run.run_type}) - {run.status}")
            
    except Exception as e:
        print(f"Error analyzing trace: {e}")

def main():
    """Main function"""
    print("Analyzing LangSmith traces with SDK...")
    print(f"Client initialized: {client.api_url}")
    
    for trace_id in TRACE_IDS:
        analyze_trace(trace_id)
    
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    
    # Also check for most recent traces
    print("\n📊 Recent Traces (last 5):")
    recent_runs = list(client.list_runs(
        project_name="ghl-langgraph-agent",
        limit=5,
        is_root=True
    ))
    
    for run in recent_runs:
        print(f"\n  - {run.id} | {run.name} | {run.start_time}")
        # Quick check for responder
        children = list(client.list_runs(parent_run_id=run.id))
        responder = any("responder" in c.name.lower() for c in children)
        print(f"    Has responder: {'✅' if responder else '❌'}")

if __name__ == "__main__":
    main()
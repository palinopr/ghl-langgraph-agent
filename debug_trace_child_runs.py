#!/usr/bin/env python3
"""
Debug child runs for trace
"""
from langsmith import Client
import json

client = Client(api_key="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")
trace_id = "1f067526-df67-678c-8476-422b77f6af9b"

print(f"🔍 Analyzing Child Runs for Trace: {trace_id}")
print("=" * 80)

# Get all child runs
child_runs = list(client.list_runs(
    project_name="ghl-langgraph-agent",
    filter=f'eq(parent_run_id, "{trace_id}")',
    limit=20
))

print(f"\nFound {len(child_runs)} child runs:\n")

for i, run in enumerate(child_runs):
    print(f"{i+1}. {run.name}")
    print(f"   Type: {run.run_type}")
    print(f"   Status: {run.status}")
    
    # Check for specific patterns
    if "supervisor" in run.name.lower():
        print("   🎯 SUPERVISOR NODE")
        if run.outputs:
            print(f"   Output: {json.dumps(run.outputs, indent=2)[:200]}...")
            
    if "receptionist" in run.name.lower():
        print("   👋 RECEPTIONIST NODE")
        
    if run.inputs and "thread_id" in str(run.inputs):
        print("   ✅ Has thread_id in inputs")
    
    print()

# Check the main run's configuration
print("\n" + "="*80)
print("🔧 Checking Main Run Configuration:")

main_run = client.read_run(trace_id)
if hasattr(main_run, 'extra') and main_run.extra:
    config = main_run.extra.get('runtime', {}).get('configurable', {})
    if config:
        print(f"Configurable: {json.dumps(config, indent=2)}")
        if 'thread_id' in config:
            print(f"✅ Thread ID found in config: {config['thread_id']}")
        else:
            print("❌ No thread_id in configurable")
    else:
        print("❌ No configurable section found")
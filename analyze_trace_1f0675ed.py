#!/usr/bin/env python3
"""
Analyze trace 1f0675ed-5921-63c6-9c68-a9dab34dd57c
"""
from langsmith import Client
import json

client = Client(api_key="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")
trace_id = "1f0675ed-5921-63c6-9c68-a9dab34dd57c"

print(f"🔍 Analyzing Trace: {trace_id}")
print("=" * 80)

try:
    run = client.read_run(trace_id)
    
    print(f"\n📊 Trace Details:")
    print(f"Name: {run.name}")
    print(f"Status: {run.status}")
    print(f"Start Time: {run.start_time}")
    
    # Check inputs for thread_id
    if run.inputs:
        print(f"\n📥 Inputs:")
        input_str = json.dumps(run.inputs, indent=2)
        print(input_str[:500] + "...")
        
        if "thread_id" in input_str:
            print("✅ Thread ID found in inputs")
        else:
            print("❌ No thread_id in inputs")
    
    # Check outputs for message duplication
    if run.outputs and isinstance(run.outputs, dict):
        messages = run.outputs.get("messages", [])
        print(f"\n📤 Output Messages: {len(messages)}")
        
        # Count duplicates
        content_counts = {}
        for msg in messages:
            content = msg.get("content", "") if isinstance(msg, dict) else ""
            if content:
                content_counts[content] = content_counts.get(content, 0) + 1
        
        duplicates = [(content, count) for content, count in content_counts.items() if count > 1]
        if duplicates:
            print(f"❌ Found duplicates:")
            for content, count in duplicates[:3]:
                print(f"   '{content[:30]}...' repeated {count} times")
    
    # Check child runs
    child_runs = list(client.list_runs(
        project_name="ghl-langgraph-agent",
        filter=f'eq(parent_run_id, "{trace_id}")',
        limit=20
    ))
    
    print(f"\n🔍 Child Runs ({len(child_runs)}):")
    
    redis_found = False
    checkpoint_found = False
    supervisor_error = None
    workflow_indicators = []
    
    for child in child_runs:
        print(f"  - {child.name}")
        
        # Check for Redis/checkpoint operations
        if "redis" in child.name.lower():
            redis_found = True
            print("    ✅ Redis operation detected!")
        if "checkpoint" in child.name.lower():
            checkpoint_found = True
            print("    ✅ Checkpoint operation detected!")
            
        # Check supervisor
        if "supervisor" in child.name.lower() and child.outputs:
            if "error" in str(child.outputs).lower():
                supervisor_error = str(child.outputs)[:200]
        
        # Look for workflow indicators
        if child.run_type == "chain":
            workflow_indicators.append(child.name)
    
    # Determine which workflow is running
    print(f"\n🔧 Workflow Analysis:")
    print(f"Redis Operations: {'✅ Yes' if redis_found else '❌ No'}")
    print(f"Checkpoint Operations: {'✅ Yes' if checkpoint_found else '❌ No'}")
    
    if supervisor_error:
        print(f"\n❌ Supervisor Error Detected:")
        print(f"   {supervisor_error}")
    
    # Check deployment metadata
    if hasattr(run, 'extra') and run.extra:
        metadata = run.extra.get('metadata', {})
        if metadata.get('assistant_id'):
            print(f"\n📦 Deployment Info:")
            print(f"Assistant ID: {metadata.get('assistant_id')}")
            print(f"Graph ID: {metadata.get('graph_id', 'N/A')}")
    
    print(f"\n🎯 VERDICT:")
    if redis_found or checkpoint_found:
        print("✅ Using FIXED workflow with Redis!")
    else:
        print("❌ Still using OLD workflow without Redis")
        print("\n⚠️  Possible reasons:")
        print("1. Deployment hasn't restarted yet")
        print("2. Redis URL not configured in deployment")
        print("3. Workflow file not found at expected path")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
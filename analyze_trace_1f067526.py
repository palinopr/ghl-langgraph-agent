#!/usr/bin/env python3
"""
Analyze specific trace for Redis persistence
"""
from langsmith import Client
import json
from datetime import datetime

# Initialize client
client = Client(api_key="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")

# Trace ID
trace_id = "1f067526-df67-678c-8476-422b77f6af9b"

print(f"🔍 Analyzing Trace: {trace_id}")
print("=" * 80)

try:
    # Get the run
    run = client.read_run(trace_id)
    
    print(f"\n📊 Trace Details:")
    print(f"Name: {run.name}")
    print(f"Status: {run.status}")
    print(f"Start Time: {run.start_time}")
    print(f"End Time: {run.end_time}")
    
    # Check inputs
    if run.inputs:
        print(f"\n📥 Inputs:")
        print(json.dumps(run.inputs, indent=2)[:500] + "...")
        
        # Check for thread_id
        if "thread_id" in str(run.inputs):
            print("\n✅ Thread ID found in inputs")
        else:
            print("\n⚠️ No thread_id in inputs")
    
    # Check outputs
    if run.outputs:
        print(f"\n📤 Outputs:")
        print(json.dumps(run.outputs, indent=2)[:500] + "...")
        
        # Check message count
        if "messages" in run.outputs:
            msg_count = len(run.outputs.get("messages", []))
            print(f"\n📨 Message Count: {msg_count}")
            if msg_count > 2:
                print("✅ Multiple messages found - context might be maintained")
            else:
                print("⚠️ Only few messages - might be first interaction")
    
    # Check for checkpoint-related runs
    print(f"\n🔍 Checking child runs for checkpoint operations...")
    child_runs = list(client.list_runs(
        project_name="ghl-langgraph-agent",
        filter=f'eq(parent_run_id, "{trace_id}")',
        limit=100
    ))
    
    checkpoint_found = False
    checkpoint_loaded = False
    redis_operations = []
    
    for child in child_runs:
        # Check for checkpoint operations
        if "checkpoint" in child.name.lower():
            checkpoint_found = True
            print(f"\n📌 Checkpoint Operation: {child.name}")
            print(f"   Status: {child.status}")
            
            if "load" in child.name.lower() or "get" in child.name.lower():
                checkpoint_loaded = True
                
        # Check for Redis operations
        if "redis" in child.name.lower():
            redis_operations.append(child.name)
    
    # Summary
    print(f"\n📊 Checkpoint Analysis:")
    print(f"Checkpoint Operations Found: {'✅ Yes' if checkpoint_found else '❌ No'}")
    print(f"Checkpoint Loaded: {'✅ Yes' if checkpoint_loaded else '❌ No'}")
    
    if redis_operations:
        print(f"\n🔴 Redis Operations Found:")
        for op in redis_operations:
            print(f"  - {op}")
    else:
        print(f"\n⚠️ No explicit Redis operations found")
        print("   (Redis might be used internally without explicit traces)")
    
    # Check metadata
    if hasattr(run, 'extra') and run.extra:
        metadata = run.extra.get('metadata', {})
        if metadata:
            print(f"\n📋 Metadata:")
            print(json.dumps(metadata, indent=2)[:300] + "...")
            
            # Check for checkpoint_ns, checkpoint_id
            if 'checkpoint_ns' in str(metadata) or 'checkpoint_id' in str(metadata):
                print("\n✅ Checkpoint metadata found")
    
    # Final verdict
    print(f"\n{'='*80}")
    print("🎯 VERDICT:")
    
    if checkpoint_loaded:
        print("✅ Checkpoint persistence appears to be working!")
        print("   - Previous conversation state was loaded")
    else:
        print("⚠️ No clear evidence of checkpoint loading")
        print("   - This might be the first message in the conversation")
        print("   - Or Redis might not be configured in production yet")
    
    print(f"\n📊 View full trace at:")
    print(f"https://smith.langchain.com/o/6bd7e183-2238-416a-974c-51b9f53aafdd/projects/p/ghl-langgraph-agent/runs/{trace_id}")
    
except Exception as e:
    print(f"❌ Error analyzing trace: {e}")
    import traceback
    traceback.print_exc()
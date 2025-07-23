#!/usr/bin/env python3
"""
Analyze trace 1f067640-5783-6164-8703-064875bd88a9
Check if fixes are applied
"""
from langsmith import Client
import json

client = Client(api_key="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")
trace_id = "1f067640-5783-6164-8703-064875bd88a9"

print(f"🔍 Analyzing Trace: {trace_id}")
print("=" * 80)

try:
    run = client.read_run(trace_id)
    
    print(f"\n📊 Trace Details:")
    print(f"Name: {run.name}")
    print(f"Status: {run.status}")
    print(f"Start Time: {run.start_time}")
    
    # Check for thread_id in inputs
    if run.inputs:
        input_str = json.dumps(run.inputs, indent=2)
        if "thread_id" in input_str:
            print("✅ Thread ID found in inputs")
            # Extract thread_id
            if isinstance(run.inputs, dict):
                thread_id = run.inputs.get("thread_id", "not found")
                print(f"   Thread ID: {thread_id}")
        else:
            print("❌ No thread_id in inputs")
    
    # Check outputs
    if run.outputs and isinstance(run.outputs, dict):
        messages = run.outputs.get("messages", [])
        print(f"\n📤 Output Messages: {len(messages)}")
        
        # Count unique messages
        unique_contents = set()
        for msg in messages:
            content = msg.get("content", "") if isinstance(msg, dict) else ""
            if content:
                unique_contents.add(content)
        
        print(f"Unique messages: {len(unique_contents)}")
        if len(unique_contents) < len(messages) / 2:
            print("❌ High message duplication detected")
        else:
            print("✅ Normal message variation")
    
    # Check child runs for our fixes
    child_runs = list(client.list_runs(
        project_name="ghl-langgraph-agent",
        filter=f'eq(parent_run_id, "{trace_id}")',
        limit=20
    ))
    
    print(f"\n🔍 Checking Child Runs for Fixes:")
    
    supervisor_fixed = True
    intelligence_fixed = True
    redis_found = False
    checkpoint_ops = []
    
    for child in child_runs:
        # Check supervisor
        if child.name == "supervisor":
            if hasattr(child, 'error') and child.error:
                if "messages_modifier" in str(child.error):
                    supervisor_fixed = False
                    print("❌ Supervisor still has messages_modifier error")
            else:
                print("✅ Supervisor ran without error")
                
        # Check intelligence
        if child.name == "intelligence":
            if hasattr(child, 'error') and child.error:
                if "TracedOperation" in str(child.error):
                    intelligence_fixed = False
                    print("❌ Intelligence still has TracedOperation error")
            else:
                print("✅ Intelligence ran without error")
                
        # Look for Redis/checkpoint operations
        if "checkpoint" in child.name.lower():
            checkpoint_ops.append(child.name)
        if "redis" in child.name.lower():
            redis_found = True
    
    print(f"\n🔧 Fix Status:")
    print(f"Supervisor Fixed: {'✅ Yes' if supervisor_fixed else '❌ No'}")
    print(f"Intelligence Fixed: {'✅ Yes' if intelligence_fixed else '❌ No'}")
    print(f"Redis Operations: {'✅ Found' if redis_found else '❌ Not found'}")
    print(f"Checkpoint Operations: {len(checkpoint_ops)}")
    
    # Check configuration
    if hasattr(run, 'extra') and run.extra:
        metadata = run.extra.get('metadata', {})
        runtime = run.extra.get('runtime', {})
        
        print(f"\n📋 Configuration:")
        if metadata:
            print(f"Graph ID: {metadata.get('graph_id', 'N/A')}")
            print(f"Assistant ID: {metadata.get('assistant_id', 'N/A')}")
            
        if runtime and 'configurable' in runtime:
            config = runtime['configurable']
            if 'thread_id' in config:
                print(f"✅ Thread ID in config: {config['thread_id']}")
            else:
                print("❌ No thread_id in runtime config")
    
    print(f"\n🎯 VERDICT:")
    if supervisor_fixed and intelligence_fixed:
        print("✅ Code fixes are applied!")
        if not redis_found:
            print("⚠️  But Redis still not detected - might be import issue")
    else:
        print("❌ Fixes not yet applied - deployment might not have updated")
        print("   Wait a few more minutes for auto-update")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
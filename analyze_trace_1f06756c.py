#!/usr/bin/env python3
"""
Analyze trace 1f06756c-e331-6458-bb28-7a955752db21
"""
from langsmith import Client
import json
from datetime import datetime

# Initialize client
client = Client(api_key="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")

# Trace ID
trace_id = "1f06756c-e331-6458-bb28-7a955752db21"

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
    if hasattr(run, 'error') and run.error:
        print(f"❌ Error: {run.error}")
    
    # Check inputs
    if run.inputs:
        print(f"\n📥 Inputs:")
        print(json.dumps(run.inputs, indent=2)[:1000] + "...")
        
        # Check for thread_id in inputs
        if "thread_id" in str(run.inputs):
            print("\n✅ Thread ID found in inputs")
        else:
            print("\n⚠️ No thread_id in inputs")
    
    # Check outputs
    if run.outputs:
        print(f"\n📤 Outputs:")
        print(json.dumps(run.outputs, indent=2)[:1000] + "...")
        
        # Check message count
        if isinstance(run.outputs, dict) and "messages" in run.outputs:
            msg_count = len(run.outputs.get("messages", []))
            print(f"\n📨 Message Count: {msg_count}")
            
            # Check for duplicates
            messages = run.outputs.get("messages", [])
            unique_contents = set()
            duplicates = []
            
            for msg in messages:
                content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
                if content in unique_contents and content:
                    duplicates.append(content)
                unique_contents.add(content)
            
            if duplicates:
                print(f"⚠️ Found {len(duplicates)} duplicate messages")
                print(f"   Example: '{duplicates[0][:50]}...'")
    
    # Check metadata for configuration
    if hasattr(run, 'extra') and run.extra:
        metadata = run.extra.get('metadata', {})
        runtime = run.extra.get('runtime', {})
        
        print(f"\n🔧 Configuration:")
        if runtime:
            configurable = runtime.get('configurable', {})
            if configurable:
                print(f"Configurable: {json.dumps(configurable, indent=2)}")
                if 'thread_id' in configurable:
                    print(f"✅ Thread ID in config: {configurable['thread_id']}")
                else:
                    print("❌ No thread_id in configurable")
    
    # Check for child runs
    print(f"\n🔍 Checking child runs...")
    child_runs = list(client.list_runs(
        project_name="ghl-langgraph-agent",
        filter=f'eq(parent_run_id, "{trace_id}")',
        limit=50
    ))
    
    print(f"Found {len(child_runs)} child runs:")
    
    # Analyze child runs
    checkpoint_operations = []
    redis_operations = []
    errors = []
    supervisor_runs = []
    
    for child in child_runs:
        # Print each child run
        print(f"\n  - {child.name} ({child.run_type})")
        if child.status != "success":
            print(f"    Status: {child.status}")
        
        # Check for errors
        if hasattr(child, 'error') and child.error:
            errors.append(f"{child.name}: {child.error}")
        
        # Look for specific patterns
        if "checkpoint" in child.name.lower():
            checkpoint_operations.append(child.name)
        if "redis" in child.name.lower():
            redis_operations.append(child.name)
        if "supervisor" in child.name.lower():
            supervisor_runs.append(child)
            # Check supervisor output
            if child.outputs:
                print(f"    Supervisor output: {json.dumps(child.outputs, indent=2)[:200]}...")
    
    # Summary
    print(f"\n📊 Analysis Summary:")
    print(f"{'='*80}")
    
    if checkpoint_operations:
        print(f"✅ Checkpoint operations found: {len(checkpoint_operations)}")
        for op in checkpoint_operations:
            print(f"   - {op}")
    else:
        print("❌ No checkpoint operations found")
    
    if redis_operations:
        print(f"\n✅ Redis operations found: {len(redis_operations)}")
        for op in redis_operations:
            print(f"   - {op}")
    else:
        print("\n⚠️ No explicit Redis operations found")
    
    if errors:
        print(f"\n❌ Errors found ({len(errors)}):")
        for err in errors[:5]:  # Show first 5 errors
            print(f"   - {err}")
    
    # Check if we're using the fixed workflow
    if run.name == "agent":
        print(f"\n🔧 Workflow Version Check:")
        # Look for signs of the fixed workflow
        has_redis = any("redis" in str(child.name).lower() for child in child_runs)
        has_fixed_supervisor = any("supervisor" in child.name.lower() and child.status == "success" for child in child_runs)
        
        if has_redis:
            print("✅ Redis checkpointer detected")
        else:
            print("❌ No Redis checkpointer detected - might be using old workflow")
        
        if has_fixed_supervisor:
            print("✅ Supervisor ran successfully")
        else:
            print("❌ Supervisor issues detected")
    
    print(f"\n📊 View full trace at:")
    print(f"https://smith.langchain.com/o/6bd7e183-2238-416a-974c-51b9f53aafdd/projects/p/ghl-langgraph-agent/runs/{trace_id}")
    
except Exception as e:
    print(f"❌ Error analyzing trace: {e}")
    import traceback
    traceback.print_exc()
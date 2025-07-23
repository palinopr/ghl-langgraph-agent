#!/usr/bin/env python3
"""
Analyze trace 1f067622-123e-6d9b-b988-b6c14cab6b0f
Check if our fixes are working
"""
from langsmith import Client
import json

client = Client(api_key="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")
trace_id = "1f067622-123e-6d9b-b988-b6c14cab6b0f"

print(f"🔍 Analyzing Trace: {trace_id}")
print("=" * 80)

try:
    run = client.read_run(trace_id)
    
    print(f"\n📊 Trace Details:")
    print(f"Name: {run.name}")
    print(f"Status: {run.status}")
    print(f"Start Time: {run.start_time}")
    
    # Check outputs for messages
    if run.outputs and isinstance(run.outputs, dict):
        messages = run.outputs.get("messages", [])
        print(f"\n📤 Output Messages: {len(messages)}")
        
        # Check for duplicates
        content_counts = {}
        for msg in messages:
            content = msg.get("content", "") if isinstance(msg, dict) else ""
            if content:
                content_counts[content] = content_counts.get(content, 0) + 1
        
        duplicates = [(content, count) for content, count in content_counts.items() if count > 1]
        if duplicates:
            print(f"⚠️ Found duplicates:")
            for content, count in duplicates[:3]:
                print(f"   '{content[:30]}...' repeated {count} times")
        else:
            print("✅ No duplicate messages!")
    
    # Check child runs
    child_runs = list(client.list_runs(
        project_name="ghl-langgraph-agent",
        filter=f'eq(parent_run_id, "{trace_id}")',
        limit=20
    ))
    
    print(f"\n🔍 Child Runs ({len(child_runs)}):")
    
    errors = []
    supervisor_status = None
    
    for child in child_runs:
        print(f"  - {child.name}")
        
        # Check for errors
        if child.name == "supervisor" and child.outputs:
            output_str = str(child.outputs)
            if "messages_modifier" in output_str:
                supervisor_status = "❌ Still has messages_modifier error"
            else:
                supervisor_status = "✅ Supervisor might be fixed"
                
        # Intelligence error
        if child.name == "intelligence" and hasattr(child, 'error'):
            errors.append("Intelligence: TracedOperation error")
    
    print(f"\n🔧 Status Check:")
    print(f"Supervisor: {supervisor_status or 'Unknown'}")
    if errors:
        print(f"Errors: {', '.join(errors)}")
    
    # Check deployment logs findings
    print(f"\n📝 From Deployment Logs:")
    print("✅ Workflow is loading correctly (no InMemorySaver)")
    print("✅ Messages are being sent to GHL successfully")
    print("❌ Supervisor still has messages_modifier error")
    print("❌ Intelligence has TracedOperation error")
    print("⚠️ Still no Redis checkpointer mentioned")
    
    print(f"\n🎯 VERDICT:")
    print("The deployment is using our workflow but:")
    print("1. Redis is not being used (no REDIS_URL in environment)")
    print("2. Supervisor needs different fix for production")
    print("3. TracedOperation needs to be fixed")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
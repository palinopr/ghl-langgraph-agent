#!/usr/bin/env python3
"""Analyze specific trace to verify our fixes are working"""
import os
os.environ["LANGCHAIN_API_KEY"] = "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"

from langsmith import Client
import json
from datetime import datetime

# Initialize client
client = Client()
trace_id = "1f0676c2-3fcd-6754-a8ab-e2e3f352e0c1"

print(f"🔍 Analyzing Trace: {trace_id}")
print("=" * 80)

try:
    # Get the main trace
    run = client.read_run(trace_id)
    
    print(f"\n📊 TRACE OVERVIEW:")
    print(f"Status: {run.status}")
    print(f"Start: {run.start_time}")
    print(f"End: {run.end_time}")
    print(f"Duration: {(run.end_time - run.start_time).total_seconds():.2f}s")
    
    # Check inputs
    print(f"\n📥 INPUTS:")
    if run.inputs:
        print(f"Keys: {list(run.inputs.keys())}")
        if 'messages' in run.inputs:
            print(f"Input messages count: {len(run.inputs['messages'])}")
        if 'thread_id' in run.inputs:
            print(f"Thread ID: {run.inputs['thread_id']}")
        if 'contact_id' in run.inputs:
            print(f"Contact ID: {run.inputs['contact_id']}")
    
    # Check outputs
    print(f"\n📤 OUTPUTS:")
    if run.outputs:
        if 'messages' in run.outputs:
            print(f"Output messages count: {len(run.outputs['messages'])}")
            # Check for duplicates
            messages = run.outputs['messages']
            unique_contents = set()
            duplicates = 0
            for msg in messages:
                content = msg.get('content', '') if isinstance(msg, dict) else str(msg)
                if content in unique_contents:
                    duplicates += 1
                else:
                    unique_contents.add(content)
            print(f"Unique messages: {len(unique_contents)}")
            print(f"Duplicates: {duplicates}")
    
    # Check for errors
    if run.error:
        print(f"\n❌ ERROR: {run.error}")
    
    # Get all child runs
    child_runs = list(client.list_runs(
        project_id=run.session_id,
        filter=f'eq(parent_run_id, "{trace_id}")'
    ))
    
    print(f"\n🔄 CHILD RUNS: {len(child_runs)}")
    
    # Track execution order and check for our new node names
    node_executions = []
    for child in child_runs:
        if child.name:
            node_executions.append({
                'name': child.name,
                'start': child.start_time,
                'status': child.status,
                'error': child.error
            })
    
    # Sort by start time
    node_executions.sort(key=lambda x: x['start'])
    
    print("\n📋 EXECUTION ORDER:")
    for i, node in enumerate(node_executions, 1):
        status_icon = "✅" if node['status'] == "success" else "❌"
        print(f"{i}. {status_icon} {node['name']}")
        if node['error']:
            print(f"   Error: {node['error']}")
    
    # Check for old vs new naming
    print("\n🏷️  NAMING CONVENTION CHECK:")
    old_names = ['thread_id_mapper_enhanced_node', 'receptionist_simple_node', 
                 'maria_memory_aware_node', 'carlos_node_v2_fixed', 
                 'sofia_node_v2_fixed', 'responder_streaming_node']
    new_names = ['thread_id_mapper_node', 'receptionist_node', 
                 'maria_node', 'carlos_node', 'sofia_node', 'responder_node']
    
    found_old = [name for name in old_names if any(name in str(child.name) for child in child_runs)]
    found_new = [name for name in new_names if any(name in str(child.name) for child in child_runs)]
    
    if found_old:
        print(f"⚠️  Found OLD naming: {found_old}")
    if found_new:
        print(f"✅ Found NEW naming: {found_new}")
    
    # Check thread consistency
    print("\n🧵 THREAD CONSISTENCY:")
    thread_ids = set()
    for child in child_runs:
        if child.inputs and 'thread_id' in child.inputs:
            thread_ids.add(child.inputs['thread_id'])
    
    if len(thread_ids) == 0:
        print("⚠️  No thread_id found in child runs")
    elif len(thread_ids) == 1:
        print(f"✅ Consistent thread_id: {thread_ids.pop()}")
    else:
        print(f"❌ Multiple thread_ids found: {thread_ids}")
    
    # Check for specific issues
    print("\n🔍 SPECIFIC CHECKS:")
    
    # Check if receptionist loaded messages
    receptionist_runs = [r for r in child_runs if 'receptionist' in r.name.lower()]
    if receptionist_runs:
        r = receptionist_runs[0]
        if r.outputs and 'messages' in r.outputs:
            print(f"✅ Receptionist loaded {len(r.outputs['messages'])} messages")
        else:
            print("⚠️  Receptionist didn't output messages")
    
    # Check for import errors
    import_errors = [r for r in child_runs if r.error and ('import' in str(r.error).lower() or 'module' in str(r.error).lower())]
    if import_errors:
        print(f"❌ Found {len(import_errors)} import errors:")
        for r in import_errors[:3]:  # Show first 3
            print(f"   - {r.name}: {r.error}")
    else:
        print("✅ No import errors found")

except Exception as e:
    print(f"\n❌ Error analyzing trace: {e}")
    import traceback
    traceback.print_exc()
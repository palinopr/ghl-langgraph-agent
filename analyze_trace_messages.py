#!/usr/bin/env python3
"""Analyze message duplication in the trace"""
import os
os.environ["LANGCHAIN_API_KEY"] = "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"

from langsmith import Client
import json

client = Client()
trace_id = "1f0676c2-3fcd-6754-a8ab-e2e3f352e0c1"

print(f"🔍 Analyzing Message Flow in Trace: {trace_id}")
print("=" * 80)

try:
    run = client.read_run(trace_id)
    
    # Get all child runs
    child_runs = list(client.list_runs(
        project_id=run.session_id,
        filter=f'eq(parent_run_id, "{trace_id}")'
    ))
    
    # Sort by execution order
    child_runs.sort(key=lambda x: x.start_time)
    
    print("\n📨 MESSAGE FLOW THROUGH NODES:\n")
    
    for child in child_runs:
        print(f"\n{'='*60}")
        print(f"NODE: {child.name}")
        print(f"Status: {child.status}")
        
        # Check input messages
        if child.inputs and 'messages' in child.inputs:
            input_msgs = child.inputs['messages']
            print(f"Input messages: {len(input_msgs)}")
            if len(input_msgs) <= 5:
                for i, msg in enumerate(input_msgs):
                    content = msg.get('content', '') if isinstance(msg, dict) else str(msg)
                    print(f"  [{i}] {content[:100]}...")
        
        # Check output messages
        if child.outputs and 'messages' in child.outputs:
            output_msgs = child.outputs['messages']
            print(f"Output messages: {len(output_msgs)}")
            if len(output_msgs) <= 5:
                for i, msg in enumerate(output_msgs):
                    content = msg.get('content', '') if isinstance(msg, dict) else str(msg)
                    print(f"  [{i}] {content[:100]}...")
            
            # Check if messages increased
            input_count = len(child.inputs.get('messages', []))
            output_count = len(output_msgs)
            if output_count > input_count:
                print(f"⚠️  Messages INCREASED by {output_count - input_count}")
    
    # Final analysis
    print(f"\n\n{'='*60}")
    print("📊 FINAL ANALYSIS:")
    
    if run.outputs and 'messages' in run.outputs:
        messages = run.outputs['messages']
        
        # Count unique messages
        message_counts = {}
        for msg in messages:
            content = msg.get('content', '') if isinstance(msg, dict) else str(msg)
            if content:
                message_counts[content] = message_counts.get(content, 0) + 1
        
        print(f"\nTotal messages: {len(messages)}")
        print(f"Unique messages: {len(message_counts)}")
        
        print("\nMessage breakdown:")
        for content, count in message_counts.items():
            if count > 1:
                print(f"  - Duplicated {count} times: {content[:60]}...")
            else:
                print(f"  - Single: {content[:60]}...")
    
    # Check which node is creating duplicates
    print("\n🔍 DUPLICATION SOURCE:")
    for i, child in enumerate(child_runs):
        if i == 0:
            continue
        
        prev_count = len(child_runs[i-1].outputs.get('messages', []))
        curr_count = len(child.outputs.get('messages', []))
        
        if curr_count > prev_count * 1.5:  # Messages increased by 50% or more
            print(f"⚠️  {child.name} significantly increased messages: {prev_count} → {curr_count}")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
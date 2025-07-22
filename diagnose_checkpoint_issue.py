#!/usr/bin/env python3
"""
Diagnose why checkpoints aren't loading in production
"""
import os
from langsmith import Client
from datetime import datetime, timedelta
import json

os.environ["LANGCHAIN_API_KEY"] = "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"

def diagnose_checkpoint_loading():
    """Deep dive into checkpoint loading issues"""
    
    client = Client()
    
    print("🔍 Diagnosing Checkpoint Loading Issues")
    print("=" * 80)
    
    # Get recent runs with thread_ids
    since = datetime.now() - timedelta(hours=2)
    runs = list(client.list_runs(
        project_name="ghl-langgraph-agent",
        start_time=since,
        limit=10,
        execution_order=1
    ))
    
    print(f"Analyzing {len(runs)} recent runs...\n")
    
    # Focus on runs with thread_id
    runs_with_thread_id = []
    
    for run in runs:
        if run.run_type != "chain":
            continue
            
        outputs = run.outputs or {}
        inputs = run.inputs or {}
        
        thread_id = outputs.get("thread_id") or inputs.get("thread_id")
        
        if thread_id:
            runs_with_thread_id.append({
                "run_id": run.id,
                "thread_id": thread_id,
                "messages": len(outputs.get("messages", [])),
                "checkpoint_loaded": outputs.get("checkpoint_loaded", False),
                "has_checkpoint": outputs.get("has_checkpoint", False),
                "time": run.start_time
            })
    
    print(f"Found {len(runs_with_thread_id)} runs with thread_id\n")
    
    # Analyze checkpoint loading patterns
    for run_data in runs_with_thread_id[:5]:  # First 5
        print(f"Run: {run_data['run_id']}")
        print(f"  Thread ID: {run_data['thread_id']}")
        print(f"  Messages: {run_data['messages']}")
        print(f"  Checkpoint Loaded: {run_data['checkpoint_loaded']}")
        print(f"  Has Checkpoint: {run_data['has_checkpoint']}")
        
        # Get child runs to see receptionist details
        try:
            child_runs = list(client.list_runs(
                parent_run_id=str(run_data['run_id'])
            ))
            
            for child in child_runs:
                if "receptionist" in child.name.lower():
                    print(f"  Receptionist node:")
                    if child.outputs:
                        print(f"    - checkpoint_loaded: {child.outputs.get('checkpoint_loaded', 'N/A')}")
                        print(f"    - has_checkpoint: {child.outputs.get('has_checkpoint', 'N/A')}")
                        print(f"    - messages from checkpoint: {child.outputs.get('messages_from_checkpoint', 'N/A')}")
                        print(f"    - messages from GHL: {child.outputs.get('messages_from_ghl', 'N/A')}")
                        
        except Exception as e:
            print(f"  Error getting child runs: {e}")
        
        print()
    
    # Check for patterns
    print("\n" + "=" * 80)
    print("🎯 DIAGNOSIS:")
    
    checkpoint_loaded_count = sum(1 for r in runs_with_thread_id if r["checkpoint_loaded"])
    
    if checkpoint_loaded_count == 0:
        print("\n❌ CRITICAL: No checkpoints are being loaded!")
        print("\nPossible causes:")
        print("1. MemorySaver checkpointer doesn't persist between requests")
        print("2. Receptionist node not checking for checkpoints")
        print("3. Thread ID format mismatch")
        print("4. Checkpoint storage not configured properly")
        
        print("\n🔧 SOLUTION:")
        print("1. Use persistent checkpointer (SQLite/Redis/Postgres)")
        print("2. Ensure receptionist_checkpoint_aware is used")
        print("3. Verify thread_id consistency")
    else:
        print(f"\n✅ Checkpoints loaded in {checkpoint_loaded_count}/{len(runs_with_thread_id)} runs")
    
    # Check for duplicate messages (sign of no checkpoint)
    print("\n📊 Message Duplication Analysis:")
    duplicates_found = 0
    
    for run_data in runs_with_thread_id:
        if run_data["messages"] > 10:  # High message count
            # Get the actual run to check messages
            try:
                run = client.read_run(run_data["run_id"])
                messages = run.outputs.get("messages", [])
                
                # Check if all messages are the same
                if messages:
                    unique_contents = set()
                    for msg in messages:
                        if isinstance(msg, dict):
                            unique_contents.add(msg.get("content", ""))
                    
                    if len(unique_contents) == 1:
                        duplicates_found += 1
                        print(f"  ⚠️ Run {run_data['run_id']}: All {len(messages)} messages identical!")
                        
            except:
                pass
    
    if duplicates_found > 0:
        print(f"\n❌ Found {duplicates_found} runs with duplicate messages")
        print("This indicates messages are being added without loading checkpoint!")

if __name__ == "__main__":
    diagnose_checkpoint_loading()
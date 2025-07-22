#!/usr/bin/env python3
"""
Check recent traces to see context handling patterns
"""
import os
from langsmith import Client
from datetime import datetime, timedelta
from collections import defaultdict

os.environ["LANGCHAIN_API_KEY"] = "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"

def check_recent_traces(hours=1):
    """Check recent traces for context patterns"""
    
    client = Client()
    
    print(f"🔍 Checking traces from last {hours} hour(s)...")
    print("=" * 80)
    
    # Get recent runs
    since = datetime.now() - timedelta(hours=hours)
    # Try different project names
    project_names = ["ghl-langgraph-agent", "production-test", "default"]
    runs = []
    
    for project in project_names:
        try:
            project_runs = list(client.list_runs(
                project_name=project,
                start_time=since,
                limit=20,
                execution_order=1  # Most recent first
            ))
            runs.extend(project_runs)
            if project_runs:
                print(f"Found {len(project_runs)} runs in project: {project}")
        except:
            continue
    
    print(f"Found {len(runs)} recent runs\n")
    
    # Analyze patterns
    patterns = {
        "has_thread_id": 0,
        "no_thread_id": 0,
        "checkpoint_loaded": 0,
        "no_checkpoint": 0,
        "has_history": 0,
        "no_history": 0,
        "message_counts": []
    }
    
    # Group by contact/conversation
    conversations = defaultdict(list)
    
    for run in runs:
        if run.run_type != "chain":
            continue
            
        outputs = run.outputs or {}
        inputs = run.inputs or {}
        
        # Get identifiers
        thread_id = outputs.get("thread_id") or inputs.get("thread_id")
        contact_id = outputs.get("contact_id") or inputs.get("contact_id")
        messages = outputs.get("messages", [])
        checkpoint_loaded = outputs.get("checkpoint_loaded", False)
        
        # Track patterns
        if thread_id:
            patterns["has_thread_id"] += 1
        else:
            patterns["no_thread_id"] += 1
            
        if checkpoint_loaded:
            patterns["checkpoint_loaded"] += 1
        else:
            patterns["no_checkpoint"] += 1
            
        if len(messages) > 1:
            patterns["has_history"] += 1
        else:
            patterns["no_history"] += 1
            
        patterns["message_counts"].append(len(messages))
        
        # Group by conversation
        if contact_id:
            conversations[contact_id].append({
                "run_id": run.id,
                "time": run.start_time,
                "thread_id": thread_id,
                "message_count": len(messages),
                "checkpoint_loaded": checkpoint_loaded,
                "lead_score": outputs.get("lead_score"),
                "current_agent": outputs.get("current_agent")
            })
        
        # Show individual run
        print(f"Run: {run.id}")
        print(f"  Time: {run.start_time}")
        print(f"  Thread ID: {thread_id or 'MISSING'}")
        print(f"  Messages: {len(messages)}")
        print(f"  Checkpoint: {'Loaded' if checkpoint_loaded else 'Not loaded'}")
        print(f"  Status: {run.status}")
        
        # Show message preview if duplicated
        if messages and len(set(msg.get("content", "") for msg in messages if isinstance(msg, dict))) == 1:
            print(f"  ⚠️  All messages are identical: '{messages[0].get('content', '')[:20]}...'")
        
        print()
    
    # Show patterns
    print("\n" + "=" * 80)
    print("📊 PATTERN ANALYSIS:")
    print(f"  Thread IDs: {patterns['has_thread_id']} present, {patterns['no_thread_id']} missing")
    print(f"  Checkpoints: {patterns['checkpoint_loaded']} loaded, {patterns['no_checkpoint']} not loaded")
    print(f"  History: {patterns['has_history']} with history, {patterns['no_history']} without")
    
    if patterns["message_counts"]:
        avg_messages = sum(patterns["message_counts"]) / len(patterns["message_counts"])
        print(f"  Avg messages: {avg_messages:.1f}")
    
    # Show conversation continuity
    print("\n🗣️ CONVERSATION CONTINUITY:")
    for contact_id, runs in conversations.items():
        if len(runs) > 1:
            print(f"\nContact: {contact_id}")
            print(f"  Messages across {len(runs)} runs:")
            
            for i, run in enumerate(sorted(runs, key=lambda x: x["time"])):
                print(f"    [{i+1}] Messages: {run['message_count']}, "
                      f"Checkpoint: {'✅' if run['checkpoint_loaded'] else '❌'}, "
                      f"Thread: {run['thread_id']}")
                
            # Check if context growing
            msg_counts = [r["message_count"] for r in sorted(runs, key=lambda x: x["time"])]
            if len(msg_counts) > 1 and all(msg_counts[i] <= msg_counts[i+1] for i in range(len(msg_counts)-1)):
                print(f"    ✅ Context appears to be accumulating")
            else:
                print(f"    ❌ Context may be resetting between messages")
    
    # Diagnosis
    print("\n" + "=" * 80)
    print("🎯 DIAGNOSIS:")
    
    if patterns["no_thread_id"] > patterns["has_thread_id"]:
        print("\n❌ MAJOR ISSUE: Most runs don't have thread_id!")
    
    if patterns["no_checkpoint"] > patterns["checkpoint_loaded"]:
        print("\n⚠️  ISSUE: Checkpoints rarely loading even with thread_id")
        
    if patterns["no_history"] > patterns["has_history"]:
        print("\n❌ CRITICAL: Most conversations have no history!")
    
    print("\n🔧 RECOMMENDATIONS:")
    print("1. Ensure thread_mapper runs FIRST in workflow")
    print("2. Use consistent thread_id across messages")
    print("3. Verify checkpoint persistence (Redis/Postgres for production)")
    print("4. Check receptionist_checkpoint_aware is loading history")

if __name__ == "__main__":
    check_recent_traces(hours=2)
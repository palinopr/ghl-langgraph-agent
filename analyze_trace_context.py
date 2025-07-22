#!/usr/bin/env python3
"""
Analyze specific trace to see what's happening with context
"""
import os
from langsmith import Client
from datetime import datetime
import json

# Set up LangSmith
os.environ["LANGCHAIN_API_KEY"] = "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"

def analyze_trace_for_context(trace_id: str):
    """Deep dive into a trace to check context handling"""
    
    client = Client()
    
    print(f"🔍 Analyzing Trace: {trace_id}")
    print("=" * 80)
    
    try:
        # Get the run
        run = client.read_run(trace_id)
        
        print(f"Status: {run.status}")
        print(f"Start: {run.start_time}")
        print(f"Duration: {(run.end_time - run.start_time).total_seconds():.2f}s" if run.end_time else "Still running")
        
        # Extract inputs
        inputs = run.inputs
        print(f"\n📥 INPUTS:")
        print(json.dumps(inputs, indent=2, default=str)[:500] + "...")
        
        # Extract outputs
        outputs = run.outputs
        print(f"\n📤 OUTPUTS:")
        print(json.dumps(outputs, indent=2, default=str)[:500] + "...")
        
        # Look for thread_id
        thread_id = None
        if isinstance(inputs, dict):
            thread_id = inputs.get("thread_id") or inputs.get("state", {}).get("thread_id")
        if isinstance(outputs, dict):
            thread_id = thread_id or outputs.get("thread_id")
            
        print(f"\n🧵 Thread ID: {thread_id or 'NOT FOUND!'}")
        
        # Look for messages to check context
        messages = []
        if isinstance(outputs, dict):
            messages = outputs.get("messages", [])
        
        print(f"\n💬 Messages in State: {len(messages)}")
        if messages:
            print("Message History:")
            for i, msg in enumerate(messages[:5]):  # First 5 messages
                if isinstance(msg, dict):
                    content = msg.get("content", "")[:100]
                    msg_type = msg.get("type", "unknown")
                    print(f"  [{i}] {msg_type}: {content}...")
        
        # Check for checkpoint loading
        checkpoint_loaded = False
        if isinstance(outputs, dict):
            checkpoint_loaded = outputs.get("checkpoint_loaded", False)
        
        print(f"\n💾 Checkpoint Loaded: {checkpoint_loaded}")
        
        # Get child runs to see flow
        child_runs = list(client.list_runs(parent_run_id=str(run.id)))
        
        print(f"\n🔄 Execution Flow ({len(child_runs)} steps):")
        
        # Look for specific nodes
        nodes_found = {
            "thread_mapper": False,
            "receptionist": False,
            "intelligence": False,
            "supervisor": False,
            "responder": False
        }
        
        for child in child_runs:
            child_name = child.name.lower()
            print(f"  - {child.name}")
            
            # Check for our key nodes
            for node in nodes_found:
                if node in child_name:
                    nodes_found[node] = True
                    
                    # Get details for key nodes
                    if node == "thread_mapper":
                        if child.outputs:
                            thread_output = child.outputs.get("thread_id")
                            print(f"    → Thread Mapper Output: {thread_output}")
                    
                    elif node == "receptionist":
                        if child.outputs:
                            msg_count = len(child.outputs.get("messages", []))
                            has_checkpoint = child.outputs.get("has_checkpoint", False)
                            print(f"    → Receptionist: {msg_count} messages, checkpoint={has_checkpoint}")
                    
                    elif node == "intelligence":
                        if child.outputs:
                            score = child.outputs.get("lead_score")
                            print(f"    → Intelligence: Lead score = {score}")
                    
                    elif node == "supervisor":
                        if child.outputs:
                            next_agent = child.outputs.get("next_agent")
                            print(f"    → Supervisor: Routing to {next_agent}")
                    
                    elif node == "responder":
                        if child.outputs:
                            sent = child.outputs.get("message_sent", False)
                            print(f"    → Responder: Message sent = {sent}")
        
        # Summary
        print(f"\n📊 CONTEXT ANALYSIS SUMMARY:")
        print(f"  Thread ID: {'✅ Present' if thread_id else '❌ MISSING'}")
        print(f"  Message History: {len(messages)} messages")
        print(f"  Checkpoint: {'✅ Loaded' if checkpoint_loaded else '❌ Not loaded'}")
        print(f"  Thread Mapper: {'✅ Executed' if nodes_found['thread_mapper'] else '❌ Missing'}")
        print(f"  Receptionist: {'✅ Executed' if nodes_found['receptionist'] else '❌ Missing'}")
        
        if not thread_id:
            print("\n⚠️  CONTEXT WILL BE LOST! No thread_id means no checkpoint persistence.")
        elif len(messages) <= 1:
            print("\n⚠️  NO CONVERSATION HISTORY! Each message is treated as new.")
        else:
            print("\n✅ Context appears to be maintained.")
            
        return {
            "trace_id": trace_id,
            "thread_id": thread_id,
            "message_count": len(messages),
            "checkpoint_loaded": checkpoint_loaded,
            "nodes_executed": nodes_found
        }
        
    except Exception as e:
        print(f"❌ Error analyzing trace: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Analyze the specific trace"""
    
    trace_id = "1f0674ce-7f7f-6a2a-b294-cf90594eaab8"
    
    print("🔬 LangSmith Trace Context Analysis")
    print("=" * 80)
    print(f"API Key: lsv2_pt_...36c0d")
    print(f"Trace: {trace_id}")
    print("=" * 80)
    
    result = analyze_trace_for_context(trace_id)
    
    if result:
        print("\n" + "=" * 80)
        print("🎯 DIAGNOSIS:")
        
        if not result["thread_id"]:
            print("\n❌ PROBLEM: No thread_id in the workflow state!")
            print("   This means:")
            print("   - Checkpointer cannot save conversation state")
            print("   - Each message starts a new conversation")
            print("   - Context is lost between messages")
            print("\n🔧 FIX: Ensure thread_mapper node runs first and sets thread_id")
        
        elif result["message_count"] <= 1:
            print("\n❌ PROBLEM: No conversation history loaded!")
            print("   This means:")
            print("   - Checkpoint exists but wasn't loaded")
            print("   - Or this is genuinely the first message")
            print("\n🔧 FIX: Check receptionist_checkpoint_aware is being used")
        
        else:
            print("\n✅ Context handling appears correct!")

if __name__ == "__main__":
    main()
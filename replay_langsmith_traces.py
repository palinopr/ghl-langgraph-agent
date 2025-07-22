#!/usr/bin/env python3
"""
Replay specific LangSmith traces locally to debug issues
"""
import os
import asyncio
from langsmith import Client
from datetime import datetime

# Set up LangSmith
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "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"
os.environ["LANGCHAIN_PROJECT"] = "ghl-agent-replay"

# Set up other env vars
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")
os.environ["GHL_API_KEY"] = "pit-21cee867-6a57-4eea-b6fa-2bd4462934d0"
os.environ["GHL_LOCATION_ID"] = "sHFG9Rw6BdGh6d6bfMqG"

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.workflow import run_workflow

async def get_trace_details(trace_id: str):
    """Get details from a specific trace"""
    client = Client()
    
    try:
        # Get the run
        run = client.read_run(trace_id)
        
        print(f"\n📊 Trace: {trace_id}")
        print(f"Status: {run.status}")
        print(f"Start: {run.start_time}")
        print(f"End: {run.end_time}")
        
        # Extract webhook data from inputs
        inputs = run.inputs
        if isinstance(inputs, dict):
            webhook_data = inputs.get("webhook_data", inputs)
            state = inputs.get("state", inputs)
            
            # Try to find contact and message info
            contact_id = webhook_data.get("contactId") or state.get("contact_id")
            message = webhook_data.get("body") or state.get("last_message", "")
            conversation_id = webhook_data.get("conversationId") or state.get("conversation_id")
            
            print(f"\n💬 Message Details:")
            print(f"Contact ID: {contact_id}")
            print(f"Conversation ID: {conversation_id}")
            print(f"Message: {message}")
            
            return {
                "trace_id": trace_id,
                "contact_id": contact_id,
                "conversation_id": conversation_id,
                "message": message,
                "webhook_data": webhook_data,
                "full_inputs": inputs
            }
        
    except Exception as e:
        print(f"❌ Error reading trace: {e}")
        return None

async def replay_trace(trace_data: dict):
    """Replay a trace locally"""
    print(f"\n🔄 Replaying trace {trace_data['trace_id']}...")
    
    # Reconstruct webhook data
    webhook_data = trace_data.get("webhook_data", {})
    if not webhook_data.get("contactId"):
        webhook_data["contactId"] = trace_data["contact_id"]
    if not webhook_data.get("body"):
        webhook_data["body"] = trace_data["message"]
    if not webhook_data.get("conversationId"):
        webhook_data["conversationId"] = trace_data["conversation_id"]
    
    webhook_data["locationId"] = webhook_data.get("locationId", "sHFG9Rw6BdGh6d6bfMqG")
    
    print(f"📤 Sending: {webhook_data.get('body', '')[:100]}...")
    
    try:
        result = await run_workflow(webhook_data)
        print(f"✅ Replay successful!")
        print(f"- Message sent: {result.get('message_sent')}")
        print(f"- Lead score: {result.get('lead_score')}")
        print(f"- Thread ID: {result.get('thread_id')}")
        print(f"- Checkpoint loaded: {result.get('checkpoint_loaded')}")
        return result
    except Exception as e:
        print(f"❌ Replay failed: {e}")
        import traceback
        traceback.print_exc()
        return None

async def analyze_conversation_traces(trace_ids: list):
    """Analyze multiple traces from a conversation"""
    print(f"\n🔍 Analyzing {len(trace_ids)} traces...")
    
    traces = []
    for trace_id in trace_ids:
        trace_data = await get_trace_details(trace_id)
        if trace_data:
            traces.append(trace_data)
    
    if not traces:
        print("❌ No valid traces found")
        return
    
    # Group by conversation
    conversations = {}
    for trace in traces:
        conv_id = trace.get("conversation_id", "unknown")
        if conv_id not in conversations:
            conversations[conv_id] = []
        conversations[conv_id].append(trace)
    
    print(f"\n📊 Found {len(conversations)} conversations")
    
    # Replay each conversation in order
    for conv_id, conv_traces in conversations.items():
        print(f"\n{'='*50}")
        print(f"🗣️ Conversation: {conv_id}")
        print(f"Messages: {len(conv_traces)}")
        
        # Sort by message order (assuming they're in chronological order)
        for i, trace in enumerate(conv_traces):
            print(f"\n--- Message {i+1} ---")
            result = await replay_trace(trace)
            
            # Wait a bit between messages
            if i < len(conv_traces) - 1:
                await asyncio.sleep(1)

async def test_specific_traces():
    """Test the specific traces mentioned"""
    
    # The traces you mentioned
    trace_ids = [
        "1f067457-2c04-6467-a9a8-13cdc906c098",
        "1f067452-0dda-61cc-bd5a-b380392345a3", 
        "1f067450-f248-6c65-ad62-5b003dd1b02a"
    ]
    
    print("🧪 Testing Specific LangSmith Traces")
    print("=" * 50)
    print(f"API Key: lsv2_pt_...36c0d")
    print(f"Traces to analyze: {len(trace_ids)}")
    
    await analyze_conversation_traces(trace_ids)
    
    print("\n✅ Analysis complete!")
    print(f"View new traces at: https://smith.langchain.com/o/anthropic/projects/p/ghl-agent-replay")

async def test_latest_traces():
    """Get and test the latest traces"""
    print("\n📊 Getting latest traces from LangSmith...")
    
    client = Client()
    
    # Get recent runs
    runs = list(client.list_runs(
        limit=10,
        execution_order=1  # Most recent first
    ))
    
    if not runs:
        print("❌ No recent runs found")
        return
    
    print(f"✅ Found {len(runs)} recent runs")
    
    # Show summary
    for i, run in enumerate(runs[:5]):
        print(f"\n{i+1}. Run ID: {run.id}")
        print(f"   Status: {run.status}")
        print(f"   Project: {run.project_name}")
        print(f"   Time: {run.start_time}")
    
    # Replay the most recent conversation
    print("\n🔄 Replaying most recent run...")
    latest = runs[0]
    trace_data = await get_trace_details(str(latest.id))
    if trace_data:
        await replay_trace(trace_data)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "latest":
        # Test latest traces
        asyncio.run(test_latest_traces())
    else:
        # Test specific traces
        asyncio.run(test_specific_traces())
#!/usr/bin/env python3
"""
Check LangSmith traces without running the workflow
Just analyze what happened in production
"""
import os
from datetime import datetime, timedelta
from langsmith import Client
from collections import defaultdict

# Your LangSmith API key
os.environ["LANGCHAIN_API_KEY"] = "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"

def analyze_trace(trace_id: str):
    """Analyze a specific trace"""
    client = Client()
    
    try:
        run = client.read_run(trace_id)
        
        print(f"\n{'='*60}")
        print(f"📊 Trace: {trace_id}")
        print(f"{'='*60}")
        print(f"Status: {run.status}")
        print(f"Start: {run.start_time}")
        print(f"Duration: {(run.end_time - run.start_time).total_seconds():.2f}s" if run.end_time else "Still running")
        
        # Extract key information
        inputs = run.inputs
        outputs = run.outputs
        
        # Look for webhook data
        webhook_data = None
        if isinstance(inputs, dict):
            webhook_data = inputs.get("webhook_data") or inputs.get("state", {}).get("webhook_data")
        
        if webhook_data:
            print(f"\n💬 Message Info:")
            print(f"- Contact: {webhook_data.get('contactId')}")
            print(f"- Message: {webhook_data.get('body', '')[:100]}...")
            print(f"- Conversation: {webhook_data.get('conversationId')}")
        
        # Check outputs
        if outputs:
            print(f"\n📤 Results:")
            print(f"- Lead Score: {outputs.get('lead_score', 'N/A')}")
            print(f"- Current Agent: {outputs.get('current_agent', 'N/A')}")
            print(f"- Message Sent: {outputs.get('message_sent', 'N/A')}")
            print(f"- Thread ID: {outputs.get('thread_id', 'N/A')}")
        
        # Check for errors
        if run.error:
            print(f"\n❌ Error: {run.error}")
        
        # Get child runs to see the flow
        child_runs = list(client.list_runs(parent_run_id=str(run.id)))
        if child_runs:
            print(f"\n🔄 Execution Flow ({len(child_runs)} steps):")
            for i, child in enumerate(child_runs[:10]):  # First 10
                print(f"  {i+1}. {child.name} - {child.run_type}")
                if child.error:
                    print(f"     ❌ Error: {child.error}")
        
        return {
            "trace_id": trace_id,
            "status": run.status,
            "contact_id": webhook_data.get("contactId") if webhook_data else None,
            "message": webhook_data.get("body") if webhook_data else None,
            "lead_score": outputs.get("lead_score") if outputs else None,
            "agent": outputs.get("current_agent") if outputs else None,
            "error": run.error
        }
        
    except Exception as e:
        print(f"❌ Error reading trace: {e}")
        return None

def check_recent_runs(hours=1):
    """Check recent runs for issues"""
    client = Client()
    
    print(f"\n🔍 Checking runs from last {hours} hour(s)...")
    
    # Get recent runs
    since = datetime.now() - timedelta(hours=hours)
    runs = list(client.list_runs(
        start_time=since,
        limit=50
    ))
    
    print(f"Found {len(runs)} runs")
    
    # Group by status
    by_status = defaultdict(list)
    for run in runs:
        by_status[run.status].append(run)
    
    # Show summary
    print("\n📊 Status Summary:")
    for status, status_runs in by_status.items():
        print(f"- {status}: {len(status_runs)} runs")
    
    # Show errors
    if by_status.get("error"):
        print(f"\n❌ Failed Runs ({len(by_status['error'])}):")
        for run in by_status["error"][:5]:  # First 5
            print(f"\nRun: {run.id}")
            print(f"Error: {run.error}")
            print(f"Time: {run.start_time}")
    
    # Show successful runs with context issues
    print("\n🔍 Checking for context issues...")
    context_issues = []
    
    for run in runs:
        if run.status == "success" and run.outputs:
            outputs = run.outputs
            # Check if checkpoint was loaded
            if not outputs.get("checkpoint_loaded") and outputs.get("thread_id"):
                context_issues.append(run)
    
    if context_issues:
        print(f"\n⚠️  Runs without loaded context ({len(context_issues)}):")
        for run in context_issues[:5]:
            print(f"- {run.id} (Thread: {run.outputs.get('thread_id')})")

def analyze_conversation_flow(trace_ids: list):
    """Analyze a full conversation flow"""
    print(f"\n🗣️ Analyzing Conversation Flow")
    print("=" * 60)
    
    results = []
    for trace_id in trace_ids:
        result = analyze_trace(trace_id)
        if result:
            results.append(result)
    
    # Show conversation progression
    print("\n📈 Conversation Progression:")
    for i, result in enumerate(results):
        print(f"\nMessage {i+1}:")
        print(f"- Content: {result['message'][:50]}..." if result['message'] else "N/A")
        print(f"- Lead Score: {result['lead_score']} → Agent: {result['agent']}")
        print(f"- Status: {result['status']}")

def main():
    print("🔍 LangSmith Trace Analyzer")
    print("=" * 60)
    print(f"API Key: lsv2_pt_...36c0d")
    
    # The specific traces you mentioned
    trace_ids = [
        "1f067457-2c04-6467-a9a8-13cdc906c098",
        "1f067452-0dda-61cc-bd5a-b380392345a3",
        "1f067450-f248-6c65-ad62-5b003dd1b02a"
    ]
    
    # Analyze individual traces
    print("\n📊 Analyzing Specific Traces:")
    analyze_conversation_flow(trace_ids)
    
    # Check recent runs
    check_recent_runs(hours=2)
    
    print("\n✅ Analysis complete!")
    print(f"\nView traces at: https://smith.langchain.com")

if __name__ == "__main__":
    main()
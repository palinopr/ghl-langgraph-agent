#!/usr/bin/env python3
"""
Check recent traces to verify deployment
"""
import os
from datetime import datetime, timezone, timedelta
from langsmith import Client

# Set up the API key
os.environ["LANGSMITH_API_KEY"] = "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"

# Initialize client
client = Client()

def check_recent_traces():
    """Check traces from the last hour"""
    print("🔍 Checking traces from the last hour...")
    
    # Get traces from last hour
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    
    recent_runs = list(client.list_runs(
        project_name="ghl-langgraph-agent",
        start_time=one_hour_ago,
        execution_order=1,
        limit=10
    ))
    
    print(f"\nFound {len(recent_runs)} traces in the last hour")
    
    # Show each trace
    for i, run in enumerate(recent_runs):
        print(f"\n{i+1}. Trace ID: {run.id}")
        print(f"   Time: {run.start_time}")
        print(f"   Status: {run.status}")
        
        # Get input message
        if run.inputs and 'messages' in run.inputs:
            msgs = run.inputs['messages']
            if msgs and len(msgs) > 0:
                last_msg = msgs[-1]
                if isinstance(last_msg, dict) and 'content' in last_msg:
                    print(f"   Input: '{last_msg['content']}'")
        
        # Check for child runs to see workflow execution
        child_runs = list(client.list_runs(
            project_name="ghl-langgraph-agent",
            filter=f'eq(parent_run_id, "{run.id}")'
        ))
        
        # Look for intelligence and supervisor scores
        for child in child_runs:
            if "intelligence" in child.name.lower() and child.outputs:
                score = child.outputs.get("lead_score")
                if score:
                    print(f"   Intelligence Score: {score}")
            
            if "supervisor" in child.name.lower() and child.outputs:
                score = child.outputs.get("lead_score")
                agent = child.outputs.get("next_agent")
                if score or agent:
                    print(f"   Supervisor: Score={score}, Route to {agent}")
    
    # Deployment verification
    print("\n" + "="*60)
    deployment_time = datetime(2025, 7, 21, 17, 20, 0, tzinfo=timezone.utc)
    print(f"Deployment pushed at: {deployment_time}")
    print(f"Current time: {datetime.now(timezone.utc)}")
    print(f"Time since deployment: {datetime.now(timezone.utc) - deployment_time}")
    
    # Check if deployment is live
    traces_after_deployment = []
    for r in recent_runs:
        run_time = r.start_time
        if isinstance(run_time, str):
            run_time = datetime.fromisoformat(run_time.replace('Z', '+00:00'))
        elif run_time.tzinfo is None:
            run_time = run_time.replace(tzinfo=timezone.utc)
        
        if run_time > deployment_time:
            traces_after_deployment.append(r)
    print(f"\nTraces after deployment: {len(traces_after_deployment)}")
    
    if not traces_after_deployment:
        print("\n⚠️  No traces since deployment yet.")
        print("The deployment may still be building or no messages have been received.")
        print("\nTo test manually, send a message to the GHL webhook.")

if __name__ == "__main__":
    check_recent_traces()
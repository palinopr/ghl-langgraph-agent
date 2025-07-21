#!/usr/bin/env python3
"""
Fetch specific LangSmith trace: 1f066330-0068-66af-9e52-fc516114ae68
"""
import os
import asyncio
from datetime import datetime
from langsmith import Client
from dotenv import load_dotenv

load_dotenv()

async def fetch_trace():
    """Fetch and analyze the specific trace"""
    trace_id = "1f066330-0068-66af-9e52-fc516114ae68"
    
    print(f"🔍 Fetching trace: {trace_id}")
    print("=" * 60)
    
    try:
        # Initialize LangSmith client
        client = Client()
        
        # Get the run
        run = client.read_run(trace_id)
        
        # Basic info
        print(f"\n📊 TRACE INFORMATION:")
        print(f"ID: {run.id}")
        print(f"Name: {run.name}")
        print(f"Status: {run.status}")
        print(f"Start Time: {run.start_time}")
        print(f"End Time: {run.end_time}")
        print(f"Total Tokens: {run.total_tokens if hasattr(run, 'total_tokens') else 'N/A'}")
        
        # Input/Output
        print(f"\n📥 INPUT:")
        if run.inputs:
            print(f"Message: {run.inputs.get('messages', [{}])[-1].get('content', 'N/A')}")
            print(f"Contact ID: {run.inputs.get('contact_id', 'N/A')}")
        
        print(f"\n📤 OUTPUT:")
        if run.outputs:
            print(f"Response: {run.outputs}")
        
        # Errors
        if run.error:
            print(f"\n❌ ERROR: {run.error}")
        
        # Get child runs for detailed flow
        print(f"\n🔄 EXECUTION FLOW:")
        child_runs = list(client.list_runs(run_filter={"parent_run_id": trace_id}))
        
        for i, child in enumerate(child_runs, 1):
            print(f"\n{i}. {child.name}")
            print(f"   Status: {child.status}")
            print(f"   Duration: {(child.end_time - child.start_time).total_seconds() if child.end_time else 'N/A'}s")
            
            # Check for specific agent responses
            if 'agent' in child.name.lower() or 'node' in child.name.lower():
                if child.outputs:
                    print(f"   Output: {str(child.outputs)[:200]}...")
            
            if child.error:
                print(f"   ❌ Error: {child.error}")
        
        # Analysis
        print(f"\n📝 ANALYSIS:")
        
        # Check if this is after our deployment
        if run.start_time:
            deployment_time = datetime(2025, 7, 20, 22, 0, 0)  # Our deployment time
            if run.start_time.replace(tzinfo=None) > deployment_time:
                print("✅ This trace is AFTER our deployment")
            else:
                print("⚠️ This trace is BEFORE our deployment")
        
        # Look for context usage
        for child in child_runs:
            if 'supervisor' in child.name.lower() and child.outputs:
                outputs = str(child.outputs)
                if 'score' in outputs:
                    # Extract score
                    import re
                    score_match = re.search(r'score["\']?\s*:\s*(\d+)', outputs)
                    if score_match:
                        score = int(score_match.group(1))
                        print(f"\n🎯 Lead Score: {score}")
                        if score >= 6:
                            print("✅ High score indicates context was used!")
                        else:
                            print("⚠️ Low score may indicate context issue")
        
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"❌ Error fetching trace: {str(e)}")
        print("\nPossible reasons:")
        print("- Trace is still being processed")
        print("- Trace ID is incorrect")
        print("- LangSmith API access issue")
        print(f"- Full error: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(fetch_trace())
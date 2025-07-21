#!/usr/bin/env python3
"""
Simple check of latest traces
"""
import os
from datetime import datetime, timedelta
from langsmith import Client
from dotenv import load_dotenv

load_dotenv()

def check_latest():
    """Check the most recent traces"""
    print("🔍 Checking Latest LangSmith Traces")
    print("=" * 60)
    
    client = Client()
    
    # Get traces from last hour
    start_time = datetime.utcnow() - timedelta(hours=1)
    
    try:
        runs = list(client.list_runs(
            project_name=os.getenv("LANGSMITH_PROJECT", "ghl-langgraph-agent"),
            start_time=start_time,
            limit=10
        ))
        
        print(f"Found {len(runs)} recent traces\n")
        
        deployment_time = datetime(2025, 7, 21, 8, 9, 0)
        
        for i, run in enumerate(runs[:5], 1):
            print(f"{i}. Run ID: {run.id}")
            print(f"   Time: {run.start_time}")
            
            # Check if post-deployment
            if run.start_time:
                is_post = run.start_time.replace(tzinfo=None) > deployment_time
                print(f"   Status: {'🆕 POST-DEPLOYMENT' if is_post else '🕐 Pre-deployment'}")
            
            # Get basic info
            if run.inputs:
                # Extract message
                msgs = run.inputs.get("messages", [])
                if msgs:
                    last_msg = msgs[-1]
                    if isinstance(last_msg, dict):
                        content = last_msg.get("content", "")
                        print(f"   Message: {content[:50]}...")
                
                # Contact ID
                contact = run.inputs.get("contact_id", "N/A")
                print(f"   Contact: {contact}")
            
            # Check outputs
            if run.outputs:
                score = run.outputs.get("lead_score", "N/A")
                agent = run.outputs.get("next_agent", "N/A")
                
                print(f"   📊 Score: {score}")
                print(f"   🎯 Agent: {agent}")
                
                # Check extraction
                extracted = run.outputs.get("extracted_data", {})
                if extracted:
                    biz = extracted.get("business_type", "N/A")
                    name = extracted.get("name", "N/A")
                    print(f"   📝 Extracted: name={name}, business={biz}")
            
            print("-" * 60)
            
    except Exception as e:
        print(f"Error: {e}")
        
    print("\n🎯 Key Indicators to Watch:")
    print("- Score 6+ for business owners with problems")
    print("- Routing to Carlos/Sofia instead of Maria")
    print("- Business type extracted from history")
    print("- Context-aware responses")


if __name__ == "__main__":
    check_latest()
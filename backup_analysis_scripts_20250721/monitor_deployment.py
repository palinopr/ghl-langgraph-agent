#!/usr/bin/env python3
"""
Monitor LangSmith traces after deployment to verify fixes are working
"""
import os
import asyncio
from datetime import datetime, timedelta, timezone
from langsmith import Client
from dotenv import load_dotenv
import json

load_dotenv()

# Deployment time (UTC)
DEPLOYMENT_TIME = datetime(2025, 7, 21, 8, 9, 0, tzinfo=timezone.utc)

async def monitor_traces():
    """Monitor recent traces to verify deployment success"""
    print("🔍 Monitoring LangSmith Traces Post-Deployment")
    print(f"Deployment Time: {DEPLOYMENT_TIME}")
    print("=" * 80)
    
    try:
        client = Client()
        
        # Get traces from the last 2 hours
        start_time = datetime.now(timezone.utc) - timedelta(hours=2)
        
        # Query for recent runs
        runs = list(client.list_runs(
            project_name=os.getenv("LANGSMITH_PROJECT", "ghl-langgraph-agent"),
            start_time=start_time,
            run_type="chain",
            limit=20
        ))
        
        print(f"\nFound {len(runs)} recent traces")
        print("-" * 80)
        
        # Analyze each trace
        post_deployment_traces = []
        
        for run in runs:
            if run.start_time and run.start_time.replace(tzinfo=timezone.utc) > DEPLOYMENT_TIME:
                post_deployment_traces.append(run)
        
        print(f"\n📊 Post-Deployment Traces: {len(post_deployment_traces)}")
        
        # Analyze post-deployment behavior
        for i, run in enumerate(post_deployment_traces[:5], 1):  # Show first 5
            print(f"\n{i}. Trace ID: {run.id}")
            print(f"   Time: {run.start_time}")
            print(f"   Status: {run.status}")
            
            # Check inputs
            if run.inputs:
                messages = run.inputs.get("messages", [])
                if messages and isinstance(messages, list) and len(messages) > 0:
                    last_msg = messages[-1]
                    if isinstance(last_msg, dict):
                        print(f"   Message: {last_msg.get('content', 'N/A')}")
                
                # Check for contact info
                contact_id = run.inputs.get("contact_id", "N/A")
                print(f"   Contact: {contact_id}")
            
            # Check outputs for scoring
            if run.outputs:
                lead_score = run.outputs.get("lead_score", 0)
                next_agent = run.outputs.get("next_agent", "N/A")
                extracted = run.outputs.get("extracted_data", {})
                
                print(f"   Lead Score: {lead_score}")
                print(f"   Routed to: {next_agent}")
                
                if extracted:
                    print(f"   Extracted: {json.dumps(extracted, indent=6)}")
            
            # Look for supervisor execution
            child_runs = list(client.list_runs(
                run_filter={"parent_run_id": str(run.id)},
                limit=10
            ))
            
            supervisor_found = False
            for child in child_runs:
                if "supervisor" in child.name.lower():
                    supervisor_found = True
                    if child.outputs:
                        print(f"   ✅ Supervisor executed!")
                        # Check if AI was used
                        if "ai_insights" in str(child.outputs):
                            print(f"   🤖 AI Analysis used!")
                    break
            
            if not supervisor_found:
                print(f"   ⚠️ No supervisor execution found")
            
        # Summary statistics
        print("\n" + "=" * 80)
        print("📈 DEPLOYMENT VERIFICATION SUMMARY")
        print("=" * 80)
        
        if post_deployment_traces:
            high_scores = sum(1 for run in post_deployment_traces 
                            if run.outputs and run.outputs.get("lead_score", 0) >= 6)
            
            carlos_sofia_routes = sum(1 for run in post_deployment_traces 
                                    if run.outputs and run.outputs.get("next_agent") in ["carlos", "sofia"])
            
            print(f"Total traces after deployment: {len(post_deployment_traces)}")
            print(f"High scores (6+): {high_scores} ({high_scores/len(post_deployment_traces)*100:.1f}%)")
            print(f"Routed to Carlos/Sofia: {carlos_sofia_routes} ({carlos_sofia_routes/len(post_deployment_traces)*100:.1f}%)")
            
            # Check for specific improvements
            print("\n🔍 Looking for context awareness indicators...")
            
            context_aware_count = 0
            for run in post_deployment_traces:
                if run.outputs:
                    extracted = run.outputs.get("extracted_data", {})
                    if extracted.get("business_type") and extracted.get("business_type") != "NO_MENCIONADO":
                        context_aware_count += 1
            
            print(f"Traces with business extracted: {context_aware_count} ({context_aware_count/len(post_deployment_traces)*100:.1f}%)")
            
            if high_scores > 0 or context_aware_count > 0:
                print("\n✅ DEPLOYMENT APPEARS SUCCESSFUL!")
                print("   - Seeing higher lead scores")
                print("   - Business information being extracted")
            else:
                print("\n⚠️ DEPLOYMENT MAY NEED MORE TIME")
                print("   - Not seeing expected improvements yet")
                print("   - Check again in 10-15 minutes")
        else:
            print("No post-deployment traces found yet. The deployment may still be processing.")
            print("Please wait a few minutes and run this script again.")
        
    except Exception as e:
        print(f"❌ Error monitoring traces: {e}")
        import traceback
        traceback.print_exc()


async def check_specific_contact(contact_id: str = "NVSQlk21lpdBd7AO0yhe"):
    """Check traces for a specific contact (like Jaime)"""
    print(f"\n\n🔍 Checking traces for contact: {contact_id}")
    print("=" * 80)
    
    try:
        client = Client()
        
        # Get recent runs for this contact
        runs = list(client.list_runs(
            project_name=os.getenv("LANGSMITH_PROJECT", "ghl-langgraph-agent"),
            filter={"contact_id": contact_id},
            limit=5
        ))
        
        print(f"Found {len(runs)} traces for this contact")
        
        for i, run in enumerate(runs, 1):
            if run.start_time:
                is_post_deployment = run.start_time.replace(tzinfo=timezone.utc) > DEPLOYMENT_TIME
                status_emoji = "🆕" if is_post_deployment else "🕐"
                
                print(f"\n{i}. {status_emoji} {run.start_time} ({'POST' if is_post_deployment else 'PRE'}-deployment)")
                
                if run.outputs:
                    print(f"   Score: {run.outputs.get('lead_score', 'N/A')}")
                    print(f"   Agent: {run.outputs.get('next_agent', 'N/A')}")
                    
                    extracted = run.outputs.get('extracted_data', {})
                    if extracted.get('business_type'):
                        print(f"   Business: {extracted['business_type']}")
        
    except Exception as e:
        print(f"Error checking contact: {e}")


if __name__ == "__main__":
    asyncio.run(monitor_traces())
    # Also check Jaime specifically
    asyncio.run(check_specific_contact())
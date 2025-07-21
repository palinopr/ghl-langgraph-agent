#!/usr/bin/env python3
"""
Quick check of current booking status
"""
import asyncio
import sys
sys.path.append('.')

from app.tools.ghl_client import GHLClient
from langsmith import Client
import os

async def check_booking_status():
    """Check current status of booking flow"""
    contact_id = "ZPEl0zWM38GqLjOxxRCW"
    
    # Check GHL
    print("🔍 Checking GHL Status...")
    ghl_client = GHLClient()
    
    try:
        contact = await ghl_client.get_contact(contact_id)
        if contact:
            # Handle if contact is a list
            if isinstance(contact, list):
                contact = contact[0] if contact else {}
            custom_fields = contact.get('customFields', {})
            print(f"\n📊 Current GHL Status:")
            print(f"  - Contact: {contact.get('contactName', 'Unknown')}")
            print(f"  - Score: {custom_fields.get('score', 0)}")
            print(f"  - Business: {custom_fields.get('business_type', 'Not set')}")
            print(f"  - Budget: {custom_fields.get('budget', 'Not set')}")
            print(f"  - Current Agent: {custom_fields.get('current_agent', 'Unknown')}")
            
            # Check for appointments
            if contact.get('appointments'):
                print(f"\n📅 Appointments: {len(contact['appointments'])}")
                for apt in contact['appointments'][:3]:
                    print(f"  - {apt.get('title', 'No title')} at {apt.get('startTime', 'Unknown time')}")
            else:
                print("\n📅 No appointments found")
                
    except Exception as e:
        print(f"❌ GHL Error: {str(e)}")
    
    # Check recent LangSmith traces
    print("\n\n🔍 Checking Recent LangSmith Traces...")
    os.environ["LANGSMITH_API_KEY"] = "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"
    client = Client()
    
    try:
        runs = list(client.list_runs(
            project_name="ghl-langgraph-agent",
            limit=10,
            execution_order=1
        ))
        
        if runs:
            print(f"\n📊 Last 5 Traces:")
            # Filter for our contact if possible
            contact_runs = []
            for run in runs:
                if run.inputs and 'contact_id' in run.inputs:
                    if run.inputs['contact_id'] == contact_id:
                        contact_runs.append(run)
                elif run.inputs and 'messages' in run.inputs:
                    # Check in outputs too
                    if run.outputs and 'contact_id' in str(run.outputs):
                        if contact_id in str(run.outputs):
                            contact_runs.append(run)
            
            runs_to_show = contact_runs[:5] if contact_runs else runs[:5]
            
            for i, run in enumerate(runs_to_show, 1):
                if run.inputs and 'messages' in run.inputs:
                    msgs = run.inputs['messages']
                    if msgs and isinstance(msgs[-1], dict):
                        last_msg = msgs[-1].get('content', 'N/A')[:50] + "..."
                    else:
                        last_msg = "N/A"
                else:
                    last_msg = "N/A"
                    
                score = "N/A"
                agent = "N/A"
                if run.outputs:
                    score = run.outputs.get('lead_score', 'N/A')
                    agent = run.outputs.get('current_agent', 'N/A')
                
                status = "✅" if run.status == "success" else "❌"
                print(f"  {i}. {status} Message: {last_msg}")
                print(f"     Score: {score}, Agent: {agent}")
        else:
            print("  No recent traces found")
            
    except Exception as e:
        print(f"❌ LangSmith Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(check_booking_status())
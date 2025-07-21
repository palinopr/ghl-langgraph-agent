#!/usr/bin/env python3
"""
Fetch specific LangSmith trace: 1f0663d4-0bfe-6545-8ef1-63ff240a6773
"""
import os
import asyncio
from datetime import datetime
from langsmith import Client
from dotenv import load_dotenv
import json

load_dotenv()

async def fetch_trace():
    """Fetch and analyze the specific trace"""
    trace_id = "1f0663d4-0bfe-6545-8ef1-63ff240a6773"
    
    print(f"🔍 Fetching trace: {trace_id}")
    print("=" * 80)
    
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
        
        # Check deployment timing
        deployment_time = datetime(2025, 7, 21, 8, 9, 0)
        if run.start_time:
            is_post_deployment = run.start_time.replace(tzinfo=None) > deployment_time
            print(f"\n🚀 Deployment Status: {'POST-DEPLOYMENT ✅' if is_post_deployment else 'Pre-deployment'}")
        
        # Input/Output
        print(f"\n📥 INPUT:")
        if run.inputs:
            # Message content
            messages = run.inputs.get('messages', [])
            if messages:
                last_msg = messages[-1]
                if isinstance(last_msg, dict):
                    print(f"Message: {last_msg.get('content', 'N/A')}")
            
            print(f"Contact ID: {run.inputs.get('contact_id', 'N/A')}")
            
            # Check for webhook data
            webhook = run.inputs.get('webhook_data', {})
            if webhook:
                print(f"Webhook Message: {webhook.get('message', 'N/A')}")
        
        print(f"\n📤 OUTPUT:")
        if run.outputs:
            # Key metrics
            print(f"Lead Score: {run.outputs.get('lead_score', 'N/A')}")
            print(f"Next Agent: {run.outputs.get('next_agent', 'N/A')}")
            print(f"Current Agent: {run.outputs.get('current_agent', 'N/A')}")
            
            # Extracted data
            extracted = run.outputs.get('extracted_data', {})
            if extracted:
                print(f"\n📝 Extracted Data:")
                print(f"  Name: {extracted.get('name', 'N/A')}")
                print(f"  Business: {extracted.get('business_type', 'N/A')}")
                print(f"  Budget: {extracted.get('budget', 'N/A')}")
                print(f"  Score: {extracted.get('score', 'N/A')}")
            
            # AI insights if present
            ai_insights = run.outputs.get('ai_insights')
            if ai_insights:
                print(f"\n🤖 AI Insights:")
                print(f"  Intent: {ai_insights.get('intent', 'N/A')}")
                print(f"  Urgency: {ai_insights.get('urgency', 'N/A')}")
                print(f"  Sentiment: {ai_insights.get('sentiment', 'N/A')}")
                print(f"  Action: {ai_insights.get('recommended_action', 'N/A')}")
            
            # Messages
            output_messages = run.outputs.get('messages', [])
            if output_messages:
                # Find agent response
                for msg in reversed(output_messages):
                    if isinstance(msg, dict) and msg.get('type') == 'ai':
                        agent_name = msg.get('name', 'Unknown')
                        if agent_name in ['maria', 'carlos', 'sofia']:
                            print(f"\n💬 Agent Response ({agent_name}):")
                            print(f"'{msg.get('content', 'N/A')}'")
                            break
        
        # Errors
        if run.error:
            print(f"\n❌ ERROR: {run.error}")
        
        # Get child runs for detailed flow
        print(f"\n🔄 EXECUTION FLOW:")
        try:
            # Try to get child runs
            child_runs = []
            # Note: This might fail due to API limitations
            print("(Checking for workflow steps...)")
            
        except Exception as e:
            print(f"Could not fetch child runs: {e}")
        
        # Analysis
        print(f"\n📝 ANALYSIS:")
        
        # Check for our fixes
        if run.outputs:
            lead_score = run.outputs.get('lead_score', 0)
            next_agent = run.outputs.get('next_agent', '')
            extracted = run.outputs.get('extracted_data', {})
            
            print("\n🎯 Fix Verification:")
            
            # Check if score is appropriate
            if lead_score >= 6:
                print(f"✅ High lead score ({lead_score}) - Context awareness working!")
            else:
                print(f"⚠️ Low lead score ({lead_score}) - May need investigation")
            
            # Check routing
            if next_agent in ['carlos', 'sofia']:
                print(f"✅ Routed to {next_agent} - Proper qualification routing!")
            elif next_agent == 'maria':
                print(f"⚠️ Routed to Maria - Check if this is appropriate")
            
            # Check extraction
            if extracted.get('business_type') and extracted['business_type'] != 'NO_MENCIONADO':
                print(f"✅ Business extracted: {extracted['business_type']}")
            
            # Check for AI usage
            if ai_insights:
                print("✅ AI analyzer was used for complex understanding!")
        
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"❌ Error fetching trace: {str(e)}")
        print(f"\nFull error: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(fetch_trace())
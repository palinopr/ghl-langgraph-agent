#!/usr/bin/env python3
"""
Analyze specific trace from LangSmith
Trace ID: 1f064de9-573b-6b85-8ffd-fa9713fc6cd8
"""
import os
import json
import httpx
from datetime import datetime

# Load environment
from dotenv import load_dotenv
load_dotenv()

TRACE_ID = "1f064de9-573b-6b85-8ffd-fa9713fc6cd8"
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")

async def fetch_trace():
    """Fetch trace details from LangSmith"""
    
    headers = {
        "x-api-key": LANGSMITH_API_KEY,
        "Content-Type": "application/json"
    }
    
    # LangSmith API endpoint
    url = f"https://api.smith.langchain.com/runs/{TRACE_ID}"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, timeout=30.0)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching trace: {response.status_code}")
            print(response.text)
            return None

async def analyze_trace(trace_data):
    """Analyze the trace to understand what happened"""
    
    print("\n" + "="*60)
    print(f"TRACE ANALYSIS: {TRACE_ID}")
    print("="*60)
    
    # Basic info
    print(f"\n📊 BASIC INFO:")
    print(f"  - Name: {trace_data.get('name', 'N/A')}")
    print(f"  - Status: {trace_data.get('status', 'N/A')}")
    print(f"  - Start: {trace_data.get('start_time', 'N/A')}")
    print(f"  - End: {trace_data.get('end_time', 'N/A')}")
    
    # Check if it's successful
    if trace_data.get('error'):
        print(f"\n❌ ERROR DETECTED:")
        print(f"  {trace_data['error']}")
    
    # Get inputs
    inputs = trace_data.get('inputs', {})
    if inputs:
        print(f"\n📥 INPUTS:")
        webhook_data = inputs.get('webhook_data', {})
        if webhook_data:
            print(f"  - Contact ID: {webhook_data.get('contactId', 'N/A')}")
            print(f"  - Message: {webhook_data.get('message', 'N/A')}")
        
        # Check state
        print(f"  - Lead Score: {inputs.get('lead_score', 'N/A')}")
        print(f"  - Current Agent: {inputs.get('current_agent', 'N/A')}")
    
    # Get outputs
    outputs = trace_data.get('outputs', {})
    if outputs:
        print(f"\n📤 OUTPUTS:")
        print(f"  - Final Agent: {outputs.get('current_agent', 'N/A')}")
        print(f"  - Lead Score: {outputs.get('lead_score', 'N/A')}")
        print(f"  - Appointment Status: {outputs.get('appointment_status', 'N/A')}")
        
        # Check messages
        messages = outputs.get('messages', [])
        if messages:
            print(f"  - Total Messages: {len(messages)}")
            # Find last AI message
            for msg in reversed(messages):
                if isinstance(msg, dict) and msg.get('type') == 'ai':
                    print(f"  - AI Response: {msg.get('content', '')[:100]}...")
                    break
    
    # Get child runs to see the flow
    print(f"\n🔄 WORKFLOW FLOW:")
    
    # Fetch child runs
    child_url = f"https://api.smith.langchain.com/runs?trace_id={TRACE_ID}"
    
    headers = {
        "x-api-key": LANGSMITH_API_KEY,
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(child_url, headers=headers, timeout=30.0)
        
        if response.status_code == 200:
            runs = response.json()
            
            # Sort by start time
            sorted_runs = sorted(runs, key=lambda x: x.get('start_time', ''))
            
            for i, run in enumerate(sorted_runs):
                name = run.get('name', 'Unknown')
                status = "✅" if run.get('status') == 'success' else "❌"
                
                # Skip internal nodes
                if name not in ['ChannelWrite', 'ChannelRead', '__start__', '__end__']:
                    print(f"  {i+1}. {status} {name}")
                    
                    # Check for specific events
                    if 'sofia' in name.lower():
                        # Check if appointment tools were used
                        if run.get('outputs'):
                            print(f"     → Sofia activated")
                            
                    if 'book_appointment' in name.lower():
                        print(f"     → 📅 APPOINTMENT BOOKING ATTEMPTED!")
                        # Check the details
                        if run.get('inputs'):
                            inputs = run['inputs']
                            print(f"     → Contact ID: {inputs.get('contact_id', 'N/A')}")
                            print(f"     → Confirmation: {inputs.get('customer_confirmation', 'N/A')}")
    
    # Check for appointment-related patterns
    print(f"\n🎯 APPOINTMENT BOOKING ANALYSIS:")
    
    # Look for appointment-related content in outputs
    output_str = json.dumps(outputs)
    if 'book_appointment' in output_str:
        print("  ✅ Appointment booking tool was called")
    else:
        print("  ❌ No appointment booking detected")
    
    if 'confirmado' in output_str.lower() or 'agendada' in output_str.lower():
        print("  ✅ Appointment confirmation found in response")
    else:
        print("  ⚠️  No confirmation keywords found")
    
    # Check Sofia's involvement
    if 'sofia' in output_str.lower():
        print("  ✅ Sofia was involved in the conversation")
    else:
        print("  ❌ Sofia was not activated")

async def main():
    """Main analysis"""
    print(f"Fetching trace {TRACE_ID}...")
    
    trace_data = await fetch_trace()
    
    if trace_data:
        await analyze_trace(trace_data)
        
        # Save full trace for reference
        with open(f"trace_{TRACE_ID}.json", "w") as f:
            json.dump(trace_data, f, indent=2)
        print(f"\n💾 Full trace saved to trace_{TRACE_ID}.json")
    else:
        print("Failed to fetch trace")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
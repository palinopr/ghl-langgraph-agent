#!/usr/bin/env python3
"""
Analyze trace 1f067fce-f1ce-65e8-93ab-3b9149bc2eec for context issues - V2
"""

import os
import sys
from datetime import datetime
from langsmith import Client
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Check for API key
api_key = os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGSMITH_API_KEY")
if not api_key:
    print("❌ No LangSmith API key found!")
    sys.exit(1)

def analyze_context_trace_v2(trace_id):
    """Analyze the context extraction and routing decisions"""
    client = Client(api_key=api_key)
    
    print(f"\n{'='*80}")
    print(f"Context Analysis V2 for Trace: {trace_id}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")
    
    try:
        # Get the main run
        run = client.read_run(trace_id)
        
        print(f"✅ Main Run: {run.name}")
        print(f"   Project: {run.session_id if hasattr(run, 'session_id') else 'Unknown'}")
        
        # Get input message
        input_msg = "N/A"
        if run.inputs and 'messages' in run.inputs:
            msgs = run.inputs['messages']
            if msgs and len(msgs) > 0:
                input_msg = msgs[0].get('content', 'N/A')
        
        print(f"   Input message: '{input_msg}'")
        
        # Get output message
        output_msg = "N/A"
        if run.outputs and 'messages' in run.outputs:
            msgs = run.outputs['messages']
            for msg in msgs:
                if msg.get('type') == 'ai' or msg.get('role') == 'assistant':
                    output_msg = msg.get('content', 'N/A')
                    break
        
        print(f"\n   Output message: '{output_msg[:200]}...'")
        
        # Analyze the response
        print(f"\n🔍 RESPONSE ANALYSIS:")
        
        # Check if input mentions restaurant
        if 'restaurant' in input_msg.lower() or 'rstaurante' in input_msg.lower():
            print(f"   ✅ Input mentions restaurant")
        else:
            print(f"   ❌ Input doesn't mention restaurant")
        
        # Check if input mentions losing customers
        if 'perdiendo' in input_msg.lower() and 'cliente' in input_msg.lower():
            print(f"   ✅ Input mentions losing customers")
        else:
            print(f"   ❌ Input doesn't mention losing customers")
        
        # Check if output addresses restaurant context
        output_lower = output_msg.lower()
        if 'restaurant' in output_lower or 'cliente' in output_lower or 'retención' in output_lower:
            print(f"   ✅ Output addresses restaurant/customer context")
        else:
            print(f"   ❌ Output doesn't address restaurant context")
        
        # Check if output mentions generic communication
        if 'comunicación' in output_lower or 'whatsapp' in output_lower:
            print(f"   ⚠️ Output mentions generic communication/WhatsApp")
        
        # Try to get child runs with different approach
        print(f"\n📊 Searching for related runs in project...")
        
        # Get project name from metadata
        project_name = "ghl-langgraph-agent"
        if hasattr(run, 'extra') and run.extra and 'metadata' in run.extra:
            metadata = run.extra['metadata']
            project_name = metadata.get('LANGSMITH_PROJECT', project_name)
        
        # Search for runs around the same time
        from datetime import timedelta
        start_time = run.start_time - timedelta(seconds=30)
        end_time = run.end_time + timedelta(seconds=30) if run.end_time else run.start_time + timedelta(seconds=30)
        
        related_runs = list(client.list_runs(
            project_name=project_name,
            start_time=start_time,
            end_time=end_time,
            limit=100
        ))
        
        print(f"   Found {len(related_runs)} runs in time window")
        
        # Filter for relevant runs
        smart_router_runs = [r for r in related_runs if 'smart_router' in r.name.lower()]
        maria_runs = [r for r in related_runs if 'maria' in r.name.lower()]
        
        if smart_router_runs:
            print(f"\n🧠 SMART ROUTER RUNS: {len(smart_router_runs)}")
            for r in smart_router_runs[:2]:
                print(f"   - {r.name} at {r.start_time.strftime('%H:%M:%S')}")
                if r.outputs:
                    print(f"     extracted_data: {r.outputs.get('extracted_data', {})}")
        
        if maria_runs:
            print(f"\n👩 MARIA RUNS: {len(maria_runs)}")
            for r in maria_runs[:2]:
                print(f"   - {r.name} at {r.start_time.strftime('%H:%M:%S')}")
        
        print(f"\n{'='*40} ISSUE SUMMARY {'='*40}")
        print("\n🚨 CONTEXT MISMATCH DETECTED:")
        print(f"   Customer: 'tengo un restaurante y estoy perdiendo clientes'")
        print(f"   Response: Generic communication/WhatsApp pitch")
        print(f"\n   Expected: Restaurant-specific customer retention solution")
        print(f"   Actual: Generic business communication solution")
        
        print(f"\n🔧 POTENTIAL FIXES:")
        print("1. Smart Router: Ensure restaurant/food keywords trigger business_type extraction")
        print("2. Smart Router: Add direct message scanning for context keywords")
        print("3. Maria Agent: Verify context adaptation is receiving extracted_data")
        print("4. Maria Agent: Add fallback context detection from current message")
        
    except Exception as e:
        print(f"\n❌ Error analyzing trace: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    trace_id = "1f067fce-f1ce-65e8-93ab-3b9149bc2eec"
    if len(sys.argv) > 1:
        trace_id = sys.argv[1]
    
    analyze_context_trace_v2(trace_id)
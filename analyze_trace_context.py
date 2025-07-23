#!/usr/bin/env python3
"""
Analyze trace 1f067fce-f1ce-65e8-93ab-3b9149bc2eec for context issues
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

def analyze_context_trace(trace_id):
    """Analyze the context extraction and routing decisions"""
    client = Client(api_key=api_key)
    
    print(f"\n{'='*80}")
    print(f"Context Analysis for Trace: {trace_id}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")
    
    try:
        # Get the main run
        run = client.read_run(trace_id)
        
        print(f"✅ Main Run: {run.name}")
        print(f"   Input message: '{run.inputs.get('messages', [{}])[0].get('content', 'N/A')}'")
        
        # Get all child runs
        child_runs = list(client.list_runs(
            run_ids=[trace_id],
            is_root=False,
            order_by_desc="start_time"
        ))
        
        print(f"\n📊 Found {len(child_runs)} child runs")
        
        # Look for smart router analysis
        for child in child_runs:
            if 'smart_router' in child.name:
                print(f"\n🔍 SMART ROUTER ANALYSIS:")
                print(f"   Run: {child.name}")
                print(f"   Status: {child.status}")
                
                # Check outputs
                if child.outputs:
                    outputs = child.outputs
                    print(f"\n   📤 Router Outputs:")
                    print(f"      Lead Score: {outputs.get('lead_score', 'N/A')}")
                    print(f"      Next Agent: {outputs.get('next_agent', 'N/A')}")
                    print(f"      Routing Reason: {outputs.get('routing_reason', 'N/A')}")
                    print(f"      Intent: {outputs.get('intent', 'N/A')}")
                    
                    extracted = outputs.get('extracted_data', {})
                    print(f"\n   📋 Extracted Data:")
                    for key, value in extracted.items():
                        if value and value != "NOT PROVIDED":
                            print(f"      {key}: {value}")
                    
                    # Check if business_type was extracted
                    if not extracted.get('business_type') or extracted.get('business_type') == 'NOT PROVIDED':
                        print(f"\n   ⚠️ WARNING: business_type not extracted from 'restaurante'!")
                    
                    if not extracted.get('goal') or extracted.get('goal') == 'NOT PROVIDED':
                        print(f"   ⚠️ WARNING: goal not extracted from 'perdiendo clientes'!")
                
                # Check metadata for state snapshots
                if hasattr(child, 'extra') and child.extra and 'metadata' in child.extra:
                    metadata = child.extra['metadata']
                    
                    # Look for state snapshots
                    for key, value in metadata.items():
                        if 'state_snapshot' in key and 'smart_router' in key:
                            print(f"\n   📸 State Snapshot ({key}):")
                            if isinstance(value, dict):
                                # Check extracted_data in snapshot
                                if 'extracted_data' in value:
                                    print(f"      Extracted data in snapshot: {value['extracted_data']}")
            
            # Look for Maria's response
            elif 'maria' in child.name:
                print(f"\n👩 MARIA AGENT:")
                print(f"   Run: {child.name}")
                
                # Check outputs for the response
                if child.outputs and 'messages' in child.outputs:
                    messages = child.outputs['messages']
                    for msg in messages:
                        if msg.get('type') == 'ai' or msg.get('role') == 'assistant':
                            print(f"\n   💬 Maria's Response:")
                            print(f"      '{msg.get('content', 'N/A')[:200]}...'")
                            
                            # Check if response mentions restaurant/customer retention
                            response = msg.get('content', '').lower()
                            if 'restaurant' in response or 'cliente' in response:
                                print(f"   ✅ Response mentions restaurant/customer context")
                            else:
                                print(f"   ❌ Response doesn't mention restaurant context")
                            
                            if 'whatsapp' in response or 'comunicación' in response:
                                print(f"   ⚠️ Response mentions generic WhatsApp/communication")
        
        print(f"\n{'='*40} DIAGNOSIS {'='*40}")
        print("\n1. The customer said: 'tengo un restaurante y estoy perdiendo clientes'")
        print("2. This should trigger:")
        print("   - business_type: 'restaurante' or 'restaurant'")
        print("   - goal: 'customer retention' or 'perdiendo clientes'")
        print("   - Context adaptation for restaurant/customer retention")
        print("\n3. Check if smart_router's _analyze_message properly extracts this")
        print("4. Check if Maria receives the extracted_data with business_type")
        print("5. Verify Maria's context adaptation is working")
        
    except Exception as e:
        print(f"\n❌ Error analyzing trace: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    trace_id = "1f067fce-f1ce-65e8-93ab-3b9149bc2eec"
    if len(sys.argv) > 1:
        trace_id = sys.argv[1]
    
    analyze_context_trace(trace_id)
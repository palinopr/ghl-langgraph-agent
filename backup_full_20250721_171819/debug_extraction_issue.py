#!/usr/bin/env python3
"""
Debug why 'negocio' is still being extracted
"""
import os
from langsmith import Client
from datetime import datetime

os.environ["LANGSMITH_API_KEY"] = "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"

def get_intelligence_node_output(trace_id):
    """Get what the intelligence node extracted"""
    client = Client()
    
    # Get child runs
    child_runs = list(client.list_runs(
        project_name="ghl-langgraph-agent",
        filter=f'eq(parent_run_id, "{trace_id}")',
        limit=50
    ))
    
    for child in child_runs:
        if "intelligence" in child.name.lower():
            return {
                "node_name": child.name,
                "outputs": child.outputs,
                "error": child.error
            }
    
    return None

def main():
    traces = [
        ("1f066626-74a1-62f4-a9c3-51db0c3f06bd", "Hola"),
        ("1f066627-71b4-6921-a7c2-70571227038a", "tengo un restaurante")
    ]
    
    print("🔍 DEBUGGING EXTRACTION ISSUE")
    print("=" * 80)
    
    client = Client()
    
    for trace_id, message in traces:
        print(f"\nMESSAGE: '{message}'")
        print(f"TRACE: {trace_id}")
        print("-" * 40)
        
        # Get intelligence node output
        intel = get_intelligence_node_output(trace_id)
        
        if intel:
            print(f"Intelligence Node: {intel['node_name']}")
            if intel['outputs']:
                extracted = intel['outputs'].get('extracted_data', {})
                print(f"Extracted Data: {extracted}")
                
                # Check business type
                business = extracted.get('business_type')
                if business == 'negocio':
                    print("❌ ERROR: 'negocio' was extracted by intelligence layer!")
                    print("   This means the fix hasn't deployed yet OR there's a deeper issue")
                elif business:
                    print(f"✅ Correctly extracted: {business}")
                else:
                    print("✅ No business extracted (correct for generic message)")
        else:
            print("❌ No intelligence node found!")
        
        # Get the full run to see timing
        run = client.read_run(trace_id)
        print(f"Run Time: {run.start_time}")
        
        # Check if this is before or after our deployment
        deployment_time = datetime(2025, 7, 21, 18, 30, 0)  # 1:30 PM CDT in UTC
        run_time = run.start_time
        if isinstance(run_time, str):
            run_time = datetime.fromisoformat(run_time.replace('Z', '+00:00'))
        
        if run_time > deployment_time:
            print("⏰ This trace is AFTER deployment (should have fixes)")
        else:
            print("⏰ This trace is BEFORE deployment (won't have fixes)")

if __name__ == "__main__":
    main()
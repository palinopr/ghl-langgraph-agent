#!/usr/bin/env python3
"""
Analyze the intelligence node issue - why it's not extracting restaurant info
"""
import os
from langsmith import Client
import json

client = Client()

def get_node_details(trace_id, node_name):
    """Get details for a specific node"""
    runs = list(client.list_runs(
        parent_run_id=trace_id,
        limit=50
    ))
    
    for run in runs:
        if node_name.lower() in run.name.lower():
            return run
    return None

def analyze_intelligence_issue(trace_id):
    """Analyze why intelligence isn't extracting data"""
    
    # Get intelligence node
    intel_run = get_node_details(trace_id, "intelligence")
    if intel_run:
        print("INTELLIGENCE NODE:")
        print(f"- Status: {intel_run.status}")
        print(f"- Duration: {(intel_run.end_time - intel_run.start_time).total_seconds():.3f}s")
        
        if intel_run.inputs:
            print("\nINPUTS:")
            # Check what messages were passed
            messages = intel_run.inputs.get("messages", [])
            for msg in messages:
                if isinstance(msg, dict):
                    content = msg.get("content", "")
                    if "restaurante" in content.lower():
                        print(f"  Found restaurant mention: {content}")
                        
        if intel_run.outputs:
            print("\nOUTPUTS:")
            print(json.dumps(intel_run.outputs, indent=2))
    
    # Get supervisor node
    sup_run = get_node_details(trace_id, "supervisor")
    if sup_run:
        print("\n" + "="*60)
        print("SUPERVISOR NODE:")
        print(f"- Status: {sup_run.status}")
        
        if sup_run.inputs:
            print("\nINPUTS to supervisor:")
            # Check extracted_data
            extracted = sup_run.inputs.get("extracted_data", {})
            score = sup_run.inputs.get("lead_score", "?")
            print(f"- Lead Score: {score}")
            print(f"- Extracted Data: {extracted}")
            
        if sup_run.outputs:
            print("\nOUTPUTS from supervisor:")
            print(f"- Next Agent: {sup_run.outputs.get('next_agent', '?')}")
            
    # Check the actual message
    print("\n" + "="*60)
    print("MESSAGE ANALYSIS:")
    message = "Tengo u. Restaurante y estoy perdiendo muchas reservas pq no puedo contestar todo"
    print(f"Original: {message}")
    print(f"Contains 'restaurante': {'restaurante' in message.lower()}")
    print(f"Contains 'perdiendo': {'perdiendo' in message}")
    print(f"Contains 'reservas': {'reservas' in message}")
    
    # This should be:
    # - Business: Restaurant
    # - Problem: Losing reservations
    # - Score: At least 5-6 (has business + clear problem)

if __name__ == "__main__":
    trace_id = "1f065788-1e9c-6548-b835-c97ff1654fdc"
    analyze_intelligence_issue(trace_id)
#!/usr/bin/env python3
"""
Check why supervisor is boosting the score
"""
import os
from langsmith import Client
from datetime import datetime
import json

# Set up the API key
os.environ["LANGSMITH_API_KEY"] = "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"

# Initialize client
client = Client()

# Trace ID to analyze
trace_id = "1f066553-ca87-6360-8166-b920e1498c46"

def check_supervisor_boost():
    """Check why supervisor changed the score"""
    print(f"\n🔍 Checking supervisor score boost")
    print("=" * 80)
    
    # Get all runs
    all_runs = list(client.list_runs(
        project_name="ghl-langgraph-agent",
        filter=f'has(trace_id, "{trace_id}")'
    ))
    
    # Find intelligence and supervisor runs
    intelligence_run = None
    supervisor_run = None
    
    for run in all_runs:
        if "intelligence" in run.name.lower():
            intelligence_run = run
        elif "supervisor_ai" in run.name.lower():
            supervisor_run = run
    
    if intelligence_run:
        print(f"\n📊 Intelligence Analysis:")
        print(f"Score: {intelligence_run.outputs.get('lead_score', 'N/A')}")
        print(f"Extracted: {intelligence_run.outputs.get('extracted_data', {})}")
        print(f"Reasoning: {intelligence_run.outputs.get('score_reasoning', '')}")
    
    if supervisor_run:
        print(f"\n🎯 Supervisor Decision:")
        print(f"Score: {supervisor_run.outputs.get('lead_score', 'N/A')}")
        
        # Check inputs to supervisor
        print(f"\n📥 Supervisor Inputs:")
        if supervisor_run.inputs:
            if 'previous_custom_fields' in supervisor_run.inputs:
                fields = supervisor_run.inputs['previous_custom_fields']
                print(f"Previous fields: {fields}")
            if 'conversation_history' in supervisor_run.inputs:
                history = supervisor_run.inputs['conversation_history']
                print(f"History messages: {len(history) if history else 0}")
                # Show a few messages
                if history and len(history) > 0:
                    print(f"\nSample history messages:")
                    for i, msg in enumerate(history[:3]):
                        if isinstance(msg, dict):
                            content = msg.get('body', msg.get('message', ''))[:100]
                            print(f"  {i+1}. {content}...")
    
    # Check for historical context boost
    print(f"\n🔍 Checking for historical context boost:")
    print("The supervisor might be detecting historical business/problem mentions")
    print("and boosting the score to 6 for returning customers")

if __name__ == "__main__":
    check_supervisor_boost()
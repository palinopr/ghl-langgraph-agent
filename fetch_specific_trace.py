#!/usr/bin/env python3
"""
Fetch and analyze a specific trace from LangSmith
"""
import os
from langsmith import Client
import json
from datetime import datetime

# Create client
client = Client()

def analyze_trace(trace_id):
    """Fetch and analyze a specific trace"""
    print(f"Fetching trace: {trace_id}")
    
    try:
        # Get the run
        run = client.read_run(trace_id)
        
        print(f"\n{'='*80}")
        print(f"TRACE ANALYSIS: {trace_id}")
        print(f"{'='*80}")
        
        # Basic info
        print(f"\nBASIC INFO:")
        print(f"- Name: {run.name}")
        print(f"- Status: {run.status}")
        print(f"- Start: {run.start_time}")
        print(f"- End: {run.end_time}")
        print(f"- Duration: {(run.end_time - run.start_time).total_seconds():.2f}s")
        
        # Inputs
        print(f"\nINPUTS:")
        print(json.dumps(run.inputs, indent=2))
        
        # Outputs
        print(f"\nOUTPUTS:")
        if run.outputs:
            print(json.dumps(run.outputs, indent=2))
        
        # Error if any
        if run.error:
            print(f"\nERROR: {run.error}")
        
        # Get child runs to see the workflow
        print(f"\n{'='*80}")
        print("WORKFLOW EXECUTION:")
        print(f"{'='*80}")
        
        child_runs = list(client.list_runs(
            parent_run_id=trace_id,
            limit=50
        ))
        
        # Sort by start time
        child_runs.sort(key=lambda x: x.start_time)
        
        for i, child in enumerate(child_runs):
            duration = (child.end_time - child.start_time).total_seconds() if child.end_time else 0
            print(f"\n{i+1}. {child.name} ({duration:.2f}s) - {child.status}")
            
            # Show key details based on node type
            if "supervisor" in child.name.lower():
                if child.outputs:
                    score = child.outputs.get("lead_score", "?")
                    next_agent = child.outputs.get("next_agent", "?")
                    print(f"   - Score: {score}")
                    print(f"   - Next Agent: {next_agent}")
                    
            elif "receptionist" in child.name.lower():
                if child.outputs:
                    contact_id = child.outputs.get("contact_id", "?")
                    print(f"   - Contact ID: {contact_id}")
                    
            elif any(agent in child.name.lower() for agent in ["maria", "carlos", "sofia"]):
                if child.outputs and "messages" in child.outputs:
                    messages = child.outputs["messages"]
                    for msg in messages[-1:]:  # Last message
                        if hasattr(msg, "content"):
                            print(f"   - Response: {msg.content[:100]}...")
                        elif isinstance(msg, dict) and "content" in msg:
                            print(f"   - Response: {msg['content'][:100]}...")
                            
            # Show any errors
            if child.error:
                print(f"   - ERROR: {child.error}")
                
        # Look for specific issues
        print(f"\n{'='*80}")
        print("ANALYSIS:")
        print(f"{'='*80}")
        
        # Check conversation history loading
        receptionist_runs = [r for r in child_runs if "receptionist" in r.name.lower()]
        if receptionist_runs:
            rec_run = receptionist_runs[0]
            if rec_run.outputs:
                conv_history = rec_run.outputs.get("conversation_history", [])
                print(f"\n- Conversation History: {len(conv_history)} messages loaded")
                if conv_history:
                    print("  Recent messages:")
                    for msg in conv_history[-5:]:
                        if isinstance(msg, dict):
                            role = msg.get("type", msg.get("role", "?"))
                            content = msg.get("content", "")
                            print(f"    {role}: {content[:80]}...")
                
        # Check scoring
        supervisor_runs = [r for r in child_runs if "supervisor" in r.name.lower()]
        if supervisor_runs:
            sup_run = supervisor_runs[0]
            if sup_run.outputs:
                print(f"\n- Lead Score: {sup_run.outputs.get('lead_score', '?')}")
                print(f"- Extracted Data: {sup_run.outputs.get('extracted_data', {})}")
                
        return run
        
    except Exception as e:
        print(f"Error analyzing trace: {e}")
        return None

if __name__ == "__main__":
    trace_id = "1f065788-1e9c-6548-b835-c97ff1654fdc"
    analyze_trace(trace_id)
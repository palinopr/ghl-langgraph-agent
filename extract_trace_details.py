#!/usr/bin/env python3
"""
Extract detailed information from LangSmith traces
"""
import sys
import os
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    from langsmith import Client
except ImportError:
    print("Error: langsmith package not installed")
    sys.exit(1)

def extract_trace_details(trace_id):
    """Extract all details from a trace"""
    
    api_key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
    if not api_key:
        print("Error: API key not set")
        return
    
    try:
        client = Client()
        
        # Get the main run
        print(f"\n{'='*80}")
        print(f"EXTRACTING TRACE: {trace_id}")
        print(f"{'='*80}")
        
        run = client.read_run(trace_id)
        
        print(f"\nMain Run Details:")
        print(f"- Name: {run.name}")
        print(f"- Type: {run.run_type}")
        print(f"- Status: {run.status}")
        print(f"- Start: {run.start_time}")
        print(f"- Project: {run.session_id}")
        
        # Show full inputs
        print(f"\n{'='*60}")
        print("FULL INPUTS:")
        print(f"{'='*60}")
        if run.inputs:
            print(json.dumps(run.inputs, indent=2, default=str))
        else:
            print("No inputs found")
            
        # Show full outputs
        print(f"\n{'='*60}")
        print("FULL OUTPUTS:")
        print(f"{'='*60}")
        if run.outputs:
            print(json.dumps(run.outputs, indent=2, default=str))
        else:
            print("No outputs found")
        
        # Get ALL child runs
        print(f"\n{'='*60}")
        print("ALL CHILD RUNS (in order):")
        print(f"{'='*60}")
        
        # Use the correct project name
        project_name = os.getenv("LANGCHAIN_PROJECT", "ghl-langgraph-migration")
        
        child_runs = list(client.list_runs(
            project_name=project_name,
            filter=f'eq(parent_run_id, "{trace_id}")',
            limit=200  # Get more runs
        ))
        
        # Sort by start time
        child_runs.sort(key=lambda x: x.start_time)
        
        # Track important events
        conversation_events = []
        
        for i, child in enumerate(child_runs):
            print(f"\n{i+1}. {child.name} ({child.run_type})")
            print(f"   Start: {child.start_time}")
            print(f"   Status: {child.status}")
            
            # Show inputs if interesting
            if child.inputs and any(key in str(child.inputs).lower() for key in ["challenge", "question", "answer", "customer"]):
                print(f"   Inputs Preview: {str(child.inputs)[:200]}...")
                
            # Show outputs for LLM calls
            if child.run_type == "llm" and child.outputs:
                try:
                    content = ""
                    if "generations" in child.outputs:
                        gen = child.outputs["generations"][0][0]
                        if "text" in gen:
                            content = gen["text"]
                        elif "message" in gen and "content" in gen["message"]:
                            content = gen["message"]["content"]
                    
                    if content:
                        print(f"   OUTPUT: {content[:300]}...")
                        
                        # Track if this mentions challenge
                        if any(word in content.lower() for word in ["challenge", "question", "secret"]):
                            conversation_events.append({
                                "type": "challenge_mention",
                                "time": child.start_time,
                                "content": content[:500]
                            })
                except:
                    pass
                    
            # Look for tool calls
            if child.run_type == "tool" and child.name:
                print(f"   Tool: {child.name}")
                if child.outputs:
                    print(f"   Output: {str(child.outputs)[:200]}...")
                    
        # Summary of findings
        print(f"\n{'='*60}")
        print("CHALLENGE-RELATED EVENTS:")
        print(f"{'='*60}")
        for event in conversation_events:
            print(f"\n[{event['time'].strftime('%H:%M:%S')}] {event['type']}")
            print(f"{event['content']}")
            
        # Look for state updates
        print(f"\n{'='*60}")
        print("SEARCHING FOR STATE UPDATES:")
        print(f"{'='*60}")
        
        # Check for conversation analyzer or state updates
        for child in child_runs:
            if any(term in child.name.lower() for term in ["analyze", "state", "update", "conversation"]):
                print(f"\nFound: {child.name}")
                if child.inputs:
                    print("Inputs:")
                    print(json.dumps(child.inputs, indent=2, default=str)[:500])
                if child.outputs:
                    print("Outputs:")
                    print(json.dumps(child.outputs, indent=2, default=str)[:500])
                    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

# Analyze both traces
trace_ids = [
    "1f064982-efbc-6aba-9b85-f3b5227b2c2b",
    "1f064974-3f93-6d5e-a756-1dd912bc6798"
]

for trace_id in trace_ids:
    extract_trace_details(trace_id)
#!/usr/bin/env python3
"""
Extract detailed information from LangSmith traces
"""
import sys
import os
import json
from datetime import datetime

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
        project_name = os.getenv("LANGSMITH_PROJECT", os.getenv("LANGCHAIN_PROJECT", "ghl-langgraph-agent"))
        
        child_runs = list(client.list_runs(
            project_name=project_name,
            filter=f'eq(parent_run_id, "{trace_id}")',
            limit=200  # Get more runs
        ))
        
        # Sort by start time
        child_runs.sort(key=lambda x: x.start_time)
        
        # Track important events
        conversation_events = []
        contact_id_events = []
        get_conversations_calls = []
        
        for i, child in enumerate(child_runs):
            print(f"\n{i+1}. {child.name} ({child.run_type})")
            print(f"   Start: {child.start_time}")
            print(f"   Status: {child.status}")
            
            # Look for contact ID usage
            if child.inputs and "contact_id" in str(child.inputs):
                contact_id_events.append({
                    "node": child.name,
                    "time": child.start_time,
                    "inputs": str(child.inputs)[:500]
                })
                print(f"   ⚠️  CONTACT ID FOUND: {str(child.inputs)[:200]}...")
            
            # Look for get_conversations calls
            if "get_conversations" in child.name.lower():
                get_conversations_calls.append({
                    "time": child.start_time,
                    "inputs": child.inputs,
                    "outputs": child.outputs,
                    "status": child.status
                })
                print(f"   📞 GET_CONVERSATIONS CALL")
                
            # Show inputs if interesting
            if child.inputs and any(key in str(child.inputs).lower() for key in ["challenge", "question", "answer", "customer", "receptionist"]):
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
                    
        # Summary of contact ID usage
        print(f"\n{'='*60}")
        print("CONTACT ID USAGE:")
        print(f"{'='*60}")
        if contact_id_events:
            for event in contact_id_events:
                print(f"\n[{event['time'].strftime('%H:%M:%S')}] in {event['node']}")
                print(f"Inputs: {event['inputs']}")
        else:
            print("No contact_id found in any inputs!")
            
        # Summary of get_conversations calls
        print(f"\n{'='*60}")
        print("GET_CONVERSATIONS CALLS:")
        print(f"{'='*60}")
        if get_conversations_calls:
            for call in get_conversations_calls:
                print(f"\n[{call['time'].strftime('%H:%M:%S')}] Status: {call['status']}")
                if call['inputs']:
                    print(f"Inputs: {json.dumps(call['inputs'], indent=2, default=str)[:500]}")
                if call['outputs']:
                    print(f"Outputs: {json.dumps(call['outputs'], indent=2, default=str)[:500]}")
        else:
            print("No get_conversations calls found!")
        
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

# Analyze the specific trace
if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--trace-id" and len(sys.argv) > 2:
            trace_id = sys.argv[2]
        else:
            # Direct trace ID as argument
            trace_id = sys.argv[1]
    else:
        # Default trace ID
        trace_id = "1f064b62-61bc-6f2d-9273-668c50712976"
    extract_trace_details(trace_id)
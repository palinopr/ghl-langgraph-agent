#!/usr/bin/env python3
"""Debug receptionist message processing issue"""

import os
import sys
from datetime import datetime
from langsmith import Client
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

def debug_receptionist_trace(trace_id):
    """Debug specific receptionist behavior in trace"""
    client = Client()
    
    print(f"\n{'='*80}")
    print(f"Debugging Receptionist Issue in Trace: {trace_id}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")
    
    try:
        # Get the main run
        run = client.read_run(trace_id)
        
        print("MAIN RUN DETAILS:")
        print(f"Status: {run.status}")
        print(f"Name: {run.name}")
        
        # Check input state
        print("\nINPUT STATE:")
        if run.inputs:
            messages = run.inputs.get('messages', [])
            print(f"Input messages count: {len(messages)}")
            for i, msg in enumerate(messages):
                if isinstance(msg, dict):
                    print(f"  Message {i+1}: {msg.get('role', 'unknown')} - {msg.get('content', '')}")
            
            print(f"\nContact ID: {run.inputs.get('contact_id')}")
            print(f"Thread ID from input: {run.inputs.get('thread_id', 'Not set')}")
        
        # Check output state
        print("\nOUTPUT STATE:")
        if run.outputs:
            messages = run.outputs.get('messages', [])
            print(f"Output messages count: {len(messages)}")
            for i, msg in enumerate(messages):
                if isinstance(msg, dict):
                    print(f"  Message {i+1}: {msg.get('role', 'unknown')} - {msg.get('content', '')}")
            
            print(f"\nThread ID in output: {run.outputs.get('thread_id')}")
            print(f"Thread message count: {run.outputs.get('thread_message_count')}")
            print(f"Is first contact: {run.outputs.get('is_first_contact')}")
            print(f"Receptionist complete: {run.outputs.get('receptionist_complete')}")
            print(f"Next agent: {run.outputs.get('next_agent')}")
            print(f"Agent task: {run.outputs.get('agent_task')}")
        
        # Look for logs/events
        print("\n" + "="*40 + " EXECUTION FLOW " + "="*40)
        
        # Try to get events/feedback
        try:
            # Get feedback or events
            print("\nChecking for run events/feedback...")
            
            # Look at run extras
            if hasattr(run, 'extra') and run.extra:
                print(f"\nRun extras: {json.dumps(run.extra, indent=2)[:500]}")
            
            # Look at run events
            if hasattr(run, 'events') and run.events:
                print(f"\nRun events: {run.events[:5]}")
                
        except Exception as e:
            print(f"Could not get events: {e}")
        
        # Analyze the problem
        print("\n" + "="*40 + " ANALYSIS " + "="*40)
        print("\nKey Issues Identified:")
        
        # Check if message was processed
        input_messages = run.inputs.get('messages', []) if run.inputs else []
        output_messages = run.outputs.get('messages', []) if run.outputs else []
        
        print(f"1. Input had {len(input_messages)} messages")
        print(f"2. Output has {len(output_messages)} messages")
        print(f"3. Messages {'were' if len(input_messages) == len(output_messages) else 'were NOT'} preserved")
        
        # Check thread mapping
        thread_id = run.outputs.get('thread_id') if run.outputs else None
        contact_id = run.inputs.get('contact_id') if run.inputs else None
        expected_thread = f"contact-{contact_id}" if contact_id else None
        
        print(f"\n4. Thread ID mapping:")
        print(f"   - Contact ID: {contact_id}")
        print(f"   - Expected thread: {expected_thread}")
        print(f"   - Actual thread: {thread_id}")
        print(f"   - Mapping {'correct' if thread_id == expected_thread else 'INCORRECT'}")
        
        # Check receptionist completion
        receptionist_complete = run.outputs.get('receptionist_complete', False) if run.outputs else False
        next_agent = run.outputs.get('next_agent') if run.outputs else None
        
        print(f"\n5. Workflow continuation:")
        print(f"   - Receptionist marked complete: {receptionist_complete}")
        print(f"   - Next agent selected: {next_agent}")
        print(f"   - Should continue: {'YES' if receptionist_complete and next_agent else 'NO'}")
        
    except Exception as e:
        print(f"Error analyzing trace: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    trace_id = "1f067eb0-decd-6fa0-bd20-0b503c8fd356"
    if len(sys.argv) > 1:
        trace_id = sys.argv[1]
    
    debug_receptionist_trace(trace_id)
#!/usr/bin/env python3
"""
Analyze the traces where customer said "Jaime" and no response was sent
"""
import os
import json
from langsmith import Client
from datetime import datetime

# The trace IDs to analyze
TRACE_IDS = [
    "1f064b9a-6c3e-6b6a-85c8-9fbb6bb359dd",
    "1f064b62-61bc-6f2d-9273-668c50712976"
]

# Set API key
os.environ["LANGSMITH_API_KEY"] = "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"

def analyze_trace(trace_id):
    """Analyze a single trace to understand why no response was sent"""
    
    print(f"\n{'='*80}")
    print(f"ANALYZING TRACE: {trace_id}")
    print(f"{'='*80}")
    
    try:
        client = Client()
        
        # Get the main run
        run = client.read_run(trace_id)
        
        print(f"\nMain Run Details:")
        print(f"- Name: {run.name}")
        print(f"- Type: {run.run_type}")
        print(f"- Status: {run.status}")
        print(f"- Start: {run.start_time}")
        print(f"- End: {run.end_time}")
        
        # Show inputs to see the customer message
        print(f"\n{'='*60}")
        print("WEBHOOK INPUT (Customer Message):")
        print(f"{'='*60}")
        if run.inputs:
            inputs_str = json.dumps(run.inputs, indent=2, default=str)
            # Look for "Jaime" in the inputs
            if "jaime" in inputs_str.lower():
                print("✅ Found 'Jaime' in inputs!")
            print(inputs_str[:1000])
        
        # Get child runs
        try:
            project_id = run.session_id
            child_runs = list(client.list_runs(
                project_id=project_id,
                filter=f'eq(parent_run_id, "{trace_id}")',
                limit=200
            ))
        except:
            child_runs = list(client.list_runs(
                filter=f'eq(parent_run_id, "{trace_id}")',
                limit=200
            ))
        
        # Sort by start time
        child_runs.sort(key=lambda x: x.start_time)
        
        print(f"\n{'='*60}")
        print(f"WORKFLOW EXECUTION ({len(child_runs)} steps):")
        print(f"{'='*60}")
        
        # Track key events
        receptionist_complete = False
        supervisor_decision = None
        agent_selected = None
        agent_response = None
        responder_executed = False
        messages_sent = 0
        
        for i, child in enumerate(child_runs):
            # Show node progression
            print(f"\n{i+1}. {child.name} ({child.run_type}) - {child.status}")
            
            # Receptionist check
            if "receptionist" in child.name.lower():
                receptionist_complete = child.status == "completed"
                if child.outputs and "receptionist_complete" in str(child.outputs):
                    print("   ✅ Receptionist completed data loading")
                    
            # Supervisor decision
            if "supervisor" in child.name.lower() and "brain" in child.name.lower():
                if child.outputs:
                    outputs_str = str(child.outputs)
                    if "next_agent" in outputs_str:
                        # Extract next_agent value
                        try:
                            if isinstance(child.outputs, dict):
                                agent_selected = child.outputs.get("next_agent")
                            print(f"   📋 Supervisor decision: Route to {agent_selected}")
                        except:
                            pass
                    if "should_end" in outputs_str:
                        print(f"   ⚠️  Should end flag found in supervisor output")
                        
            # Agent execution (maria, carlos, sofia)
            if child.name.lower() in ["maria", "carlos", "sofia"]:
                agent_selected = child.name.lower()
                print(f"   🤖 {agent_selected.capitalize()} agent executed")
                
                # Look for agent's response
                if child.outputs:
                    try:
                        # Check if agent generated a message
                        if "messages" in str(child.outputs) or "content" in str(child.outputs):
                            agent_response = "Generated response"
                            print(f"   💬 Agent generated a response")
                    except:
                        pass
                        
            # Responder check
            if "responder" in child.name.lower():
                responder_executed = True
                print(f"   📤 Responder executed")
                
                if child.outputs:
                    outputs_str = str(child.outputs)
                    if "messages_sent_count" in outputs_str:
                        try:
                            # Extract count
                            if isinstance(child.outputs, dict):
                                messages_sent = child.outputs.get("messages_sent_count", 0)
                            print(f"   📨 Messages sent: {messages_sent}")
                        except:
                            pass
                    
                    if "no_new_messages" in outputs_str:
                        print(f"   ⚠️  No new messages to send!")
                    
                    if "error" in outputs_str:
                        print(f"   ❌ Responder error found")
                        
            # Look for errors
            if child.error:
                print(f"   ❌ ERROR: {child.error}")
                
        # Summary
        print(f"\n{'='*60}")
        print("ANALYSIS SUMMARY:")
        print(f"{'='*60}")
        print(f"1. Customer said: 'Jaime' ✅")
        print(f"2. Receptionist completed: {receptionist_complete}")
        print(f"3. Supervisor selected: {agent_selected or 'NONE'}")
        print(f"4. Agent response generated: {agent_response or 'NO'}")
        print(f"5. Responder executed: {responder_executed}")
        print(f"6. Messages sent: {messages_sent}")
        
        # Diagnosis
        print(f"\n🔍 DIAGNOSIS:")
        if not receptionist_complete:
            print("❌ Receptionist failed to complete data loading")
        elif not agent_selected:
            print("❌ Supervisor failed to select an agent")
        elif not agent_response:
            print("❌ Agent didn't generate a response message")
        elif not responder_executed:
            print("❌ Responder wasn't executed")
        elif messages_sent == 0:
            print("❌ Responder executed but sent 0 messages")
            print("   Possible reasons:")
            print("   - Message was filtered as duplicate")
            print("   - No AI messages found in state")
            print("   - Agent message wasn't properly added to state")
        else:
            print("✅ Workflow completed successfully")
            
        # Show final outputs
        print(f"\n{'='*60}")
        print("FINAL OUTPUTS:")
        print(f"{'='*60}")
        if run.outputs:
            print(json.dumps(run.outputs, indent=2, default=str)[:1000])
            
    except Exception as e:
        print(f"Error analyzing trace {trace_id}: {e}")
        import traceback
        traceback.print_exc()

# Main execution
if __name__ == "__main__":
    for trace_id in TRACE_IDS:
        analyze_trace(trace_id)
        
    print(f"\n{'='*80}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*80}")
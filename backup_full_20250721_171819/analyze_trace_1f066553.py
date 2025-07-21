#!/usr/bin/env python3
"""
Analyze LangSmith trace using SDK
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

def format_message(msg):
    """Format a message for display"""
    if isinstance(msg, dict):
        if 'content' in msg:
            return msg['content']
        elif 'text' in msg:
            return msg['text']
        else:
            return str(msg)
    return str(msg)

def analyze_trace(trace_id):
    """Analyze a specific trace"""
    print(f"\n🔍 Analyzing trace: {trace_id}")
    print("=" * 80)
    
    try:
        # Get the main run
        run = client.read_run(trace_id)
        
        # Basic info
        print(f"\n📊 TRACE INFORMATION:")
        print(f"ID: {run.id}")
        print(f"Name: {run.name}")
        print(f"Status: {run.status}")
        print(f"Start: {run.start_time}")
        print(f"End: {run.end_time}")
        if run.end_time and run.start_time:
            duration = (run.end_time - run.start_time).total_seconds()
            print(f"Duration: {duration:.2f} seconds")
        
        # Check inputs
        print(f"\n📥 INPUTS:")
        if run.inputs:
            if 'messages' in run.inputs:
                messages = run.inputs['messages']
                if messages and len(messages) > 0:
                    for msg in messages:
                        content = format_message(msg)
                        print(f"  Message: {content}")
            else:
                print(json.dumps(run.inputs, indent=2)[:500])
        
        # Check outputs
        print(f"\n📤 OUTPUTS:")
        if run.outputs:
            print(json.dumps(run.outputs, indent=2)[:500])
        
        # Check for errors
        if run.error:
            print(f"\n❌ ERROR:")
            print(f"{run.error}")
        
        # Get child runs
        print(f"\n🔄 EXECUTION FLOW:")
        child_runs = list(client.list_runs(
            project_name="ghl-langgraph-agent",
            filter=f'eq(parent_run_id, "{trace_id}")',
            execution_order=1
        ))
        
        if child_runs:
            print(f"Found {len(child_runs)} child runs:")
            for i, child in enumerate(child_runs):
                print(f"\n  {i+1}. {child.name}")
                print(f"     Status: {child.status}")
                if child.error:
                    print(f"     ❌ Error: {child.error}")
                
                # Check for specific node outputs
                if "intelligence" in child.name.lower():
                    print(f"     🧠 Intelligence Analysis:")
                    if child.outputs:
                        if 'lead_score' in child.outputs:
                            print(f"        Score: {child.outputs['lead_score']}")
                        if 'extracted_data' in child.outputs:
                            print(f"        Extracted: {child.outputs['extracted_data']}")
                
                elif "supervisor" in child.name.lower():
                    print(f"     🎯 Supervisor Decision:")
                    if child.outputs:
                        if 'next_agent' in child.outputs:
                            print(f"        Route to: {child.outputs['next_agent']}")
                        if 'lead_score' in child.outputs:
                            print(f"        Score: {child.outputs['lead_score']}")
                
                elif any(agent in child.name.lower() for agent in ["maria", "carlos", "sofia"]):
                    print(f"     💬 Agent Response:")
                    if child.outputs and 'messages' in child.outputs:
                        for msg in child.outputs['messages'][-1:]:  # Last message
                            if hasattr(msg, 'content'):
                                print(f"        {msg.content[:100]}...")
                
                # Get inputs/outputs summary
                if child.inputs:
                    input_keys = list(child.inputs.keys())
                    print(f"     Inputs: {', '.join(input_keys[:5])}")
                if child.outputs:
                    output_keys = list(child.outputs.keys())
                    print(f"     Outputs: {', '.join(output_keys[:5])}")
        
        # Check for specific issues
        print(f"\n🔍 CHECKING FOR KNOWN ISSUES:")
        
        # Check conversation history
        history_loaded = False
        for child in child_runs:
            if "receptionist" in child.name.lower() and child.outputs:
                if 'conversation_history' in child.outputs:
                    history = child.outputs['conversation_history']
                    if history and len(history) > 0:
                        history_loaded = True
                        print(f"✓ Conversation history loaded: {len(history)} messages")
                    else:
                        print(f"⚠️  No conversation history loaded")
        
        if not history_loaded:
            print(f"✓ No old conversation history (good!)")
        
        # Check for debug messages
        debug_found = False
        for child in child_runs:
            if child.outputs and 'messages' in child.outputs:
                for msg in child.outputs['messages']:
                    if hasattr(msg, 'content'):
                        content = msg.content.lower()
                        if any(pattern in content for pattern in ['lead scored', 'routing to', 'debug:']):
                            debug_found = True
                            print(f"⚠️  Debug message found: {msg.content[:50]}...")
        
        if not debug_found:
            print(f"✓ No debug messages in output")
        
        # Check score
        final_score = None
        for child in child_runs:
            if child.outputs and 'lead_score' in child.outputs:
                final_score = child.outputs['lead_score']
        
        if final_score:
            print(f"\n📊 Final Score: {final_score}/10")
            if final_score > 2 and "hola" in str(run.inputs).lower():
                print(f"⚠️  Score too high for 'hola'")
            else:
                print(f"✓ Score seems appropriate")
        
    except Exception as e:
        print(f"\n❌ Error analyzing trace: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_trace(trace_id)
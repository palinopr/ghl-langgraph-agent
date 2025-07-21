#!/usr/bin/env python3
"""
Check what the conversation enforcer is telling agents to say
"""
import os
from langsmith import Client
import json

# Set API key
os.environ["LANGSMITH_API_KEY"] = "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"

def get_child_runs_by_node(trace_id, node_name):
    """Get child runs for a specific node"""
    client = Client()
    
    child_runs = list(client.list_runs(
        project_name="ghl-langgraph-agent",
        filter=f'eq(parent_run_id, "{trace_id}")',
        limit=50
    ))
    
    for child in child_runs:
        if child.name == node_name:
            return child
    
    return None

def analyze_maria_decision(trace_id):
    """Analyze what Maria agent was told to do"""
    client = Client()
    
    # Get Maria's run
    maria_run = get_child_runs_by_node(trace_id, "maria")
    
    if not maria_run:
        return {"error": "Maria node not found"}
    
    # Look for conversation enforcer data in inputs
    enforcer_data = None
    if maria_run.inputs:
        # The enforcer data might be in the prompt or state
        input_str = str(maria_run.inputs)
        
        # Extract allowed response
        if "ALLOWED RESPONSE:" in input_str:
            start = input_str.find("ALLOWED RESPONSE:") + len("ALLOWED RESPONSE:")
            end = input_str.find('"', start + 2)
            if end > start:
                allowed_response = input_str[start:end].strip().strip('"')
                enforcer_data = {"allowed_response": allowed_response}
    
    return {
        "trace_id": trace_id,
        "maria_inputs": maria_run.inputs if maria_run else None,
        "maria_outputs": maria_run.outputs if maria_run else None,
        "enforcer_data": enforcer_data
    }

def main():
    """Check conversation enforcer behavior"""
    print("🔍 Conversation Enforcer Analysis")
    print("=" * 80)
    
    trace_ids = [
        ("1f0665dd-9068-66a3-84bb-26a8a0c201a5", "Hola"),
        ("1f0665de-65c0-649d-88fc-17a24f9ca734", "jaime"),
        ("1f0665df-46f9-6d57-889b-74d1726b4a41", "tengo un restaurante")
    ]
    
    for trace_id, message in trace_ids:
        print(f"\n{'='*80}")
        print(f"MESSAGE: '{message}'")
        print(f"TRACE: {trace_id}")
        print(f"{'='*80}")
        
        analysis = analyze_maria_decision(trace_id)
        
        if "error" in analysis:
            print(f"❌ Error: {analysis['error']}")
            continue
        
        # Check if Maria got extracted data
        if analysis['maria_inputs'] and 'extracted_data' in str(analysis['maria_inputs']):
            print("✅ Maria received extracted_data")
            
            # Try to extract the data
            input_str = str(analysis['maria_inputs'])
            if "'extracted_data':" in input_str:
                start = input_str.find("'extracted_data':") + len("'extracted_data':")
                # Find the matching closing brace
                brace_count = 0
                i = start
                while i < len(input_str):
                    if input_str[i] == '{':
                        brace_count += 1
                    elif input_str[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            extracted_str = input_str[start:i+1]
                            print(f"   Extracted data: {extracted_str[:100]}...")
                            break
                    i += 1
        
        # Check enforcer data
        if analysis['enforcer_data']:
            print(f"\n📝 ENFORCER TOLD MARIA TO SAY:")
            print(f"   '{analysis['enforcer_data']['allowed_response']}'")
        
        # Check what Maria actually said
        if analysis['maria_outputs'] and isinstance(analysis['maria_outputs'], dict):
            if 'messages' in analysis['maria_outputs']:
                msgs = analysis['maria_outputs']['messages']
                if isinstance(msgs, list) and msgs:
                    last_msg = msgs[-1]
                    if isinstance(last_msg, dict):
                        actual_response = last_msg.get('content', '')
                        print(f"\n🤖 MARIA ACTUALLY SAID:")
                        print(f"   '{actual_response}'")
                        
                        # Check if it matches
                        if analysis['enforcer_data'] and analysis['enforcer_data']['allowed_response'] in actual_response:
                            print(f"\n✅ Maria followed the enforcer's instruction")
                        else:
                            print(f"\n❌ Maria did NOT follow the enforcer exactly")

if __name__ == "__main__":
    main()
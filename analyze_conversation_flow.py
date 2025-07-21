#!/usr/bin/env python3
"""
Analyze the conversation flow to see if agents are properly using extracted data
"""
import os
from datetime import datetime
from langsmith import Client
import json

# Set API key
os.environ["LANGSMITH_API_KEY"] = "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"

def get_full_conversation(trace_id):
    """Get the full conversation including all previous messages"""
    client = Client()
    run = client.read_run(trace_id)
    
    messages = []
    if run.inputs and 'messages' in run.inputs:
        for msg in run.inputs['messages']:
            if isinstance(msg, dict):
                role = msg.get('type', msg.get('role', 'unknown'))
                content = msg.get('content', '')
                messages.append({"role": role, "content": content})
    
    return messages

def analyze_agent_response_correctness(trace_id):
    """Check if agent response is correct given the extracted data"""
    client = Client()
    
    try:
        run = client.read_run(trace_id)
        
        # Get extracted data
        extracted_data = None
        if run.outputs and isinstance(run.outputs, dict):
            extracted_data = run.outputs.get("extracted_data", {})
        
        # Get the agent's response
        agent_response = None
        if run.outputs and isinstance(run.outputs, dict):
            if "messages" in run.outputs:
                msgs = run.outputs["messages"]
                if isinstance(msgs, list) and len(msgs) > 0:
                    last_msg = msgs[-1]
                    if isinstance(last_msg, dict):
                        agent_response = last_msg.get("content", "")
        
        # Get current message
        current_message = None
        if run.inputs and 'messages' in run.inputs:
            msgs = run.inputs['messages']
            if msgs and len(msgs) > 0:
                last_msg = msgs[-1]
                if isinstance(last_msg, dict):
                    current_message = last_msg.get('content', '')
        
        return {
            "trace_id": trace_id,
            "current_message": current_message,
            "extracted_data": extracted_data,
            "agent_response": agent_response,
            "full_conversation": get_full_conversation(trace_id)
        }
        
    except Exception as e:
        return {"trace_id": trace_id, "error": str(e)}

def main():
    """Analyze the conversation flow"""
    print("🔍 Conversation Flow Analysis")
    print("=" * 80)
    
    trace_ids = [
        "1f0665dd-9068-66a3-84bb-26a8a0c201a5",  # "Hola"
        "1f0665de-65c0-649d-88fc-17a24f9ca734",  # "jaime"
        "1f0665df-46f9-6d57-889b-74d1726b4a41"   # "tengo un restaurante"
    ]
    
    for i, trace_id in enumerate(trace_ids, 1):
        print(f"\n{'='*80}")
        print(f"TRACE {i}: {trace_id}")
        print(f"{'='*80}")
        
        analysis = analyze_agent_response_correctness(trace_id)
        
        if "error" in analysis:
            print(f"❌ Error: {analysis['error']}")
            continue
        
        print(f"\n📨 CURRENT MESSAGE: '{analysis['current_message']}'")
        
        print(f"\n📊 EXTRACTED DATA:")
        if analysis['extracted_data']:
            for key, value in analysis['extracted_data'].items():
                if value is not None:
                    print(f"   {key}: {value}")
        
        print(f"\n🤖 AGENT RESPONSE:")
        print(f"   {analysis['agent_response']}")
        
        print(f"\n💬 FULL CONVERSATION CONTEXT:")
        for j, msg in enumerate(analysis['full_conversation']):
            prefix = "Customer:" if msg['role'] == 'human' else "AI:"
            print(f"   {j+1}. {prefix} {msg['content']}")
        
        # Analyze correctness
        print(f"\n✅ ANALYSIS:")
        
        extracted = analysis['extracted_data'] or {}
        response = analysis['agent_response'] or ""
        
        # Check if name was asked when already known
        if "¿Cuál es tu nombre?" in response and extracted.get('name'):
            print(f"   ❌ ERROR: Asked for name when already extracted: {extracted.get('name')}")
        elif "Mucho gusto" in response and analysis['current_message'].lower() in ['hola', 'hi', 'buenas']:
            print(f"   ❌ ERROR: Said 'Mucho gusto' to a greeting, not a name")
        elif "Mucho gusto" in response and extracted.get('name'):
            print(f"   ✅ CORRECT: Acknowledged name: {extracted.get('name')}")
        elif "¿Cuál es tu nombre?" in response and not extracted.get('name'):
            print(f"   ✅ CORRECT: Asked for name (not extracted)")
        
        # Check if business was asked when already known
        if "¿Qué tipo de negocio" in response and extracted.get('business_type'):
            print(f"   ❌ ERROR: Asked for business when already extracted: {extracted.get('business_type')}")
        elif "¿Qué tipo de negocio" in response and not extracted.get('business_type'):
            print(f"   ✅ CORRECT: Asked for business (not extracted)")
        
        # Check if agent acknowledged extracted business
        if extracted.get('business_type') and extracted['business_type'] != 'negocio':
            if extracted['business_type'] in response.lower():
                print(f"   ✅ CORRECT: Acknowledged business type: {extracted['business_type']}")
            else:
                print(f"   ⚠️  WARNING: Did not acknowledge business type: {extracted['business_type']}")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Analyze conversation context across multiple traces
"""
import os
from langsmith import Client
from datetime import datetime
import json

# Set API key
os.environ["LANGSMITH_API_KEY"] = "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"

# Initialize client
client = Client()

# Trace IDs to analyze (in order)
TRACE_IDS = [
    "1f067450-f248-6c65-ad62-5b003dd1b02a",  # First message
    "1f067452-0dda-61cc-bd5a-b380392345a3",  # Second message
    "1f067457-2c04-6467-a9a8-13cdc906c098"   # Third message
]

def extract_conversation_context(trace_id: str):
    """Extract conversation context from a trace"""
    print(f"\n{'='*70}")
    print(f"TRACE: {trace_id}")
    print(f"{'='*70}")
    
    try:
        # Get the main run
        run = client.read_run(trace_id)
        
        print(f"\nTime: {run.start_time}")
        
        # Get inputs
        if run.inputs:
            print(f"\n📥 INPUTS:")
            if 'messages' in run.inputs:
                messages = run.inputs['messages']
                print(f"  - Message count: {len(messages)}")
                for i, msg in enumerate(messages):
                    role = msg.get('role', msg.get('type', 'unknown'))
                    content = msg.get('content', '')
                    print(f"  - [{i}] {role}: {content[:100]}...")
            
            # Check other important fields
            for key in ['contact_id', 'conversation_id', 'thread_id']:
                if key in run.inputs:
                    print(f"  - {key}: {run.inputs[key]}")
        
        # Get child runs to see the flow
        child_runs = list(client.list_runs(parent_run_id=trace_id))
        
        # Look for receptionist to see what message was processed
        receptionist_run = None
        maria_run = None
        responder_run = None
        
        for child in child_runs:
            if "receptionist" in child.name.lower():
                receptionist_run = child
            elif "maria" in child.name.lower():
                maria_run = child
            elif "responder" in child.name.lower():
                responder_run = child
        
        # Check receptionist
        if receptionist_run and receptionist_run.outputs:
            print(f"\n📋 RECEPTIONIST OUTPUT:")
            for key, value in receptionist_run.outputs.items():
                if key == "messages" and isinstance(value, list):
                    print(f"  - {key}: {len(value)} messages")
                    for i, msg in enumerate(value[-3:]):  # Last 3 messages
                        if isinstance(msg, dict):
                            role = msg.get('type', 'unknown')
                            content = msg.get('content', '')
                            print(f"    [{i}] {role}: {content[:80]}...")
                else:
                    print(f"  - {key}: {value}")
        
        # Check Maria's input/output
        if maria_run:
            print(f"\n🤖 MARIA AGENT:")
            if maria_run.inputs and 'messages' in maria_run.inputs:
                print(f"  - Input messages: {len(maria_run.inputs['messages'])}")
            if maria_run.outputs and 'messages' in maria_run.outputs:
                print(f"  - Output messages: {len(maria_run.outputs['messages'])}")
                # Get Maria's response
                for msg in maria_run.outputs['messages'][-1:]:
                    if hasattr(msg, 'content'):
                        print(f"  - Response: {msg.content[:100]}...")
                    elif isinstance(msg, dict) and 'content' in msg:
                        print(f"  - Response: {msg['content'][:100]}...")
        
        # Check final response
        if responder_run and responder_run.outputs:
            print(f"\n📤 RESPONDER OUTPUT:")
            if 'last_sent_message' in responder_run.outputs:
                print(f"  - Message sent: {responder_run.outputs['last_sent_message'][:100]}...")
        
        # Check for conversation history loading
        print(f"\n🔍 CONTEXT CHECK:")
        
        # Look for any signs of previous conversation
        all_messages = []
        if run.inputs and 'messages' in run.inputs:
            all_messages = run.inputs['messages']
        
        human_messages = [m for m in all_messages if m.get('role') == 'human' or m.get('type') == 'human']
        ai_messages = [m for m in all_messages if m.get('role') == 'ai' or m.get('type') == 'ai']
        
        print(f"  - Total messages in input: {len(all_messages)}")
        print(f"  - Human messages: {len(human_messages)}")
        print(f"  - AI messages: {len(ai_messages)}")
        
        if len(all_messages) > 1:
            print(f"  - ✅ Conversation history present!")
        else:
            print(f"  - ❌ No conversation history - only current message")
            
    except Exception as e:
        print(f"Error analyzing trace: {e}")

def main():
    """Main function"""
    print("Analyzing conversation context across traces...")
    print("="*70)
    
    # Analyze each trace
    for i, trace_id in enumerate(TRACE_IDS):
        print(f"\n\n{'*'*30} MESSAGE {i+1} {'*'*30}")
        extract_conversation_context(trace_id)
    
    print("\n\n" + "="*70)
    print("CONTEXT ANALYSIS SUMMARY")
    print("="*70)
    
    print("\n❓ KEY QUESTIONS:")
    print("1. Is conversation history being loaded from previous messages?")
    print("2. Are thread IDs consistent across messages?")
    print("3. Is the receptionist adding previous messages to state?")
    print("4. Is Maria seeing the conversation history?")
    
    print("\n💡 LIKELY ISSUE:")
    print("The webhook handler is NOT loading conversation history from the database.")
    print("Each message is being processed as a new conversation without context.")

if __name__ == "__main__":
    main()
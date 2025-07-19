#!/usr/bin/env python3
"""
Analyze the fetched trace to look for repeated questions from Maria
"""

import json
from datetime import datetime

# Load the trace data
with open('trace_1f064e45_raw.json', 'r') as f:
    trace_data = json.load(f)

print("=== ANALYZING TRACE FOR REPEATED QUESTIONS ===\n")

# Extract messages from outputs
if 'outputs' in trace_data and 'messages' in trace_data['outputs']:
    messages = trace_data['outputs']['messages']
    
    print(f"Total messages in conversation: {len(messages)}\n")
    
    # Track Maria's questions
    maria_questions = []
    user_responses = []
    
    print("=== CONVERSATION FLOW ===\n")
    
    for i, msg in enumerate(messages):
        role = msg.get('type', 'unknown')
        content = msg.get('content', '')
        timestamp = msg.get('additional_kwargs', {}).get('timestamp', 'N/A')
        msg_id = msg.get('id', 'N/A')
        source = msg.get('additional_kwargs', {}).get('source', 'new')
        
        print(f"[{i}] {role.upper()} ({source}) - {timestamp}")
        print(f"    ID: {msg_id}")
        print(f"    Content: {content}")
        print()
        
        # Track AI (Maria) messages
        if role == 'ai':
            maria_questions.append({
                'index': i,
                'content': content,
                'timestamp': timestamp
            })
        elif role == 'human':
            user_responses.append({
                'index': i,
                'content': content,
                'timestamp': timestamp
            })
    
    # Analyze for repeated questions
    print("\n=== MARIA'S QUESTIONS ANALYSIS ===\n")
    
    business_type_questions = []
    
    for q in maria_questions:
        content_lower = q['content'].lower()
        if any(phrase in content_lower for phrase in ['tipo de negocio', 'qué tipo de negocio', 'que tipo de negocio']):
            business_type_questions.append(q)
    
    print(f"Maria asked about business type {len(business_type_questions)} time(s)")
    
    if business_type_questions:
        print("\nBusiness type questions:")
        for q in business_type_questions:
            print(f"  - [{q['index']}] {q['content']}")
    
    # Check if user already answered
    print("\n=== USER RESPONSES ===\n")
    
    for resp in user_responses:
        print(f"[{resp['index']}] {resp['content']}")
        if resp['content'].lower() in ['restaurante', 'restaurant']:
            print("  ^ User provided business type: RESTAURANTE")
    
    # Look for the issue pattern
    print("\n=== ISSUE ANALYSIS ===\n")
    
    # Find if Maria asks about business type after user already said "Restaurante"
    user_said_restaurante = False
    
    for msg in messages:
        if msg.get('type') == 'human' and msg.get('content', '').lower() == 'restaurante':
            user_said_restaurante = True
            print(f"✓ User said 'Restaurante' at message index {messages.index(msg)}")
        
        if user_said_restaurante and msg.get('type') == 'ai':
            content_lower = msg.get('content', '').lower()
            if 'tipo de negocio' in content_lower:
                print(f"\n❌ ISSUE FOUND: Maria asked about business type AFTER user already said 'Restaurante'")
                print(f"   Message: {msg.get('content')}")
                print(f"   This indicates the duplicate question issue is still present!")
                break
    else:
        if user_said_restaurante:
            print("\n✓ No repeated business type questions found after user said 'Restaurante'")

# Also check the trace inputs
print("\n=== TRACE INPUTS ===")
if 'inputs' in trace_data:
    print(json.dumps(trace_data['inputs'], indent=2))
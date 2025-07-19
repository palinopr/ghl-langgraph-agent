#!/usr/bin/env python3
"""
Analyze and compare two traces that keep asking the same questions
Trace 1: 1f064e15-6490-676d-8106-7ccb4cea9fa0
Trace 2: 1f064e14-c10f-6c1d-bea0-0d98f490dc85
"""
import os
import json
import httpx
from datetime import datetime
import asyncio

# Load environment
from dotenv import load_dotenv
load_dotenv()

TRACE_IDS = [
    "1f064e15-6490-676d-8106-7ccb4cea9fa0",
    "1f064e14-c10f-6c1d-bea0-0d98f490dc85"
]

LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")

async def fetch_trace(trace_id):
    """Fetch trace details from LangSmith"""
    headers = {
        "x-api-key": LANGSMITH_API_KEY,
        "Content-Type": "application/json"
    }
    
    url = f"https://api.smith.langchain.com/runs/{trace_id}"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, timeout=30.0)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching trace {trace_id}: {response.status_code}")
            return None

def extract_messages(trace_data):
    """Extract all messages from the trace"""
    messages = []
    
    # Get messages from outputs
    outputs = trace_data.get('outputs', {})
    output_messages = outputs.get('messages', [])
    
    for msg in output_messages:
        msg_type = msg.get('type', 'unknown')
        content = msg.get('content', '')
        timestamp = msg.get('additional_kwargs', {}).get('timestamp', '')
        
        messages.append({
            'type': msg_type,
            'content': content,
            'timestamp': timestamp,
            'source': msg.get('additional_kwargs', {}).get('source', 'new')
        })
    
    return messages

def analyze_conversation_flow(messages):
    """Analyze the conversation flow"""
    questions_asked = []
    responses_given = []
    
    for i, msg in enumerate(messages):
        if msg['type'] == 'ai':
            # Check for common questions
            content = msg['content'].lower()
            if '¿cuál es tu nombre?' in content or "what's your name?" in content:
                questions_asked.append(('name', i, msg['content'][:50]))
            elif '¿qué tipo de negocio' in content or 'what type of business' in content:
                questions_asked.append(('business', i, msg['content'][:50]))
            elif '¿cuál es tu mayor desafío' in content or 'biggest challenge' in content:
                questions_asked.append(('problem', i, msg['content'][:50]))
            elif '$' in content and ('presupuesto' in content or 'budget' in content):
                questions_asked.append(('budget', i, msg['content'][:50]))
            elif 'email' in content or 'correo' in content:
                questions_asked.append(('email', i, msg['content'][:50]))
                
        elif msg['type'] == 'human':
            responses_given.append((i, msg['content'][:50]))
    
    return questions_asked, responses_given

async def analyze_traces():
    """Analyze both traces"""
    print("="*60)
    print("TRACE COMPARISON ANALYSIS")
    print("="*60)
    
    trace_results = []
    
    for trace_id in TRACE_IDS:
        print(f"\n📊 Analyzing trace: {trace_id}")
        trace_data = await fetch_trace(trace_id)
        
        if trace_data:
            # Basic info
            result = {
                'id': trace_id,
                'status': trace_data.get('status', 'N/A'),
                'start_time': trace_data.get('start_time', 'N/A'),
                'end_time': trace_data.get('end_time', 'N/A')
            }
            
            # Get inputs
            inputs = trace_data.get('inputs', {})
            webhook_data = inputs.get('webhook_data', {})
            result['contact_id'] = webhook_data.get('contactId', inputs.get('contact_id', 'N/A'))
            result['incoming_message'] = webhook_data.get('message', 'N/A')
            
            # Get outputs
            outputs = trace_data.get('outputs', {})
            result['lead_score'] = outputs.get('lead_score', 'N/A')
            result['current_agent'] = outputs.get('current_agent', 'N/A')
            
            # Extract messages
            messages = extract_messages(trace_data)
            result['total_messages'] = len(messages)
            
            # Analyze conversation
            questions, responses = analyze_conversation_flow(messages)
            result['questions_asked'] = questions
            result['responses_given'] = responses
            
            # Find the last AI response
            for msg in reversed(messages):
                if msg['type'] == 'ai' and not msg['content'].startswith('\n'):
                    result['last_ai_response'] = msg['content'][:100]
                    break
            
            trace_results.append(result)
            
            # Save full trace
            with open(f"trace_{trace_id[:8]}.json", "w") as f:
                json.dump(trace_data, f, indent=2)
    
    # Compare results
    print("\n" + "="*60)
    print("COMPARISON RESULTS")
    print("="*60)
    
    if len(trace_results) == 2:
        t1, t2 = trace_results[0], trace_results[1]
        
        print(f"\n📍 Trace 1: {t1['id'][:8]}...")
        print(f"   Contact: {t1['contact_id']}")
        print(f"   Message: '{t1['incoming_message']}'")
        print(f"   Lead Score: {t1['lead_score']}")
        print(f"   Agent: {t1['current_agent']}")
        print(f"   Last Response: {t1.get('last_ai_response', 'N/A')}")
        
        print(f"\n📍 Trace 2: {t2['id'][:8]}...")
        print(f"   Contact: {t2['contact_id']}")
        print(f"   Message: '{t2['incoming_message']}'")
        print(f"   Lead Score: {t2['lead_score']}")
        print(f"   Agent: {t2['current_agent']}")
        print(f"   Last Response: {t2.get('last_ai_response', 'N/A')}")
        
        # Check for repeated questions
        print("\n🔄 REPEATED QUESTIONS ANALYSIS:")
        
        # Compare questions asked
        t1_questions = [q[0] for q in t1['questions_asked']]
        t2_questions = [q[0] for q in t2['questions_asked']]
        
        print(f"\nTrace 1 asked about: {', '.join(t1_questions)}")
        print(f"Trace 2 asked about: {', '.join(t2_questions)}")
        
        # Find duplicates
        for q_type in ['name', 'business', 'problem', 'budget', 'email']:
            count1 = t1_questions.count(q_type)
            count2 = t2_questions.count(q_type)
            
            if count1 > 1:
                print(f"\n⚠️  Trace 1: Asked for '{q_type}' {count1} times!")
                for q in t1['questions_asked']:
                    if q[0] == q_type:
                        print(f"   - Message #{q[1]}: {q[2]}")
                        
            if count2 > 1:
                print(f"\n⚠️  Trace 2: Asked for '{q_type}' {count2} times!")
                for q in t2['questions_asked']:
                    if q[0] == q_type:
                        print(f"   - Message #{q[1]}: {q[2]}")
        
        # Check if same question in last response
        if t1.get('last_ai_response') == t2.get('last_ai_response'):
            print(f"\n❌ BOTH TRACES HAVE IDENTICAL LAST RESPONSE!")
            print(f"   '{t1.get('last_ai_response')}'")
        
        # Message history comparison
        print(f"\n📜 MESSAGE HISTORY:")
        print(f"Trace 1: {t1['total_messages']} messages")
        print(f"Trace 2: {t2['total_messages']} messages")

async def main():
    await analyze_traces()

if __name__ == "__main__":
    asyncio.run(main())
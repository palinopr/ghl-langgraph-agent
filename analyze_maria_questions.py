#!/usr/bin/env python3
"""
Analyze if Maria is still asking repeated questions
"""
import json

def analyze_maria_behavior(file_path):
    """Analyze Maria's responses to check for repeated questions"""
    
    print("\n" + "="*80)
    print("MARIA QUESTION ANALYSIS")
    print("="*80)
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Extract conversation history
    history_start = content.find('"conversation_history": [')
    if history_start == -1:
        print("ERROR: No conversation history found")
        return
    
    history_end = content.find(']', history_start + 25)
    history_section = content[history_start:history_end+1]
    
    # Parse messages
    messages = []
    for line in content.split('\n'):
        if '"body":' in line and ('"Hola"' in line or '"Jaime"' in line or 'nombre' in line or 'negocio' in line or 'Restaurante' in line):
            body_start = line.find('"body": "') + 9
            body_end = line.find('"', body_start)
            if body_start > 8 and body_end > body_start:
                body = line[body_start:body_end]
                messages.append(body)
    
    print("\nConversation Flow:")
    for i, msg in enumerate(messages):
        print(f"{i+1}. {msg}")
    
    # Check Maria's final response
    print("\n" + "-"*60)
    print("MARIA'S FINAL RESPONSE:")
    
    maria_response = None
    if '"name": "maria"' in content:
        # Find Maria's response
        maria_start = content.rfind('"name": "maria"')
        # Look backwards for the content
        search_area = content[max(0, maria_start-1000):maria_start]
        if '"content": "' in search_area:
            content_start = search_area.rfind('"content": "') + 12
            content_end = search_area.find('"', content_start)
            if content_end > content_start:
                maria_response = search_area[content_start:content_end]
    
    if maria_response:
        print(f"Response: {maria_response}")
        
        # Analysis
        print("\n" + "-"*60)
        print("ANALYSIS:")
        
        # Check what Maria asked about
        if "nombre" in maria_response.lower():
            print("❌ ISSUE: Maria is asking for the name again!")
            print("   The user already provided their name: Jaime")
        elif "negocio" in maria_response.lower() or "tipo de negocio" in maria_response.lower():
            print("✅ GOOD: Maria is asking about business type")
            print("   This is the correct next question after getting the name")
        else:
            print("🤔 UNCLEAR: Maria's response doesn't follow expected pattern")
        
        # Check supervisor detection
        print("\n" + "-"*60)
        print("SUPERVISOR DETECTION:")
        
        if '"Business: restaurante"' in content or '"business_type": "restaurante"' in content:
            print("✅ GOOD: Supervisor correctly detected 'restaurante' as business type")
        else:
            print("❌ ISSUE: Supervisor may not have detected the business type")
        
        # Check extracted data
        if '"extracted_data":' in content:
            data_start = content.find('"extracted_data":')
            data_end = content.find('}', data_start) + 1
            extracted = content[data_start:data_end]
            print(f"\nExtracted data section: {extracted}")
    else:
        print("ERROR: Could not find Maria's response")
    
    # Check lead score
    print("\n" + "-"*60)
    print("LEAD SCORE PROGRESSION:")
    
    if '"Previous Score: 2/10"' in content:
        print("Previous score: 2/10")
    if '"lead_score": 4' in content:
        print("New score: 4/10")
        print("✅ Score increased from 2 to 4 (business type provided)")

if __name__ == "__main__":
    analyze_maria_behavior("trace_analysis_1f064e83_v2.txt")
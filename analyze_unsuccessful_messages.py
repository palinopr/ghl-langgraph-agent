#!/usr/bin/env python3
"""
Analyze why messages are unsuccessful and mixed language
"""
import os
from langsmith import Client
from datetime import datetime, timedelta
import json

# Set up the client
os.environ["LANGSMITH_API_KEY"] = "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"
client = Client()

def analyze_recent_issues():
    """Analyze recent traces for issues"""
    print("🔍 ANALYZING UNSUCCESSFUL MESSAGES AND LANGUAGE MIXING")
    print("="*80)
    
    # Get recent runs
    try:
        runs = list(client.list_runs(
            project_name="ghl-langgraph-agent",
            limit=30,
            execution_order=1,
            start_time=datetime.now(timezone.utc) - timedelta(hours=1)
        ))
        
        # Group by issues
        unsuccessful_messages = []
        language_switches = []
        repeated_questions = []
        sofia_english = []
        
        for run in runs:
            if not run.outputs:
                continue
                
            # Check for messages
            if 'messages' in run.outputs:
                msgs = run.outputs['messages']
                if msgs and isinstance(msgs[-1], dict):
                    content = msgs[-1].get('content', '')
                    agent = run.outputs.get('current_agent', 'unknown')
                    
                    # Check for repeated Maria question
                    if "¿Qué tipo de negocio tienes?" in content:
                        repeated_questions.append({
                            'time': run.start_time,
                            'agent': agent,
                            'score': run.outputs.get('lead_score', 'N/A')
                        })
                    
                    # Check for English from Sofia
                    if agent == 'sofia' and "email" in content.lower():
                        sofia_english.append({
                            'time': run.start_time,
                            'content': content,
                            'score': run.outputs.get('lead_score', 'N/A')
                        })
                    
                    # Check for language switches
                    if run.inputs and 'messages' in run.inputs:
                        input_msgs = run.inputs['messages']
                        if input_msgs and isinstance(input_msgs[-1], dict):
                            input_content = input_msgs[-1].get('content', '')
                            
                            # Spanish input, English output
                            spanish_words = ['hola', 'tengo', 'quiero', 'necesito', 'restaurante']
                            english_words = ['email', 'great', 'need', 'send', 'calendar']
                            
                            if any(word in input_content.lower() for word in spanish_words):
                                if any(word in content.lower() for word in english_words):
                                    language_switches.append({
                                        'input': input_content[:50],
                                        'output': content[:50],
                                        'agent': agent
                                    })
        
        # Report findings
        print("\n📊 ISSUES FOUND:")
        
        print(f"\n1. REPEATED QUESTIONS ({len(repeated_questions)} instances)")
        if repeated_questions:
            for i, q in enumerate(repeated_questions[-5:], 1):
                print(f"   {i}. Score {q['score']} - Agent: {q['agent']} - Time: {q['time'].strftime('%H:%M:%S')}")
        
        print(f"\n2. LANGUAGE SWITCHING ({len(language_switches)} instances)")
        if language_switches:
            for i, switch in enumerate(language_switches[-3:], 1):
                print(f"   {i}. {switch['agent']}: '{switch['input']}' → '{switch['output']}'")
        
        print(f"\n3. SOFIA SPEAKING ENGLISH ({len(sofia_english)} instances)")
        if sofia_english:
            for i, eng in enumerate(sofia_english[-3:], 1):
                print(f"   {i}. Score {eng['score']}: '{eng['content'][:60]}...'")
        
        # Check for specific patterns
        print("\n\n🔍 PATTERN ANALYSIS:")
        
        # Check if Sofia is being called at wrong score
        sofia_runs = [r for r in runs if r.outputs and r.outputs.get('current_agent') == 'sofia']
        if sofia_runs:
            scores = [r.outputs.get('lead_score', 0) for r in sofia_runs]
            print(f"\n📊 Sofia activation scores: {scores}")
            if any(s < 8 for s in scores if s):
                print("   ⚠️  WARNING: Sofia activated at score < 8!")
        
        # Check for message delivery issues
        responder_runs = [r for r in runs if 'responder' in str(r.name).lower()]
        if responder_runs:
            failed = [r for r in responder_runs if r.status != 'success']
            if failed:
                print(f"\n❌ Failed responder runs: {len(failed)}")
                for f in failed[-3:]:
                    print(f"   - Error: {f.error}")
        
        # Diagnosis
        print("\n\n🏥 DIAGNOSIS:")
        print("\n1. REPEATED QUESTIONS")
        print("   - Maria keeps asking about business type")
        print("   - State not being updated properly")
        print("   - Possible issue: Intelligence layer not extracting business")
        
        print("\n2. LANGUAGE MIXING")
        print("   - Sofia is responding in English")
        print("   - Should always respond in Spanish")
        print("   - Check Sofia's prompt configuration")
        
        print("\n3. UNSUCCESSFUL MESSAGES")
        print("   - Messages marked as 'Unsuccessful' in GHL")
        print("   - Could be API errors or delivery issues")
        print("   - Check GHL message sending logs")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    import sys
    sys.path.append('.')
    from datetime import timezone
    analyze_recent_issues()
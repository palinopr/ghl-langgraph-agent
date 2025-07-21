#!/usr/bin/env python3
"""
Detailed analysis of LangSmith trace
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

def get_all_runs(trace_id):
    """Get all runs including nested ones"""
    all_runs = []
    
    # Get main run
    main_run = client.read_run(trace_id)
    all_runs.append(main_run)
    
    # Get all child runs recursively
    def get_children(parent_id):
        children = list(client.list_runs(
            project_name="ghl-langgraph-agent",
            filter=f'eq(parent_run_id, "{parent_id}")'
        ))
        for child in children:
            all_runs.append(child)
            get_children(str(child.id))
    
    get_children(trace_id)
    return all_runs

def analyze_detailed(trace_id):
    """Detailed trace analysis"""
    print(f"\n🔍 DETAILED ANALYSIS OF TRACE: {trace_id}")
    print("=" * 100)
    
    try:
        # Get all runs
        all_runs = get_all_runs(trace_id)
        print(f"\n📊 Found {len(all_runs)} total runs (including nested)")
        
        # Main run
        main_run = all_runs[0]
        print(f"\n🎯 MAIN RUN:")
        print(f"Status: {main_run.status}")
        if main_run.error:
            print(f"❌ Error: {main_run.error}")
        
        # Input message
        print(f"\n📥 INPUT MESSAGE:")
        if main_run.inputs and 'messages' in main_run.inputs:
            for msg in main_run.inputs['messages']:
                if isinstance(msg, dict) and 'content' in msg:
                    print(f"  '{msg['content']}'")
        
        # Track execution flow
        print(f"\n🔄 EXECUTION TIMELINE:")
        
        # Sort runs by start time
        sorted_runs = sorted(all_runs[1:], key=lambda r: r.start_time if r.start_time else datetime.min)
        
        for i, run in enumerate(sorted_runs):
            indent = "  " * (run.name.count('/') + 1)
            print(f"\n{indent}{i+1}. {run.name}")
            
            # Special handling for each node type
            if "receptionist" in run.name.lower():
                print(f"{indent}   📋 Data Loading:")
                if run.outputs:
                    if 'contact_info' in run.outputs:
                        contact = run.outputs['contact_info']
                        if contact:
                            print(f"{indent}     - Contact loaded: {contact.get('firstName', 'Unknown')}")
                    if 'conversation_history' in run.outputs:
                        history = run.outputs['conversation_history']
                        print(f"{indent}     - History: {len(history) if history else 0} messages")
                    if 'previous_custom_fields' in run.outputs:
                        fields = run.outputs['previous_custom_fields']
                        if fields:
                            print(f"{indent}     - Previous score: {fields.get('score', '0')}")
            
            elif "intelligence" in run.name.lower():
                print(f"{indent}   🧠 Intelligence Analysis:")
                if run.outputs:
                    print(f"{indent}     - Lead score: {run.outputs.get('lead_score', 'N/A')}")
                    extracted = run.outputs.get('extracted_data', {})
                    if extracted:
                        print(f"{indent}     - Extracted:")
                        for key, value in extracted.items():
                            if value and key != 'extraction_confidence':
                                print(f"{indent}       • {key}: {value}")
                    reasoning = run.outputs.get('score_reasoning', '')
                    if reasoning:
                        print(f"{indent}     - Reasoning: {reasoning}")
            
            elif "supervisor" in run.name.lower():
                print(f"{indent}   🎯 Routing Decision:")
                if run.outputs:
                    print(f"{indent}     - Next agent: {run.outputs.get('next_agent', 'N/A')}")
                    print(f"{indent}     - Score: {run.outputs.get('lead_score', 'N/A')}")
                    print(f"{indent}     - Route: {run.outputs.get('lead_category', 'N/A')}")
            
            elif any(agent in run.name.lower() for agent in ["maria", "carlos", "sofia"]):
                agent_name = next((a for a in ["maria", "carlos", "sofia"] if a in run.name.lower()), "agent")
                print(f"{indent}   💬 {agent_name.title()} Response:")
                if run.outputs and 'messages' in run.outputs:
                    for msg in run.outputs['messages']:
                        if hasattr(msg, 'content') and msg.content:
                            # Skip system messages
                            if hasattr(msg, 'name') and msg.name in ['receptionist', 'supervisor']:
                                continue
                            content = msg.content[:150] + "..." if len(msg.content) > 150 else msg.content
                            print(f"{indent}     '{content}'")
            
            elif "responder" in run.name.lower():
                print(f"{indent}   📤 Message Sent:")
                if run.outputs:
                    sent = run.outputs.get('response_sent', False)
                    print(f"{indent}     - Sent: {'Yes' if sent else 'No'}")
                    if 'responder_status' in run.outputs:
                        print(f"{indent}     - Status: {run.outputs['responder_status']}")
            
            # Show any errors
            if run.error:
                print(f"{indent}   ❌ ERROR: {run.error}")
            
            # Timing
            if run.start_time and run.end_time:
                duration = (run.end_time - run.start_time).total_seconds()
                print(f"{indent}   ⏱️  Duration: {duration:.2f}s")
        
        # Final output
        print(f"\n📤 FINAL OUTPUT:")
        if main_run.outputs and 'messages' in main_run.outputs:
            final_messages = main_run.outputs['messages']
            # Find the last AI message that's not from system
            for msg in reversed(final_messages):
                if hasattr(msg, 'type') and msg.type == 'ai':
                    if hasattr(msg, 'name') and msg.name in ['receptionist', 'supervisor', 'intelligence']:
                        continue
                    print(f"  '{msg.content}'")
                    break
        
        # Analysis summary
        print(f"\n📊 ANALYSIS SUMMARY:")
        
        # Check for issues
        issues = []
        warnings = []
        
        # Check score
        final_score = None
        for run in all_runs:
            if run.outputs and 'lead_score' in run.outputs:
                final_score = run.outputs['lead_score']
        
        if final_score:
            print(f"  - Final Score: {final_score}/10")
            if "hola" in str(main_run.inputs).lower() and final_score > 2:
                issues.append(f"Score too high ({final_score}) for simple 'hola'")
        
        # Check for old history
        for run in all_runs:
            if "receptionist" in run.name.lower() and run.outputs:
                if 'conversation_history' in run.outputs:
                    history = run.outputs['conversation_history']
                    if history and len(history) > 1:
                        warnings.append(f"Loaded {len(history)} historical messages")
        
        # Check for debug messages
        for run in all_runs:
            if run.outputs and 'messages' in run.outputs:
                for msg in run.outputs['messages']:
                    if hasattr(msg, 'content'):
                        content = msg.content.lower()
                        if any(pattern in content for pattern in ['lead scored', 'routing to', 'debug:']):
                            issues.append(f"Debug message in output: '{msg.content[:50]}...'")
        
        # Check for nonsense extractions
        for run in all_runs:
            if "intelligence" in run.name.lower() and run.outputs:
                extracted = run.outputs.get('extracted_data', {})
                if extracted.get('business_type') and 'hola' in str(extracted.get('business_type')):
                    issues.append(f"Invalid business extraction: {extracted.get('business_type')}")
        
        # Print issues
        if issues:
            print(f"\n❌ ISSUES FOUND:")
            for issue in issues:
                print(f"  - {issue}")
        
        if warnings:
            print(f"\n⚠️  WARNINGS:")
            for warning in warnings:
                print(f"  - {warning}")
        
        if not issues and not warnings:
            print(f"\n✅ NO MAJOR ISSUES DETECTED!")
        
    except Exception as e:
        print(f"\n❌ Error in analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_detailed(trace_id)
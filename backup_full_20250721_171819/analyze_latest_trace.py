#!/usr/bin/env python3
"""
Analyze latest traces to debug the scoring issue
"""
import os
import sys
from datetime import datetime, timezone, timedelta

# Try to import langsmith
try:
    from langsmith import Client
except ImportError:
    print("❌ langsmith package not installed.")
    print("Please install it with: pip install langsmith")
    sys.exit(1)


def analyze_scoring_issue():
    """Analyze recent traces to find why lead is scored 9/10 without data"""
    
    # Initialize client
    api_key = os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGSMITH_API_KEY")
    if not api_key:
        print("❌ No API key found. Please set LANGCHAIN_API_KEY or LANGSMITH_API_KEY")
        return
    
    client = Client(api_key=api_key)
    
    # Project name for production
    project_name = "ghl-langgraph-agent"
    
    print(f"🔍 Analyzing traces for scoring issues in project: {project_name}")
    print("=" * 80)
    
    # Get recent traces
    runs = list(client.list_runs(
        project_name=project_name,
        limit=10,
        execution_order=1  # Top-level runs only
    ))
    
    print(f"\n✅ Found {len(runs)} recent traces")
    
    # Look for specific patterns
    scoring_issues = []
    appointment_without_qual = []
    debug_messages_shown = []
    
    for run in runs:
        # Check inputs
        if run.inputs and 'messages' in run.inputs:
            messages = run.inputs.get('messages', [])
            
            # Get first customer message
            first_msg = ""
            if messages and len(messages) > 0:
                first_msg = messages[0].get('content', '') if isinstance(messages[0], dict) else ""
            
            # Check outputs for scoring
            if run.outputs:
                output_str = str(run.outputs)
                
                # Check for high scores without qualification
                if "scored 9/10" in output_str or "scored 8/10" in output_str:
                    # Check if basic info was collected
                    if "nombre" not in output_str.lower() and "budget" not in output_str.lower():
                        scoring_issues.append({
                            'id': run.id,
                            'message': first_msg,
                            'score_given': "8-9/10",
                            'issue': "High score without collecting data"
                        })
                
                # Check for immediate appointment offers
                if ("tengo disponible" in output_str or "estos horarios" in output_str) and len(first_msg) < 50:
                    appointment_without_qual.append({
                        'id': run.id,
                        'message': first_msg,
                        'response': output_str[:200],
                        'issue': "Offering appointments without qualification"
                    })
                
                # Check for debug messages
                if "routing to" in output_str.lower() or "lead scored" in output_str.lower():
                    debug_messages_shown.append({
                        'id': run.id,
                        'debug_msg': output_str[:100],
                        'issue': "Debug message visible to customer"
                    })
    
    # Print findings
    print(f"\n🚨 SCORING ISSUES FOUND: {len(scoring_issues)}")
    for issue in scoring_issues[:3]:
        print(f"\n📊 Trace ID: {issue['id']}")
        print(f"   Customer: '{issue['message'][:50]}...'")
        print(f"   Problem: {issue['issue']}")
        print(f"   Score: {issue['score_given']}")
    
    print(f"\n🚨 APPOINTMENT WITHOUT QUALIFICATION: {len(appointment_without_qual)}")
    for issue in appointment_without_qual[:3]:
        print(f"\n📅 Trace ID: {issue['id']}")
        print(f"   Customer: '{issue['message'][:50]}...'")
        print(f"   Response: '{issue['response'][:100]}...'")
        print(f"   Problem: {issue['issue']}")
    
    print(f"\n🚨 DEBUG MESSAGES SHOWN: {len(debug_messages_shown)}")
    for issue in debug_messages_shown[:3]:
        print(f"\n🐛 Trace ID: {issue['id']}")
        print(f"   Debug: '{issue['debug_msg']}'")
        print(f"   Problem: {issue['issue']}")
    
    # Analyze root cause
    print("\n🔍 ROOT CAUSE ANALYSIS:")
    print("1. AI Analyzer is being too generous with scoring")
    print("2. Supervisor is not checking for required data before scoring")
    print("3. Debug messages are being added to customer-visible messages")
    print("4. Agents are not following conversation rules (ask one question at a time)")
    
    # Provide fix recommendations
    print("\n💡 RECOMMENDED FIXES:")
    print("1. Fix scoring logic to require actual data (name, business, budget)")
    print("2. Remove debug messages from customer view")
    print("3. Enforce conversation rules in agent prompts")
    print("4. Add validation before offering appointments")


def check_specific_trace(trace_id: str):
    """Deep dive into a specific trace"""
    api_key = os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGSMITH_API_KEY")
    client = Client(api_key=api_key)
    
    print(f"\n🔍 Analyzing trace: {trace_id}")
    
    try:
        # Get the specific run
        run = client.read_run(trace_id)
        
        print(f"Status: {run.status}")
        print(f"Start time: {run.start_time}")
        
        # Check all steps
        child_runs = list(client.list_runs(
            parent_run=trace_id,
            execution_order=1
        ))
        
        print(f"\nChild runs: {len(child_runs)}")
        
        for i, child in enumerate(child_runs):
            print(f"\n{i+1}. {child.name}")
            if child.inputs:
                print(f"   Input: {str(child.inputs)[:100]}...")
            if child.outputs:
                print(f"   Output: {str(child.outputs)[:100]}...")
            if child.error:
                print(f"   ERROR: {child.error}")
                
    except Exception as e:
        print(f"Error reading trace: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Analyze specific trace
        check_specific_trace(sys.argv[1])
    else:
        # General analysis
        analyze_scoring_issue()
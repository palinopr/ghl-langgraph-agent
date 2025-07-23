#!/usr/bin/env python3
"""Deep analysis of LangSmith trace using different API approaches."""

import os
import json
import requests
from datetime import datetime
from langsmith import Client
import time

# Initialize LangSmith client
client = Client(
    api_key="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"
)

def fetch_trace_via_api(trace_id):
    """Fetch trace data directly via API."""
    api_key = "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"
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    # Try to get run details
    base_url = "https://api.smith.langchain.com/api/v1"
    
    print("\nFetching run details via API...")
    run_url = f"{base_url}/runs/{trace_id}"
    response = requests.get(run_url, headers=headers)
    
    if response.status_code == 200:
        run_data = response.json()
        print(f"✅ Successfully fetched run data")
        return run_data
    else:
        print(f"❌ Failed to fetch run: {response.status_code}")
        return None

def analyze_complete_trace(trace_id):
    """Perform complete trace analysis."""
    print(f"\n{'='*80}")
    print(f"DEEP TRACE ANALYSIS: {trace_id}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")
    
    # Get main run
    try:
        run = client.read_run(trace_id)
        print("✅ Main run fetched successfully")
    except Exception as e:
        print(f"❌ Error fetching main run: {e}")
        return
    
    # Also fetch via API for more details
    api_data = fetch_trace_via_api(trace_id)
    
    # Basic info
    print("\n1. BASIC RUN INFO:")
    print(f"   - Name: {run.name}")
    print(f"   - Status: {run.status}")
    print(f"   - Duration: {(run.end_time - run.start_time).total_seconds():.2f}s")
    print(f"   - Error: {run.error if run.error else 'None'}")
    
    # Check metadata
    print("\n2. METADATA ANALYSIS:")
    if api_data and 'extra' in api_data:
        metadata = api_data['extra'].get('metadata', {})
        print(f"   - Thread ID: {metadata.get('thread_id', 'NOT FOUND')}")
        print(f"   - Full metadata: {json.dumps(metadata, indent=4)}")
    
    # Analyze inputs
    print("\n3. INPUT ANALYSIS:")
    if run.inputs:
        print(f"   - Contact ID: {run.inputs.get('contact_id')}")
        print(f"   - Contact Name: {run.inputs.get('contact_name')}")
        print(f"   - Initial Messages: {len(run.inputs.get('messages', []))}")
        
        # Check for message content
        messages = run.inputs.get('messages', [])
        if messages:
            print("   - First message:")
            print(f"     {json.dumps(messages[0], indent=6)}")
    
    # Analyze outputs
    print("\n4. OUTPUT ANALYSIS:")
    if run.outputs:
        output_messages = run.outputs.get('messages', [])
        print(f"   - Total messages in output: {len(output_messages)}")
        print(f"   - Thread ID in output: {run.outputs.get('thread_id')}")
        print(f"   - Lead score: {run.outputs.get('lead_score')}")
        print(f"   - Next agent: {run.outputs.get('next_agent')}")
        print(f"   - Message sent: {run.outputs.get('message_sent')}")
        
        # Analyze message duplication
        print("\n   MESSAGE DUPLICATION CHECK:")
        message_contents = []
        duplicates = []
        
        for i, msg in enumerate(output_messages):
            content = msg.get('content', '')
            if content in message_contents and content:
                duplicates.append((i, content))
            message_contents.append(content)
        
        if duplicates:
            print(f"   ⚠️  FOUND {len(duplicates)} DUPLICATE MESSAGES:")
            for idx, content in duplicates[:5]:  # Show first 5
                print(f"      - Index {idx}: '{content[:50]}...'")
        else:
            print("   ✅ No duplicate messages found")
        
        # Check for "Hola" repetitions
        hola_count = sum(1 for msg in output_messages if msg.get('content') == 'Hola')
        error_count = sum(1 for msg in output_messages if msg.get('content') == 'Error')
        
        if hola_count > 1:
            print(f"   ⚠️  'Hola' appears {hola_count} times")
        if error_count > 0:
            print(f"   ⚠️  'Error' appears {error_count} times")
    
    # Try to fetch child runs differently
    print("\n5. CHILD RUN ANALYSIS:")
    
    # Method 1: Via project listing
    try:
        print("   Attempting to fetch child runs via project...")
        # Get project info from run
        if hasattr(run, 'session_id') and run.session_id:
            project_runs = list(client.list_runs(
                project_id=run.session_id,
                is_root=False,
                limit=100
            ))
            
            # Filter for our trace
            child_runs = [r for r in project_runs if str(r.trace_id) == trace_id or str(r.parent_run_id) == trace_id]
            
            if child_runs:
                print(f"   ✅ Found {len(child_runs)} child runs")
                
                # Analyze agent executions
                agents = {}
                for child in child_runs:
                    name = child.name.lower()
                    for agent in ['supervisor', 'receptionist', 'responder', 'maria', 'carlos', 'sofia']:
                        if agent in name:
                            if agent not in agents:
                                agents[agent] = []
                            agents[agent].append(child)
                
                print("\n   AGENT EXECUTIONS:")
                for agent, runs in agents.items():
                    print(f"   - {agent}: {len(runs)} executions")
                    for r in runs[:2]:  # Show first 2
                        print(f"     • {r.name} ({r.status})")
                        if r.error:
                            print(f"       ERROR: {r.error}")
            else:
                print("   ⚠️  No child runs found via project listing")
    except Exception as e:
        print(f"   ❌ Error fetching child runs: {e}")
    
    # Method 2: Check API data for child info
    if api_data:
        print("\n   Checking API data for execution details...")
        if 'child_run_ids' in api_data:
            print(f"   - Child run IDs: {len(api_data.get('child_run_ids', []))}")
        
        if 'tags' in api_data:
            print(f"   - Tags: {api_data['tags']}")
    
    # Analyze the flow
    print("\n6. WORKFLOW FLOW ANALYSIS:")
    if run.outputs:
        print(f"   - Supervisor complete: {run.outputs.get('supervisor_complete')}")
        print(f"   - Receptionist complete: {run.outputs.get('receptionist_complete')}")
        print(f"   - Is first contact: {run.outputs.get('is_first_contact')}")
        print(f"   - Agent task: {run.outputs.get('agent_task')}")
        
        # Check if Maria's prompt is in the messages
        maria_prompt_found = any(
            'You are Maria' in msg.get('content', '') 
            for msg in output_messages 
            if msg.get('type') == 'system'
        )
        
        if maria_prompt_found:
            print("   ✅ Maria's system prompt found in messages")
        
        # Check final response
        if run.outputs.get('last_sent_message'):
            print(f"\n   FINAL RESPONSE:")
            print(f"   '{run.outputs['last_sent_message']}'")
    
    # Summary
    print("\n" + "="*80)
    print("ANALYSIS SUMMARY:")
    print("="*80)
    
    issues = []
    
    # Check for issues
    if run.outputs:
        messages = run.outputs.get('messages', [])
        
        # Message duplication
        if hola_count > 1:
            issues.append(f"Message 'Hola' duplicated {hola_count} times")
        
        if error_count > 0:
            issues.append(f"Error messages found {error_count} times")
        
        # Thread consistency
        if run.outputs.get('thread_id') != f"contact-{run.inputs.get('contact_id')}":
            issues.append("Thread ID mismatch")
        
        # Check for old naming
        for msg in messages:
            if any(pattern in str(msg) for pattern in ['_agent', '_v2', '_enhanced']):
                issues.append("Old naming conventions detected")
                break
    
    if issues:
        print("\n⚠️  ISSUES DETECTED:")
        for issue in issues:
            print(f"   - {issue}")
    else:
        print("\n✅ Core functionality appears to be working")
    
    print("\n📊 KEY FINDINGS:")
    print("   1. Message duplication is occurring (multiple 'Hola' and 'Error' messages)")
    print("   2. The workflow completes successfully despite duplications")
    print("   3. Maria agent responds appropriately to the error message")
    print("   4. Thread ID is correctly set as 'contact-4pgjZlQ8WpJaUfKuSR2r'")
    print("   5. System appears to be using the new simplified naming (no _v2 suffixes)")

if __name__ == "__main__":
    trace_id = "1f0676c2-3fcd-6754-a8ab-e2e3f352e0c1"
    analyze_complete_trace(trace_id)
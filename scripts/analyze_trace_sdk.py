#!/usr/bin/env python3
"""
Analyze a specific trace using LangSmith SDK
"""
import os
import json
from datetime import datetime
from langsmith import Client

def analyze_trace(trace_id: str, api_key: str):
    """Analyze a trace in detail"""
    
    # Initialize client
    client = Client(api_key=api_key)
    
    print(f"🔍 Analyzing trace: {trace_id}")
    print("=" * 80)
    
    try:
        # Get the main run
        run = client.read_run(trace_id)
        
        print(f"\n📊 TRACE OVERVIEW")
        print(f"Name: {run.name}")
        print(f"Status: {run.status}")
        print(f"Start Time: {run.start_time}")
        print(f"End Time: {run.end_time}")
        print(f"Duration: {(run.end_time - run.start_time).total_seconds():.2f}s")
        
        # Inputs
        print(f"\n📥 INPUTS:")
        if run.inputs:
            # Check for messages
            if 'messages' in run.inputs:
                print("  Messages:")
                for msg in run.inputs['messages']:
                    if isinstance(msg, dict):
                        msg_type = msg.get('type', 'unknown')
                        content = msg.get('content', '')
                        print(f"    [{msg_type}]: {content}")
            
            # Other input fields
            for key, value in run.inputs.items():
                if key != 'messages':
                    print(f"  {key}: {value}")
        
        # Outputs
        print(f"\n📤 OUTPUTS:")
        if run.outputs:
            # Check for messages in outputs
            if 'messages' in run.outputs:
                print("  Messages:")
                for msg in run.outputs['messages']:
                    if isinstance(msg, dict):
                        msg_type = msg.get('type', 'unknown')
                        content = msg.get('content', '')
                        if content:
                            print(f"    [{msg_type}]: {content[:200]}{'...' if len(content) > 200 else ''}")
            
            # Other output fields
            for key, value in run.outputs.items():
                if key != 'messages':
                    print(f"  {key}: {value}")
        
        # Check for tool calls
        if hasattr(run, 'outputs') and run.outputs:
            messages = run.outputs.get('messages', [])
            for msg in messages:
                if isinstance(msg, dict) and 'tool_calls' in msg:
                    print(f"\n🔧 TOOL CALLS:")
                    for tool_call in msg['tool_calls']:
                        print(f"  Tool: {tool_call.get('name', 'unknown')}")
                        print(f"  Args: {tool_call.get('args', {})}")
        
        # Error info
        if run.error:
            print(f"\n❌ ERROR: {run.error}")
        
        # Metadata
        if hasattr(run, 'extra') and run.extra:
            print(f"\n📋 METADATA:")
            metadata = run.extra.get('metadata', {})
            for key, value in metadata.items():
                print(f"  {key}: {value}")
        
        # Try to get child runs
        print(f"\n👶 CHILD RUNS:")
        try:
            # Use the run's session_id to query child runs
            if hasattr(run, 'session_id') and run.session_id:
                child_runs = list(client.list_runs(
                    run_filter={"session": str(run.session_id)},
                    limit=20
                ))
                
                # Filter for actual child runs
                child_runs = [r for r in child_runs if r.id != trace_id]
                
                print(f"Found {len(child_runs)} runs in same session")
                
                for i, child in enumerate(child_runs[:10]):
                    print(f"\n  Run {i+1}: {child.name}")
                    print(f"    ID: {child.id}")
                    print(f"    Status: {child.status}")
                    print(f"    Start: {child.start_time}")
                    
                    # Check if it's an agent response
                    if child.outputs and 'messages' in child.outputs:
                        for msg in child.outputs['messages']:
                            if isinstance(msg, dict) and msg.get('type') == 'ai':
                                content = msg.get('content', '')
                                if content:
                                    print(f"    Response: {content[:150]}{'...' if len(content) > 150 else ''}")
                                    break
        except Exception as e:
            print(f"  Could not fetch child runs: {e}")
        
        # Analysis summary
        print(f"\n🎯 ANALYSIS SUMMARY:")
        
        # Check if supervisor responded directly
        supervisor_responded = False
        agent_routed = None
        
        if run.outputs and 'messages' in run.outputs:
            for msg in run.outputs['messages']:
                if isinstance(msg, dict):
                    # Check for direct response
                    if msg.get('type') == 'ai' and msg.get('content') and 'tool_calls' not in msg:
                        content = msg['content']
                        if not content.startswith('[Task from supervisor:'):
                            supervisor_responded = True
                            print(f"  ⚠️  Supervisor responded directly: {content[:100]}...")
                    
                    # Check for agent routing
                    if 'next_agent' in run.outputs:
                        agent_routed = run.outputs['next_agent']
                        print(f"  ✅ Routed to agent: {agent_routed}")
        
        if not supervisor_responded and not agent_routed:
            print("  ❓ Could not determine routing behavior")
        
    except Exception as e:
        print(f"\n❌ Error analyzing trace: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        trace_id = sys.argv[1]
    else:
        trace_id = "1f0672f3-d1bd-6524-a9cf-70f85cf81955"
    
    api_key = os.getenv("LANGCHAIN_API_KEY", "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")
    
    analyze_trace(trace_id, api_key)
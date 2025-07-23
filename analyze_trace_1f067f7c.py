#!/usr/bin/env python3
"""
Detailed trace analysis for trace 1f067f7c-90e1-6b5f-9070-0011f54194b7
"""
import os
import json
from datetime import datetime
from langsmith import Client

# Set up LangSmith
os.environ["LANGSMITH_API_KEY"] = "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"
client = Client()

trace_id = "1f067f7c-90e1-6b5f-9070-0011f54194b7"


def analyze_metadata(metadata):
    """Extract key debug information from metadata"""
    debug_info = {}
    
    # Look for state snapshots
    for key, value in metadata.items():
        if 'state_snapshot' in key:
            print(f"\n📸 {key}:")
            if isinstance(value, dict):
                for k, v in value.items():
                    if k in ['phase', 'current_agent', 'next_agent', 'lead_score', 
                            'last_message', 'routing_reason', 'agent_task']:
                        print(f"   {k}: {v}")
        elif 'routing_decision' in key:
            print(f"\n🔀 Routing Decision:")
            if isinstance(value, dict):
                for k, v in value.items():
                    print(f"   {k}: {v}")
        elif 'message_analysis' in key:
            print(f"\n📊 Message Analysis:")
            if isinstance(value, dict):
                for k, v in value.items():
                    if k != 'extracted_data' or v:  # Skip empty extracted_data
                        print(f"   {k}: {v}")
        elif 'tool_' in key:
            print(f"\n🔧 Tool Execution: {key}")
            if isinstance(value, dict):
                print(f"   Success: {value.get('success', 'unknown')}")
                if 'error' in value:
                    print(f"   Error: {value['error']}")
    
    return debug_info


def get_node_flow(runs):
    """Extract the flow of nodes"""
    nodes = []
    for run in runs:
        if run.run_type in ['chain', 'llm']:
            nodes.append({
                'name': run.name,
                'status': run.status,
                'start': run.start_time,
                'duration': (run.end_time - run.start_time).total_seconds() if run.end_time else 0
            })
    return sorted(nodes, key=lambda x: x['start'])


def analyze_messages(run):
    """Analyze message flow"""
    if run.inputs:
        input_msgs = run.inputs.get('messages', [])
        print(f"\n📥 Input Messages: {len(input_msgs)}")
        for i, msg in enumerate(input_msgs[-3:]):  # Last 3
            if isinstance(msg, dict):
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')[:100]
                print(f"   [{i}] {role}: {content}...")
    
    if run.outputs:
        output_msgs = run.outputs.get('messages', [])
        print(f"\n📤 Output Messages: {len(output_msgs)}")
        for i, msg in enumerate(output_msgs[-3:]):  # Last 3
            if isinstance(msg, dict):
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')[:100]
                print(f"   [{i}] {role}: {content}...")


print("="*80)
print(f"Comprehensive Trace Analysis: {trace_id}")
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*80)

# Get main run
try:
    run = client.read_run(trace_id)
    print(f"\n✅ Main Run: {run.name}")
    print(f"   Status: {run.status}")
    print(f"   Duration: {(run.end_time - run.start_time).total_seconds():.2f}s")
    
    # Analyze messages
    analyze_messages(run)
    
    # Get all child runs
    all_runs = list(client.list_runs(
        project_name="ghl-langgraph-agent",
        run_ids=[trace_id],
        is_root=False
    ))
    
    # Reverse to get chronological order
    all_runs.reverse()
    
    print(f"\n📊 Total Child Runs: {len(all_runs)}")
    
    # Show node flow
    node_flow = get_node_flow(all_runs)
    print("\n🔄 Node Execution Flow:")
    for i, node in enumerate(node_flow):
        print(f"   {i+1}. {node['name']} ({node['duration']:.2f}s) - {node['status']}")
    
    # Analyze each significant run
    print("\n" + "="*80)
    print("DETAILED NODE ANALYSIS")
    print("="*80)
    
    for run in all_runs:
        if any(keyword in run.name for keyword in ['debug', 'router', 'agent', 'responder']):
            print(f"\n{'='*60}")
            print(f"Node: {run.name}")
            print(f"Status: {run.status}")
            print(f"Duration: {(run.end_time - run.start_time).total_seconds():.2f}s")
            
            # Extract metadata
            if hasattr(run, 'extra') and run.extra and 'metadata' in run.extra:
                analyze_metadata(run.extra['metadata'])
            
            # Show errors if any
            if run.error:
                print(f"\n❌ ERROR: {run.error}")

    # Summary of findings
    print("\n" + "="*80)
    print("ANALYSIS SUMMARY")
    print("="*80)
    
    print("\n1. CONTEXT MISMATCH:")
    print("   - Customer: 'tengo un restaurante y estoy perdiendo clientes'")
    print("   - System Response: About WhatsApp automation (WRONG CONTEXT)")
    print("   - Issue: System is hardcoded for WhatsApp automation sales")
    
    print("\n2. SYSTEM BEHAVIOR:")
    print("   - All agents are programmed to sell WhatsApp automation")
    print("   - Smart router analyzes for 'WhatsApp conversation' lead qualification")
    print("   - Maria introduces herself as 'WhatsApp automation specialist'")
    
    print("\n3. RECOMMENDATIONS:")
    print("   - System needs to be configurable for different business contexts")
    print("   - Agents should adapt their responses based on customer's actual needs")
    print("   - Consider making the business context a configuration parameter")

except Exception as e:
    print(f"\n❌ Error analyzing trace: {str(e)}")
    import traceback
    traceback.print_exc()
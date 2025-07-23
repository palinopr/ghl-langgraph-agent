#!/usr/bin/env python3
"""
Analyze LangSmith trace 1f067ef4-9109-6606-8c4e-86e61914c970
Focus on debug features: state snapshots, routing decisions, tool tracking
"""

import os
import sys
from datetime import datetime
from langsmith import Client
from dotenv import load_dotenv
import json
from collections import defaultdict

# Load environment variables
load_dotenv()

# Check for API key
if not os.getenv("LANGCHAIN_API_KEY") and not os.getenv("LANGSMITH_API_KEY"):
    print("❌ No LangSmith API key found!")
    print("Set one of these environment variables:")
    print("  export LANGCHAIN_API_KEY=your-key")
    print("  export LANGSMITH_API_KEY=your-key")
    sys.exit(1)

def analyze_debug_features(trace_id):
    """Analyze a trace focusing on the new debug features"""
    client = Client()
    
    print(f"\n{'='*80}")
    print(f"Debug Feature Analysis for Trace: {trace_id}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")
    
    # Track debug metadata found
    debug_features_found = defaultdict(list)
    state_snapshots = []
    routing_decisions = []
    tool_executions = []
    
    try:
        # Get the main run
        run = client.read_run(trace_id)
        
        print(f"Run Name: {run.name}")
        print(f"Run Type: {run.run_type}")
        print(f"Status: {run.status}")
        print(f"Duration: {(run.end_time - run.start_time).total_seconds() if run.end_time else 'N/A'} seconds")
        
        # Check for debug metadata in main run
        if hasattr(run, 'extra') and run.extra:
            metadata = run.extra.get('metadata', {})
            if metadata:
                print(f"\n[MAIN RUN DEBUG METADATA]")
                for key, value in metadata.items():
                    if 'debug' in key.lower():
                        debug_features_found['main_run'].append(key)
                        print(f"  {key}: {json.dumps(value, indent=2)[:200]}...")
        
        # Get all child runs to analyze
        print(f"\n{'='*40} ANALYZING CHILD RUNS {'='*40}")
        
        # Collect all runs
        all_runs = []
        try:
            # Get project name/ID from the run
            project_name = None
            if hasattr(run, 'session_id'):
                project_name = str(run.session_id)
            elif os.getenv('LANGCHAIN_PROJECT'):
                project_name = os.getenv('LANGCHAIN_PROJECT')
            elif os.getenv('LANGSMITH_PROJECT'):
                project_name = os.getenv('LANGSMITH_PROJECT')
            
            if project_name:
                print(f"Using project: {project_name}")
                # List runs from the project with parent filter
                runs = client.list_runs(
                    project_name=project_name,
                    run_ids=[trace_id],  # Get runs related to this trace
                    limit=100
                )
                # First add the main run's direct children
                for r in runs:
                    if hasattr(r, 'parent_run_id') and str(r.parent_run_id) == trace_id:
                        all_runs.append(r)
                
                # If we found children, also get their children (grandchildren)
                if all_runs:
                    child_ids = [str(r.id) for r in all_runs[:20]]  # Limit for performance
                    for child_id in child_ids:
                        grandchildren = client.list_runs(
                            project_name=project_name,
                            run_ids=[child_id],
                            limit=50
                        )
                        for gc in grandchildren:
                            if hasattr(gc, 'parent_run_id') and str(gc.parent_run_id) == child_id:
                                all_runs.append(gc)
            else:
                print("Warning: Could not determine project name")
                # Fallback: try to get runs by trace
                all_runs = list(client.list_runs(
                    run_ids=[trace_id],
                    limit=100
                ))
                
        except Exception as e:
            print(f"Error collecting runs: {e}")
            # Try alternative approach
            try:
                print("Trying alternative approach...")
                # Get all runs and filter
                recent_runs = list(client.list_runs(limit=500))
                for r in recent_runs:
                    if hasattr(r, 'parent_run_id') and str(r.parent_run_id) == trace_id:
                        all_runs.append(r)
                    # Also check if it's part of the same trace
                    elif hasattr(r, 'trace_id') and str(r.trace_id) == trace_id:
                        all_runs.append(r)
            except Exception as e2:
                print(f"Alternative approach also failed: {e2}")
        
        # Analyze each run for debug features
        for run_idx, child_run in enumerate(all_runs):
            run_name = child_run.name
            
            # Check for debug metadata
            if hasattr(child_run, 'extra') and child_run.extra:
                metadata = child_run.extra.get('metadata', {})
                
                # Look for state snapshots
                for key in metadata:
                    if 'state_snapshot' in key:
                        state_snapshots.append({
                            'run_name': run_name,
                            'snapshot_type': key,
                            'data': metadata[key]
                        })
                        debug_features_found['state_snapshots'].append(f"{run_name}:{key}")
                    
                    # Look for specific debug nodes
                    if key in ['thread_id_mapper_debug', 'receptionist_debug', 'smart_router_debug']:
                        debug_features_found[key].append(run_name)
                    
                    # Look for tool execution tracking
                    if 'tool_execution' in key or 'tool_call' in key:
                        tool_executions.append({
                            'run_name': run_name,
                            'tool_data': metadata[key]
                        })
                        debug_features_found['tool_tracking'].append(f"{run_name}:{key}")
            
            # Check for routing decisions
            if 'route' in run_name.lower() or 'supervisor' in run_name.lower():
                if child_run.outputs:
                    routing_decisions.append({
                        'run_name': run_name,
                        'decision': child_run.outputs
                    })
        
        # Report findings
        print(f"\n{'='*40} DEBUG FEATURES FOUND {'='*40}")
        
        print("\n[1] DEBUG METADATA TRACKING:")
        for feature, occurrences in debug_features_found.items():
            print(f"  - {feature}: {len(occurrences)} occurrences")
            if occurrences and len(occurrences) <= 5:
                for occ in occurrences:
                    print(f"    • {occ}")
        
        print(f"\n[2] STATE SNAPSHOTS: {len(state_snapshots)} found")
        for snapshot in state_snapshots[:3]:  # Show first 3
            print(f"\n  Snapshot in {snapshot['run_name']} ({snapshot['snapshot_type']}):")
            data = snapshot['data']
            print(f"    - Phase: {data.get('phase', 'N/A')}")
            print(f"    - Thread ID: {data.get('thread_id', 'N/A')}")
            print(f"    - Contact ID: {data.get('contact_id', 'N/A')}")
            print(f"    - Current Agent: {data.get('current_agent', 'N/A')}")
            print(f"    - Message Count: {data.get('message_count', 'N/A')}")
            print(f"    - Lead Score: {data.get('lead_score', 'N/A')}")
            if 'last_message' in data:
                print(f"    - Last Message: {data['last_message'][:100]}...")
        
        print(f"\n[3] ROUTING DECISIONS: {len(routing_decisions)} found")
        for decision in routing_decisions[:3]:  # Show first 3
            print(f"\n  Decision in {decision['run_name']}:")
            output = decision['decision']
            if isinstance(output, dict):
                print(f"    - Next: {output.get('next', 'N/A')}")
                print(f"    - Reason: {output.get('reason', output.get('routing_reason', 'N/A'))}")
        
        print(f"\n[4] TOOL EXECUTIONS: {len(tool_executions)} tracked")
        for tool in tool_executions[:3]:  # Show first 3
            print(f"\n  Tool in {tool['run_name']}:")
            print(f"    Data: {json.dumps(tool['tool_data'], indent=2)[:200]}...")
        
        # Check for @debug_node decorator usage
        print(f"\n[5] @debug_node DECORATOR USAGE:")
        debug_wrapped_nodes = [r for r in all_runs if '_debug' in r.name]
        print(f"  - Found {len(debug_wrapped_nodes)} debug-wrapped nodes")
        for node in debug_wrapped_nodes[:5]:
            print(f"    • {node.name}")
        
        # Analyze message flow
        print(f"\n{'='*40} MESSAGE FLOW ANALYSIS {'='*40}")
        message_counts = {}
        for r in all_runs:
            if r.outputs and isinstance(r.outputs, dict) and 'messages' in r.outputs:
                messages = r.outputs['messages']
                if isinstance(messages, list):
                    message_counts[r.name] = len(messages)
        
        if message_counts:
            print("\nMessage counts by node:")
            for node, count in sorted(message_counts.items(), key=lambda x: x[1]):
                print(f"  - {node}: {count} messages")
        
        # Look for issues
        print(f"\n{'='*40} POTENTIAL ISSUES {'='*40}")
        issues = []
        
        # Check for missing debug metadata
        nodes_without_debug = [r.name for r in all_runs if not any(r.name in v for v in debug_features_found.values())]
        if nodes_without_debug:
            issues.append(f"Nodes without debug metadata: {len(nodes_without_debug)}")
            print(f"\n[!] {len(nodes_without_debug)} nodes lack debug metadata:")
            for node in nodes_without_debug[:5]:
                print(f"    - {node}")
        
        # Check for state consistency
        if state_snapshots:
            thread_ids = set(s['data'].get('thread_id') for s in state_snapshots)
            if len(thread_ids) > 1:
                issues.append(f"Multiple thread IDs detected: {thread_ids}")
                print(f"\n[!] Thread ID inconsistency: {thread_ids}")
        
        if not issues:
            print("\n✅ No major issues detected")
        
        # Summary
        print(f"\n{'='*40} SUMMARY {'='*40}")
        print(f"Total child runs analyzed: {len(all_runs)}")
        print(f"Debug features coverage: {len(debug_features_found)} types")
        print(f"State tracking: {'✅ Active' if state_snapshots else '❌ Not found'}")
        print(f"Tool tracking: {'✅ Active' if tool_executions else '❌ Not found'}")
        print(f"Routing tracking: {'✅ Active' if routing_decisions else '❌ Not found'}")
        
    except Exception as e:
        print(f"\nError analyzing trace: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    trace_id = "1f067ef4-9109-6606-8c4e-86e61914c970"
    if len(sys.argv) > 1:
        trace_id = sys.argv[1]
    
    analyze_debug_features(trace_id)
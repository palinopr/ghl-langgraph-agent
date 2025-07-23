#!/usr/bin/env python3
"""
Simple trace analysis for LangSmith traces
Direct approach to examine debug features
"""

import os
import sys
from datetime import datetime
from langsmith import Client
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Check for API key
api_key = os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGSMITH_API_KEY")
if not api_key:
    print("❌ No LangSmith API key found!")
    sys.exit(1)

def analyze_trace_simple(trace_id):
    """Simple direct analysis of a trace"""
    client = Client(api_key=api_key)
    
    print(f"\n{'='*80}")
    print(f"Simple Trace Analysis: {trace_id}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")
    
    try:
        # Get the main run
        print("Fetching main run...")
        run = client.read_run(trace_id)
        
        print(f"✅ Run found: {run.name}")
        print(f"   Type: {run.run_type}")
        print(f"   Status: {run.status}")
        print(f"   Duration: {(run.end_time - run.start_time).total_seconds():.2f}s")
        
        # Check for inputs
        print(f"\n📥 INPUTS:")
        if run.inputs:
            print(json.dumps(run.inputs, indent=2)[:500])
        else:
            print("   No inputs")
        
        # Check for outputs
        print(f"\n📤 OUTPUTS:")
        if run.outputs:
            print(json.dumps(run.outputs, indent=2)[:500])
        else:
            print("   No outputs")
        
        # Check for metadata
        print(f"\n🏷️ METADATA:")
        if hasattr(run, 'extra') and run.extra:
            if 'metadata' in run.extra:
                print("   Metadata found:")
                for key, value in run.extra['metadata'].items():
                    print(f"   - {key}: {str(value)[:100]}...")
            else:
                print("   No metadata in extra")
        else:
            print("   No extra field")
        
        # Try to get all runs from this project
        print(f"\n🔍 Searching for related runs...")
        
        # Get project name from trace metadata or environment
        project_name = None
        
        # Try to get from trace metadata
        if hasattr(run, 'extra') and run.extra and 'metadata' in run.extra:
            metadata = run.extra['metadata']
            project_name = metadata.get('LANGSMITH_PROJECT') or metadata.get('LANGSMITH_HOST_PROJECT_NAME')
        
        # Fallback to environment
        if not project_name:
            project_name = os.getenv('LANGCHAIN_PROJECT') or os.getenv('LANGSMITH_PROJECT') or "ghl-langgraph-agent"
        
        print(f"   Using project: {project_name}")
        
        try:
            # Get recent runs from the project
            recent_runs = list(client.list_runs(
                project_name=project_name,
                limit=50,
                order_by_desc="start_time"
            ))
            
            print(f"   Found {len(recent_runs)} recent runs")
            
            # Find runs that might be related to our trace
            related_runs = []
            for r in recent_runs:
                # Check if it's our main run
                if str(r.id) == trace_id:
                    print(f"   ✓ Found main run")
                    continue
                
                # Check if it has debug in the name
                if 'debug' in r.name.lower():
                    related_runs.append(r)
                elif any(keyword in r.name.lower() for keyword in ['receptionist', 'router', 'responder', 'agent', 'mapper']):
                    related_runs.append(r)
            
            print(f"\n📊 POTENTIALLY RELATED RUNS: {len(related_runs)}")
            
            # Group by run name
            run_groups = {}
            for r in related_runs[:20]:  # Limit to first 20
                base_name = r.name.split('_')[0]
                if base_name not in run_groups:
                    run_groups[base_name] = []
                run_groups[base_name].append(r)
            
            # Display grouped runs
            for group_name, runs in run_groups.items():
                print(f"\n   {group_name}: {len(runs)} runs")
                for r in runs[:3]:  # Show first 3 of each type
                    print(f"      - {r.name}")
                    print(f"        Status: {r.status}")
                    print(f"        Time: {r.start_time.strftime('%H:%M:%S')}")
                    
                    # Check for debug metadata
                    if hasattr(r, 'extra') and r.extra and 'metadata' in r.extra:
                        metadata = r.extra['metadata']
                        debug_keys = [k for k in metadata.keys() if 'debug' in k or 'snapshot' in k]
                        if debug_keys:
                            print(f"        Debug metadata: {', '.join(debug_keys)}")
            
            # Look for specific debug features
            print(f"\n🔍 DEBUG FEATURE SEARCH:")
            
            debug_features = {
                'state_snapshots': 0,
                'tool_executions': 0,
                'routing_decisions': 0,
                'debug_metadata': 0
            }
            
            for r in related_runs:
                if hasattr(r, 'extra') and r.extra and 'metadata' in r.extra:
                    metadata = r.extra['metadata']
                    
                    if any('state_snapshot' in k for k in metadata.keys()):
                        debug_features['state_snapshots'] += 1
                    
                    if any('tool' in k for k in metadata.keys()):
                        debug_features['tool_executions'] += 1
                    
                    if 'routing_decision' in metadata or 'routing_context' in metadata:
                        debug_features['routing_decisions'] += 1
                    
                    if any('debug' in k for k in metadata.keys()):
                        debug_features['debug_metadata'] += 1
            
            print("\n   Debug features found in recent runs:")
            for feature, count in debug_features.items():
                status = "✅" if count > 0 else "❌"
                print(f"   {status} {feature}: {count}")
            
        except Exception as e:
            print(f"   Error searching for runs: {e}")
        
        print(f"\n{'='*40} RECOMMENDATIONS {'='*40}")
        print("\n1. Check the LangSmith UI directly:")
        print(f"   https://smith.langchain.com/o/*/projects/p/{project_name}/r/{trace_id}")
        print("\n2. Look for these in the UI:")
        print("   - Expand each node to see metadata")
        print("   - Check the 'Metadata' tab for debug info")
        print("   - Look for state_snapshot_* entries")
        print("   - Check for tool_execution_* entries")
        print("\n3. If debug features are missing:")
        print("   - Ensure @debug_node decorator is applied")
        print("   - Check that debug_helpers.py is imported")
        print("   - Verify LANGSMITH_TRACING=true is set")
        
    except Exception as e:
        print(f"\n❌ Error analyzing trace: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    trace_id = "1f067ef4-9109-6606-8c4e-86e61914c970"
    if len(sys.argv) > 1:
        trace_id = sys.argv[1]
    
    analyze_trace_simple(trace_id)
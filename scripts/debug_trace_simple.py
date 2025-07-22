#!/usr/bin/env python3
"""
Debug LangSmith trace 1f0672b6-ec5a-6038-aca0-bf769eee3742
Using standard library only
"""
import os
import json
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, Any, List, Optional
from collections import defaultdict

# Configuration
TRACE_ID = "1f0672b6-ec5a-6038-aca0-bf769eee3742"
LANGSMITH_API_KEY = "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"
PROJECT_NAME = "ghl-langgraph-agent"
LANGSMITH_API_URL = "https://api.smith.langchain.com"

# Set environment variable
os.environ["LANGCHAIN_API_KEY"] = LANGSMITH_API_KEY


def format_timestamp(ts: Optional[str]) -> str:
    """Format timestamp for display"""
    if not ts:
        return "N/A"
    try:
        # Handle both formats
        if '.' in ts:
            # Has milliseconds
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        else:
            # No milliseconds
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return ts


def make_request(url: str, method: str = "GET", data: Optional[Dict] = None) -> Dict[str, Any]:
    """Make HTTP request to LangSmith API"""
    headers = {
        "x-api-key": LANGSMITH_API_KEY,
        "Content-Type": "application/json"
    }
    
    request = urllib.request.Request(url, headers=headers, method=method)
    
    if data and method == "POST":
        request.data = json.dumps(data).encode('utf-8')
    
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP Error {e.code}: {e.reason}")
        print(f"Response: {e.read().decode('utf-8')}")
        return {}
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {}


def fetch_trace(trace_id: str) -> Dict[str, Any]:
    """Fetch a specific trace from LangSmith"""
    trace_url = f"{LANGSMITH_API_URL}/runs/{trace_id}"
    print(f"Fetching trace from: {trace_url}")
    return make_request(trace_url)


def fetch_child_runs(trace_id: str) -> List[Dict[str, Any]]:
    """Fetch all child runs of a trace"""
    query_url = f"{LANGSMITH_API_URL}/runs/query"
    query_data = {
        "parent_run_id": trace_id,
        "limit": 100
    }
    
    result = make_request(query_url, method="POST", data=query_data)
    return result.get("runs", [])


def analyze_input_output(trace: Dict[str, Any]):
    """Analyze input and output messages"""
    print("\n📥 INPUT ANALYSIS:")
    inputs = trace.get('inputs', {})
    
    # Extract key fields
    if inputs:
        # Check for messages
        messages = inputs.get('messages', [])
        if messages:
            print(f"  Messages: {len(messages)}")
            for i, msg in enumerate(messages[:3]):  # Show first 3
                if isinstance(msg, dict):
                    msg_type = msg.get('type', 'unknown')
                    content = msg.get('content', '')[:100]
                    print(f"    [{i}] {msg_type}: {content}...")
        
        # Check other key fields
        for key in ['thread_id', 'contact_id', 'webhook_data', 'conversation_id']:
            if key in inputs:
                print(f"  {key}: {inputs[key]}")
    
    print("\n📤 OUTPUT ANALYSIS:")
    outputs = trace.get('outputs', {})
    if outputs:
        # Show key routing information
        for key in ['next_agent', 'agent_task', 'routing_reason', 'lead_score', 'error']:
            if key in outputs:
                print(f"  {key}: {outputs[key]}")


def analyze_workflow_nodes(child_runs: List[Dict[str, Any]]):
    """Analyze workflow node execution"""
    print("\n🔄 WORKFLOW NODES EXECUTED:")
    
    # Group by node name
    node_groups = defaultdict(list)
    for run in child_runs:
        node_groups[run.get('name', 'unknown')].append(run)
    
    # Sort nodes by execution order (using start_time)
    sorted_nodes = []
    for node_name, runs in node_groups.items():
        first_run = min(runs, key=lambda x: x.get('start_time', ''))
        sorted_nodes.append((node_name, runs, first_run.get('start_time', '')))
    
    sorted_nodes.sort(key=lambda x: x[2])
    
    # Display each node
    for node_name, runs, _ in sorted_nodes:
        status_counts = defaultdict(int)
        for run in runs:
            status_counts[run.get('status', 'unknown')] += 1
        
        status_str = ", ".join([f"{s}:{c}" for s, c in status_counts.items()])
        print(f"\n  📌 {node_name} (ran {len(runs)}x) - Status: {status_str}")
        
        # Show first run details
        run = runs[0]
        
        # Check for errors
        if run.get('error'):
            print(f"    ❌ ERROR: {run['error']}")
        
        # Show key outputs
        outputs = run.get('outputs', {})
        if outputs:
            # Routing info
            if 'next_agent' in outputs:
                print(f"    → Routes to: {outputs['next_agent']}")
            if 'lead_score' in outputs:
                print(f"    → Lead Score: {outputs['lead_score']}")
            if 'agent_task' in outputs:
                print(f"    → Task: {outputs['agent_task'][:100]}...")
            
            # Show other interesting fields
            interesting_keys = ['supervisor_complete', 'current_agent', 'needs_rerouting']
            for key in interesting_keys:
                if key in outputs:
                    print(f"    → {key}: {outputs[key]}")


def check_memory_consistency(trace: Dict[str, Any], child_runs: List[Dict[str, Any]]):
    """Check thread_id and memory consistency"""
    print("\n🧵 MEMORY & THREAD CONSISTENCY:")
    
    # Collect all thread_ids
    thread_ids = {}
    
    # From main trace
    main_inputs = trace.get('inputs', {})
    if 'thread_id' in main_inputs:
        thread_ids['main_input'] = main_inputs['thread_id']
    
    # From child runs
    for run in child_runs:
        run_inputs = run.get('inputs', {})
        if 'thread_id' in run_inputs:
            thread_ids[run['name']] = run_inputs['thread_id']
    
    # Check consistency
    unique_threads = set(thread_ids.values())
    if len(unique_threads) == 0:
        print("  ⚠️  No thread_id found!")
    elif len(unique_threads) == 1:
        print(f"  ✅ Thread ID consistent: {list(unique_threads)[0]}")
    else:
        print(f"  ❌ INCONSISTENT thread_ids found:")
        for source, tid in thread_ids.items():
            print(f"     {source}: {tid}")
    
    # Check for checkpoint/memory operations
    print("\n  Memory Operations:")
    memory_ops = []
    for run in child_runs:
        name_lower = run['name'].lower()
        if any(keyword in name_lower for keyword in ['checkpoint', 'memory', 'conversation', 'sqlite']):
            memory_ops.append(run)
            print(f"    - {run['name']}: {run.get('status', 'unknown')}")
            
            # Check outputs for loaded messages
            outputs = run.get('outputs', {})
            if 'messages' in outputs and isinstance(outputs['messages'], list):
                print(f"      Loaded {len(outputs['messages'])} messages")


def analyze_routing(child_runs: List[Dict[str, Any]]):
    """Analyze agent routing decisions"""
    print("\n🚦 ROUTING ANALYSIS:")
    
    # Find supervisor runs
    supervisor_runs = [r for r in child_runs if 'supervisor' in r['name'].lower()]
    
    if supervisor_runs:
        print("  Supervisor Decisions:")
        for i, run in enumerate(supervisor_runs):
            outputs = run.get('outputs', {})
            inputs = run.get('inputs', {})
            
            # Show lead score from inputs
            lead_score = inputs.get('lead_score', 'N/A')
            print(f"\n  Decision #{i+1}:")
            print(f"    Input Lead Score: {lead_score}")
            
            # Show routing decision
            next_agent = outputs.get('next_agent', 'N/A')
            agent_task = outputs.get('agent_task', 'N/A')
            routing_reason = outputs.get('routing_reason', 'N/A')
            
            print(f"    → Routes to: {next_agent}")
            print(f"    → Task: {agent_task}")
            print(f"    → Reason: {routing_reason}")
    
    # Check which agents actually ran
    print("\n  Agents Executed:")
    agents = ['maria', 'carlos', 'sofia']
    for agent in agents:
        agent_runs = [r for r in child_runs if agent in r['name'].lower() and 'supervisor' not in r['name'].lower()]
        if agent_runs:
            print(f"    - {agent.title()}: {len(agent_runs)} time(s)")


def main():
    """Main analysis function"""
    print(f"🔍 LangSmith Trace Debugger")
    print(f"📋 Trace ID: {TRACE_ID}")
    print("=" * 80)
    
    # Fetch the trace
    print("\n📥 Fetching trace data...")
    trace = fetch_trace(TRACE_ID)
    
    if not trace:
        print("❌ Failed to fetch trace. Please check:")
        print("   1. The trace ID is correct")
        print("   2. The API key has access to this project")
        return
    
    # Basic info
    print("\n📊 TRACE OVERVIEW:")
    print(f"  Name: {trace.get('name', 'N/A')}")
    print(f"  Status: {trace.get('status', 'N/A')}")
    print(f"  Run Type: {trace.get('run_type', 'N/A')}")
    print(f"  Start: {format_timestamp(trace.get('start_time'))}")
    print(f"  End: {format_timestamp(trace.get('end_time'))}")
    
    # Calculate duration
    if trace.get('start_time') and trace.get('end_time'):
        try:
            start = datetime.fromisoformat(trace['start_time'].replace('Z', '+00:00').split('.')[0] + '+00:00')
            end = datetime.fromisoformat(trace['end_time'].replace('Z', '+00:00').split('.')[0] + '+00:00')
            duration = (end - start).total_seconds()
            print(f"  Duration: {duration:.2f} seconds")
        except:
            pass
    
    # Analyze input/output
    analyze_input_output(trace)
    
    # Fetch child runs
    print("\n📥 Fetching child runs...")
    child_runs = fetch_child_runs(TRACE_ID)
    print(f"  Found {len(child_runs)} child runs")
    
    if child_runs:
        # Analyze workflow
        analyze_workflow_nodes(child_runs)
        
        # Check memory consistency
        check_memory_consistency(trace, child_runs)
        
        # Analyze routing
        analyze_routing(child_runs)
    
    # Error summary
    print("\n❌ ERROR SUMMARY:")
    errors_found = False
    
    # Check main trace for errors
    if trace.get('error'):
        print(f"  Main trace error: {trace['error']}")
        errors_found = True
    
    # Check child runs for errors
    error_runs = [r for r in child_runs if r.get('error')]
    if error_runs:
        for run in error_runs:
            print(f"  {run['name']}: {run['error']}")
        errors_found = True
    
    if not errors_found:
        print("  ✅ No errors found")
    
    # Save raw data
    print("\n💾 Saving raw data for further analysis...")
    filename = f"trace_debug_{TRACE_ID[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            "trace": trace,
            "child_runs": child_runs,
            "analysis_timestamp": datetime.now().isoformat()
        }, f, indent=2)
    
    print(f"  Saved to: {filename}")
    print("\n✅ Analysis complete!")


if __name__ == "__main__":
    main()
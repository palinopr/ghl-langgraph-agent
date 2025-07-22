#!/usr/bin/env python3
"""
Debug LangSmith trace 1f0672b6-ec5a-6038-aca0-bf769eee3742
Analyzes workflow execution, memory, routing, and errors
"""
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
import httpx
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
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    except:
        return ts


def extract_key_info(data: Any, path: str = "") -> Dict[str, Any]:
    """Extract key information from nested data"""
    result = {}
    
    if isinstance(data, dict):
        for key, value in data.items():
            new_path = f"{path}.{key}" if path else key
            
            # Extract specific keys we're interested in
            if key in ["thread_id", "contact_id", "lead_score", "next_agent", "agent_task", 
                      "routing_reason", "supervisor_complete", "current_agent", "error",
                      "checkpoint_id", "checkpoint_loaded"]:
                result[new_path] = value
            
            # Recurse into nested structures
            if isinstance(value, (dict, list)):
                result.update(extract_key_info(value, new_path))
                
    elif isinstance(data, list):
        for i, item in enumerate(data):
            result.update(extract_key_info(item, f"{path}[{i}]"))
    
    return result


async def fetch_trace(trace_id: str) -> Dict[str, Any]:
    """Fetch a specific trace from LangSmith"""
    async with httpx.AsyncClient() as client:
        headers = {
            "x-api-key": LANGSMITH_API_KEY,
            "Content-Type": "application/json"
        }
        
        # Get the main trace
        trace_url = f"{LANGSMITH_API_URL}/runs/{trace_id}"
        response = await client.get(trace_url, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Failed to fetch trace: {response.status_code}")
            print(f"Response: {response.text}")
            return {}
        
        return response.json()


async def fetch_child_runs(trace_id: str) -> List[Dict[str, Any]]:
    """Fetch all child runs of a trace"""
    async with httpx.AsyncClient() as client:
        headers = {
            "x-api-key": LANGSMITH_API_KEY,
            "Content-Type": "application/json"
        }
        
        # Query for child runs
        query_url = f"{LANGSMITH_API_URL}/runs/query"
        query_data = {
            "parent_run_id": trace_id,
            "limit": 100
        }
        
        response = await client.post(query_url, json=query_data, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Failed to fetch child runs: {response.status_code}")
            return []
        
        result = response.json()
        return result.get("runs", [])


def analyze_trace(trace: Dict[str, Any], child_runs: List[Dict[str, Any]]):
    """Analyze the trace and display findings"""
    print("=" * 80)
    print(f"🔍 TRACE ANALYSIS: {TRACE_ID}")
    print("=" * 80)
    
    # Basic info
    print("\n📋 BASIC INFORMATION:")
    print(f"Name: {trace.get('name', 'N/A')}")
    print(f"Run Type: {trace.get('run_type', 'N/A')}")
    print(f"Status: {trace.get('status', 'N/A')}")
    print(f"Start Time: {format_timestamp(trace.get('start_time'))}")
    print(f"End Time: {format_timestamp(trace.get('end_time'))}")
    
    # Calculate duration
    if trace.get('start_time') and trace.get('end_time'):
        start = datetime.fromisoformat(trace['start_time'].replace('Z', '+00:00'))
        end = datetime.fromisoformat(trace['end_time'].replace('Z', '+00:00'))
        duration = (end - start).total_seconds()
        print(f"Duration: {duration:.2f} seconds")
    
    # Input/Output
    print("\n📥 INPUT:")
    inputs = trace.get('inputs', {})
    if inputs:
        print(json.dumps(inputs, indent=2, ensure_ascii=False)[:500] + "...")
    
    print("\n📤 OUTPUT:")
    outputs = trace.get('outputs', {})
    if outputs:
        print(json.dumps(outputs, indent=2, ensure_ascii=False)[:500] + "...")
    
    # Extract key information
    print("\n🔑 KEY INFORMATION EXTRACTED:")
    key_info = extract_key_info(inputs)
    key_info.update(extract_key_info(outputs))
    
    for key, value in sorted(key_info.items()):
        print(f"  {key}: {value}")
    
    # Thread ID Analysis
    print("\n🧵 THREAD ID CONSISTENCY:")
    thread_ids = []
    contact_ids = []
    
    # Check main trace
    if 'thread_id' in inputs:
        thread_ids.append(('main_input', inputs['thread_id']))
    if 'contact_id' in inputs:
        contact_ids.append(('main_input', inputs['contact_id']))
    
    # Check child runs
    for run in child_runs:
        run_inputs = run.get('inputs', {})
        if 'thread_id' in run_inputs:
            thread_ids.append((run['name'], run_inputs['thread_id']))
        if 'contact_id' in run_inputs:
            contact_ids.append((run['name'], run_inputs['contact_id']))
    
    # Display thread consistency
    if thread_ids:
        unique_threads = set(tid for _, tid in thread_ids)
        if len(unique_threads) == 1:
            print(f"  ✅ Thread ID consistent: {thread_ids[0][1]}")
        else:
            print(f"  ❌ Thread ID INCONSISTENT! Found {len(unique_threads)} different values:")
            for source, tid in thread_ids:
                print(f"     - {source}: {tid}")
    
    # Analyze workflow nodes
    print("\n🔄 WORKFLOW EXECUTION:")
    nodes_executed = []
    errors = []
    
    # Group child runs by name
    node_executions = defaultdict(list)
    for run in sorted(child_runs, key=lambda x: x.get('start_time', '')):
        node_executions[run['name']].append(run)
    
    # Display each node
    for node_name, executions in node_executions.items():
        print(f"\n  📌 {node_name} (executed {len(executions)} time(s)):")
        
        for i, run in enumerate(executions):
            if len(executions) > 1:
                print(f"    Execution {i+1}:")
            
            # Status and timing
            status = run.get('status', 'unknown')
            status_icon = "✅" if status == "success" else "❌"
            print(f"    {status_icon} Status: {status}")
            
            # Key outputs
            outputs = run.get('outputs', {})
            if outputs:
                # Show routing decisions
                if 'next_agent' in outputs:
                    print(f"    → Routed to: {outputs['next_agent']}")
                if 'agent_task' in outputs:
                    print(f"    → Task: {outputs['agent_task']}")
                if 'routing_reason' in outputs:
                    print(f"    → Reason: {outputs['routing_reason']}")
                if 'lead_score' in outputs:
                    print(f"    → Lead Score: {outputs['lead_score']}")
                
            # Errors
            if run.get('error'):
                errors.append((node_name, run['error']))
                print(f"    ❌ ERROR: {run['error']}")
    
    # Checkpoint/Memory Analysis
    print("\n💾 CHECKPOINT/MEMORY ANALYSIS:")
    checkpoint_info = []
    
    for run in child_runs:
        # Look for checkpoint-related information
        if 'checkpoint' in run['name'].lower() or 'sqlite' in str(run.get('inputs', {})).lower():
            checkpoint_info.append(run)
        
        # Check for conversation loading
        if 'conversation' in run['name'].lower() or 'memory' in run['name'].lower():
            print(f"  Found memory operation: {run['name']}")
            if run.get('outputs'):
                print(f"    Output: {json.dumps(run['outputs'], indent=2)[:200]}...")
    
    # Routing Analysis
    print("\n🚦 ROUTING ANALYSIS:")
    
    # Find supervisor decisions
    supervisor_runs = [r for r in child_runs if 'supervisor' in r['name'].lower()]
    if supervisor_runs:
        for run in supervisor_runs:
            outputs = run.get('outputs', {})
            print(f"  Supervisor Decision:")
            print(f"    - Next Agent: {outputs.get('next_agent', 'N/A')}")
            print(f"    - Task: {outputs.get('agent_task', 'N/A')}")
            print(f"    - Reason: {outputs.get('routing_reason', 'N/A')}")
    
    # Find which agent handled the request
    agent_nodes = ['maria', 'carlos', 'sofia']
    for agent in agent_nodes:
        agent_runs = [r for r in child_runs if agent in r['name'].lower()]
        if agent_runs:
            print(f"  {agent.title()} executed: {len(agent_runs)} time(s)")
    
    # Error Summary
    if errors:
        print("\n❌ ERRORS FOUND:")
        for node, error in errors:
            print(f"  - {node}: {error}")
    else:
        print("\n✅ No errors detected")
    
    # Performance Analysis
    print("\n⚡ PERFORMANCE:")
    
    # Node execution times
    node_times = []
    for run in child_runs:
        if run.get('start_time') and run.get('end_time'):
            start = datetime.fromisoformat(run['start_time'].replace('Z', '+00:00'))
            end = datetime.fromisoformat(run['end_time'].replace('Z', '+00:00'))
            duration = (end - start).total_seconds()
            node_times.append((run['name'], duration))
    
    # Sort by duration
    node_times.sort(key=lambda x: x[1], reverse=True)
    
    print("  Slowest operations:")
    for name, duration in node_times[:5]:
        print(f"    - {name}: {duration:.2f}s")
    
    # Final Summary
    print("\n📊 SUMMARY:")
    print(f"  Total Nodes Executed: {len(child_runs)}")
    print(f"  Unique Node Types: {len(node_executions)}")
    print(f"  Errors Encountered: {len(errors)}")
    print(f"  Thread Consistency: {'✅ Consistent' if len(unique_threads) == 1 else '❌ Inconsistent'}")


async def main():
    """Main analysis function"""
    print(f"🔍 Fetching trace {TRACE_ID}...")
    
    # Fetch the trace
    trace = await fetch_trace(TRACE_ID)
    if not trace:
        print("❌ Failed to fetch trace")
        return
    
    # Fetch child runs
    print("📥 Fetching child runs...")
    child_runs = await fetch_child_runs(TRACE_ID)
    print(f"  Found {len(child_runs)} child runs")
    
    # Analyze
    analyze_trace(trace, child_runs)
    
    # Save raw data for further analysis
    print("\n💾 Saving raw data...")
    
    raw_data = {
        "trace": trace,
        "child_runs": child_runs,
        "analysis_time": datetime.now().isoformat()
    }
    
    filename = f"trace_analysis_{TRACE_ID[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(raw_data, f, indent=2, ensure_ascii=False)
    
    print(f"  Saved to: {filename}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
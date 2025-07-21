#!/usr/bin/env python3
"""
Analyze production traces to understand why Maria repeats business type questions
"""

import os
import json
from langsmith import Client
from datetime import datetime
from typing import Dict, List, Any

# Initialize LangSmith client
client = Client(api_key="sv2_pt_6bd7e1832238416a974c51b9f53aafdd_76c2a36c0d")

# Trace IDs to analyze
trace_ids = [
    "1f0666ce-dd6e-602b-9a98-381d8a6d73e4",
    "1f0666cf-d7c4-6f3f-b89f-d384ff4c6ba0"
]

def extract_relevant_info(run_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract relevant information from a run"""
    info = {
        "id": run_data.get("id"),
        "name": run_data.get("name"),
        "run_type": run_data.get("run_type"),
        "status": run_data.get("status"),
        "start_time": run_data.get("start_time"),
        "end_time": run_data.get("end_time"),
        "inputs": run_data.get("inputs", {}),
        "outputs": run_data.get("outputs", {}),
        "error": run_data.get("error"),
        "extra": run_data.get("extra", {})
    }
    
    # Extract metadata
    if "metadata" in run_data.get("extra", {}):
        info["metadata"] = run_data["extra"]["metadata"]
    
    return info

def find_maria_interactions(runs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Find all Maria agent interactions"""
    maria_runs = []
    
    for run in runs:
        if run.get("name") == "maria_agent_v2" or "maria" in run.get("name", "").lower():
            maria_runs.append(run)
    
    return maria_runs

def find_extracted_data(runs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Find all instances where extracted_data is present"""
    extracted_data_instances = []
    
    for run in runs:
        # Check in inputs
        if "state" in run.get("inputs", {}):
            state = run["inputs"]["state"]
            if isinstance(state, dict) and "extracted_data" in state:
                extracted_data_instances.append({
                    "run_name": run.get("name"),
                    "run_id": run.get("id"),
                    "extracted_data": state["extracted_data"],
                    "timestamp": run.get("start_time")
                })
        
        # Check in outputs
        if "extracted_data" in run.get("outputs", {}):
            extracted_data_instances.append({
                "run_name": run.get("name"),
                "run_id": run.get("id"),
                "extracted_data": run["outputs"]["extracted_data"],
                "timestamp": run.get("end_time")
            })
    
    return extracted_data_instances

def analyze_message_flow(runs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Analyze the flow of messages through the system"""
    message_flow = []
    
    for run in runs:
        # Look for messages in inputs/outputs
        messages = []
        
        if "messages" in run.get("inputs", {}).get("state", {}):
            messages = run["inputs"]["state"]["messages"]
        elif "messages" in run.get("outputs", {}):
            messages = run["outputs"]["messages"]
        
        if messages:
            message_flow.append({
                "run_name": run.get("name"),
                "run_id": run.get("id"),
                "message_count": len(messages) if isinstance(messages, list) else 1,
                "timestamp": run.get("start_time"),
                "messages": messages[-3:] if isinstance(messages, list) else messages  # Last 3 messages
            })
    
    return message_flow

def main():
    for trace_id in trace_ids:
        print(f"\n{'='*80}")
        print(f"Analyzing Trace: {trace_id}")
        print(f"{'='*80}")
        
        try:
            # Fetch the trace
            trace = client.read_run(trace_id)
            
            # Get all child runs
            child_runs = list(client.list_runs(
                project_name="langgraph-ghl-agent",
                trace_id=trace_id,
                execution_order=1
            ))
            
            print(f"\nTotal runs in trace: {len(child_runs)}")
            
            # Find Maria interactions
            maria_runs = find_maria_interactions(child_runs)
            print(f"\nMaria agent runs: {len(maria_runs)}")
            
            # Analyze each Maria run
            for i, maria_run in enumerate(maria_runs):
                print(f"\n--- Maria Run {i+1} ---")
                print(f"Run ID: {maria_run.get('id')}")
                print(f"Start time: {maria_run.get('start_time')}")
                
                # Check inputs
                if "state" in maria_run.get("inputs", {}):
                    state = maria_run["inputs"]["state"]
                    
                    # Check extracted_data
                    if "extracted_data" in state:
                        print("\nExtracted Data in Input:")
                        print(json.dumps(state["extracted_data"], indent=2, ensure_ascii=False))
                    
                    # Check last few messages
                    if "messages" in state and isinstance(state["messages"], list):
                        print(f"\nLast 3 messages before Maria:")
                        for msg in state["messages"][-3:]:
                            if isinstance(msg, dict):
                                print(f"  - {msg.get('type', 'unknown')}: {msg.get('content', '')[:100]}...")
                
                # Check outputs
                if "response" in maria_run.get("outputs", {}):
                    print(f"\nMaria's Response:")
                    print(f"  {maria_run['outputs']['response'][:200]}...")
            
            # Find all extracted_data instances
            print(f"\n{'='*40}")
            print("All Extracted Data Instances:")
            print(f"{'='*40}")
            
            extracted_data_instances = find_extracted_data(child_runs)
            for instance in extracted_data_instances:
                print(f"\nRun: {instance['run_name']} ({instance['run_id'][:8]}...)")
                print(f"Timestamp: {instance['timestamp']}")
                print(f"Extracted Data: {json.dumps(instance['extracted_data'], indent=2, ensure_ascii=False)}")
            
            # Analyze message flow
            print(f"\n{'='*40}")
            print("Message Flow Analysis:")
            print(f"{'='*40}")
            
            # Look for "restaurante" mentions
            restaurante_mentions = []
            for run in child_runs:
                if "state" in run.get("inputs", {}):
                    messages = run["inputs"]["state"].get("messages", [])
                    if isinstance(messages, list):
                        for msg in messages:
                            if isinstance(msg, dict) and "restaurante" in str(msg.get("content", "")).lower():
                                restaurante_mentions.append({
                                    "run_name": run.get("name"),
                                    "message": msg.get("content", "")[:200],
                                    "timestamp": run.get("start_time")
                                })
            
            print(f"\nFound {len(restaurante_mentions)} mentions of 'restaurante':")
            for mention in restaurante_mentions:
                print(f"\n- In {mention['run_name']}:")
                print(f"  Message: {mention['message']}...")
            
            # Look for supervisor decisions
            print(f"\n{'='*40}")
            print("Supervisor Decisions:")
            print(f"{'='*40}")
            
            supervisor_runs = [r for r in child_runs if "supervisor" in r.get("name", "").lower()]
            for sup_run in supervisor_runs:
                if "next" in sup_run.get("outputs", {}):
                    print(f"\nSupervisor ({sup_run['id'][:8]}...) decided: {sup_run['outputs']['next']}")
                    if "state" in sup_run.get("inputs", {}):
                        extracted = sup_run["inputs"]["state"].get("extracted_data", {})
                        print(f"  Extracted data at decision: {json.dumps(extracted, ensure_ascii=False)}")
            
        except Exception as e:
            print(f"Error analyzing trace {trace_id}: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
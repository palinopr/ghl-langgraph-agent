#!/usr/bin/env python3
"""Fetch and analyze a specific LangSmith trace."""

import os
import json
import requests
from datetime import datetime
from typing import Dict, List, Any

# LangSmith API configuration
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_API_URL = "https://api.smith.langchain.com"

def fetch_trace(trace_id: str) -> Dict[str, Any]:
    """Fetch a specific trace from LangSmith."""
    headers = {
        "x-api-key": LANGSMITH_API_KEY,
        "Content-Type": "application/json"
    }
    
    # Get the trace
    trace_url = f"{LANGSMITH_API_URL}/runs/{trace_id}"
    response = requests.get(trace_url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error fetching trace: {response.status_code}")
        print(f"Response: {response.text}")
        return None
    
    return response.json()

def fetch_trace_children(trace_id: str) -> List[Dict[str, Any]]:
    """Fetch all child runs of a trace."""
    headers = {
        "x-api-key": LANGSMITH_API_KEY,
        "Content-Type": "application/json"
    }
    
    # Get child runs
    children_url = f"{LANGSMITH_API_URL}/runs?parent_run={trace_id}"
    response = requests.get(children_url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error fetching children: {response.status_code}")
        return []
    
    return response.json().get("runs", [])

def analyze_trace(trace_id: str):
    """Analyze a LangSmith trace in detail."""
    print(f"Fetching trace: {trace_id}")
    print("=" * 80)
    
    # Fetch the main trace
    trace = fetch_trace(trace_id)
    if not trace:
        return
    
    # Basic trace information
    print("\n## TRACE OVERVIEW")
    print(f"Name: {trace.get('name', 'N/A')}")
    print(f"Run Type: {trace.get('run_type', 'N/A')}")
    print(f"Status: {trace.get('status', 'N/A')}")
    print(f"Start Time: {trace.get('start_time', 'N/A')}")
    print(f"End Time: {trace.get('end_time', 'N/A')}")
    
    if trace.get('error'):
        print(f"\n⚠️  ERROR: {trace.get('error')}")
    
    # Input data
    if trace.get('inputs'):
        print("\n## INPUTS")
        print(json.dumps(trace.get('inputs'), indent=2))
    
    # Output data
    if trace.get('outputs'):
        print("\n## OUTPUTS")
        print(json.dumps(trace.get('outputs'), indent=2))
    
    # Metadata
    if trace.get('extra', {}).get('metadata'):
        print("\n## METADATA")
        print(json.dumps(trace.get('extra', {}).get('metadata'), indent=2))
    
    # Fetch and analyze child runs
    print("\n## CHILD RUNS")
    children = fetch_trace_children(trace_id)
    
    if children:
        print(f"Found {len(children)} child runs:")
        for i, child in enumerate(children):
            print(f"\n### Child Run {i+1}: {child.get('name', 'N/A')}")
            print(f"Type: {child.get('run_type', 'N/A')}")
            print(f"Status: {child.get('status', 'N/A')}")
            
            if child.get('error'):
                print(f"⚠️  ERROR: {child.get('error')}")
            
            # Show inputs/outputs for specific run types
            if child.get('run_type') in ['llm', 'chain', 'tool']:
                if child.get('inputs'):
                    print(f"Inputs: {json.dumps(child.get('inputs'), indent=2)[:500]}...")
                if child.get('outputs'):
                    print(f"Outputs: {json.dumps(child.get('outputs'), indent=2)[:500]}...")
    else:
        print("No child runs found.")
    
    # Events and feedback
    if trace.get('events'):
        print("\n## EVENTS")
        for event in trace.get('events', []):
            print(f"- {event}")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    trace_id = "1f065dba-a87b-68cb-b397-963a5f264096"
    
    if not LANGSMITH_API_KEY:
        print("Error: LANGSMITH_API_KEY environment variable not set")
        exit(1)
    
    analyze_trace(trace_id)
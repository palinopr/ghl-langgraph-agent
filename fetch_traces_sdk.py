#!/usr/bin/env python3
"""
Fetch recent traces using LangSmith SDK
"""
import os
from langsmith import Client
from datetime import datetime
import json

# Create client
client = Client()

def get_recent_runs(project_name=None, limit=3):
    """Fetch recent runs from LangSmith"""
    project_name = project_name or os.getenv("LANGCHAIN_PROJECT", "ghl-langgraph-agent")
    
    print(f"Fetching runs from project: {project_name}")
    
    # List runs
    runs = list(client.list_runs(
        project_name=project_name,
        limit=limit,
        execution_order=1,  # Root runs only
    ))
    
    return runs

def format_run(run):
    """Format a run for display"""
    print(f"\n{'='*60}")
    print(f"Run ID: {run.id}")
    print(f"Name: {run.name}")
    print(f"Status: {run.status}")
    print(f"Start Time: {run.start_time}")
    print(f"End Time: {run.end_time}")
    
    # Show inputs
    if run.inputs:
        print("\nInputs:")
        # Extract message if available
        messages = run.inputs.get("messages", [])
        if messages:
            for msg in messages:
                if isinstance(msg, dict):
                    role = msg.get("type", msg.get("role", "unknown"))
                    content = msg.get("content", "")
                    print(f"  {role}: {content[:100]}...")
        else:
            print(f"  {str(run.inputs)[:200]}...")
    
    # Show outputs
    if run.outputs:
        print("\nOutputs:")
        output_str = json.dumps(run.outputs, indent=2)
        print(f"  {output_str[:300]}..." if len(output_str) > 300 else f"  {output_str}")
    
    # Show error if any
    if run.error:
        print(f"\nError: {run.error}")
    
    # Show trace URL
    print(f"\nTrace URL: https://smith.langchain.com/public/{run.id}/r")

def main():
    try:
        runs = get_recent_runs(limit=3)
        
        if not runs:
            print("No runs found")
            return
        
        print(f"\nFound {len(runs)} recent runs:")
        
        for run in runs:
            format_run(run)
            
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure you have:")
        print("1. LANGCHAIN_API_KEY set in your environment")
        print("2. The correct project name")

if __name__ == "__main__":
    main()
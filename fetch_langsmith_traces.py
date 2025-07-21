#!/usr/bin/env python3
"""
Fetch recent traces from LangSmith API
"""
import os
import requests
from datetime import datetime, timedelta
import json

# Get API key from environment
LANGSMITH_API_KEY = os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGSMITH_API_KEY")
if not LANGSMITH_API_KEY:
    print("Error: LANGCHAIN_API_KEY or LANGSMITH_API_KEY not set")
    exit(1)

# API configuration
BASE_URL = "https://api.smith.langchain.com"
PROJECT_NAME = os.getenv("LANGCHAIN_PROJECT", "ghl-langgraph-agent")

def get_recent_runs(limit=3):
    """Fetch recent runs from LangSmith"""
    headers = {
        "x-api-key": LANGSMITH_API_KEY,
        "Content-Type": "application/json"
    }
    
    # First, get the project ID
    projects_url = f"{BASE_URL}/projects"
    response = requests.get(projects_url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error fetching projects: {response.status_code}")
        print(response.text)
        return None
        
    projects = response.json()
    project_id = None
    
    for project in projects:
        if project.get("name") == PROJECT_NAME:
            project_id = project.get("id")
            break
    
    if not project_id:
        print(f"Project '{PROJECT_NAME}' not found")
        return None
    
    print(f"Found project: {PROJECT_NAME} (ID: {project_id})")
    
    # Now fetch recent runs
    runs_url = f"{BASE_URL}/runs"
    params = {
        "project_id": project_id,
        "limit": limit,
        "order": "desc"  # Most recent first
    }
    
    response = requests.get(runs_url, headers=headers, params=params)
    
    if response.status_code != 200:
        print(f"Error fetching runs: {response.status_code}")
        print(response.text)
        return None
    
    return response.json()

def format_run(run):
    """Format a run for display"""
    run_id = run.get("id", "Unknown")
    name = run.get("name", "Unknown")
    status = run.get("status", "Unknown")
    start_time = run.get("start_time", "")
    inputs = run.get("inputs", {})
    outputs = run.get("outputs", {})
    error = run.get("error")
    
    # Extract message from inputs
    messages = inputs.get("messages", [])
    user_message = "No message"
    if messages:
        for msg in messages:
            if isinstance(msg, dict) and msg.get("type") == "human":
                user_message = msg.get("content", "No content")
                break
    
    print(f"\n{'='*60}")
    print(f"Run ID: {run_id}")
    print(f"Name: {name}")
    print(f"Status: {status}")
    print(f"Start Time: {start_time}")
    print(f"User Message: {user_message}")
    
    if error:
        print(f"Error: {error}")
    
    # Show outputs if available
    if outputs:
        print("\nOutputs:")
        print(json.dumps(outputs, indent=2)[:500] + "..." if len(str(outputs)) > 500 else json.dumps(outputs, indent=2))

def main():
    print(f"Fetching last 3 runs from LangSmith project: {PROJECT_NAME}")
    print(f"Using API key: {LANGSMITH_API_KEY[:10]}...")
    
    runs = get_recent_runs(3)
    
    if not runs:
        print("No runs found or error occurred")
        return
    
    print(f"\nFound {len(runs)} recent runs:")
    
    for run in runs:
        format_run(run)

if __name__ == "__main__":
    main()
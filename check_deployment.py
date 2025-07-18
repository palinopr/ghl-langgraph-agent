#!/usr/bin/env python3
"""Quick deployment check using LangSmith API"""
import os
import requests
from datetime import datetime

# Get API key from environment or file
api_key = os.getenv("LANGCHAIN_API_KEY", "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")
project_name = "ghl-langgraph-agent"

headers = {
    "x-api-key": api_key,
    "Content-Type": "application/json"
}

# Check project
print(f"Checking LangSmith project: {project_name}")
print("=" * 50)

# Get recent runs
url = "https://api.smith.langchain.com/runs"
params = {
    "project_name": project_name,
    "limit": 5
}

try:
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        if data:
            print(f"Found {len(data)} recent runs")
            for run in data[:5]:
                print(f"\n- Run ID: {run.get('id')}")
                print(f"  Status: {run.get('status')}")
                print(f"  Name: {run.get('name')}")
                print(f"  Start: {run.get('start_time')}")
        else:
            print("No runs found yet. The deployment might still be building.")
    else:
        print(f"API Error: {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"Error: {e}")

print("\nTo check deployment status:")
print("1. Go to https://smith.langchain.com")
print("2. Click on 'LangGraph Platform' in the left menu")
print("3. Look for your deployment 'ghl-langgraph-agent'")
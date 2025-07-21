#!/usr/bin/env python3
"""Fetch LangSmith trace using urllib."""

import os
import json
import urllib.request
import urllib.error
from datetime import datetime

# LangSmith API configuration
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_API_URL = "https://api.smith.langchain.com"

def fetch_trace(trace_id: str):
    """Fetch a specific trace from LangSmith."""
    headers = {
        "x-api-key": LANGSMITH_API_KEY,
        "Content-Type": "application/json"
    }
    
    # Get the trace
    trace_url = f"{LANGSMITH_API_URL}/runs/{trace_id}"
    
    req = urllib.request.Request(trace_url, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data
    except urllib.error.HTTPError as e:
        print(f"Error fetching trace: {e.code}")
        print(f"Response: {e.read().decode('utf-8')}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def analyze_trace(trace_id: str):
    """Analyze a LangSmith trace."""
    print(f"Fetching trace: {trace_id}")
    print("=" * 80)
    
    trace = fetch_trace(trace_id)
    if not trace:
        return
    
    # Pretty print the entire trace
    print(json.dumps(trace, indent=2, default=str))

if __name__ == "__main__":
    trace_id = "1f065dba-a87b-68cb-b397-963a5f264096"
    
    if not LANGSMITH_API_KEY:
        print("Error: LANGSMITH_API_KEY environment variable not set")
        print("Checking if it might be available in .env file...")
        
        # Try to load from .env
        env_path = ".env"
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    if line.startswith('LANGCHAIN_API_KEY='):
                        LANGSMITH_API_KEY = line.strip().split('=', 1)[1]
                        os.environ['LANGSMITH_API_KEY'] = LANGSMITH_API_KEY
                        print("Found API key in .env file")
                        break
        
        if not LANGSMITH_API_KEY:
            exit(1)
    
    analyze_trace(trace_id)
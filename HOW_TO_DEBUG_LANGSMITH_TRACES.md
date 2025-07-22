# How to Debug LangSmith Traces - Complete Guide

## What I Did to Analyze Your Traces

### 1. Got Your Trace IDs
You provided 4 trace IDs:
```
1f0669c6-a989-67ec-a016-8f63b91f79c2
1f0669c7-6120-6563-b484-e5ca2a2740d1
1f0669c8-709c-6207-9a9f-ac54af55789c
1f0669c9-c860-6dac-9fd9-2f962b941a71
```

### 2. Created Analysis Script
Created `analyze_specific_traces.py`:
```python
from langsmith import Client

# Your API key
api_key = "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"

client = Client(
    api_key=api_key,
    api_url="https://api.smith.langchain.com"
)

# Fetch each trace
run = client.read_run(trace_id)

# Get child runs
child_runs = list(client.list_runs(
    project_name="ghl-langgraph-agent",
    filter=f'eq(parent_run_id, "{trace_id}")'
))
```

### 3. Ran the Analysis
```bash
source venv/bin/activate
pip install langsmith rich
python analyze_specific_traces.py
```

### 4. Created Full Debug Script
Created `full_raw_debug.py` to dump ALL data:
```python
def full_debug_trace(run_id):
    run = client.read_run(run_id)
    
    # Show everything
    print(f"Name: {run.name}")
    print(f"Status: {run.status}")
    print(f"Inputs: {run.inputs}")
    print(f"Outputs: {run.outputs}")
    print(f"Metadata: {run.metadata}")
    print(f"Token Usage: {run.total_tokens}")
    
    # Get all child runs
    child_runs = list(client.list_runs(
        project_name="ghl-langgraph-agent",
        filter=f'eq(parent_run_id, "{run_id}")'
    ))
```

### 5. Saved Full Output
```bash
python full_raw_debug.py > FULL_DEBUG_OUTPUT.txt 2>&1
```

### 6. Discovered the Problem
By comparing thread_ids across traces:
- Trace 1: `thread_id: d779d1e2-ee2c-458d-8ce6-8828d106ad7f`
- Trace 2: `thread_id: 0dbc1c79-30eb-4a12-9509-dbd17eb0d4bd` (DIFFERENT!)
- Trace 3: `thread_id: 3969eb20-54d1-41a9-a201-2da88df6a578` (DIFFERENT!)
- Trace 4: `thread_id: c95ee525-421e-4810-8887-4bd2ce0e4746` (DIFFERENT!)

Each message had a different thread_id = No conversation memory!

## Complete Step-by-Step Process

### Step 1: Install Dependencies
```bash
source venv/bin/activate
pip install langsmith rich
```

### Step 2: Create Analysis Script
Save as `analyze_traces.py`:
```python
#!/usr/bin/env python3
from langsmith import Client
from rich.console import Console
import json

console = Console()

# Initialize client
client = Client(
    api_key="YOUR_LANGSMITH_API_KEY",
    api_url="https://api.smith.langchain.com"
)

# Your trace IDs
TRACE_IDS = ["trace-id-1", "trace-id-2"]

for trace_id in TRACE_IDS:
    console.print(f"\n[bold]Analyzing {trace_id}[/bold]")
    
    # Get the run
    run = client.read_run(trace_id)
    
    # Extract key info
    console.print(f"Message: {run.inputs.get('messages', [{}])[0].get('content')}")
    console.print(f"Thread ID: {run.metadata.get('thread_id')}")
    console.print(f"Lead Score: {run.outputs.get('lead_score')}")
    console.print(f"Response: {run.outputs.get('messages', [{}])[-1].get('content')}")
    
    # Get child runs
    child_runs = list(client.list_runs(
        project_name="ghl-langgraph-agent",
        filter=f'eq(parent_run_id, "{trace_id}")'
    ))
    console.print(f"Child runs: {len(child_runs)}")
```

### Step 3: Run Analysis
```bash
python analyze_traces.py
```

### Step 4: Create Full Debug Dump
Save as `debug_all.py`:
```python
#!/usr/bin/env python3
from langsmith import Client

client = Client(api_key="YOUR_KEY")

def debug_trace(run_id):
    run = client.read_run(run_id)
    
    print(f"\n{'='*80}")
    print(f"TRACE: {run_id}")
    print(f"{'='*80}")
    print(f"Status: {run.status}")
    print(f"Start: {run.start_time}")
    print(f"End: {run.end_time}")
    print(f"\nINPUTS:")
    print(run.inputs)
    print(f"\nOUTPUTS:")
    print(run.outputs)
    print(f"\nMETADATA:")
    print(run.metadata)
    
    # Get child runs
    children = list(client.list_runs(
        project_name="ghl-langgraph-agent",
        filter=f'eq(parent_run_id, "{run_id}")'
    ))
    
    print(f"\nCHILD RUNS ({len(children)}):")
    for child in children:
        print(f"- {child.name}: {child.status}")

# Debug all traces
traces = ["id1", "id2", "id3", "id4"]
for trace in traces:
    debug_trace(trace)
```

### Step 5: Save Output
```bash
python debug_all.py > FULL_DEBUG.txt 2>&1
```

### Step 6: Analyze Results
Look for:
1. **Thread ID changes** - Should be same for conversation
2. **Extracted data loss** - Data should persist
3. **Score regression** - Score should increase with info
4. **Response repetition** - Asking same questions

## Quick Reference Commands

### Get Single Trace
```python
run = client.read_run("trace-id-here")
print(run.inputs)
print(run.outputs)
print(run.metadata)
```

### Get All Child Runs
```python
children = list(client.list_runs(
    project_name="ghl-langgraph-agent",
    filter=f'eq(parent_run_id, "{trace_id}")'
))
```

### Extract Key Data
```python
# Message
message = run.inputs.get('messages', [{}])[0].get('content')

# Thread ID
thread_id = run.metadata.get('thread_id')

# Lead Score
score = run.outputs.get('lead_score')

# Agent Response
response = run.outputs.get('messages', [{}])[-1].get('content')
```

## Files Created
1. `analyze_specific_traces.py` - Main analysis script
2. `full_raw_debug.py` - Complete debug dump
3. `trace_every_step.py` - Step-by-step tracer
4. `FULL_DEBUG_OUTPUT.txt` - Raw output (2315 lines)
5. `COMPLETE_TRACE_ANALYSIS.md` - Analysis summary
6. `FULL_DEBUG_ALL_TRACES.md` - Key findings

## The Discovery
By running these scripts, I found that each message from the same contact had a different thread_id, causing the agent to forget everything between messages!
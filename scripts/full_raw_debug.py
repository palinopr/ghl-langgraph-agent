#!/usr/bin/env python3
"""
Full Raw Debug Output for All Traces
Shows complete details for each trace with all data
"""

import os
import json
from datetime import datetime
from langsmith import Client
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel

console = Console()

# Your API key
api_key = "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"

# Initialize client
client = Client(
    api_key=api_key,
    api_url="https://api.smith.langchain.com"
)

# Your specific trace IDs
TRACE_IDS = [
    "1f0669c6-a989-67ec-a016-8f63b91f79c2",
    "1f0669c7-6120-6563-b484-e5ca2a2740d1",
    "1f0669c8-709c-6207-9a9f-ac54af55789c",
    "1f0669c9-c860-6dac-9fd9-2f962b941a71"
]

def full_debug_trace(run_id: str, index: int):
    """Show complete raw debug for a trace"""
    console.print(f"\n[bold red]{'='*80}[/bold red]")
    console.print(f"[bold yellow]TRACE {index}: {run_id}[/bold yellow]")
    console.print(f"[bold red]{'='*80}[/bold red]")
    
    try:
        # Get the run
        run = client.read_run(run_id)
        
        # 1. BASIC INFO
        console.print("\n[bold cyan]1. BASIC INFO:[/bold cyan]")
        console.print(f"Name: {run.name}")
        console.print(f"Status: {run.status}")
        console.print(f"Type: {run.run_type}")
        console.print(f"Start: {run.start_time}")
        console.print(f"End: {run.end_time}")
        console.print(f"Parent: {run.parent_run_id or 'None'}")
        console.print(f"Error: {run.error or 'None'}")
        
        # 2. FULL METADATA
        console.print("\n[bold cyan]2. FULL METADATA:[/bold cyan]")
        if run.metadata:
            console.print(Syntax(json.dumps(run.metadata, indent=2), "json", theme="monokai"))
        else:
            console.print("No metadata")
        
        # 3. FULL INPUTS
        console.print("\n[bold cyan]3. FULL INPUTS:[/bold cyan]")
        if run.inputs:
            console.print(Syntax(json.dumps(run.inputs, indent=2), "json", theme="monokai"))
        else:
            console.print("No inputs")
        
        # 4. FULL OUTPUTS
        console.print("\n[bold cyan]4. FULL OUTPUTS:[/bold cyan]")
        if run.outputs:
            console.print(Syntax(json.dumps(run.outputs, indent=2), "json", theme="monokai"))
        else:
            console.print("No outputs")
        
        # 5. EXTRA DATA
        console.print("\n[bold cyan]5. EXTRA DATA:[/bold cyan]")
        if run.extra:
            console.print(Syntax(json.dumps(run.extra, indent=2), "json", theme="monokai"))
        else:
            console.print("No extra data")
        
        # 6. TOKEN USAGE
        console.print("\n[bold cyan]6. TOKEN USAGE:[/bold cyan]")
        console.print(f"Total Tokens: {run.total_tokens or 0}")
        console.print(f"Prompt Tokens: {run.prompt_tokens or 0}")
        console.print(f"Completion Tokens: {run.completion_tokens or 0}")
        console.print(f"Total Cost: ${run.total_cost or 0}")
        console.print(f"Prompt Cost: ${run.prompt_cost or 0}")
        console.print(f"Completion Cost: ${run.completion_cost or 0}")
        
        # 7. EVENTS
        console.print("\n[bold cyan]7. EVENTS:[/bold cyan]")
        if hasattr(run, 'events') and run.events:
            for i, event in enumerate(run.events[:5], 1):
                console.print(f"Event {i}: {event}")
        else:
            console.print("No events")
        
        # 8. TAGS
        console.print("\n[bold cyan]8. TAGS:[/bold cyan]")
        if run.tags:
            console.print(f"Tags: {', '.join(run.tags)}")
        else:
            console.print("No tags")
        
        # 9. ALL CHILD RUNS
        console.print("\n[bold cyan]9. ALL CHILD RUNS:[/bold cyan]")
        child_runs = list(client.list_runs(
            project_name="ghl-langgraph-agent",
            filter=f'eq(parent_run_id, "{run_id}")',
            limit=100
        ))
        
        console.print(f"Total child runs: {len(child_runs)}")
        
        for i, child in enumerate(child_runs, 1):
            console.print(f"\n[yellow]Child {i}: {child.name}[/yellow]")
            console.print(f"  ID: {child.id}")
            console.print(f"  Type: {child.run_type}")
            console.print(f"  Status: {child.status}")
            console.print(f"  Start: {child.start_time}")
            console.print(f"  End: {child.end_time}")
            
            if child.inputs:
                console.print("  [dim]Inputs:[/dim]")
                input_str = json.dumps(child.inputs, indent=4)
                for line in input_str.split('\n')[:10]:  # First 10 lines
                    console.print(f"    {line}")
                if len(input_str.split('\n')) > 10:
                    console.print("    ...")
                    
            if child.outputs:
                console.print("  [dim]Outputs:[/dim]")
                output_str = json.dumps(child.outputs, indent=4)
                for line in output_str.split('\n')[:10]:  # First 10 lines
                    console.print(f"    {line}")
                if len(output_str.split('\n')) > 10:
                    console.print("    ...")
            
            if child.error:
                console.print(f"  [red]Error: {child.error}[/red]")
        
        # 10. FEEDBACK
        console.print("\n[bold cyan]10. FEEDBACK:[/bold cyan]")
        try:
            feedbacks = list(client.list_feedback(run_ids=[run_id]))
            if feedbacks:
                for feedback in feedbacks:
                    console.print(f"Feedback: {feedback}")
            else:
                console.print("No feedback")
        except:
            console.print("Could not fetch feedback")
        
        # 11. RAW RUN OBJECT
        console.print("\n[bold cyan]11. RAW RUN OBJECT ATTRIBUTES:[/bold cyan]")
        for attr in dir(run):
            if not attr.startswith('_'):
                try:
                    value = getattr(run, attr)
                    if not callable(value):
                        console.print(f"{attr}: {value}")
                except:
                    pass
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        import traceback
        console.print(traceback.format_exc())

def main():
    """Show full debug for all traces"""
    console.print("[bold magenta]FULL RAW DEBUG OUTPUT[/bold magenta]")
    console.print(f"Analyzing {len(TRACE_IDS)} traces")
    console.print(f"Timestamp: {datetime.now()}")
    
    for i, trace_id in enumerate(TRACE_IDS, 1):
        full_debug_trace(trace_id, i)
    
    console.print(f"\n[bold green]{'='*80}[/bold green]")
    console.print("[bold green]DEBUG COMPLETE[/bold green]")
    console.print(f"[bold green]{'='*80}[/bold green]")

if __name__ == "__main__":
    main()
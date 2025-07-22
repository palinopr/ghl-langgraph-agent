#!/usr/bin/env python3
"""
Analyze Specific LangSmith Traces
Fetches and analyzes the exact traces you provided
"""

import os
from datetime import datetime
from langsmith import Client
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.tree import Tree
import json

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

def analyze_trace(run_id: str):
    """Analyze a specific trace in detail"""
    console.print(f"\n[bold blue]━━━ Analyzing Trace: {run_id} ━━━[/bold blue]")
    
    try:
        # Get the run
        run = client.read_run(run_id)
        
        # Basic info panel
        info = f"""
[cyan]Name:[/cyan] {run.name}
[cyan]Status:[/cyan] {run.status}
[cyan]Type:[/cyan] {run.run_type}
[cyan]Start:[/cyan] {run.start_time}
[cyan]End:[/cyan] {run.end_time}
[cyan]Parent:[/cyan] {run.parent_run_id or 'None'}
        """
        console.print(Panel(info.strip(), title="Run Information", border_style="blue"))
        
        # Show metadata
        if run.metadata:
            console.print("\n[yellow]Metadata:[/yellow]")
            console.print(Syntax(
                json.dumps(run.metadata, indent=2),
                "json",
                theme="monokai"
            ))
        
        # Show inputs
        if run.inputs:
            console.print("\n[cyan]Inputs:[/cyan]")
            # Pretty print based on type
            if isinstance(run.inputs, dict):
                # Check if it's a state object
                if "messages" in run.inputs:
                    console.print("  [dim]State object with fields:[/dim]")
                    for key, value in run.inputs.items():
                        if key == "messages":
                            console.print(f"    • messages: {len(value)} messages")
                        elif isinstance(value, dict):
                            console.print(f"    • {key}: {json.dumps(value, indent=6)}")
                        else:
                            console.print(f"    • {key}: {value}")
                else:
                    console.print(Syntax(
                        json.dumps(run.inputs, indent=2),
                        "json",
                        theme="monokai"
                    ))
            else:
                console.print(f"  {run.inputs}")
        
        # Show outputs
        if run.outputs:
            console.print("\n[green]Outputs:[/green]")
            if isinstance(run.outputs, dict):
                # Check for agent response
                if "messages" in run.outputs:
                    messages = run.outputs.get("messages", [])
                    console.print(f"  [dim]Output contains {len(messages)} messages[/dim]")
                    # Show last message if it's an agent response
                    if messages:
                        last_msg = messages[-1]
                        if isinstance(last_msg, dict) and last_msg.get("type") == "ai":
                            console.print(f"\n  [green]Agent Response:[/green]")
                            console.print(Panel(
                                last_msg.get("content", "No content"),
                                border_style="green"
                            ))
                
                # Show other important fields
                important_fields = [
                    "lead_score", "current_agent", "extracted_data",
                    "suggested_agent", "score_reasoning"
                ]
                for field in important_fields:
                    if field in run.outputs:
                        console.print(f"  • {field}: {run.outputs[field]}")
            else:
                console.print(f"  {run.outputs}")
        
        # Show error if any
        if run.error:
            console.print(f"\n[red]Error:[/red]")
            console.print(Panel(run.error, border_style="red"))
        
        # Token usage
        if run.total_tokens:
            console.print(f"\n[cyan]Token Usage:[/cyan]")
            console.print(f"  • Total: {run.total_tokens}")
            console.print(f"  • Prompt: {run.prompt_tokens}")
            console.print(f"  • Completion: {run.completion_tokens}")
        
        # Get child runs
        console.print("\n[yellow]Fetching child runs...[/yellow]")
        child_runs = list(client.list_runs(
            project_name="ghl-langgraph-agent",
            filter=f'eq(parent_run_id, "{run_id}")',
            limit=50
        ))
        
        if child_runs:
            console.print(f"Found {len(child_runs)} child runs")
            
            # Group by node/agent
            nodes = {}
            for child in child_runs:
                node_name = child.name or "Unknown"
                if node_name not in nodes:
                    nodes[node_name] = []
                nodes[node_name].append(child)
            
            # Create execution tree
            tree = Tree(f"🌳 Execution Flow for {run.name}")
            
            for node_name, node_runs in nodes.items():
                node_branch = tree.add(f"[cyan]{node_name}[/cyan] ({len(node_runs)} calls)")
                
                # Show details for each run
                for i, child_run in enumerate(node_runs[:5]):  # Limit to 5 per node
                    duration = "—"
                    if child_run.end_time and child_run.start_time:
                        duration = f"{(child_run.end_time - child_run.start_time).total_seconds():.3f}s"
                    
                    run_info = f"[{i+1}] {child_run.run_type} ({duration})"
                    run_branch = node_branch.add(run_info)
                    
                    # Add key details
                    if child_run.error:
                        run_branch.add(f"[red]Error: {child_run.error[:100]}...[/red]")
                    elif child_run.outputs:
                        output_preview = str(child_run.outputs)[:100]
                        run_branch.add(f"[dim]Output: {output_preview}...[/dim]")
                
                if len(node_runs) > 5:
                    node_branch.add(f"[dim]... and {len(node_runs) - 5} more[/dim]")
            
            console.print(tree)
            
            # Summary table
            console.print("\n[yellow]Node Summary:[/yellow]")
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Node", style="cyan")
            table.add_column("Calls", style="green")
            table.add_column("Avg Duration", style="blue")
            table.add_column("Errors", style="red")
            
            for node_name, node_runs in nodes.items():
                total_duration = 0
                valid_durations = 0
                errors = 0
                
                for run in node_runs:
                    if run.error:
                        errors += 1
                    if run.end_time and run.start_time:
                        total_duration += (run.end_time - run.start_time).total_seconds()
                        valid_durations += 1
                
                avg_duration = total_duration / valid_durations if valid_durations > 0 else 0
                
                table.add_row(
                    node_name,
                    str(len(node_runs)),
                    f"{avg_duration:.3f}s" if avg_duration > 0 else "—",
                    str(errors) if errors > 0 else "—"
                )
            
            console.print(table)
        
        return run
        
    except Exception as e:
        console.print(f"[red]Error analyzing trace: {str(e)}[/red]")
        import traceback
        console.print(traceback.format_exc())
        return None

def main():
    """Main analysis function"""
    console.print("[bold magenta]🔍 LangSmith Trace Analysis[/bold magenta]")
    console.print(f"API Key: {api_key[:20]}...")
    console.print(f"Analyzing {len(TRACE_IDS)} traces")
    console.print("=" * 60)
    
    # Analyze each trace
    for trace_id in TRACE_IDS:
        run = analyze_trace(trace_id)
        
        if run:
            # Try to determine what happened
            console.print("\n[yellow]📊 Analysis Summary:[/yellow]")
            
            # Check if it's a parent or child run
            if not run.parent_run_id:
                console.print("  • This is a [bold]parent run[/bold] (full workflow execution)")
            else:
                console.print(f"  • This is a [bold]child run[/bold] (part of {run.parent_run_id})")
            
            # Check for errors
            if run.error:
                console.print("  • [red]Run failed with error[/red]")
            elif run.status == "success":
                console.print("  • [green]Run completed successfully[/green]")
            
            # Check for specific patterns
            if run.outputs and isinstance(run.outputs, dict):
                if run.outputs.get("lead_score"):
                    console.print(f"  • Lead scored as: {run.outputs['lead_score']}/10")
                if run.outputs.get("current_agent"):
                    console.print(f"  • Routed to agent: {run.outputs['current_agent']}")
                if run.outputs.get("extracted_data"):
                    console.print(f"  • Extracted data: {list(run.outputs['extracted_data'].keys())}")
        
        console.print("\n" + "─" * 60)
    
    # Try to get recent runs for context
    console.print("\n[yellow]Recent Runs in Project:[/yellow]")
    try:
        recent_runs = list(client.list_runs(
            project_name="ghl-langgraph-agent",
            limit=5
        ))
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Run ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Start Time", style="blue")
        
        for run in recent_runs:
            table.add_row(
                str(run.id)[:8] + "...",
                run.name or "Unknown",
                run.status,
                run.start_time.strftime("%Y-%m-%d %H:%M:%S") if run.start_time else "—"
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Could not fetch recent runs: {str(e)}[/red]")

if __name__ == "__main__":
    main()
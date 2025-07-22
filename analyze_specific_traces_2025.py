#!/usr/bin/env python3
"""
Analyze specific LangSmith traces to check responder_streaming_node execution
"""

import os
import asyncio
from datetime import datetime
from langsmith import Client
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich.syntax import Syntax
import json

console = Console()

# Initialize LangSmith client
client = Client(
    api_key=os.getenv("LANGCHAIN_API_KEY"),
    api_url="https://api.smith.langchain.com"
)

class TraceAnalyzer:
    """Analyze specific traces for responder_streaming_node execution"""
    
    def __init__(self):
        self.client = client
        
    async def analyze_trace(self, trace_id: str):
        """Analyze a single trace in detail"""
        console.print(f"\n[bold blue]━━━ Analyzing Trace: {trace_id} ━━━[/bold blue]")
        
        try:
            # Get the main run
            run = self.client.read_run(trace_id)
            
            # Basic info
            console.print(f"\n[cyan]Basic Information:[/cyan]")
            console.print(f"  • Status: {run.status}")
            console.print(f"  • Start: {run.start_time}")
            console.print(f"  • End: {run.end_time}")
            console.print(f"  • Duration: {(run.end_time - run.start_time).total_seconds():.2f}s" if run.end_time and run.start_time else "N/A")
            
            # Check for errors
            if run.error:
                console.print(f"\n[red]ERROR FOUND:[/red] {run.error}")
            
            # Get all child runs
            child_runs = list(self.client.list_runs(
                project_name="ghl-langgraph-agent",
                filter=f'eq(parent_run_id, "{trace_id}")'
            ))
            
            console.print(f"\n[cyan]Total Child Runs:[/cyan] {len(child_runs)}")
            
            # Look for responder_streaming_node
            responder_found = False
            ghl_api_calls = []
            errors = []
            
            # Create execution flow tree
            tree = Tree(f"[bold]Trace {trace_id}[/bold]")
            
            # Group runs by node
            nodes_executed = {}
            for child in child_runs:
                node_name = child.name or "Unknown"
                
                # Track responder_streaming_node
                if "responder_streaming" in node_name.lower():
                    responder_found = True
                
                # Track GHL API calls
                if "ghl" in node_name.lower() or "send_message" in node_name.lower():
                    ghl_api_calls.append({
                        "name": node_name,
                        "status": child.status,
                        "error": child.error
                    })
                
                # Track errors
                if child.error:
                    errors.append({
                        "node": node_name,
                        "error": child.error
                    })
                
                # Group by node
                if node_name not in nodes_executed:
                    nodes_executed[node_name] = []
                nodes_executed[node_name].append(child)
            
            # Build execution tree
            for node_name, runs in nodes_executed.items():
                node_style = "green" if "responder_streaming" in node_name.lower() else "cyan"
                node_branch = tree.add(f"[{node_style}]{node_name}[/{node_style}] ({len(runs)} calls)")
                
                for run in runs[:3]:  # Show first 3
                    status_color = "green" if run.status == "success" else "red"
                    run_info = f"[{status_color}]{run.status}[/{status_color}]"
                    
                    if run.end_time and run.start_time:
                        duration = (run.end_time - run.start_time).total_seconds()
                        run_info += f" ({duration:.2f}s)"
                    
                    run_branch.add(run_info)
                    
                    # Show outputs for responder_streaming_node
                    if "responder_streaming" in node_name.lower() and run.outputs:
                        output_str = str(run.outputs)[:200]
                        run_branch.add(f"[dim]Output: {output_str}...[/dim]")
            
            console.print(tree)
            
            # Summary table
            console.print(f"\n[yellow]━━━ Analysis Summary ━━━[/yellow]")
            
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Check", style="cyan", width=30)
            table.add_column("Result", style="green")
            
            # Check results
            table.add_row(
                "Responder Streaming Node Called?",
                "✓ YES" if responder_found else "✗ NO"
            )
            
            table.add_row(
                "GHL API Calls Made?",
                f"✓ YES ({len(ghl_api_calls)} calls)" if ghl_api_calls else "✗ NO"
            )
            
            table.add_row(
                "Execution Errors?",
                f"✗ YES ({len(errors)} errors)" if errors else "✓ NO"
            )
            
            table.add_row(
                "Final Trace Status",
                f"{run.status}" + (" ✓" if run.status == "success" else " ✗")
            )
            
            console.print(table)
            
            # Show GHL API calls details
            if ghl_api_calls:
                console.print(f"\n[cyan]GHL API Calls:[/cyan]")
                for call in ghl_api_calls:
                    status_icon = "✓" if call["status"] == "success" else "✗"
                    console.print(f"  {status_icon} {call['name']} - {call['status']}")
                    if call["error"]:
                        console.print(f"    Error: {call['error']}")
            
            # Show errors details
            if errors:
                console.print(f"\n[red]Errors Found:[/red]")
                for err in errors:
                    console.print(f"  • {err['node']}: {err['error']}")
            
            # Check final state
            if run.outputs:
                console.print(f"\n[cyan]Final State Analysis:[/cyan]")
                outputs = run.outputs
                
                # Check if response was sent
                if isinstance(outputs, dict):
                    response_sent = outputs.get("response_sent", False)
                    last_message = outputs.get("last_sent_message")
                    messages_to_send = outputs.get("messages_to_send", [])
                    
                    console.print(f"  • Response Sent: {'✓ YES' if response_sent else '✗ NO'}")
                    if last_message:
                        console.print(f"  • Last Message: {last_message[:100]}...")
                    if messages_to_send:
                        console.print(f"  • Pending Messages: {len(messages_to_send)}")
            
            return {
                "trace_id": trace_id,
                "status": run.status,
                "responder_found": responder_found,
                "ghl_calls": len(ghl_api_calls),
                "errors": len(errors),
                "response_sent": outputs.get("response_sent", False) if isinstance(outputs, dict) else False
            }
            
        except Exception as e:
            console.print(f"[red]Error analyzing trace: {str(e)}[/red]")
            return {
                "trace_id": trace_id,
                "status": "error",
                "error": str(e)
            }

async def main():
    """Analyze the three specific traces"""
    analyzer = TraceAnalyzer()
    
    # The traces to analyze
    trace_ids = [
        "1f067450-f248-6c65-ad62-5b003dd1b02a",
        "1f067450-f248-6c65-ad62-5b003dd1b02a",  # Duplicate
        "1f067452-0dda-61cc-bd5a-b380392345a3"
    ]
    
    console.print("[bold magenta]🔍 Analyzing Specific LangSmith Traces[/bold magenta]")
    console.print("=" * 60)
    console.print("Checking for responder_streaming_node execution and GHL API calls")
    
    # Remove duplicates
    unique_traces = list(set(trace_ids))
    
    results = []
    for trace_id in unique_traces:
        result = await analyzer.analyze_trace(trace_id)
        results.append(result)
        
        if trace_id != unique_traces[-1]:
            console.print("\n" + "─" * 60)
    
    # Final summary
    console.print(f"\n[bold yellow]━━━ FINAL SUMMARY ━━━[/bold yellow]")
    
    summary_table = Table(show_header=True, header_style="bold magenta")
    summary_table.add_column("Trace ID", style="cyan")
    summary_table.add_column("Status", style="yellow")
    summary_table.add_column("Responder", style="green")
    summary_table.add_column("GHL Calls", style="blue")
    summary_table.add_column("Errors", style="red")
    summary_table.add_column("Sent?", style="green")
    
    for result in results:
        if "error" in result:
            summary_table.add_row(
                result["trace_id"][:8] + "...",
                "ERROR",
                "—",
                "—",
                "—",
                "—"
            )
        else:
            summary_table.add_row(
                result["trace_id"][:8] + "...",
                result["status"],
                "✓" if result["responder_found"] else "✗",
                str(result["ghl_calls"]),
                str(result["errors"]),
                "✓" if result["response_sent"] else "✗"
            )
    
    console.print(summary_table)
    
    # Overall assessment
    all_have_responder = all(r.get("responder_found", False) for r in results if "error" not in r)
    any_ghl_calls = any(r.get("ghl_calls", 0) > 0 for r in results if "error" not in r)
    any_errors = any(r.get("errors", 0) > 0 for r in results if "error" not in r)
    
    console.print(f"\n[bold]Overall Assessment:[/bold]")
    if all_have_responder:
        console.print("✅ [green]All traces executed responder_streaming_node[/green]")
    else:
        console.print("❌ [red]Not all traces executed responder_streaming_node[/red]")
    
    if any_ghl_calls:
        console.print("✅ [green]GHL API calls were made[/green]")
    else:
        console.print("❌ [red]No GHL API calls were made[/red]")
    
    if not any_errors:
        console.print("✅ [green]No execution errors found[/green]")
    else:
        console.print("⚠️  [yellow]Some traces had errors[/yellow]")

if __name__ == "__main__":
    # Ensure LangSmith is configured
    if not os.getenv("LANGCHAIN_API_KEY"):
        console.print("[red]Error: LANGCHAIN_API_KEY not set[/red]")
        console.print("Please set your LangSmith API key first")
    else:
        asyncio.run(main())
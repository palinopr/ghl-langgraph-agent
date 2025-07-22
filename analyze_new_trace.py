#!/usr/bin/env python3
"""
Analyze New Trace After Thread ID Fix
Using the debugging guide to check if the fix is working
"""

from langsmith import Client
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import json

console = Console()

# Your API key
api_key = "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"

# Initialize client
client = Client(
    api_key=api_key,
    api_url="https://api.smith.langchain.com"
)

# New trace ID to analyze
TRACE_ID = "1f066a2d-302a-6ee9-88b8-db984174a418"

def analyze_trace_after_fix(run_id: str):
    """Analyze trace to see if thread_id fix is working"""
    console.print(f"\n[bold blue]━━━ Analyzing Trace After Thread ID Fix ━━━[/bold blue]")
    console.print(f"Trace ID: {run_id}")
    
    try:
        # Get the run
        run = client.read_run(run_id)
        
        # Basic info
        info_panel = f"""
[cyan]Status:[/cyan] {run.status}
[cyan]Start:[/cyan] {run.start_time}
[cyan]Type:[/cyan] {run.run_type}
        """
        console.print(Panel(info_panel.strip(), title="Run Information", border_style="blue"))
        
        # Extract key data
        if run.inputs and isinstance(run.inputs, dict):
            messages = run.inputs.get('messages', [])
            if messages and len(messages) > 0:
                message_content = messages[0].get('content', 'No content')
            else:
                message_content = "No message"
            
            contact_id = run.inputs.get('contact_id', 'Unknown')
            console.print(f"\n[yellow]Input Message:[/yellow] {message_content}")
            console.print(f"[yellow]Contact ID:[/yellow] {contact_id}")
        
        # Check metadata for thread_id
        if run.metadata:
            thread_id = run.metadata.get('thread_id', 'Not found in metadata')
            console.print(f"[green]Thread ID (metadata):[/green] {thread_id}")
        
        # Check outputs for thread_id
        if run.outputs and isinstance(run.outputs, dict):
            output_thread_id = run.outputs.get('thread_id', 'Not found in outputs')
            console.print(f"[green]Thread ID (outputs):[/green] {output_thread_id}")
            
            # Lead score and agent info
            lead_score = run.outputs.get('lead_score', 'N/A')
            current_agent = run.outputs.get('current_agent', 'N/A')
            console.print(f"\n[cyan]Lead Score:[/cyan] {lead_score}")
            console.print(f"[cyan]Current Agent:[/cyan] {current_agent}")
            
            # Extracted data
            extracted = run.outputs.get('extracted_data', {})
            if extracted:
                console.print(f"\n[cyan]Extracted Data:[/cyan]")
                for key, value in extracted.items():
                    if value is not None:
                        console.print(f"  • {key}: {value}")
            
            # Get response
            output_messages = run.outputs.get('messages', [])
            if output_messages:
                last_msg = output_messages[-1]
                if isinstance(last_msg, dict) and last_msg.get('type') == 'ai':
                    response = last_msg.get('content', 'No response')
                    console.print(f"\n[green]Agent Response:[/green]")
                    console.print(Panel(response[:200] + "..." if len(response) > 200 else response, border_style="green"))
        
        # Get child runs to see execution flow
        console.print(f"\n[yellow]Fetching child runs...[/yellow]")
        child_runs = list(client.list_runs(
            project_name="ghl-langgraph-agent",
            filter=f'eq(parent_run_id, "{run_id}")',
            limit=20
        ))
        
        if child_runs:
            console.print(f"Found {len(child_runs)} child runs")
            
            # Create execution flow table
            table = Table(title="Execution Flow", show_header=True, header_style="bold magenta")
            table.add_column("Node", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Duration", style="blue")
            
            for child in child_runs:
                duration = "—"
                if child.end_time and child.start_time:
                    duration = f"{(child.end_time - child.start_time).total_seconds():.2f}s"
                
                table.add_row(
                    child.name or "Unknown",
                    child.status,
                    duration
                )
            
            console.print(table)
        
        # Analysis summary
        console.print(f"\n[bold yellow]━━━ Analysis Summary ━━━[/bold yellow]")
        
        # Check if this is after the fix
        if run.start_time:
            import datetime
            fix_time = datetime.datetime(2025, 7, 22, 2, 0, 0, tzinfo=datetime.timezone.utc)  # Approximate fix deployment time
            if run.start_time > fix_time:
                console.print("✅ This trace is AFTER the thread_id fix")
            else:
                console.print("❌ This trace is BEFORE the thread_id fix")
        
        # Look for thread_id consistency
        console.print("\n[yellow]Thread ID Check:[/yellow]")
        console.print("To verify the fix is working:")
        console.print("1. Check if thread_id matches conversationId from webhook")
        console.print("2. Compare with other messages from same contact")
        console.print("3. Verify agents remember previous context")
        
        return run
        
    except Exception as e:
        console.print(f"[red]Error analyzing trace: {str(e)}[/red]")
        import traceback
        console.print(traceback.format_exc())

def main():
    """Analyze the new trace"""
    console.print("[bold magenta]🔍 Analyzing New Trace After Thread ID Fix[/bold magenta]")
    console.print("=" * 60)
    
    analyze_trace_after_fix(TRACE_ID)
    
    console.print("\n" + "=" * 60)
    console.print("[green]Analysis Complete![/green]")
    
    # Provide next steps
    console.print("\n[yellow]Next Steps:[/yellow]")
    console.print("1. Get more traces from the same contact to verify thread_id consistency")
    console.print("2. Check if agents are remembering context between messages")
    console.print("3. Look for the debug log: 'Using thread_id: X for contact: Y'")

if __name__ == "__main__":
    main()
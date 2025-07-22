#!/usr/bin/env python3
"""
Check Thread ID Consistency for Contact
Find all traces for the same contact to verify thread_id is consistent
"""

from langsmith import Client
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from datetime import datetime
import json

console = Console()

# Your API key
api_key = "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"

# Initialize client
client = Client(
    api_key=api_key,
    api_url="https://api.smith.langchain.com"
)

def find_traces_for_contact(contact_id: str, limit: int = 10):
    """Find all recent traces for a specific contact"""
    console.print(f"\n[yellow]Searching for traces with contact_id: {contact_id}[/yellow]")
    
    # Get recent runs
    runs = list(client.list_runs(
        project_name="ghl-langgraph-agent",
        limit=100,  # Get more to find matches
        filter='eq(run_type, "chain")'
    ))
    
    # Filter for our contact
    contact_runs = []
    for run in runs:
        if run.inputs and isinstance(run.inputs, dict):
            if run.inputs.get('contact_id') == contact_id:
                contact_runs.append(run)
    
    return contact_runs[:limit]

def analyze_thread_consistency(contact_id: str = "McKodFLYef5PeMDvK7n6"):
    """Analyze thread_id consistency for a contact"""
    console.print(f"\n[bold blue]━━━ Thread ID Consistency Check ━━━[/bold blue]")
    console.print(f"Contact: {contact_id}")
    
    # Find traces for this contact
    traces = find_traces_for_contact(contact_id)
    
    if not traces:
        console.print("[red]No traces found for this contact[/red]")
        return
    
    console.print(f"Found {len(traces)} traces for this contact")
    
    # Create analysis table
    table = Table(title="Thread ID Analysis", show_header=True, header_style="bold magenta")
    table.add_column("Time", style="blue", width=20)
    table.add_column("Message", style="white", width=30)
    table.add_column("Thread ID", style="green", width=40)
    table.add_column("Score", style="yellow", width=6)
    table.add_column("Agent", style="cyan", width=10)
    
    thread_ids = set()
    
    for run in sorted(traces, key=lambda x: x.start_time):
        # Extract message
        message = "N/A"
        if run.inputs and 'messages' in run.inputs:
            msgs = run.inputs['messages']
            if msgs and len(msgs) > 0:
                message = msgs[0].get('content', 'No content')[:30]
        
        # Extract thread_id
        thread_id = "Not found"
        if run.metadata:
            thread_id = run.metadata.get('thread_id', 'Not in metadata')
        if run.outputs and isinstance(run.outputs, dict):
            output_thread = run.outputs.get('thread_id')
            if output_thread:
                thread_id = output_thread
        
        thread_ids.add(thread_id)
        
        # Extract other info
        score = "N/A"
        agent = "N/A"
        if run.outputs and isinstance(run.outputs, dict):
            score = str(run.outputs.get('lead_score', 'N/A'))
            agent = run.outputs.get('current_agent', 'N/A')
        
        # Add to table
        time_str = run.start_time.strftime("%m/%d %H:%M:%S") if run.start_time else "Unknown"
        table.add_row(
            time_str,
            message + "..." if len(message) == 30 else message,
            thread_id,
            score,
            agent
        )
    
    console.print(table)
    
    # Analysis
    console.print(f"\n[bold yellow]━━━ Analysis Results ━━━[/bold yellow]")
    
    if len(thread_ids) == 1:
        console.print(f"✅ [green]CONSISTENT![/green] All messages use the same thread_id: {list(thread_ids)[0]}")
    else:
        console.print(f"❌ [red]INCONSISTENT![/red] Found {len(thread_ids)} different thread_ids:")
        for tid in thread_ids:
            console.print(f"  • {tid}")
    
    # Check if using the fix pattern
    for tid in thread_ids:
        if tid.startswith("contact-"):
            console.print(f"\n✅ Using contact-based fallback: {tid}")
        elif "-" in tid and len(tid) > 30:  # Likely a UUID
            console.print(f"\n✅ Using conversationId or threadId: {tid}")
    
    # Look for progression in scores
    console.print(f"\n[yellow]Score Progression:[/yellow]")
    scores = []
    for run in sorted(traces, key=lambda x: x.start_time):
        if run.outputs and isinstance(run.outputs, dict):
            score = run.outputs.get('lead_score')
            if score is not None:
                scores.append(score)
    
    if scores:
        console.print(f"Scores over time: {' → '.join(map(str, scores))}")
        if len(set(scores)) > 1:
            console.print("✅ Scores are changing (good sign of memory)")
        else:
            console.print("⚠️  Scores not changing (might indicate no memory)")

def main():
    """Check thread consistency"""
    console.print("[bold magenta]🔍 Thread ID Consistency Checker[/bold magenta]")
    console.print("=" * 60)
    
    # Analyze the contact from the new trace
    analyze_thread_consistency("McKodFLYef5PeMDvK7n6")
    
    console.print("\n" + "=" * 60)
    
    # Also check a few recent contacts
    console.print("\n[yellow]Checking other recent contacts...[/yellow]")
    
    # Get some recent runs to find other contacts
    recent_runs = list(client.list_runs(
        project_name="ghl-langgraph-agent",
        limit=50,
        filter='eq(run_type, "chain")'
    ))
    
    # Find unique contacts
    contacts = set()
    for run in recent_runs:
        if run.inputs and isinstance(run.inputs, dict):
            contact_id = run.inputs.get('contact_id')
            if contact_id and contact_id != "McKodFLYef5PeMDvK7n6":
                contacts.add(contact_id)
    
    # Check a few more contacts
    for contact in list(contacts)[:2]:
        console.print(f"\n[cyan]Checking contact: {contact}[/cyan]")
        traces = find_traces_for_contact(contact, limit=3)
        if traces:
            thread_ids = set()
            for run in traces:
                if run.metadata:
                    tid = run.metadata.get('thread_id', 'Not found')
                    thread_ids.add(tid)
            
            if len(thread_ids) == 1:
                console.print(f"✅ Consistent thread_id: {list(thread_ids)[0]}")
            else:
                console.print(f"❌ Multiple thread_ids: {thread_ids}")

if __name__ == "__main__":
    main()
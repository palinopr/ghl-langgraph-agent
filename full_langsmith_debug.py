#!/usr/bin/env python3
"""
Full LangSmith SDK Debugging
Shows EVERYTHING that happens in the workflow with detailed tracing
"""

import asyncio
import os
from datetime import datetime
from typing import Dict, Any, List
from langsmith import Client
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.tree import Tree
from rich.progress import Progress, SpinnerColumn, TextColumn
import json

# Import our workflow
from app.workflow import workflow

console = Console()

# Initialize LangSmith client
client = Client(
    api_key=os.getenv("LANGCHAIN_API_KEY"),
    api_url="https://api.smith.langchain.com"
)

class WorkflowDebugger:
    """Complete workflow debugger with LangSmith integration"""
    
    def __init__(self):
        self.client = client
        self.traces = []
        self.current_run_id = None
        
    async def debug_message(self, message: str, contact_id: str = "debug-test"):
        """Debug a single message through the entire workflow"""
        
        console.print(f"\n[bold blue]━━━ FULL DEBUG SESSION ━━━[/bold blue]")
        console.print(Panel(message, title="Input Message", border_style="blue"))
        console.print(f"Contact ID: {contact_id}")
        console.print(f"Timestamp: {datetime.now().isoformat()}")
        
        # Create initial state
        state = {
            "messages": [HumanMessage(content=message)],
            "contact_id": contact_id,
            "thread_id": f"debug-thread-{contact_id}",
            "webhook_data": {
                "body": message,
                "contactId": contact_id,
                "type": "SMS",
                "locationId": "debug-location"
            },
            "lead_score": 0,
            "lead_category": "cold",
            "extracted_data": {},
            "current_agent": None,
            "next_agent": None,
            "agent_task": None,
            "should_end": False,
            "needs_rerouting": False,
            "needs_escalation": False,
            "response_to_send": None,
            "conversation_stage": None,
            "messages_to_send": [],
            "appointment_status": None,
            "available_slots": None,
            "appointment_details": None,
            "contact_name": None,
            "custom_fields": {},
            "agent_handoff": None,
            "error": None,
            "remaining_steps": 10,
            "supervisor_complete": False,
            "routing_attempts": 0,
            "interaction_count": 0,
            "escalation_reason": None,
            "response_sent": False,
            "last_sent_message": None,
            "contact_info": None,
            "previous_custom_fields": None,
            "score_reasoning": None,
            "score_history": [],
            "suggested_agent": None
        }
        
        # Show initial state
        self._show_state("Initial State", state)
        
        # Configure with metadata for tracing
        config = {
            "configurable": {
                "thread_id": f"debug-thread-{contact_id}"
            },
            "metadata": {
                "debug_session": True,
                "message": message,
                "contact_id": contact_id
            },
            "callbacks": [],  # LangSmith will auto-attach
            "tags": ["debug", "full-trace"]
        }
        
        # Run workflow with progress tracking
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task("Running workflow...", total=None)
            
            try:
                # Invoke workflow
                result = await workflow.ainvoke(state, config)
                progress.update(task, completed=True, description="Workflow completed!")
                
                # Get the run ID from LangSmith
                await asyncio.sleep(2)  # Give LangSmith time to process
                
                # Show final state
                self._show_state("Final State", result)
                
                # Analyze the trace
                await self._analyze_trace(contact_id)
                
                return result
                
            except Exception as e:
                console.print(f"\n[red]ERROR: {str(e)}[/red]")
                import traceback
                console.print(traceback.format_exc())
                return None
    
    def _show_state(self, title: str, state: Dict[str, Any]):
        """Display state in a formatted way"""
        console.print(f"\n[yellow]━━━ {title} ━━━[/yellow]")
        
        # Key fields table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Field", style="cyan", width=25)
        table.add_column("Value", style="green")
        
        # Show important fields
        important_fields = [
            ("lead_score", "Lead Score"),
            ("lead_category", "Category"),
            ("current_agent", "Current Agent"),
            ("suggested_agent", "Suggested Agent"),
            ("supervisor_complete", "Supervisor Complete"),
            ("should_end", "Should End"),
            ("response_sent", "Response Sent"),
            ("error", "Error")
        ]
        
        for field, label in important_fields:
            value = state.get(field, "None")
            if isinstance(value, bool):
                value = "✓" if value else "✗"
            elif value is None:
                value = "—"
            table.add_row(label, str(value))
        
        console.print(table)
        
        # Show extracted data if any
        if state.get("extracted_data"):
            console.print("\n[cyan]Extracted Data:[/cyan]")
            for key, value in state["extracted_data"].items():
                console.print(f"  • {key}: {value}")
        
        # Show messages
        messages = state.get("messages", [])
        if messages:
            console.print(f"\n[cyan]Messages ({len(messages)} total):[/cyan]")
            for i, msg in enumerate(messages[-3:]):  # Show last 3
                if isinstance(msg, HumanMessage):
                    console.print(f"  [{i+1}] Human: {msg.content[:100]}...")
                elif isinstance(msg, AIMessage):
                    console.print(f"  [{i+1}] AI: {msg.content[:100]}...")
    
    async def _analyze_trace(self, contact_id: str):
        """Analyze the LangSmith trace for this run"""
        console.print(f"\n[yellow]━━━ LangSmith Trace Analysis ━━━[/yellow]")
        
        try:
            # Get recent runs from the project
            runs = list(self.client.list_runs(
                project_name="ghl-langgraph-agent",
                limit=10,
                filter='eq(tags, "debug")'
            ))
            
            if not runs:
                console.print("[red]No debug runs found in LangSmith[/red]")
                return
            
            # Find our run
            our_run = None
            for run in runs:
                if run.metadata and run.metadata.get("contact_id") == contact_id:
                    our_run = run
                    break
            
            if not our_run:
                # Just use the most recent run
                our_run = runs[0]
            
            console.print(f"Run ID: {our_run.id}")
            console.print(f"Status: {our_run.status}")
            console.print(f"Start: {our_run.start_time}")
            console.print(f"End: {our_run.end_time}")
            
            # Show execution tree
            tree = Tree("🌳 Execution Flow")
            
            # Add run details
            run_node = tree.add(f"[bold]Workflow Run[/bold] ({our_run.status})")
            
            # Get child runs
            child_runs = list(self.client.list_runs(
                project_name="ghl-langgraph-agent",
                filter=f'eq(parent_run_id, "{our_run.id}")'
            ))
            
            # Group by node
            nodes = {}
            for child in child_runs:
                node_name = child.name or "Unknown"
                if node_name not in nodes:
                    nodes[node_name] = []
                nodes[node_name].append(child)
            
            # Add nodes to tree
            for node_name, node_runs in nodes.items():
                node_branch = run_node.add(f"[cyan]{node_name}[/cyan] ({len(node_runs)} calls)")
                
                for run in node_runs[:3]:  # Show first 3
                    # Get run details
                    duration = None
                    if run.end_time and run.start_time:
                        duration = (run.end_time - run.start_time).total_seconds()
                    
                    run_text = f"{run.run_type}"
                    if duration:
                        run_text += f" ({duration:.2f}s)"
                    
                    run_branch = node_branch.add(run_text)
                    
                    # Show inputs/outputs if available
                    if run.inputs:
                        run_branch.add(f"[dim]Input: {str(run.inputs)[:100]}...[/dim]")
                    if run.outputs:
                        run_branch.add(f"[dim]Output: {str(run.outputs)[:100]}...[/dim]")
            
            console.print(tree)
            
            # Show token usage
            if our_run.total_tokens:
                console.print(f"\n[cyan]Token Usage:[/cyan]")
                console.print(f"  • Total: {our_run.total_tokens}")
                console.print(f"  • Prompt: {our_run.prompt_tokens}")
                console.print(f"  • Completion: {our_run.completion_tokens}")
            
            # Show any errors
            if our_run.error:
                console.print(f"\n[red]Error:[/red] {our_run.error}")
            
        except Exception as e:
            console.print(f"[red]Error analyzing trace: {str(e)}[/red]")

async def run_full_debug():
    """Run a complete debug session"""
    debugger = WorkflowDebugger()
    
    # Test cases with detailed debugging
    test_cases = [
        {
            "message": "Hola, tengo un restaurante mexicano",
            "contact_id": "debug-restaurant",
            "description": "Basic business extraction"
        },
        {
            "message": "Mi nombre es Carlos, tengo una barbería y mi presupuesto es $400 al mes",
            "contact_id": "debug-barbershop",
            "description": "Full data extraction"
        },
        {
            "message": "Quiero agendar una cita para mañana a las 3pm",
            "contact_id": "debug-appointment",
            "description": "Appointment booking flow"
        }
    ]
    
    console.print("[bold magenta]🔍 Full Workflow Debugging with LangSmith[/bold magenta]")
    console.print("=" * 60)
    
    for i, test in enumerate(test_cases, 1):
        console.print(f"\n[bold cyan]TEST {i}/{len(test_cases)}: {test['description']}[/bold cyan]")
        
        result = await debugger.debug_message(
            test["message"],
            test["contact_id"]
        )
        
        if result:
            # Show the final response
            response = None
            for msg in reversed(result.get("messages", [])):
                if isinstance(msg, AIMessage) and msg.content:
                    response = msg.content
                    break
            
            if response:
                console.print(f"\n[green]Final Response:[/green]")
                console.print(Panel(response, border_style="green"))
        
        if i < len(test_cases):
            console.print("\n" + "─" * 60)
            await asyncio.sleep(2)  # Give LangSmith time between tests

async def debug_specific_run(run_id: str):
    """Debug a specific LangSmith run by ID"""
    console.print(f"\n[bold blue]━━━ Debugging Run: {run_id} ━━━[/bold blue]")
    
    try:
        # Get the run
        run = client.read_run(run_id)
        
        # Show run details
        console.print(f"\nRun Name: {run.name}")
        console.print(f"Status: {run.status}")
        console.print(f"Start: {run.start_time}")
        console.print(f"End: {run.end_time}")
        console.print(f"Run Type: {run.run_type}")
        
        # Show inputs
        if run.inputs:
            console.print("\n[cyan]Inputs:[/cyan]")
            console.print(Syntax(
                json.dumps(run.inputs, indent=2),
                "json",
                theme="monokai"
            ))
        
        # Show outputs
        if run.outputs:
            console.print("\n[green]Outputs:[/green]")
            console.print(Syntax(
                json.dumps(run.outputs, indent=2),
                "json",
                theme="monokai"
            ))
        
        # Show error if any
        if run.error:
            console.print(f"\n[red]Error:[/red] {run.error}")
        
        # Get child runs
        child_runs = list(client.list_runs(
            project_name="ghl-langgraph-agent",
            filter=f'eq(parent_run_id, "{run_id}")'
        ))
        
        if child_runs:
            console.print(f"\n[yellow]Child Runs ({len(child_runs)}):[/yellow]")
            
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Name", style="cyan")
            table.add_column("Type", style="green")
            table.add_column("Status", style="yellow")
            table.add_column("Duration", style="blue")
            
            for child in child_runs:
                duration = "—"
                if child.end_time and child.start_time:
                    duration = f"{(child.end_time - child.start_time).total_seconds():.2f}s"
                
                table.add_row(
                    child.name or "Unknown",
                    child.run_type,
                    child.status,
                    duration
                )
            
            console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")

async def main():
    """Main debug interface"""
    console.print("[bold]🔍 LangSmith Full Debugging System[/bold]")
    console.print("This tool provides complete visibility into workflow execution\n")
    
    while True:
        console.print("\n[cyan]Options:[/cyan]")
        console.print("1. Run full debug suite")
        console.print("2. Debug specific message")
        console.print("3. Debug specific run ID")
        console.print("4. Exit")
        
        choice = input("\nSelect option: ")
        
        if choice == "1":
            await run_full_debug()
        elif choice == "2":
            message = input("Enter message: ")
            contact_id = input("Enter contact ID (or press Enter): ") or f"debug-{datetime.now().timestamp()}"
            debugger = WorkflowDebugger()
            await debugger.debug_message(message, contact_id)
        elif choice == "3":
            run_id = input("Enter LangSmith run ID: ")
            await debug_specific_run(run_id)
        elif choice == "4":
            break
        else:
            console.print("[red]Invalid option[/red]")

if __name__ == "__main__":
    # Ensure LangSmith is configured
    if not os.getenv("LANGCHAIN_API_KEY"):
        console.print("[red]Error: LANGCHAIN_API_KEY not set[/red]")
        console.print("Please set your LangSmith API key first")
    else:
        asyncio.run(main())
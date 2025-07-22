#!/usr/bin/env python3
"""
Tool Usage Tracer
Patches agent tools to log exactly when and how they're called
"""

import functools
import json
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from typing import Any, Callable

console = Console()

# Track all tool calls
tool_call_history = []

def trace_tool(tool_name: str):
    """Decorator to trace tool calls"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            call_id = f"{tool_name}_{datetime.now().timestamp()}"
            
            # Log the call
            console.print(f"\n[bold yellow]🔧 TOOL CALLED: {tool_name}[/bold yellow]")
            console.print(f"   [cyan]Call ID:[/cyan] {call_id}")
            console.print(f"   [cyan]Timestamp:[/cyan] {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
            
            # Show arguments
            if args:
                console.print("   [cyan]Args:[/cyan]")
                for i, arg in enumerate(args):
                    console.print(f"      [{i}]: {_format_arg(arg)}")
            
            if kwargs:
                console.print("   [cyan]Kwargs:[/cyan]")
                for key, value in kwargs.items():
                    console.print(f"      {key}: {_format_arg(value)}")
            
            # Track the call
            call_info = {
                "tool": tool_name,
                "call_id": call_id,
                "timestamp": datetime.now().isoformat(),
                "args": [str(arg)[:100] for arg in args],
                "kwargs": {k: str(v)[:100] for k, v in kwargs.items()}
            }
            
            try:
                # Execute the tool
                result = await func(*args, **kwargs)
                
                # Log the result
                console.print(f"   [green]Result:[/green] {_format_arg(result)}")
                call_info["result"] = str(result)[:200]
                call_info["status"] = "success"
                
                return result
                
            except Exception as e:
                # Log the error
                console.print(f"   [red]Error:[/red] {str(e)}")
                call_info["error"] = str(e)
                call_info["status"] = "error"
                raise
            
            finally:
                tool_call_history.append(call_info)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Similar logic for sync functions
            call_id = f"{tool_name}_{datetime.now().timestamp()}"
            
            console.print(f"\n[bold yellow]🔧 TOOL CALLED: {tool_name}[/bold yellow]")
            console.print(f"   [cyan]Call ID:[/cyan] {call_id}")
            console.print(f"   [cyan]Timestamp:[/cyan] {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
            
            if args:
                console.print("   [cyan]Args:[/cyan]")
                for i, arg in enumerate(args):
                    console.print(f"      [{i}]: {_format_arg(arg)}")
            
            if kwargs:
                console.print("   [cyan]Kwargs:[/cyan]")
                for key, value in kwargs.items():
                    console.print(f"      {key}: {_format_arg(value)}")
            
            try:
                result = func(*args, **kwargs)
                console.print(f"   [green]Result:[/green] {_format_arg(result)}")
                return result
            except Exception as e:
                console.print(f"   [red]Error:[/red] {str(e)}")
                raise
        
        # Return appropriate wrapper based on function type
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator

def _format_arg(arg: Any) -> str:
    """Format argument for display"""
    if isinstance(arg, dict):
        # Pretty print dicts
        if len(str(arg)) > 100:
            return json.dumps(arg, indent=2)[:100] + "..."
        return json.dumps(arg, indent=2)
    elif isinstance(arg, (list, tuple)):
        if len(arg) > 3:
            return f"{type(arg).__name__}[{len(arg)} items]"
        return str(arg)
    elif isinstance(arg, str):
        if len(arg) > 50:
            return f'"{arg[:50]}..."'
        return f'"{arg}"'
    else:
        return str(arg)[:100]

def patch_all_tools():
    """Patch all agent tools to add tracing"""
    try:
        # Import tools modules
        from app.tools import agent_tools_modernized
        from app.tools import ghl_client_simple
        
        # List of tools to patch
        tools_to_patch = [
            # Agent tools
            ("get_contact_details_with_task", agent_tools_modernized),
            ("update_contact_with_context", agent_tools_modernized),
            ("escalate_to_supervisor", agent_tools_modernized),
            ("book_appointment_with_instructions", agent_tools_modernized),
            
            # GHL client methods
            ("get_contact", ghl_client_simple.SimpleGHLClient),
            ("update_contact", ghl_client_simple.SimpleGHLClient),
            ("send_message", ghl_client_simple.SimpleGHLClient),
            ("get_conversation_messages", ghl_client_simple.SimpleGHLClient),
            ("create_appointment", ghl_client_simple.SimpleGHLClient),
        ]
        
        patched_count = 0
        
        for tool_name, module in tools_to_patch:
            if hasattr(module, tool_name):
                original = getattr(module, tool_name)
                traced = trace_tool(tool_name)(original)
                setattr(module, tool_name, traced)
                patched_count += 1
                console.print(f"[green]✓[/green] Patched: {tool_name}")
            else:
                console.print(f"[yellow]⚠[/yellow] Tool not found: {tool_name}")
        
        console.print(f"\n[bold green]Successfully patched {patched_count} tools![/bold green]")
        
    except ImportError as e:
        console.print(f"[red]Error importing tools: {e}[/red]")

def show_tool_summary():
    """Show summary of all tool calls"""
    if not tool_call_history:
        console.print("[yellow]No tool calls recorded yet.[/yellow]")
        return
    
    console.print("\n[bold cyan]📊 Tool Call Summary[/bold cyan]")
    console.print("=" * 60)
    
    # Count calls by tool
    tool_counts = {}
    for call in tool_call_history:
        tool = call["tool"]
        tool_counts[tool] = tool_counts.get(tool, 0) + 1
    
    # Show counts
    for tool, count in sorted(tool_counts.items()):
        console.print(f"  • {tool}: {count} call(s)")
    
    console.print(f"\n  Total calls: {len(tool_call_history)}")
    
    # Show recent calls
    console.print("\n[bold]Recent Tool Calls:[/bold]")
    for call in tool_call_history[-5:]:
        status_color = "green" if call["status"] == "success" else "red"
        console.print(f"  [{status_color}]{call['timestamp']}: {call['tool']}[/{status_color}]")

async def test_with_tracing():
    """Run a test with tool tracing enabled"""
    from app.workflow import workflow
    
    # Patch tools first
    patch_all_tools()
    
    # Run a test
    console.print("\n[bold magenta]Running test with tool tracing...[/bold magenta]")
    
    state = {
        "messages": [{"role": "human", "content": "Hola, tengo un restaurante"}],
        "contact_id": "trace-test-123",
        "webhook_data": {"body": "Hola, tengo un restaurante"}
    }
    
    try:
        result = await workflow.ainvoke(state)
        console.print("\n[green]Workflow completed successfully![/green]")
    except Exception as e:
        console.print(f"\n[red]Workflow error: {e}[/red]")
    
    # Show summary
    show_tool_summary()

import asyncio

if __name__ == "__main__":
    # Demo tool tracing
    console.print("[bold]Tool Usage Tracer[/bold]")
    console.print("This will show you exactly which tools are called and when.\n")
    
    asyncio.run(test_with_tracing())
#!/usr/bin/env python3
"""
LangSmith Local Tracing
Enable detailed tracing locally to see exactly what's happening
"""

import os
import asyncio
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from langchain_core.messages import HumanMessage
import webbrowser

console = Console()

def setup_tracing(project_name: str = "local-testing"):
    """Setup LangSmith tracing for local testing"""
    # Enable tracing
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = project_name
    
    # Check if API key is set
    if not os.getenv("LANGSMITH_API_KEY") and not os.getenv("LANGCHAIN_API_KEY"):
        console.print("[yellow]⚠️  Warning: No LangSmith API key found![/yellow]")
        console.print("Set LANGSMITH_API_KEY or LANGCHAIN_API_KEY to enable tracing.")
        return False
    
    console.print(f"[green]✅ LangSmith tracing enabled![/green]")
    console.print(f"[cyan]Project:[/cyan] {project_name}")
    console.print(f"[cyan]Dashboard:[/cyan] https://smith.langchain.com")
    
    return True

async def run_traced_test(message: str, contact_id: str = None):
    """Run a test with full LangSmith tracing"""
    from app.workflow import workflow
    
    if not contact_id:
        contact_id = f"trace-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    console.print(f"\n[bold blue]Running traced test[/bold blue]")
    console.print(f"Message: \"{message}\"")
    console.print(f"Contact: {contact_id}")
    
    # Create state
    state = {
        "messages": [HumanMessage(content=message)],
        "contact_id": contact_id,
        "thread_id": f"thread-{contact_id}",
        "webhook_data": {
            "body": message,
            "contactId": contact_id,
            "type": "SMS",
            "locationId": "test-location",
            "dateAdded": datetime.now().isoformat()
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
        "error": None
    }
    
    try:
        # Run with tracing
        console.print("\n[yellow]⏳ Running workflow (check LangSmith for live trace)...[/yellow]")
        
        result = await workflow.ainvoke(
            state,
            config={
                "metadata": {
                    "test_type": "local",
                    "message": message,
                    "timestamp": datetime.now().isoformat()
                },
                "tags": ["local-test", f"agent-{result.get('current_agent', 'unknown')}"],
                "run_name": f"Test: {message[:30]}..."
            }
        )
        
        console.print("[green]✅ Workflow completed![/green]")
        
        # Show results
        console.print("\n[bold]Results:[/bold]")
        console.print(f"  • Score: {result.get('lead_score', 0)}")
        console.print(f"  • Agent: {result.get('current_agent', 'none')}")
        console.print(f"  • Business: {result.get('extracted_data', {}).get('business_type', 'none')}")
        
        # Extract response
        response = None
        for msg in reversed(result.get('messages', [])):
            if hasattr(msg, 'content') and msg.content and msg.__class__.__name__ == 'AIMessage':
                response = msg.content
                break
        
        if response:
            console.print(f"\n[bold]Response:[/bold]")
            console.print(Panel(response, border_style="green"))
        
        return result
        
    except Exception as e:
        console.print(f"[red]❌ Error: {str(e)}[/red]")
        return None

async def run_comprehensive_trace():
    """Run a comprehensive test showing all aspects"""
    console.print("\n[bold magenta]🔍 Comprehensive Trace Test[/bold magenta]")
    console.print("This will show you everything in LangSmith:")
    console.print("  • LLM calls and prompts")
    console.print("  • Tool invocations")
    console.print("  • State transitions")
    console.print("  • Agent routing decisions")
    console.print("  • Token usage and costs")
    
    # Test different scenarios
    test_cases = [
        {
            "message": "Hola",
            "description": "Simple greeting → Maria"
        },
        {
            "message": "Tengo un restaurante y necesito automatizar WhatsApp",
            "description": "Business + need → Carlos"
        },
        {
            "message": "Mi nombre es Ana, tengo una clínica y mi presupuesto es $500. Quiero agendar.",
            "description": "Full info → Sofia"
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        console.print(f"\n[cyan]Test {i}/{len(test_cases)}: {test['description']}[/cyan]")
        
        await run_traced_test(
            test["message"],
            f"comprehensive-test-{i}"
        )
        
        if i < len(test_cases):
            console.print("\n" + "-" * 60)

def show_trace_tips():
    """Show tips for using LangSmith effectively"""
    console.print("\n[bold yellow]💡 LangSmith Tips:[/bold yellow]")
    
    tips = [
        "Use the 'Runs' tab to see all your test runs",
        "Click on a run to see the full trace tree",
        "Look for red nodes - those are errors",
        "Check token usage in the metadata",
        "Use tags to filter your tests",
        "Compare runs side-by-side",
        "Export traces for sharing"
    ]
    
    for tip in tips:
        console.print(f"  • {tip}")
    
    console.print("\n[cyan]Keyboard shortcuts in LangSmith:[/cyan]")
    console.print("  • Space: Expand/collapse nodes")
    console.print("  • /: Search within trace")
    console.print("  • ?: Show all shortcuts")

async def test_specific_agent_trace(agent_name: str):
    """Test a specific agent with detailed tracing"""
    messages = {
        "maria": "Hola, quisiera saber más información",
        "carlos": "Tengo una barbería y me interesa el servicio",
        "sofia": "Quiero agendar una cita, ya tengo el presupuesto"
    }
    
    message = messages.get(agent_name.lower())
    if not message:
        console.print(f"[red]Unknown agent: {agent_name}[/red]")
        return
    
    console.print(f"\n[bold]Testing {agent_name.title()} with tracing[/bold]")
    
    # Set specific project for this agent
    os.environ["LANGCHAIN_PROJECT"] = f"test-{agent_name.lower()}"
    
    await run_traced_test(message, f"{agent_name.lower()}-specific-test")

async def main():
    """Main interactive tracing menu"""
    console.print("[bold]🔍 LangSmith Local Tracing Tool[/bold]")
    console.print("See exactly what's happening inside your agents!\n")
    
    # Setup tracing
    if not setup_tracing():
        console.print("\n[red]Tracing not available without API key.[/red]")
        return
    
    while True:
        console.print("\n[bold cyan]Options:[/bold cyan]")
        console.print("1. Run single traced test")
        console.print("2. Run comprehensive trace suite")
        console.print("3. Test specific agent (Maria/Carlos/Sofia)")
        console.print("4. Show LangSmith tips")
        console.print("5. Open LangSmith dashboard")
        console.print("6. Exit")
        
        choice = input("\nSelect option: ")
        
        if choice == "1":
            message = input("Enter message to test: ")
            await run_traced_test(message)
            
        elif choice == "2":
            await run_comprehensive_trace()
            
        elif choice == "3":
            agent = input("Which agent? (maria/carlos/sofia): ")
            await test_specific_agent_trace(agent)
            
        elif choice == "4":
            show_trace_tips()
            
        elif choice == "5":
            console.print("[cyan]Opening LangSmith dashboard...[/cyan]")
            webbrowser.open("https://smith.langchain.com")
            
        elif choice == "6":
            console.print("\n[green]Goodbye![/green]")
            break
            
        else:
            console.print("[red]Invalid option![/red]")

if __name__ == "__main__":
    asyncio.run(main())
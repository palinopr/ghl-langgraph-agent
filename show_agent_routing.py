#!/usr/bin/env python3
"""
Visual Agent Routing Display
Shows exactly how lead scores map to agents
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, BarColumn, TextColumn
import time

console = Console()

def show_routing_table():
    """Display agent routing table"""
    console.print("\n[bold cyan]📊 Agent Routing by Lead Score[/bold cyan]")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Score", justify="center", style="yellow")
    table.add_column("Category", justify="center")
    table.add_column("Agent", justify="center", style="bold")
    table.add_column("Agent Role", style="dim")
    
    # Define routing
    for score in range(1, 11):
        if score <= 4:
            category = "[red]Cold[/red]"
            agent = "[red]Maria[/red]"
            role = "Initial contact, trust building"
        elif score <= 7:
            category = "[yellow]Warm[/yellow]"
            agent = "[yellow]Carlos[/yellow]"
            role = "Qualification, value proposition"
        else:
            category = "[green]Hot[/green]"
            agent = "[green]Sofia[/green]"
            role = "Appointment booking, closing"
        
        table.add_row(str(score), category, agent, role)
    
    console.print(table)

def show_visual_flow():
    """Show visual representation of the flow"""
    console.print("\n[bold magenta]🔄 Message Flow Visualization[/bold magenta]")
    
    flow = """
    📱 WhatsApp/SMS Message
            ↓
    🚪 Webhook Reception
            ↓
    🧠 Intelligence Layer
       • Extract patterns
       • Calculate score (1-10)
       • Detect business/budget
            ↓
    🎯 Supervisor Routes by Score:
    
    ┌─────────────┬─────────────┬─────────────┐
    │  Score 1-4  │  Score 5-7  │  Score 8-10 │
    │      ↓      │      ↓      │      ↓      │
    │   [red]MARIA[/red]    │  [yellow]CARLOS[/yellow]   │   [green]SOFIA[/green]    │
    │             │             │             │
    │ Cold Leads  │ Warm Leads  │  Hot Leads  │
    │             │             │             │
    │ • Greeting  │ • Qualify   │ • Book apt  │
    │ • Trust     │ • Value     │ • Close     │
    │ • Basic Q   │ • Benefits  │ • Confirm   │
    └─────────────┴─────────────┴─────────────┘
            ↓            ↓            ↓
    📤 Response sent back to customer
    """
    
    console.print(flow)

def simulate_routing():
    """Simulate routing decisions with animation"""
    console.print("\n[bold yellow]🎮 Live Routing Simulation[/bold yellow]")
    
    test_messages = [
        {"msg": "Hola", "business": None, "budget": None},
        {"msg": "Tengo un restaurante", "business": "restaurante", "budget": None},
        {"msg": "Mi presupuesto es $300", "business": "restaurante", "budget": "$300"},
        {"msg": "Quiero agendar una cita", "business": "restaurante", "budget": "$300"},
    ]
    
    for i, test in enumerate(test_messages):
        console.print(f"\n[cyan]Message {i+1}:[/cyan] \"{test['msg']}\"")
        
        # Simulate processing
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            transient=True,
        ) as progress:
            task = progress.add_task("Processing...", total=100)
            for _ in range(100):
                progress.update(task, advance=1)
                time.sleep(0.01)
        
        # Calculate score
        score = 1  # Base score
        if test["business"]:
            score += 2
        if test["budget"]:
            score += 3
        if "agendar" in test["msg"].lower():
            score += 3
        
        score = min(score, 10)
        
        # Show results
        console.print(f"  📊 Calculated Score: [bold]{score}/10[/bold]")
        console.print(f"  🏢 Business: {test['business'] or '[dim]Not detected[/dim]'}")
        console.print(f"  💰 Budget: {test['budget'] or '[dim]Not mentioned[/dim]'}")
        
        # Route to agent
        if score <= 4:
            console.print(f"  ➡️  Routing to: [bold red]MARIA[/bold red] (Cold Lead Handler)")
        elif score <= 7:
            console.print(f"  ➡️  Routing to: [bold yellow]CARLOS[/bold yellow] (Warm Lead Specialist)")
        else:
            console.print(f"  ➡️  Routing to: [bold green]SOFIA[/bold green] (Hot Lead Closer)")

def show_scoring_logic():
    """Display scoring logic details"""
    console.print("\n[bold blue]🧮 Lead Scoring Logic[/bold blue]")
    
    panel_content = """[bold]Base Scoring Rules:[/bold]

• Start with score: 1
• Has name: +1 point
• Has business type: +2 points
• Has specific goal: +1 point
• Has budget mentioned: +2 points
• Budget confirmed (sí/yes): +1 point
• Wants appointment: +2 points
• All info complete: +1 point

[bold]Score Ranges:[/bold]
• 1-4: Cold Lead → Maria
• 5-7: Warm Lead → Carlos
• 8-10: Hot Lead → Sofia

[bold]Important:[/bold]
• Scores never decrease
• Saved to GHL custom fields
• Deterministic (same input = same score)
"""
    
    console.print(Panel(panel_content, title="Scoring System", border_style="blue"))

def show_agent_personalities():
    """Show each agent's personality and approach"""
    console.print("\n[bold green]👥 Agent Personalities[/bold green]")
    
    agents = [
        {
            "name": "Maria",
            "emoji": "👋",
            "color": "red",
            "personality": "Friendly, welcoming, patient",
            "approach": "Build trust, gather basic info",
            "phrases": [
                "¡Hola! Soy María de WhatsApp Automation",
                "¿Me podrías compartir tu nombre?",
                "¿Qué tipo de negocio tienes?"
            ]
        },
        {
            "name": "Carlos",
            "emoji": "💼",
            "color": "yellow",
            "personality": "Professional, informative, value-focused",
            "approach": "Explain benefits, qualify budget",
            "phrases": [
                "Te explico cómo podemos ayudarte",
                "Automatizamos respuestas 24/7",
                "¿Cuál es tu presupuesto mensual?"
            ]
        },
        {
            "name": "Sofia",
            "emoji": "📅",
            "color": "green",
            "personality": "Efficient, closing-focused, helpful",
            "approach": "Book appointments, confirm details",
            "phrases": [
                "¡Perfecto! Vamos a agendar tu cita",
                "Tengo estos horarios disponibles",
                "Tu cita está confirmada para..."
            ]
        }
    ]
    
    for agent in agents:
        console.print(f"\n[bold {agent['color']}]{agent['emoji']} {agent['name']}[/bold {agent['color']}]")
        console.print(f"  Personality: {agent['personality']}")
        console.print(f"  Approach: {agent['approach']}")
        console.print("  Common phrases:")
        for phrase in agent['phrases']:
            console.print(f"    • \"{phrase}\"")

def main():
    """Main menu for routing visualization"""
    console.print("[bold]🗺️ Agent Routing Visualizer[/bold]")
    console.print("Understand exactly how messages are routed to agents\n")
    
    while True:
        console.print("\n[cyan]Options:[/cyan]")
        console.print("1. Show routing table")
        console.print("2. Show visual flow")
        console.print("3. Simulate routing decisions")
        console.print("4. Show scoring logic")
        console.print("5. Show agent personalities")
        console.print("6. Show everything")
        console.print("7. Exit")
        
        choice = input("\nSelect option: ")
        
        if choice == "1":
            show_routing_table()
        elif choice == "2":
            show_visual_flow()
        elif choice == "3":
            simulate_routing()
        elif choice == "4":
            show_scoring_logic()
        elif choice == "5":
            show_agent_personalities()
        elif choice == "6":
            show_routing_table()
            show_visual_flow()
            show_scoring_logic()
            show_agent_personalities()
        elif choice == "7":
            console.print("\n[green]Goodbye![/green]")
            break
        else:
            console.print("[red]Invalid option![/red]")

if __name__ == "__main__":
    main()